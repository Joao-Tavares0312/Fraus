"""Isolamento e evidências dos experimentos; não configura o produto."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import shutil
import contextlib
import threading
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

RAIZ = Path(__file__).resolve().parents[2]
PADRAO_WORKSPACE = '/tmp/fraus-analise-20261016'
SEMENTE = 20261016


def preparar_workspace(caminho: str | Path) -> Path:
    alvo = Path(caminho).expanduser().resolve()
    if alvo == RAIZ or alvo.is_relative_to(RAIZ) or RAIZ.is_relative_to(alvo):
        raise ValueError('workspace deve ser externo ao repositorio e nao seu ancestral')
    alvo.mkdir(parents=True, exist_ok=True)
    (alvo / '.gitignore').write_text('*\n', encoding='utf-8')
    for nome in ('experimentos', 'home', 'cache', 'tmp'):
        (alvo / nome).mkdir(exist_ok=True)
    return alvo


def parser_base(descricao: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=descricao)
    parser.add_argument('--workspace', default=PADRAO_WORKSPACE)
    return parser


def ambiente_isolado(workspace: Path, parametros: dict[str, str] | None = None) -> dict[str, str]:
    ambiente = {k: os.environ[k] for k in ('PATH', 'LANG', 'LC_ALL', 'LC_CTYPE', 'LD_LIBRARY_PATH', 'SYSTEMROOT') if k in os.environ}
    ambiente.update(HOME=str(workspace / 'home'), XDG_CACHE_HOME=str(workspace / 'cache'),
                    HF_HOME=str(workspace / 'cache' / 'huggingface'), TMPDIR=str(workspace / 'tmp'),
                    HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', PYTHONDONTWRITEBYTECODE='1',
                    PYTHONPATH=str(RAIZ), OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', TOKENIZERS_PARALLELISM='false')
    permitidos = {'FRAUS_BACKEND', 'FRAUS_ONNX_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                  'FRAUS_IRONIA_BACKEND', 'FRAUS_INFERENCIAS_SIMULTANEAS', 'FRAUS_AQUECER',
                  'FRAUS_CAMINHO_MODELO_TEXTO', 'FRAUS_CAMINHO_MODELO_EMOCAO', 'FRAUS_CAMINHO_MODELO_IRONIA',
                  'FRAUS_CAMINHO_FUSOR', 'FRAUS_CAMINHO_ONNX_TEXTO', 'FRAUS_CAMINHO_ONNX_EMOCAO',
                  'FRAUS_CAMINHO_ONNX_IRONIA', 'FRAUS_CAMINHO_ONNX_LAYA', 'FRAUS_CAMINHO_ONNX_MULTITAREFA'}
    for chave, valor in (parametros or {}).items():
        if chave not in permitidos:
            raise ValueError('parametro de subprocesso nao declarado')
        ambiente[chave] = str(valor)
    return ambiente


def memoria() -> dict:
    def ler(caminho):
        valores = {}
        try:
            for linha in Path(caminho).read_text().splitlines():
                partes = linha.split()
                if len(partes) > 1 and partes[1].isdigit():
                    valores[partes[0].rstrip(':')] = int(partes[1]) * (1024 if len(partes) > 2 and partes[2] == 'kB' else 1)
        except OSError:
            pass
        return valores
    ram, processo = ler('/proc/meminfo'), ler('/proc/self/status')
    return {'ram_total_bytes': ram.get('MemTotal'), 'ram_disponivel_bytes': ram.get('MemAvailable'),
            'swap_ocupada_bytes': ram['SwapTotal'] - ram['SwapFree'] if {'SwapTotal', 'SwapFree'} <= ram.keys() else None,
            'rss_bytes': processo.get('VmRSS'), 'pico_bytes': processo.get('VmHWM'), 'swap_processo_bytes': processo.get('VmSwap')}


def condicoes() -> dict:
    return {'semente': SEMENTE, 'n': None, 'backend': None, 'versoes': {'python': platform.python_version()},
            'hashes': {}, 'threads': None, 'afinidade': sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None,
            'cpu': platform.processor() or platform.machine(), 'memoria': memoria(), 'warm_cold': None,
            'duracao_s': None, 'operacao': None}


def resultado(fase: str, status='medido', motivo=None, *, condicoes=None, artefatos=None, medicoes=None) -> dict:
    if status not in {'medido', 'nao_verificado', 'erro'}:
        raise ValueError('status invalido')
    base = globals()['condicoes']()
    base.update(condicoes or {})
    return {'schema_version': 1, 'fase': fase, 'status': status, 'motivo': motivo,
            'comando': ['python', '-m', 'scripts.analise_motores.executar', fase],
            'condicoes': base, 'artefatos': artefatos or [], 'medicoes': medicoes or {}}


def salvar_resultado(workspace: Path, dados: dict) -> Path:
    texto = json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    pasta = workspace / 'experimentos' / 'resultados'
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / (dados['fase'] + '.json')
    destino.write_text(texto, encoding='utf-8')
    print(json.dumps({'fase': dados['fase'], 'status': dados['status'], 'motivo': dados['motivo'], 'resultado': str(destino)}, ensure_ascii=False))
    return destino


def copiar_arvore(origem: Path, destino: Path) -> Path:
    if origem.is_symlink() or any(p.is_symlink() for p in origem.rglob('*')):
        raise ValueError('symlink recusado em artefatos')
    if destino.exists():
        raise FileExistsError('destino de copia ja existe')
    shutil.copytree(origem, destino, copy_function=shutil.copy2)
    return destino


def cliente_loopback(url: str):
    import httpx
    partes = urlsplit(url)
    if partes.scheme != 'http' or partes.hostname != '127.0.0.1' or partes.username or partes.password or not partes.port or partes.path not in ('', '/') or partes.query or partes.fragment:
        raise ValueError('HTTP permitido somente no loopback criado pelo runner')
    return httpx.Client(base_url=url, trust_env=False, follow_redirects=False, timeout=300)


@contextlib.contextmanager
def prazo_operacao(segundos=300):
    """Timeout de uma carga/passada, não da rodada (worker exclusivo)."""
    temporizador = threading.Timer(segundos, lambda: os._exit(124))
    temporizador.daemon = True
    temporizador.start()
    try:
        yield
    finally:
        temporizador.cancel()


def executar_isolado(modulo: str, argumentos: list[str], workspace: Path, *, parametros=None, timeout=300) -> dict:
    """Supervisiona um worker conhecido, guardando RSS a cada 50 ms."""
    if not modulo.startswith('scripts.analise_motores.'):
        raise ValueError('worker fora dos instrumentos')
    inicio = time.perf_counter()
    inicial = memoria()
    limite = int(inicial['ram_disponivel_bytes'] * 0.8) if inicial['ram_disponivel_bytes'] else None
    amostras = []
    processo = subprocess.Popen([sys.executable, '-m', modulo, *argumentos], cwd=RAIZ,
                               env=ambiente_isolado(workspace, parametros),
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    categoria = None
    while True:
        try:
            campos = {}
            for linha in Path(f'/proc/{processo.pid}/status').read_text().splitlines():
                partes = linha.split()
                if partes[0].rstrip(':') in {'VmRSS', 'VmHWM', 'VmSwap'}:
                    campos[partes[0].rstrip(':')] = int(partes[1]) * 1024
            amostras.append({'t_s': time.perf_counter() - inicio, **campos})
            if limite and campos.get('VmRSS', 0) >= limite:
                categoria = 'guardrail_memoria'
        except (FileNotFoundError, ProcessLookupError):
            pass
        if timeout and time.perf_counter() - inicio >= timeout:
            categoria = 'timeout'
        if categoria:
            processo.kill()
            processo.communicate()
            bruto = b''
            break
        try:
            bruto, _ = processo.communicate(timeout=0.05)
            break
        except subprocess.TimeoutExpired:
            continue
    return {'returncode': 2 if categoria else processo.returncode,
            'duracao_s': time.perf_counter() - inicio,
            'stdout': bruto.decode('utf-8', errors='replace'),
            'categoria_erro': categoria or ('timeout_operacao' if processo.returncode == 124 else
                                           None if processo.returncode in (0, 2) else 'subprocesso_recusou'),
            'rss_amostras': amostras, 'memoria_inicial': inicial, 'limite_rss_bytes': limite}


def versoes(nomes):
    saida = {}
    for nome in nomes:
        try:
            saida[nome] = importlib.metadata.version(nome)
        except importlib.metadata.PackageNotFoundError:
            saida[nome] = None
    return saida
