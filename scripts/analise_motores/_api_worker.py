"""API de laboratório local, sem fábrica padrão de app nem credenciais.

CLI: ``python -m scripts.analise_motores._api_worker --config PATH``.
Config JSON: workspace externo; perfil torch/onnx-fp32/onnx-int8;
caminhos de CÓPIAS {texto,emocao,ironia}; saida externa;
cold=5, warm=100, aquecimentos=3; evidências opcionais de fusor iguais às de
``_worker``: fusor, manifesto_fusor, fonte_confiavel_fusor e
sha256_manifesto_fusor. Não aceita URL/host/porta/banco do operador.

``coletar_api(config) -> dict`` cria processos novos por célula, um Uvicorn
worker em 127.0.0.1/porta efêmera e SQLite exclusivo por processo. O cliente
fica em outro processo; recursos nunca confundem RSS de cliente e servidor.
Sem procedência não desserializa fusor nem chama construir_motor_padrao;
mede somente prontidão e recusa de orçamento reais, sem motor substituto.
Bancos de laboratório são preservados, inclusive após timeout; nunca apagamos
um banco enquanto uma thread de repontuação ainda pode estar usando-o.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import logging
import math
import multiprocessing
import os
import resource
import socket
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.analise_motores.comum import (
    RAIZ, ambiente_isolado, cliente_loopback, memoria, prazo_operacao,
)
from scripts.analise_motores._worker import INICIO_ANALISE, _caminho_copiado
from scripts.gerenciar_artefatos import sha256


class PreRequisitoAusente(RuntimeError):
    """A fábrica real não pode atravessar a fronteira de procedência."""


def validar_config(config: dict) -> dict:
    if any(chave in config for chave in ('url', 'base_url', 'host', 'porta', 'port', 'banco', 'database_url')):
        raise ValueError('destino HTTP e banco sao exclusivos do runner')
    workspace = Path(config['workspace']).absolute()
    if any(p.is_symlink() for p in (workspace, *workspace.parents)):
        raise ValueError('symlink recusado')
    workspace = workspace.resolve()
    if workspace.is_relative_to(RAIZ) or RAIZ.is_relative_to(workspace):
        raise ValueError('workspace externo obrigatorio')
    if config['perfil'] not in {'torch', 'onnx-fp32', 'onnx-int8'}:
        raise ValueError('perfil desconhecido')
    saida = _caminho_copiado(config['saida'], workspace)
    caminhos = {nome: str(_caminho_copiado(valor, workspace))
                for nome, valor in config.get('caminhos', {}).items()}
    validada = {**config, 'workspace': str(workspace), 'saida': str(saida), 'caminhos': caminhos}
    for chave in ('fusor', 'manifesto_fusor'):
        if config.get(chave):
            validada[chave] = str(_caminho_copiado(config[chave], workspace))
    protegidos = [Path(p) for p in caminhos.values()]
    protegidos.extend(Path(validada[chave]) for chave in ('fusor', 'manifesto_fusor') if validada.get(chave))
    if any(saida == p or saida.is_relative_to(p) for p in protegidos):
        raise ValueError('saida nao pode sobrescrever artefatos copiados')
    for chave, padrao, minimo in (('cold', 5, 1), ('warm', 100, 1), ('aquecimentos', 3, 0)):
        valor = config.get(chave, padrao)
        if not isinstance(valor, int) or isinstance(valor, bool) or valor < minimo:
            raise ValueError('quantidade invalida')
        validada[chave] = valor
    return validada


def _procedencia_validada(config: dict) -> bool:
    """Mesma fronteira do coletor de paridade, mas SEM desserialização."""
    chaves = ('fusor', 'manifesto_fusor', 'fonte_confiavel_fusor', 'sha256_manifesto_fusor')
    if not all(config.get(chave) for chave in chaves):
        return False
    try:
        ws = Path(config['workspace']).resolve()
        fusor = _caminho_copiado(config['fusor'], ws)
        manifesto = _caminho_copiado(config['manifesto_fusor'], ws)
        if not fusor.is_file() or not manifesto.is_file() or sha256(manifesto) != config['sha256_manifesto_fusor']:
            return False
        dados = json.loads(manifesto.read_text(encoding='utf-8'))
        emitido = datetime.fromisoformat(dados['emitido_em'])
        return bool(emitido.tzinfo is not None and emitido < INICIO_ANALISE
                    and dados.get('fonte') == config['fonte_confiavel_fusor']
                    and dados.get('sha256') == sha256(fusor))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def _impedimento(config: dict) -> str | None:
    if not _procedencia_validada(config):
        return 'fusor_sem_procedencia'
    extensao = 'model.safetensors' if config['perfil'] == 'torch' else 'model.onnx'
    for nome in ('texto', 'emocao', 'ironia'):
        if nome not in config['caminhos'] or not (Path(config['caminhos'][nome]) / extensao).is_file():
            return 'cabecas_ausentes'
    return None


def fabrica_guardada(config: dict, construir):
    def carregar():
        motivo = _impedimento(config)
        if motivo:
            raise PreRequisitoAusente(motivo)
        with prazo_operacao():
            return construir()
    return carregar


def csv_sintetico(n: int, *, conversas: int = 1) -> str:
    if n < 1 or conversas < 1:
        raise ValueError('quantidade invalida')
    texto = io.StringIO(newline='')
    gravador = csv.writer(texto, lineterminator='\n')
    gravador.writerow(('conversa_id', 'canal', 'autor', 'texto', 'enviada_em', 'escalou_para_humano'))
    instante = datetime(2026, 10, 1, 10, tzinfo=timezone.utc)
    for conversa in range(conversas):
        for indice in range(n):
            gravador.writerow((f'laboratorio-{conversa:03d}', 'chat', 'cliente',
                               'Cobranca duplicada e problema sem solucao preciso do estorno.',
                               (instante + timedelta(seconds=indice * 30)).isoformat(), 'false'))
    return texto.getvalue()


def ler_server_timing(cabecalho: str) -> dict:
    metricas = {}
    permitidas = {'total', 'consulta_db', 'espera_pool', 'carga_modelo', 'inferencia'}
    for item in cabecalho.split(','):
        partes = item.strip().split(';')
        if partes[0] not in permitidas:
            continue
        for parametro in partes[1:]:
            if parametro.strip().startswith('dur='):
                try:
                    numero = float(parametro.strip()[4:])
                    if math.isfinite(numero) and numero >= 0:
                        metricas[partes[0]] = numero
                except ValueError:
                    pass
    return metricas


def _percentis(valores: list[float]) -> dict | None:
    if not valores:
        return None
    import numpy as np
    return dict(zip(('p50', 'p95', 'p99'), map(float, np.percentile(valores, [50, 95, 99], method='linear'))))


def resumir_http(amostras: list[dict], *, residencia_s: float) -> dict:
    tempos = [a['duracao_s'] for a in amostras if a.get('duracao_s') is not None]
    sucessos = [a for a in amostras if a.get('status_code') is not None and 200 <= a['status_code'] < 300]
    return {'n': len(amostras), 'sucessos': len(sucessos), 'erros': len(amostras) - len(sucessos),
            'timeouts': sum(a.get('categoria_erro') == 'timeout' for a in amostras),
            'recusas_400': sum(a.get('status_code') == 400 for a in amostras),
            'taxa_sucesso': len(sucessos) / len(amostras) if amostras else None,
            'latencia_s': _percentis(tempos),
            'latencia_sucessos_s': _percentis([a['duracao_s'] for a in sucessos]),
            'throughput_sucessos_s': len(sucessos) / residencia_s if sucessos and residencia_s > 0 else None,
            'residencia_s': residencia_s, 'metodo_percentil': 'numpy.linear',
            'p99_exploratorio': len(amostras) <= 100, 'amostras': amostras}


def _pedido(cliente, metodo: str, caminho: str, *, dados=None, timeout=300) -> dict:
    import httpx
    inicio = time.perf_counter()
    try:
        resposta = cliente.request(metodo, caminho, json=dados, timeout=timeout)
        leitura = {'status_code': resposta.status_code, 'duracao_s': time.perf_counter() - inicio,
                   'categoria_erro': None if 200 <= resposta.status_code < 300 else 'http',
                   'server_timing_ms': ler_server_timing(resposta.headers.get('server-timing', ''))}
        if caminho == '/saude/prontidao' or caminho == '/conversas/repontuar':
            with contextlib.suppress(ValueError, TypeError):
                corpo = resposta.json()
                corpo = corpo.get('detail', corpo)
                if isinstance(corpo, dict):
                    for chave in ('estado_motor', 'estado', 'total', 'feitas'):
                        if chave in corpo and isinstance(corpo[chave], (str, int)):
                            leitura[chave] = corpo[chave]
        return leitura
    except httpx.TimeoutException:
        return {'status_code': None, 'duracao_s': time.perf_counter() - inicio,
                'categoria_erro': 'timeout', 'server_timing_ms': {}}
    except httpx.RequestError:
        return {'status_code': None, 'duracao_s': time.perf_counter() - inicio,
                'categoria_erro': 'transporte', 'server_timing_ms': {}}


def _parametros(config: dict) -> dict:
    caminhos = config['caminhos']
    torch = config['perfil'] == 'torch'
    parametros = {'FRAUS_BACKEND': 'torch' if torch else 'onnx', 'FRAUS_AQUECER': '0'}
    for nome in ('texto', 'emocao', 'ironia'):
        # Mesmo ausente aponta para uma cópia inexistente, nunca para originais.
        valor = caminhos.get(nome, str(Path(config['workspace']) / 'ausente' / nome))
        parametros[f'FRAUS_CAMINHO_{"MODELO" if torch else "ONNX"}_{nome.upper()}'] = valor
    parametros['FRAUS_CAMINHO_FUSOR'] = config.get('fusor', str(Path(config['workspace']) / 'ausente' / 'fusor.joblib'))
    return parametros


def _servidor(config: dict, pasta: str, canal, parar, cenario: str):
    """Entry-point spawn: ambiente sanitizado ANTES de importar produto."""
    ambiente = ambiente_isolado(Path(config['workspace']), _parametros(config))
    os.environ.clear()
    os.environ.update(ambiente)
    logging.disable(logging.CRITICAL)
    inicio = time.perf_counter()
    cpu_inicio = time.process_time()
    banco, sock = None, None
    eventos, construcoes = [], []
    recursos = {'banco_fechado': False, 'construcoes_motor': 0}
    try:
        import uvicorn
        from fraus.api import main as montagem
        from fraus.api.motor_preguicoso import ProvedorDeMotor
        from fraus.db import Banco
        eventos.append({'etapa': 'imports', 'inicio_s': 0., 'fim_s': time.perf_counter() - inicio,
                        'memoria': memoria(), 'tipo': 'exclusivo'})
        # Os módulos podem ter sido importados pelo processo chamador em testes;
        # injeção explícita também impede defaults cacheados de alcançar originais.
        for nome, valor in _parametros(config).items():
            if nome.startswith('FRAUS_CAMINHO_'):
                atributo = nome.removeprefix('FRAUS_')
                setattr(montagem, atributo, Path(valor))
        t = time.perf_counter()
        banco = Banco(Path(pasta) / 'api.sqlite3')
        banco.migrar()
        if cenario == 'repontuacao':
            from fraus.modelos import Conversa
            for indice in range(20):
                conversa = Conversa.model_validate({
                    'id': f'repontuacao-{indice:03d}', 'canal': 'chat', 'escalou_para_humano': False,
                    'iniciada_em': '2026-10-01T10:00:00+00:00',
                    'mensagens': [{'autor': 'cliente', 'texto': 'Cobranca duplicada sem solucao preciso do estorno.',
                                   'enviada_em': '2026-10-01T10:00:00+00:00'}]})
                banco.salvar(conversa, None, None)
        eventos.append({'etapa': 'sqlite_migrado_preparado', 'duracao_s': time.perf_counter() - t,
                        'memoria': memoria(), 'tipo': 'exclusivo'})
        def construir_instrumentado():
            from scripts.analise_motores._desempenho_worker import EventosCarga, instrumentar_carga
            carga = EventosCarga(lambda: None)
            try:
                with instrumentar_carga(carga, config['perfil']):
                    with carga.etapa('provedor_pronto'):
                        return montagem.construir_motor_padrao()
            finally:
                recursos['eventos_carga_factory'] = carga.eventos

        guardada = fabrica_guardada(config, construir_instrumentado)

        def construir():
            construcoes.append(True)
            t_carga = time.perf_counter()
            try:
                motor = guardada()
                # Prazos por operação, não por rodada; worker exclusivo pode morrer.
                for nome in ('pontuar_conversa', 'atribuir_conversa', 'analisar_conversa'):
                    original = getattr(motor, nome)

                    def limitada(*args, _original=original, **kwargs):
                        with prazo_operacao():
                            return _original(*args, **kwargs)
                    setattr(motor, nome, limitada)
                return motor
            finally:
                eventos.append({'etapa': 'fabrica_motor', 'duracao_s': time.perf_counter() - t_carga,
                                'memoria': memoria(), 'tipo': 'inclusivo'})

        provedor = ProvedorDeMotor(construir)
        app = montagem.criar_app(banco, provedor, raiz_importacao=Path(config['workspace']),
                                 chave_mestra=None, chave_acesso_ambiente=None, jwt_segredo=None,
                                 codigo_dev=None, codigo_convite=None, caminho_conformal=None)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 0))
        porta = sock.getsockname()[1]
        servidor = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=porta, workers=1,
                                               access_log=False, log_config=None,
                                               timeout_graceful_shutdown=1, lifespan='off'))

        def encerrar():
            parar.wait()
            servidor.should_exit = True
        threading.Thread(target=encerrar, daemon=True).start()
        canal.send({'tipo': 'iniciado', 'porta': porta})
        servidor.run(sockets=[sock])
    except Exception:
        recursos['categoria_erro'] = 'servidor_local'
    finally:
        if banco is not None:
            banco.fechar()
            recursos['banco_fechado'] = True
        if sock is not None:
            sock.close()
        recursos.update(memoria=memoria(), ru_maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                        cpu_s=time.process_time() - cpu_inicio, residencia_s=time.perf_counter() - inicio,
                        eventos=eventos, construcoes_motor=len(construcoes), banco=str(Path(pasta) / 'api.sqlite3'))
        # Não despejar eventos no pipe: seu buffer finito poderia bloquear o
        # encerramento e parecer um timeout de inferência.
        arquivo_recursos = Path(pasta) / 'recursos-servidor.json'
        arquivo_recursos.write_text(json.dumps(recursos, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        with contextlib.suppress(BrokenPipeError, EOFError, OSError):
            canal.send({'tipo': 'finalizado'})
        canal.close()


def _proc(pid: int) -> dict:
    leitura = {}
    try:
        for linha in Path(f'/proc/{pid}/status').read_text().splitlines():
            campos = linha.split()
            if campos[0].rstrip(':') in {'VmRSS', 'VmHWM', 'VmSwap'}:
                leitura[campos[0].rstrip(':')] = int(campos[1]) * 1024
        stat = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        leitura['cpu_s'] = (int(stat[11]) + int(stat[12])) / os.sysconf('SC_CLK_TCK')
    except (OSError, ValueError, IndexError):
        pass
    return leitura


class _ServidorLocal:
    def __init__(self, config, *, cenario='analise'):
        self.config = config
        self.cenario = cenario
        self.recursos = {'rss_amostras': [], 'banco_fechado': False}
        self.url = None
        self._fim = threading.Event()
        self.processo = None

    def __enter__(self):
        ctx = multiprocessing.get_context('spawn')
        self.canal, filho = ctx.Pipe(duplex=False)
        self.parar = ctx.Event()
        pasta = tempfile.mkdtemp(prefix='api-', dir=self.config['workspace'])
        self.recursos.update(pasta=pasta, memoria_inicial=memoria())
        disponivel = self.recursos['memoria_inicial']['ram_disponivel_bytes']
        self.recursos['limite_rss_bytes'] = int(disponivel * .8) if disponivel else None
        self.processo = ctx.Process(target=_servidor, args=(self.config, pasta, filho, self.parar, self.cenario))
        self.inicio = time.perf_counter()
        self.processo.start()
        filho.close()

        def monitorar():
            while not self._fim.is_set():
                leitura = _proc(self.processo.pid)
                if leitura:
                    self.recursos['rss_amostras'].append({'t_s': time.perf_counter() - self.inicio, **leitura})
                    limite = self.recursos['limite_rss_bytes']
                    if limite and leitura.get('VmRSS', 0) >= limite:
                        self.recursos['categoria_erro'] = 'guardrail_memoria'
                        self.processo.kill()
                        return
                self._fim.wait(.05)
        self.monitor = threading.Thread(target=monitorar, daemon=True)
        self.monitor.start()
        try:
            if not self.canal.poll(300):
                raise TimeoutError('boot local excedeu prazo')
            mensagem = self.canal.recv()
            if mensagem.get('tipo') != 'iniciado':
                self.recursos.update(mensagem)
                raise RuntimeError('servidor nao iniciou')
            self.url = f'http://127.0.0.1:{mensagem["porta"]}'
            # Somente boot/transporte é sondado até o socket aceitar; predição
            # nunca ganha retry. Prontidão não aquece e nenhum /saude é chamado.
            prazo = time.perf_counter() + 30
            while time.perf_counter() < prazo:
                with cliente_loopback(self.url) as cliente:
                    leitura = _pedido(cliente, 'GET', '/saude/prontidao')
                if leitura['status_code'] is not None:
                    self.readiness_inicial = leitura
                    return self
                if not self.processo.is_alive():
                    break
                time.sleep(.05)
            raise RuntimeError('socket local indisponivel')
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, tipo, valor, traceback):
        if self.processo is None:
            return
        self.parar.set()
        self.processo.join(5)
        if self.processo.is_alive():
            self.recursos.setdefault('categoria_erro', 'encerramento_forcado')
            self.processo.kill()
            self.processo.join()
        self._fim.set()
        self.monitor.join()
        while self.canal.poll():
            try:
                mensagem = self.canal.recv()
            except EOFError:
                break
            if mensagem.get('tipo') == 'finalizado':
                self.recursos.update(mensagem)
        self.canal.close()
        arquivo_recursos = Path(self.recursos['pasta']) / 'recursos-servidor.json'
        if arquivo_recursos.is_file():
            self.recursos.update(json.loads(arquivo_recursos.read_text(encoding='utf-8')))
        self.recursos['returncode'] = self.processo.exitcode
        if self.processo.exitcode == 124:
            self.recursos['categoria_erro'] = 'timeout_operacao'
        self.recursos['residencia_supervisionada_s'] = time.perf_counter() - self.inicio
        self.recursos['banco_preservado'] = True


def _dados(n):
    return {'csv': csv_sintetico(n), 'nome': 'laboratorio.csv'}


def medir_concorrencia(url: str, n: int, clientes: int, *, requisicoes=20) -> dict:
    """Barreira inicial; uma conexão por cliente, vinte tentativas, sem retries."""
    if clientes not in (1, 2, 4, 8) or n not in (1, 5, 20, 100) or requisicoes < 1:
        raise ValueError('celula de concorrencia invalida')
    # Falha síncrona: URL recusada não pode deixar as threads presas na barreira.
    with cliente_loopback(url):
        pass
    inicio = time.perf_counter()
    barreira = threading.Barrier(clientes + 1)
    fim = threading.Event()
    prontidao = []

    def sondar():
        with cliente_loopback(url) as cliente:
            while not fim.is_set():
                t = time.perf_counter()
                leitura = _pedido(cliente, 'GET', '/saude/prontidao')
                prontidao.append({'inicio_s': t - inicio, **leitura})
                fim.wait(max(0., 1. - (time.perf_counter() - t)))

    def consumir(indice):
        with cliente_loopback(url) as cliente:
            barreira.wait(timeout=300)
            return [{'cliente': indice, 'indice': i,
                     **_pedido(cliente, 'POST', '/analisar', dados=_dados(n))}
                    for i in range(requisicoes)]

    monitor = threading.Thread(target=sondar, daemon=True)
    with ThreadPoolExecutor(max_workers=clientes) as pool:
        tarefas = [pool.submit(consumir, indice) for indice in range(clientes)]
        inicio = time.perf_counter()
        monitor.start()
        barreira.wait(timeout=300)
        try:
            amostras = [a for tarefa in tarefas for a in tarefa.result()]
        finally:
            fim.set()
            monitor.join()
    residencia = time.perf_counter() - inicio
    return {'clientes': clientes, 'requisicoes_por_cliente': requisicoes,
            'inicio_sincronizado': True, 'readiness_intervalo_s': 1,
            'readiness': prontidao, **resumir_http(amostras, residencia_s=residencia)}


def _impedida(n, motivo, **outros):
    return {'mensagens_cliente': n, 'status': 'nao_verificado', 'motivo': motivo,
            'n': None, 'latencia_s': None, 'throughput_sucessos_s': None, **outros}


def _repontuar(servidor) -> dict:
    inicio = time.perf_counter()
    amostras = []
    with cliente_loopback(servidor.url) as cliente:
        post = _pedido(cliente, 'POST', '/conversas/repontuar')
        if post['status_code'] != 202:
            return {'status': 'erro', 'motivo': 'post_repontuacao_recusado', 'post': post,
                    'duracao_completa_s': None}
        prazo = inicio + 300
        while time.perf_counter() < prazo:
            leitura = _pedido(cliente, 'GET', '/conversas/repontuar',
                              timeout=max(.001, prazo - time.perf_counter()))
            amostras.append(leitura)
            if leitura.get('estado') in {'concluido', 'falhou'}:
                completo = leitura.get('estado') == 'concluido' and leitura.get('total') == 20 and leitura.get('feitas') == 20
                return {'status': 'medido' if completo else 'erro',
                        'motivo': None if completo else 'repontuacao_falhou_ou_incompleta',
                        'post': post, 'terminal': leitura, 'sondagens': amostras,
                        'duracao_completa_s': time.perf_counter() - inicio,
                        'n_conversas': 20, 'inclui_carga_primeiro_uso': True}
            if leitura['categoria_erro'] == 'timeout':
                break
            time.sleep(.25)
    # O contexto encerra o processo inteiro; banco fica preservado, nunca removido.
    return {'status': 'nao_verificado', 'motivo': 'timeout_repontuacao', 'post': post,
            'sondagens': amostras, 'duracao_completa_s': None, 'n_conversas': 20}


def coletar_api(config: dict) -> dict:
    config = validar_config(config)
    Path(config['workspace']).mkdir(parents=True, exist_ok=True)
    inicio = time.perf_counter()
    cliente_inicio = memoria()
    cpu_inicio = time.process_time()
    motivo = _impedimento(config)
    dados = {'schema_version': 1, 'perfil': config['perfil'], 'status': 'nao_verificado' if motivo else 'medido',
             'motivo': motivo, 'motor_completo': False,
             'rede': {'host': '127.0.0.1', 'porta': 'efemera', 'workers': 1,
                      'trust_env': False, 'redirects': False},
             'condicoes': {'timeout_chamada_s': 300, 'retries': 0, 'cold': config['cold'],
                           'warm': config['warm'], 'aquecimentos': config['aquecimentos'],
                           'frio': 'processo_frio_nao_disco_frio', 'preparacao_copias_fora_da_carga': True,
                           'operacao': 'POST /analisar (inclui oclusao)',
                           'pool_postgres': 'nao_medido_SQLite_nao_representa_pool_remoto'},
             'cold': [], 'celulas': [], 'concorrencia': [], 'sondas': {},
             'repontuacao': {'status': 'nao_verificado', 'motivo': motivo},
             'recursos': {'cliente': {}, 'servidores': []}}

    def salvar():
        destino = Path(config['saida'])
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(dados, ensure_ascii=False, allow_nan=False, indent=2) + '\n', encoding='utf-8')

    def registrar(servidor):
        dados['recursos']['servidores'].append(servidor.recursos)
        salvar()

    try:
        # Prova leve real permanece disponível mesmo com fusor bloqueado.
        servidor = _ServidorLocal(config)
        try:
            with servidor:
                with cliente_loopback(servidor.url) as cliente:
                    dados['sondas'] = {'readiness_antes': servidor.readiness_inicial,
                                       'recusa_100': _pedido(cliente, 'POST', '/analisar', dados=_dados(100)),
                                       'readiness_depois': _pedido(cliente, 'GET', '/saude/prontidao')}
        finally:
            registrar(servidor)
        dados['sondas']['construcoes_motor'] = servidor.recursos.get('construcoes_motor', 0)
        sondas = dados['sondas']
        if not (sondas['readiness_antes']['status_code'] == 503
                and sondas['recusa_100']['status_code'] == 400
                and sondas['readiness_depois'].get('estado_motor') == 'frio'
                and sondas['construcoes_motor'] == 0):
            raise RuntimeError('contrato de prontidao ou orcamento divergiu')
        if motivo:
            dados['cold'] = [_impedida(1, motivo, processo=indice) for indice in range(config['cold'])]

        # Cinco processos novos, primeiro POST inclui a construção real do motor.
        for indice in range(0 if motivo else config['cold']):
            servidor = _ServidorLocal(config)
            try:
                with servidor:
                    with cliente_loopback(servidor.url) as cliente:
                        leitura = _pedido(cliente, 'POST', '/analisar', dados=_dados(1))
                    dados['cold'].append({'processo': indice, 'primeiro_post': leitura})
            finally:
                registrar(servidor)
            if leitura['status_code'] != 200:
                motivo = servidor.recursos.get('categoria_erro') or 'motor_ou_primeira_inferencia_indisponivel'
                break
        if motivo:
            dados.update(status='nao_verificado', motivo=motivo)
            dados['cold'].extend(_impedida(1, motivo, processo=indice)
                                  for indice in range(len(dados['cold']), config['cold']))
            dados['celulas'] = [_impedida(n, motivo) for n in (1, 5, 20)]
            dados['concorrencia'] = [_impedida(n, motivo, clientes=c, requisicoes_planejadas=c * 20)
                                     for n in (1, 5, 20) for c in (1, 2, 4, 8)]
            dados['repontuacao'] = {'status': 'nao_verificado', 'motivo': motivo}
        else:
            dados['motor_completo'] = True

        # Recusar 100 clientes independe dos pesos: não descartar essa medição.
        for n in ((100,) if motivo else (1, 5, 20, 100)):
            servidor = _ServidorLocal(config)
            try:
                with servidor:
                    with cliente_loopback(servidor.url) as cliente:
                        aquecimentos = [_pedido(cliente, 'POST', '/analisar', dados=_dados(n))
                                        for _ in range(config['aquecimentos'])]
                        t = time.perf_counter()
                        cpu = _proc(servidor.processo.pid).get('cpu_s')
                        amostras = [_pedido(cliente, 'POST', '/analisar', dados=_dados(n))
                                    for _ in range(config['warm'])]
                        duracao = time.perf_counter() - t
                        cpu_final = _proc(servidor.processo.pid).get('cpu_s')
                        cpu_s = cpu_final - cpu if cpu_final is not None and cpu is not None else None
                        resumo = resumir_http(amostras, residencia_s=duracao)
                        dados['celulas'].append({'mensagens_cliente': n, 'status': 'medido',
                                                 'operacao': 'recusa_400_nao_inferencia' if n == 100 else 'analisar',
                                                 'aquecimentos_excluidos': aquecimentos, 'cpu_servidor_s': cpu_s,
                                                 'cpu_s_por_1000_tentativas': cpu_s * 1000 / len(amostras) if cpu_s is not None else None,
                                                 'residencia_s_por_1000_tentativas': duracao * 1000 / len(amostras), **resumo})
            finally:
                registrar(servidor)

        for n in ((100,) if motivo else (1, 5, 20, 100)):
            for clientes in (1, 2, 4, 8):
                servidor = _ServidorLocal(config)
                try:
                    with servidor:
                        with cliente_loopback(servidor.url) as cliente:
                            aquecimentos = [_pedido(cliente, 'POST', '/analisar', dados=_dados(n))
                                            for _ in range(config['aquecimentos'])]
                        cpu = _proc(servidor.processo.pid).get('cpu_s')
                        coleta = medir_concorrencia(servidor.url, n, clientes)
                        cpu_final = _proc(servidor.processo.pid).get('cpu_s')
                        cpu_s = cpu_final - cpu if cpu_final is not None and cpu is not None else None
                        dados['concorrencia'].append({'mensagens_cliente': n, 'status': 'medido',
                                                      'operacao': 'recusa_400_nao_inferencia' if n == 100 else 'analisar',
                                                      'aquecimentos_excluidos': aquecimentos,
                                                      'cpu_servidor_s': cpu_s, **coleta})
                        dados['concorrencia'][-1]['cpu_s_por_1000_tentativas'] = (
                            cpu_s * 1000 / coleta['n'] if cpu_s is not None and coleta['n'] else None)
                        dados['concorrencia'][-1]['residencia_s_por_1000_tentativas'] = (
                            coleta['residencia_s'] * 1000 / coleta['n'] if coleta['n'] else None)
                finally:
                    registrar(servidor)
        if motivo:
            return dados
        servidor = _ServidorLocal(config, cenario='repontuacao')
        try:
            with servidor:
                dados['repontuacao'] = _repontuar(servidor)
        finally:
            registrar(servidor)
        return dados
    except Exception:
        dados.update(status='erro', motivo='coleta_api_local')
        return dados
    finally:
        dados['sondas']['construcoes_motor_total'] = sum(
            servidor.get('construcoes_motor', 0) for servidor in dados['recursos']['servidores'])
        faltou = dados.get('motivo') or 'coleta_nao_concluida'
        existentes = {c['mensagens_cliente'] for c in dados['celulas']}
        dados['celulas'].extend(_impedida(n, faltou) for n in (1, 5, 20, 100) if n not in existentes)
        existentes = {(c['mensagens_cliente'], c['clientes']) for c in dados['concorrencia']}
        dados['concorrencia'].extend(_impedida(n, faltou, clientes=c, requisicoes_planejadas=c * 20)
                                     for n in (1, 5, 20, 100) for c in (1, 2, 4, 8)
                                     if (n, c) not in existentes)
        dados['cold_resumo'] = {
            'n_planejadas': config['cold'],
            **resumir_http([c['primeiro_post'] for c in dados['cold'] if 'primeiro_post' in c],
                           residencia_s=sum(c['primeiro_post']['duracao_s'] for c in dados['cold']
                                            if 'primeiro_post' in c))}
        dados['recursos']['cliente'] = {**memoria(), 'inicial': cliente_inicio,
                                         'cpu_s': time.process_time() - cpu_inicio,
                                         'residencia_s': time.perf_counter() - inicio,
                                         'ru_maxrss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        salvar()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        config = json.loads(args.config.read_text(encoding='utf-8'))
        # Recusa o próprio arquivo de configuração fora do workspace também.
        _caminho_copiado(args.config, Path(config['workspace']).resolve())
        dados = coletar_api(config)
        print(json.dumps({'status': dados['status'], 'motivo': dados['motivo']}, allow_nan=False))
        return 0 if dados['status'] == 'medido' else (2 if dados['status'] == 'nao_verificado' else 1)
    except Exception:
        print(json.dumps({'status': 'erro', 'motivo': 'configuracao_api_recusada'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
