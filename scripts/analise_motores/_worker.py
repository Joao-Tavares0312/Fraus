"""Coleta real em processo sanitizado; nunca importa a fábrica nem treina.

API de laboratório para desempenho/qualidade:
``carregar_perfil(config)`` recebe caminhos de CÓPIAS contidas em ``workspace``
e devolve classificadores reais por ``texto/emocao/ironia`` (e ``fusor`` somente
com procedência). ``coletar_perfil(config)`` usa a mesma carga e devolve dados
JSON, bordas e cinco repetições; não grava snapshots nem muda o produto.
``config``: perfil, workspace, caminhos:{texto,emocao,ironia[,laya]}, corpus,
checkpoint e, opcionalmente, fusor/manifesto_fusor/fonte_confiavel_fusor/
sha256_manifesto_fusor. O chamador deve usar ``executar_isolado``: ambiente
allowlist/offline, threads e guardrail ficam antes dos imports pesados.

Manifesto confiável NÃO é um hash calculado nesta análise: o operador informa
fonte previamente confiada e checksum do manifesto obtido dessa fonte. Seu
JSON deve conter fonte, emitido_em (aware, anterior à análise), sha256 do fusor.
Essa declaração explícita do operador é a fronteira de confiança; não há
verificação criptográfica da identidade do emissor neste instrumento.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.analise_motores.comum import RAIZ, memoria, prazo_operacao, versoes
from scripts.gerenciar_artefatos import sha256

INICIO_ANALISE = datetime(2026, 10, 16, tzinfo=timezone.utc)
BORDAS = {
    'vazio': '',
    'emoji': '👩🏽\u200d💻🙂😡',
    'canonica': 'Que maravilha, mais uma vez vocês não resolveram meu problema.',
    'longo': 'Meu atendimento continua sem solução e preciso de ajuda. ' * 240,
}


def _finito(valor):
    if isinstance(valor, dict):
        for item in valor.values():
            _finito(item)
    elif isinstance(valor, (tuple, list)):
        for item in valor:
            _finito(item)
    elif isinstance(valor, float) and not math.isfinite(valor):
        raise ValueError('numero nao finito')


def _achatar(valor):
    if isinstance(valor, dict):
        return [n for chave in sorted(valor) for n in _achatar(valor[chave])]
    if isinstance(valor, (tuple, list)):
        return [n for item in valor for n in _achatar(item)]
    if isinstance(valor, (float, int)):
        return [float(valor)]
    raise ValueError('probabilidade invalida')


def resumir_repeticoes(repeticoes: list) -> dict:
    """Igualdade exata é independente de qualquer gate de tolerância."""
    if len(repeticoes) != 5:
        raise ValueError('sao exigidas cinco repeticoes')
    _finito(repeticoes)
    referencia = _achatar(repeticoes[0])
    outras = [_achatar(item) for item in repeticoes]
    if any(len(item) != len(referencia) for item in outras):
        raise ValueError('alinhamento de repeticoes')
    delta = max((abs(a - b) for item in outras for a, b in zip(referencia, item)), default=None)
    return {'n': 5, 'igualdade_exata': all(item == repeticoes[0] for item in repeticoes),
            'max_delta': delta, 'amostras': repeticoes}


class PrevisoesAlinhadas:
    """Uma passada real reutilizada; lote e índices não podem ser permutados."""
    def __init__(self, textos: list[str], previsoes: list[list[float]]) -> None:
        if len(textos) != len(previsoes):
            raise ValueError('alinhamento de previsoes')
        _finito(previsoes)
        self._textos = tuple(textos)
        self._previsoes = previsoes

    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        if tuple(textos) != self._textos:
            raise ValueError('alinhamento de textos e indices')
        return self._previsoes


def carregar_corpus(caminho: Path) -> list[dict]:
    from fraus.modelos import Conversa

    registros, ids = [], set()
    for linha in Path(caminho).read_text(encoding='utf-8').splitlines():
        registro = json.loads(linha)
        conversa = Conversa.model_validate(registro['conversa'])
        if registro['id'] != conversa.id or conversa.id in ids:
            raise ValueError('alinhamento de ids do corpus')
        ids.add(conversa.id)
        registros.append({**registro, 'conversa': conversa})
    if not registros:
        raise ValueError('corpus vazio')
    return registros


def _caminho_copiado(caminho, workspace: Path) -> Path:
    caminho = Path(caminho).absolute()
    if any(p.is_symlink() for p in (caminho, *caminho.parents)):
        raise ValueError('symlink recusado')
    resolvido = caminho.resolve()
    if not resolvido.is_relative_to(workspace) or resolvido.is_relative_to(RAIZ):
        raise ValueError('modelo deve estar em copia externa no workspace')
    if resolvido.is_dir() and any(p.is_symlink() for p in resolvido.rglob('*')):
        raise ValueError('symlink recusado')
    return resolvido


def carregar_fusor_confiavel(config: dict):
    """Sem as três evidências explícitas, nem chama joblib/Fusor.carregar."""
    chaves = ('fusor', 'manifesto_fusor', 'fonte_confiavel_fusor', 'sha256_manifesto_fusor')
    if not all(config.get(chave) for chave in chaves):
        return None
    if not config.get('workspace'):
        return None
    workspace = Path(config['workspace']).resolve()
    caminho = _caminho_copiado(config['fusor'], workspace)
    manifesto = _caminho_copiado(config['manifesto_fusor'], workspace)
    if not caminho.is_file() or not manifesto.is_file():
        return None
    if sha256(manifesto) != config['sha256_manifesto_fusor']:
        return None
    dados = json.loads(manifesto.read_text(encoding='utf-8'))
    try:
        emitido = datetime.fromisoformat(dados['emitido_em'])
        if emitido.tzinfo is None or emitido >= INICIO_ANALISE:
            return None
    except (ValueError, KeyError, TypeError):
        return None
    if dados.get('fonte') != config['fonte_confiavel_fusor'] or dados.get('sha256') != sha256(caminho):
        return None
    from fraus.fusor import Fusor
    return Fusor.carregar(caminho)


def carregar_perfil(config: dict) -> dict:
    """Carrega apenas adaptadores reais, CPU/offline, sobre cópias externas.

    Não mede a fábrica da API: especialmente, Laya aqui é um perfil direto,
    não a carga transitória de BERT-ironia da fábrica (fase desempenho).
    ``somente_cabecas`` permite smoke de uma cabeça sem fabricar motor completo.
    """
    workspace = Path(config['workspace']).resolve()
    if workspace.is_relative_to(RAIZ) or workspace == RAIZ:
        raise ValueError('workspace interno recusado')
    if os.environ.get('HF_HUB_OFFLINE') != '1' or os.environ.get('TRANSFORMERS_OFFLINE') != '1':
        raise ValueError('carga exige subprocesso offline')
    perfil = config['perfil']
    if perfil not in {'torch', 'onnx-fp32', 'onnx-int8', 'laya-onnx'}:
        raise ValueError('perfil desconhecido')
    caminhos = {nome: _caminho_copiado(valor, workspace) for nome, valor in config['caminhos'].items()}
    if perfil == 'torch':
        from fraus.sinais.texto import ClassificadorTexto
        from fraus.sinais.emocao import ClassificadorEmocao
        from fraus.sinais.ironia import ClassificadorIronia
        classes = {'texto': ClassificadorTexto, 'emocao': ClassificadorEmocao, 'ironia': ClassificadorIronia}
        for caminho in caminhos.values():
            if not (caminho / 'model.safetensors').is_file():
                raise ValueError('somente pesos safetensors locais sao permitidos')
    else:
        from fraus.sinais.onnx import ClassificadorOnnx
        classes = {nome: ClassificadorOnnx for nome in ('texto', 'emocao', 'ironia')}
    carregados = {}
    eventos = []
    for nome in ('texto', 'emocao', 'ironia'):
        if nome not in caminhos:
            continue
        inicio = time.perf_counter()
        with prazo_operacao():
            if nome == 'ironia' and perfil == 'laya-onnx':
                from fraus.sinais.ironia_laya import ClassificadorIroniaLayaOnnx
                carregados[nome] = ClassificadorIroniaLayaOnnx(diretorio=caminhos[nome])
            else:
                carregados[nome] = classes[nome](caminhos[nome])
        eventos.append({'cabeca': nome, 'duracao_s': time.perf_counter() - inicio, 'memoria': memoria()})
    fusor_config = dict(config)
    for chave in ('fusor', 'manifesto_fusor'):
        if fusor_config.get(chave):
            fusor_config[chave] = str(_caminho_copiado(fusor_config[chave], workspace))
    carregados['fusor'] = carregar_fusor_confiavel(fusor_config)
    carregados['eventos_carga'] = eventos
    return carregados


def _prever(cabecas: dict, textos: list[str]) -> dict:
    dimensoes = {'texto': 3, 'emocao': 7, 'ironia': 2}
    saida = {}
    for nome in dimensoes:
        if nome not in cabecas:
            continue
        inicio = time.perf_counter()
        with prazo_operacao():
            previsoes = cabecas[nome].prever_mensagens(textos)
        PrevisoesAlinhadas(textos, previsoes)
        if any(len(linha) != dimensoes[nome] or any(p < 0 or p > 1 for p in linha)
               or not math.isclose(sum(linha), 1., abs_tol=1e-5) for linha in previsoes):
            raise ValueError('alinhamento das classes ou probabilidades invalidas')
        saida[nome] = {'probabilidades': previsoes, 'duracao_s': time.perf_counter() - inicio}
    return saida


def _cinco(cabecas: dict, textos: list[str]) -> tuple[dict, dict]:
    passadas = [_prever(cabecas, textos) for _ in range(5)]
    probs = [{nome: leitura['probabilidades'] for nome, leitura in passada.items()} for passada in passadas]
    repeticoes = resumir_repeticoes(probs)
    repeticoes['tempos_s'] = [{nome: leitura['duracao_s'] for nome, leitura in passada.items()} for passada in passadas]
    return probs[0], repeticoes


def _salvar_parcial(config, bordas, casos, eventos):
    if not config.get('saida'):
        return
    workspace = Path(config['workspace']).resolve()
    caminho = _caminho_copiado(config['saida'], workspace).with_suffix('.parcial.json')
    dados = {'schema_version': 1, 'perfil': config['perfil'], 'checkpoint': config.get('checkpoint'),
             'status': 'nao_verificado', 'motivo': 'coleta_interrompida_ou_em_curso',
             'motor_completo': False, 'casos': casos, 'bordas': bordas, 'eventos_carga': eventos}
    temporario = caminho.with_suffix('.tmp')
    temporario.write_text(json.dumps(dados, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    temporario.replace(caminho)


def coletar_perfil(config: dict) -> dict:
    """Retorna probabilidades reais e features sem depender de ouro pronto.

    Sem procedência do fusor: continua cabeças/features/vetor, deixa score,
    nota/categoria nulos e marca motor não verificado. Curadoria é vazia LOCAL,
    nunca representa curadoria desconhecida de produção.
    """
    inicio = time.perf_counter()
    cabecas = carregar_perfil(config)
    if not any(nome in cabecas for nome in ('texto', 'emocao', 'ironia')):
        raise ValueError('nenhuma cabeca disponivel')
    fusor = cabecas.get('fusor')
    completo = fusor is not None and all(nome in cabecas for nome in ('texto', 'emocao', 'ironia'))
    bordas = []
    for identificador, texto in BORDAS.items():
        probs, repeticoes = _cinco(cabecas, [texto])
        bordas.append({'id': identificador, 'probabilidades': probs, 'repeticoes': repeticoes,
                       'caracteres': len(texto), 'palavras': len(texto.split())})
        _salvar_parcial(config, bordas, [], cabecas.get('eventos_carga', []))
    corpus = Path(config['corpus']) if config.get('corpus') else None
    registros = carregar_corpus(corpus) if corpus and corpus.is_file() else []
    casos = []
    from fraus.fusor import NOMES_FEATURES, montar_features, vetorizar
    from fraus.indicadores import FAIXAS_NPS, categoria_nps, nota_0_10
    from fraus.motor import Motor
    for registro in registros:
        conversa = registro['conversa']
        textos = [mensagem.texto for mensagem in conversa.mensagens_cliente]
        indices = [i for i, mensagem in enumerate(conversa.mensagens) if mensagem.autor == 'cliente']
        probs, repeticoes = _cinco(cabecas, textos) if textos else (None, None)
        amostras_motor = []
        atribuicao = None
        for numero in range(5):
            previsoes = repeticoes['amostras'][numero] if repeticoes else {nome: [] for nome in ('texto', 'emocao', 'ironia') if nome in cabecas}
            adaptadores = {nome: PrevisoesAlinhadas(textos, valores) for nome, valores in previsoes.items()}
            features = vetor = score = nota = categoria = probs_fusor = classe = None
            classes_fusor = None
            if conversa.tem_sinal_cliente and all(nome in adaptadores for nome in ('texto', 'emocao')):
                features_dict = montar_features(conversa, adaptadores['texto'], adaptadores['emocao'], curadoria=None)
                features = {nome: float(features_dict[nome]) for nome in NOMES_FEATURES}
                vetor = vetorizar(features)
            if completo:
                motor = Motor(adaptadores['texto'], fusor, adaptadores['emocao'], adaptadores['ironia'])
                score = motor.pontuar_conversa(conversa, curadoria=None)
                if numero == 0:
                    atribuicao = motor.atribuir_conversa(conversa, curadoria=None)
                if score is not None:
                    from scripts._confianca_comum import probabilidades
                    probs_fusor = probabilidades(fusor, features)
                    classes_fusor = [int(c) for c in fusor._pipeline.named_steps['modelo'].classes_]
                    classe = max(classes_fusor, key=lambda c: probs_fusor[c])
                    nota = nota_0_10(score)
                    categoria = categoria_nps(score, FAIXAS_NPS)
            amostras_motor.append({'features': features, 'vetor': vetor,
                                   'probabilidades_fusor': probs_fusor, 'classes_fusor': classes_fusor,
                                   'classe': classe, 'score': score, 'nota': nota, 'categoria': categoria})
        numericas = [{chave: valor for chave, valor in amostra.items()
                      if chave in {'features', 'vetor', 'probabilidades_fusor', 'score'} and valor is not None}
                     for amostra in amostras_motor]
        determinismo = resumir_repeticoes(numericas)
        determinismo['igualdade_exata'] = all(amostra == amostras_motor[0] for amostra in amostras_motor)
        determinismo['amostras'] = amostras_motor
        casos.append({'id': registro['id'], 'grupo': registro.get('grupo'), 'par_id': registro.get('par_id'),
                      'indices_cliente': indices, 'probabilidades': probs, 'repeticoes': repeticoes,
                      'classes_cabecas': {nome: [max(range(len(linha)), key=linha.__getitem__) for linha in linhas]
                                         for nome, linhas in probs.items()} if probs else None,
                      **amostras_motor[0], 'repeticoes_motor': determinismo, 'atribuicao': atribuicao,
                      'motivo_sem_sinal': conversa.motivo_sem_sinal})
        _salvar_parcial(config, bordas, casos, cabecas.get('eventos_carga', []))
    dados = {'schema_version': 1, 'perfil': config['perfil'], 'checkpoint': config.get('checkpoint'),
             'motor_completo': completo, 'status': 'medido' if completo and registros else 'nao_verificado',
             'motivo': None if completo and registros else ('corpus_ausente' if not registros else 'fusor_ou_cabeca_sem_prerequisito'),
             'curadoria': 'vazia_local_nao_representa_producao', 'casos': casos, 'bordas': bordas,
             'eventos_carga': cabecas.get('eventos_carga', []), 'duracao_s': time.perf_counter() - inicio,
             'versoes': versoes(['torch', 'transformers', 'onnxruntime', 'laya', 'numpy', 'scikit-learn']),
             'memoria_final': memoria(), 'hashes': config.get('hashes', {})}
    _finito(dados)
    return dados


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    args = parser.parse_args(argv)
    saida = None
    try:
        arquivo = Path(args.config).resolve()
        config = json.loads(arquivo.read_text(encoding='utf-8'))
        candidato_saida = Path(config['saida'])
        base = Path(config.get('workspace', arquivo.parent)).resolve()
        saida = _caminho_copiado(candidato_saida, base)
        with open(os.devnull, 'w') as silencio, contextlib.redirect_stdout(silencio), contextlib.redirect_stderr(silencio):
            dados = coletar_perfil(config)
        codigo = 0 if dados['status'] == 'medido' else 2
    except Exception as erro:
        categoria = {'FusorIncompativelError': 'fusor_incompativel',
                     'ModeloAusenteError': 'modelo_ilegivel',
                     'ModeloOnnxAusenteError': 'modelo_ilegivel',
                     'ModuleNotFoundError': 'dependencia_ausente'}.get(type(erro).__name__, 'carga_ou_inferencia')
        dados = {'schema_version': 1, 'status': 'erro', 'categoria_erro': categoria,
                 'diagnostico': 'Carga ou inferencia local recusada; nenhum fallback foi usado.',
                 'motor_completo': False, 'casos': [], 'bordas': []}
        codigo = 1
    if saida is not None:
        saida.write_text(json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'status': dados['status'], 'categoria_erro': dados.get('categoria_erro')}))
    return codigo


if __name__ == '__main__':
    raise SystemExit(main())
