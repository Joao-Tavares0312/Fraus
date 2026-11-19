"""Worker privado: cabeças reais, hooks locais e checkpoint antes de cada passada."""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager
import importlib
import json
from pathlib import Path
import resource
import time
from unittest.mock import patch

from .comum import memoria, prazo_operacao
from ._worker import carregar_perfil, carregar_fusor_confiavel, _caminho_copiado
from .desempenho import resumir_amostras


def medir_repeticoes(operacao, *, warm, aquecimentos, checkpoint=lambda dados: None) -> dict:
    dados = {'status': 'medido', 'motivo': None, 'amostras': [], 'aquecimentos': [],
             'em_andamento': None, 'resumo': resumir_amostras([]), 'warm_solicitado': warm}
    for fase, quantidade in (('aquecimento', aquecimentos), ('warm', warm)):
        for indice in range(quantidade):
            dados['em_andamento'] = {'fase': fase, 'indice': indice}
            checkpoint(dados)
            inicio, cpu = time.perf_counter(), time.process_time()
            try:
                detalhes = operacao()
                amostra = {'status': 'sucesso', 'categoria': None}
                if isinstance(detalhes, dict):
                    amostra['contadores'] = detalhes
            except TimeoutError:
                amostra = {'status': 'timeout', 'categoria': 'timeout_operacao'}
            except Exception:
                amostra = {'status': 'erro', 'categoria': 'operacao_recusada'}
            amostra.update(duracao_s=time.perf_counter() - inicio, cpu_s=time.process_time() - cpu)
            dados['aquecimentos' if fase == 'aquecimento' else 'amostras'].append(amostra)
            dados['em_andamento'] = None
            dados['resumo'] = resumir_amostras(dados['amostras'])
            if any(a['status'] != 'sucesso' for a in dados['aquecimentos'] + dados['amostras']):
                dados.update(status='nao_verificado', motivo='operacoes_com_erro_ou_timeout')
            checkpoint(dados)
    return dados


def texto_sintetico(tokenizador, alvo: int) -> tuple[str, dict]:
    """Autoral repetível; alvo aproximado, contagens reais incluem especiais."""
    def contar(texto):
        return len(tokenizador(texto, truncation=False, add_special_tokens=True)['input_ids'])
    inferior, superior = 1, alvo * 2
    candidatos = []
    while inferior <= superior:
        meio = (inferior + superior) // 2
        texto = ' '.join(['atendimento'] * meio)
        n = contar(texto)
        candidatos.append((abs(n - alvo), meio, texto, n))
        if n < alvo:
            inferior = meio + 1
        elif n > alvo:
            superior = meio - 1
        else:
            break
    _, _, texto, n = min(candidatos)
    retidos = len(tokenizador(texto, truncation=True, max_length=192, add_special_tokens=True)['input_ids'])
    return texto, {'fonte': 'sintetico_autoral_repeticao_da_palavra_atendimento', 'tokens_alvo': alvo,
                   'tokens_sem_truncar': n, 'tokens_retidos': retidos, 'truncado': retidos < n,
                   'max_length_bert': 192, 'inclui_tokens_especiais': True,
                   'tokenizador_classe': type(tokenizador).__name__, 'padding': 'maior_mensagem_do_lote',
                   'mensagens_identicas_no_lote': True}


class _SessaoContada:
    def __init__(self, sessao, contador):
        self.sessao, self.contador = sessao, contador
    def __getattr__(self, nome):
        return getattr(self.sessao, nome)
    def run(self, *args, **kwargs):
        self.contador.forwards += 1
        with prazo_operacao():
            return self.sessao.run(*args, **kwargs)


class ContadorCabeca:
    """Conta forwards de verdade; prever_mensagens é lote, não forward presumido."""
    def __init__(self, cabeca):
        self.cabeca = cabeca
        self.forwards = 0
        self.lotes = []
        self.tempos = []
        self.handles = []
        self.sessoes = []
        modelo = getattr(cabeca, '_modelo', None)
        self.observavel = False
        if hasattr(modelo, 'register_forward_pre_hook'):
            self.handles.append(modelo.register_forward_pre_hook(self._forward))
            self.observavel = True
        sessao_wrapper = getattr(cabeca, '_sessao', None)
        self.alvos = [cabeca]
        if sessao_wrapper is not None and not hasattr(sessao_wrapper, 'run'):
            self.alvos.append(sessao_wrapper)
        agente = getattr(cabeca, '_agente', None)
        if agente is not None and all(agente is not alvo for alvo in self.alvos):
            self.alvos.append(agente)
        for alvo in self.alvos:
            # SDKs usam session/_session; não infere contagem por número de textos.
            for nome in ('_sessao', 'session', '_session', 'sessao'):
                sessao = getattr(alvo, nome, None)
                if sessao is not None and hasattr(sessao, 'run'):
                    self.sessoes.append((alvo, nome, sessao))
                    setattr(alvo, nome, _SessaoContada(sessao, self))
                    self.observavel = True
    @property
    def _tokenizador(self):
        for alvo in self.alvos:
            for nome in ('_tokenizador', 'tokenizer', '_tokenizer'):
                tokenizador = getattr(alvo, nome, None)
                if tokenizador is not None:
                    return tokenizador
        return None
    def _forward(self, modelo, argumentos):
        self.forwards += 1
    def __getattr__(self, nome):
        return getattr(self.cabeca, nome)
    def prever_mensagens(self, textos):
        self.lotes.append(len(textos))
        inicio, cpu = time.perf_counter(), time.process_time()
        try:
            with prazo_operacao():
                return self.cabeca.prever_mensagens(textos)
        finally:
            self.tempos.append({'duracao_s': time.perf_counter() - inicio, 'cpu_s': time.process_time() - cpu})
    def snapshot(self):
        return {'forwards': self.forwards if self.observavel else None, 'lotes': list(self.lotes),
                'chamadas': len(self.lotes), 'duracao_s': sum(t['duracao_s'] for t in self.tempos),
                'cpu_s': sum(t['cpu_s'] for t in self.tempos),
                'motivo_forward_nulo': None if self.observavel else 'sessao_sdk_nao_observavel'}
    def fechar(self):
        for handle in self.handles:
            handle.remove()
        for alvo, nome, sessao in self.sessoes:
            setattr(alvo, nome, sessao)


class ContadorFusor:
    def __init__(self, fusor):
        self.fusor, self.eventos = fusor, []
    def __getattr__(self, nome):
        atributo = getattr(self.fusor, nome)
        if not callable(atributo):
            return atributo
        def executar(*args, **kwargs):
            inicio, cpu = time.perf_counter(), time.process_time()
            try:
                with prazo_operacao():
                    return atributo(*args, **kwargs)
            finally:
                self.eventos.append({'metodo': nome, 'duracao_s': time.perf_counter() - inicio,
                                     'cpu_s': time.process_time() - cpu})
        return executar


class EventosCarga:
    def __init__(self, checkpoint):
        self.inicio = time.perf_counter()
        self.eventos, self.pilha = [], []
        self.checkpoint = checkpoint
        self.cabeca = None
    @contextmanager
    def etapa(self, nome):
        inicio, cpu = time.perf_counter(), time.process_time()
        registro = {'evento': nome, 'cabeca': self.cabeca, 'inicio_s': inicio - self.inicio,
                    'fim_s': None, 'inclusivo_s': None, 'exclusivo_s': None, 'cpu_s': None}
        self.eventos.append(registro)
        self.checkpoint()
        quadro = {'filhos': 0.}
        self.pilha.append(quadro)
        try:
            yield
        finally:
            fim = time.perf_counter()
            duracao = fim - inicio
            self.pilha.pop()
            if self.pilha:
                self.pilha[-1]['filhos'] += duracao
            registro.update(fim_s=fim - self.inicio, inclusivo_s=duracao,
                            exclusivo_s=duracao - quadro['filhos'], cpu_s=time.process_time() - cpu,
                            memoria=memoria())
            self.checkpoint()
    def decorar(self, nome, original):
        def medido(*args, **kwargs):
            with self.etapa(nome):
                with prazo_operacao():
                    return original(*args, **kwargs)
        return medido


@contextmanager
def instrumentar_carga(eventos, perfil):
    """Hooks de laboratório nos construtores, restaurados antes de inferir."""
    with ExitStack() as pilha:
        with eventos.etapa('import_backend'):
            with prazo_operacao():
                transformers = importlib.import_module('transformers')
                importlib.import_module('torch' if perfil == 'torch' else 'onnxruntime')
        classes = [(transformers.AutoTokenizer, 'tokenizador')]
        if perfil == 'torch':
            classes.append((transformers.AutoModelForSequenceClassification, 'leitura_carga_modelo'))
        for classe, nome in classes:
            original = classe.from_pretrained
            pilha.enter_context(patch.object(classe, 'from_pretrained', side_effect=eventos.decorar(nome, original)))
        if perfil != 'torch':
            ort = importlib.import_module('onnxruntime')
            pilha.enter_context(patch.object(ort, 'InferenceSession', side_effect=eventos.decorar('InferenceSession', ort.InferenceSession)))
        yield


def _conversa(texto, n):
    from datetime import datetime, timedelta, timezone
    from fraus.modelos import Conversa, Mensagem
    inicio = datetime(2026, 10, 16, tzinfo=timezone.utc)
    mensagens = []
    for i in range(n):
        mensagens.extend([Mensagem(autor='cliente', texto=texto, enviada_em=inicio + timedelta(seconds=i * 30)),
                          Mensagem(autor='bot', texto='Recebi sua solicitação.', enviada_em=inicio + timedelta(seconds=i * 30 + 10))])
    return Conversa(id='laboratorio-desempenho', canal='laboratorio', iniciada_em=inicio,
                    encerrada_em=inicio + timedelta(seconds=n * 30), mensagens=mensagens)


def coletar(config: dict) -> dict:
    dados = {'status': 'medido', 'motivo': None, 'amostras': [], 'aquecimentos': [],
             'resumo': resumir_amostras([]), 'em_andamento': None, 'eventos_carga': [],
             'baseline': memoria(), 'processo_frio_nao_disco_frio': True,
             'metricas_motor_por_soma_cabecas': None}
    def salvar():
        if config.get('saida'):
            workspace = Path(config['workspace']).resolve()
            alvo = _caminho_copiado(config['saida'], workspace)
            temporario = alvo.with_suffix('.tmp')
            temporario.write_text(json.dumps(dados, ensure_ascii=False, allow_nan=False), encoding='utf-8')
            temporario.replace(alvo)
    salvar()
    celula = config.get('celula', {})
    frio = config.get('modo') == 'cold'
    motor_celula = celula.get('tipo') == 'motor'
    fusor = None
    if motor_celula:
        with prazo_operacao():
            fusor = carregar_fusor_confiavel(config)
        if fusor is None:
            dados.update(status='nao_verificado', motivo='fusor_sem_procedencia')
            salvar()
            return dados
        if not all(c in config.get('caminhos', {}) for c in ('texto', 'emocao', 'ironia')):
            dados.update(status='nao_verificado', motivo='cabecas_ausentes')
            salvar()
            return dados
    eventos = EventosCarga(salvar)
    dados['eventos_carga'] = eventos.eventos
    nomes = list(config['caminhos']) if frio or motor_celula else [celula['cabeca']]
    if not nomes:
        dados.update(status='nao_verificado', motivo='cabecas_ausentes')
        salvar()
        return dados
    cabecas = {}
    # Fusor já validado acima: nunca recarregar o pickle uma vez por cabeça.
    sem_fusor = {k: v for k, v in config.items() if k not in ('fusor', 'manifesto_fusor', 'fonte_confiavel_fusor', 'sha256_manifesto_fusor')}
    with instrumentar_carga(eventos, config['perfil']):
        for nome in nomes:
            eventos.cabeca = nome
            with eventos.etapa('cabeca_pronta'):
                with prazo_operacao():
                    carregado = carregar_perfil({**sem_fusor, 'caminhos': {nome: config['caminhos'][nome]}})
                cabecas[nome] = ContadorCabeca(carregado[nome])
    eventos.cabeca = None
    dados['todos_carregados'] = memoria()
    dados['transitorio_bert_ironia'] = {'status': 'nao_verificado',
                                         'motivo': 'direto_nao_e_fabrica_api_ver_worker_api' if config['perfil'] == 'laya-onnx' else 'perfil_sem_laya'}
    try:
        if frio:
            for nome, cabeca in cabecas.items():
                eventos.cabeca = nome
                with eventos.etapa('primeira_inferencia'):
                    cabeca.prever_mensagens(['Meu atendimento não resolveu o problema.'])
            dados['contadores'] = {n: c.snapshot() for n, c in cabecas.items()}
            dados['provedor_pronto'] = None
            dados['motivo_provedor'] = 'carga_direta_cabecas_nao_provedor_api'
        else:
            tokenizador = getattr(cabecas[nomes[0]], '_tokenizador', None)
            if tokenizador is None:
                # Laya aplica cabeçalho/pergunta no SDK: não inventar tokens BERT.
                dados.update(status='nao_verificado', motivo='tokenizador_sdk_nao_observavel')
                salvar()
                return dados
            texto, tokens = texto_sintetico(tokenizador, celula['tokens_alvo'])
            dados['tokenizacao'] = tokens
            dados['tokenizacao_por_cabeca'] = {}
            for nome, cabeca in cabecas.items():
                tok = getattr(cabeca, '_tokenizador', None)
                if tok is not None:
                    dados['tokenizacao_por_cabeca'][nome] = {
                        'tokens_sem_truncar': len(tok(texto, truncation=False)['input_ids']),
                        'tokens_retidos': len(tok(texto, truncation=True, max_length=192)['input_ids'])}
            fusor_contado = ContadorFusor(fusor) if fusor else None
            if motor_celula:
                from fraus.motor import Motor
                motor = Motor(cabecas['texto'], fusor_contado, cabecas['emocao'], cabecas['ironia'])
                conversa = _conversa(texto, celula['falas'])
                chamada = getattr(motor, celula['operacao'] + '_conversa')
                def executar():
                    chamada(conversa)
            else:
                def executar():
                    previsoes = cabecas[celula['cabeca']].prever_mensagens([texto] * celula['falas'])
                    if len(previsoes) != celula['falas']:
                        raise ValueError('alinhamento_de_lote')
            def operacao():
                for cabeca in cabecas.values():
                    cabeca.lotes.clear()
                    cabeca.tempos.clear()
                    cabeca.forwards = 0
                if fusor_contado:
                    fusor_contado.eventos.clear()
                executar()
                return {'cabecas': {n: c.snapshot() for n, c in cabecas.items()},
                        'fusor': list(fusor_contado.eventos) if fusor_contado else None}
            def parcial(amostras):
                dados.update(amostras)
                dados['memoria_ultima'] = memoria()
                if (len(amostras['aquecimentos']) == config['aquecimentos']
                        and not amostras['amostras'] and amostras['em_andamento'] is None):
                    dados['apos_aquecer'] = dados['memoria_ultima']
                salvar()
            dados.update(medir_repeticoes(operacao, warm=config['warm'], aquecimentos=config['aquecimentos'], checkpoint=parcial))
            dados['apos_aquecer_e_medir'] = memoria()
        dados['ru_maxrss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        dados['cpu_processo_s'] = time.process_time()
        salvar()
        return dados
    finally:
        for cabeca in cabecas.values():
            cabeca.fechar()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    args = parser.parse_args(argv)
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    try:
        dados = coletar(config)
    except Exception:
        alvo = _caminho_copiado(config['saida'], Path(config['workspace']).resolve())
        dados = json.loads(alvo.read_text(encoding='utf-8')) if alvo.is_file() else {}
        dados.update(status='erro', motivo='carga_ou_coleta_recusada')
        alvo.write_text(json.dumps(dados, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        return 1
    return 0 if dados['status'] == 'medido' else 2


if __name__ == '__main__':
    raise SystemExit(main())
