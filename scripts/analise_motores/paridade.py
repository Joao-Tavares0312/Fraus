"""Paridade offline, sem fábrica da API, downloads, treino ou promoção.

``comparar_snapshots`` recusa checkpoints distintos/desconhecidos. A identidade
ONNX exige ``manifesto-paridade.json`` adjacente às pastas de cabeças, contendo
``checkpoint`` (digest dos arquivos Torch), ``precisao`` e ``hashes`` de TODOS
os arquivos ONNX/tokenizer da árvore. Isso vincula a comparação ao export
identificado, não prova identidade com um bundle publicado desconhecido.

O fusor exige manifesto anterior à análise, fonte explicitamente confiada e
checksum independente desse manifesto: --manifesto-fusor, --fonte-confiavel-fusor,
--sha256-manifesto-fusor. Ausência impede score, não cabeças/features. Somente
um motor completo com as 200 entradas do ouro pode gerar snapshot versionado.
A carga reutilizável vive em ``_worker.carregar_perfil/coletar_perfil``.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from scripts.analise_motores.comum import (
    RAIZ, copiar_arvore, executar_isolado, parser_base, preparar_workspace,
    resultado, salvar_resultado, versoes,
)
from scripts.gerenciar_artefatos import sha256

PERFIS = ('torch', 'onnx-fp32', 'onnx-int8', 'laya-onnx')
PASTAS = {'texto': 'bertimbau-satisfacao', 'emocao': 'bertimbau-emocao', 'ironia': 'bertimbau-ironia'}
GATES = {'fp32': {'max_delta_probabilidade': 1e-3, 'max_delta_score': .01, 'max_flips_categoria': 0},
         'int8': {'max_delta_probabilidade': .02, 'max_queda_f1_macro': .005, 'max_flips_categoria': 0}}
OURO = RAIZ / 'tests/golden/analise_motores'


def _sem_links(caminho: Path) -> None:
    if any(item.is_symlink() for item in (caminho, *caminho.parents)):
        raise ValueError('symlink recusado em artefatos')
    if caminho.is_dir() and any(item.is_symlink() for item in caminho.rglob('*')):
        raise ValueError('symlink recusado em artefatos')


def hashes_arvore(pasta: Path) -> dict[str, str]:
    _sem_links(pasta)
    return {item.relative_to(pasta).as_posix(): sha256(item)
            for item in sorted(pasta.rglob('*')) if item.is_file()}


def copiar_com_hashes(origem: Path, destino: Path) -> dict:
    """Cópia física com hashes antes/depois; nunca links nem extração/pickle."""
    origem, destino = Path(origem).absolute(), Path(destino).absolute()
    _sem_links(origem)
    _sem_links(destino)
    antes = hashes_arvore(origem)
    copiar_arvore(origem, destino)
    copias, depois = hashes_arvore(destino), hashes_arvore(origem)
    if antes != copias or antes != depois:
        raise ValueError('integridade da copia recusada')
    if any((origem / nome).stat().st_ino == (destino / nome).stat().st_ino
           and (origem / nome).stat().st_dev == (destino / nome).stat().st_dev for nome in antes):
        raise ValueError('hardlink recusado')
    return {'origem': str(origem), 'copia': str(destino), 'originais': antes, 'copias': copias,
            'originais_apos_copia': depois}


def _copiar_arquivo(origem: Path, destino: Path) -> dict:
    _sem_links(origem)
    _sem_links(destino)
    if destino.exists():
        raise ValueError('destino existente recusado')
    antes = sha256(origem)
    shutil.copy2(origem, destino)
    if sha256(destino) != antes or sha256(origem) != antes:
        raise ValueError('integridade de arquivo recusada')
    return {'origem': str(origem), 'copia': str(destino), 'originais': {origem.name: antes},
            'copias': {origem.name: antes}, 'originais_apos_copia': {origem.name: antes}}


def _digest(hashes: dict) -> str | None:
    if not hashes:
        return None
    return hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _numeros(valor) -> list[float]:
    if isinstance(valor, dict):
        return [numero for chave in sorted(valor) for numero in _numeros(valor[chave])]
    if isinstance(valor, list):
        return [numero for item in valor for numero in _numeros(item)]
    if not isinstance(valor, (int, float)):
        raise ValueError('probabilidade invalida')
    import math
    if not math.isfinite(valor):
        raise ValueError('numero nao finito recusado')
    return [float(valor)]


def _forma(valor):
    if isinstance(valor, dict):
        return {chave: _forma(item) for chave, item in valor.items()}
    if isinstance(valor, list):
        return [_forma(item) for item in valor]
    return 'numero'


def comparar_snapshots(base: dict, candidato: dict, precisao: str, *, queda_f1_macro=None) -> dict:
    """Deltas/denominadores reais; ouro sintético nunca fornece F1 de holdout.

    ``queda_f1_macro`` só pode vir de avaliação independente identificada pelo
    chamador; o CLI desta fase não a inventa a partir de rótulos sintéticos.
    """
    if not base.get('checkpoint') or base['checkpoint'] != candidato.get('checkpoint'):
        raise ValueError('checkpoint distinto ou identidade nao verificada; comparar qualidade/custo')
    if precisao not in GATES:
        raise ValueError('precisao desconhecida')
    if queda_f1_macro is not None:
        _numeros(queda_f1_macro)
    originais = {caso['id']: caso for caso in base['casos']}
    novos = {caso['id']: caso for caso in candidato['casos']}
    if (len(originais) != len(base['casos']) or len(novos) != len(candidato['casos'])
            or set(originais) != set(novos)):
        raise ValueError('alinhamento de ids')
    if not originais:
        raise ValueError('alinhamento vazio')
    saida = {}
    for campo in ('probabilidades', 'probabilidades_fusor', 'score', 'classe', 'nota', 'categoria'):
        deltas, flips, nulos, assimetricos, detalhes, diferentes = [], [], [], [], [], []
        n = n_argmax = 0
        for identificador, antes in originais.items():
            a, b = antes.get(campo), novos[identificador].get(campo)
            if a is None or b is None:
                nulos.append(identificador)
                if (a is None) != (b is None):
                    assimetricos.append(identificador)
                continue
            if campo.startswith('probabilidades'):
                if _forma(a) != _forma(b):
                    raise ValueError('alinhamento de probabilidades')
                aa, bb = _numeros(a), _numeros(b)
                delta_caso = [abs(x - y) for x, y in zip(aa, bb)]
                deltas.extend(delta_caso)
                if any(delta_caso):
                    diferentes.append(identificador)
                n += len(aa)
                if campo == 'probabilidades':
                    for cabeca in a:
                        for indice, (pa, pb) in enumerate(zip(a[cabeca], b[cabeca])):
                            n_argmax += 1
                            if max(range(len(pa)), key=pa.__getitem__) != max(range(len(pb)), key=pb.__getitem__):
                                detalhes.append({'id': identificador, 'cabeca': cabeca, 'indice_cliente': indice})
            else:
                n += 1
                if campo == 'score':
                    delta_caso = abs(_numeros(a)[0] - _numeros(b)[0])
                    deltas.append(delta_caso)
                    if delta_caso:
                        diferentes.append(identificador)
                elif a != b:
                    flips.append(identificador)
        chave = {'probabilidades': 'probabilidade', 'probabilidades_fusor': 'probabilidade_fusor'}.get(campo, campo)
        saida[chave] = {'n': n, 'ids_nulos': nulos, 'ids_nulos_assimetricos': assimetricos,
                        'ids_diferentes': diferentes if campo.startswith('probabilidades') or campo == 'score' else flips}
        if campo.startswith('probabilidades') or campo == 'score':
            saida[chave].update(max_delta=max(deltas) if deltas else None,
                                media_delta=sum(deltas) / len(deltas) if deltas else None)
        else:
            saida[chave].update(flips=len(flips), ids_flips=flips,
                                fracao_flips=len(flips) / n if n else None)
        if campo == 'probabilidades':
            saida['argmax_cabecas'] = {'n': n_argmax, 'flips': len(detalhes), 'detalhes': detalhes,
                                      'fracao_flips': len(detalhes) / n_argmax if n_argmax else None,
                                      'ids_flips': sorted({item['id'] for item in detalhes})}
    gate = dict(GATES[precisao])
    tem_prob = saida['probabilidade']['n'] > 0
    tem_motor = bool(base.get('motor_completo') and candidato.get('motor_completo')
                     and saida['score']['n'] and saida['categoria']['n'])
    assimetria = any(metrica.get('ids_nulos_assimetricos') for metrica in saida.values())
    falha = assimetria or (tem_prob and saida['probabilidade']['max_delta'] > gate['max_delta_probabilidade'])
    if saida['probabilidade_fusor']['n']:
        falha = falha or saida['probabilidade_fusor']['max_delta'] > gate['max_delta_probabilidade']
    falha = falha or saida['categoria']['flips'] > 0
    if precisao == 'fp32' and saida['score']['n']:
        falha = falha or saida['score']['max_delta'] > gate['max_delta_score']
    if precisao == 'int8' and queda_f1_macro is not None:
        falha = falha or queda_f1_macro > gate['max_queda_f1_macro']
    faltando = not tem_prob or not tem_motor or (precisao == 'int8' and queda_f1_macro is None)
    saida['aceite'] = {'limites_congelados': gate, 'aprovado': False if falha else (None if faltando else True),
                       'queda_f1_macro': queda_f1_macro, 'motor_verificado': tem_motor,
                       'motivo': 'prerequisitos_incompletos' if faltando else None}
    return saida


def _checkpoint_torch(modelos: Path) -> str | None:
    hashes = {}
    for nome, pasta in PASTAS.items():
        caminho = modelos / pasta
        if not (caminho / 'model.safetensors').is_file():
            return None
        for relativo, digest in hashes_arvore(caminho).items():
            # Métricas não participam da identidade numérica; configs/tokenizer sim.
            if relativo != 'metricas.json':
                hashes[f'{nome}/{relativo}'] = digest
    return _digest(hashes)


def _checkpoint_onnx(raiz: Path, esperado: str | None, precisao: str) -> str | None:
    arquivo = raiz / 'manifesto-paridade.json'
    if not arquivo.is_file() or not esperado:
        return None
    _sem_links(arquivo)
    manifesto = json.loads(arquivo.read_text(encoding='utf-8'))
    if manifesto.get('checkpoint') != esperado or manifesto.get('precisao') != precisao:
        return None
    hashes = {nome: digest for nome, digest in hashes_arvore(raiz).items() if nome != 'manifesto-paridade.json'}
    return esperado if manifesto.get('hashes') == hashes else None


def _preparar_config(args, perfil: str, workspace: Path, rodada: Path, checkpoint: str | None) -> tuple[dict | None, list[dict], str | None]:
    destino = rodada / perfil
    destino.mkdir()
    raiz = Path(args.modelos if perfil == 'torch' else (getattr(args, perfil.replace('-', '_'), None) or args.onnx)).absolute()
    if perfil != 'torch' and (raiz / perfil).is_dir():
        raiz = raiz / perfil
    if not raiz.is_dir():
        return None, [], 'diretorio_de_modelos_ausente'
    _sem_links(raiz)
    caminhos, evidencias, faltantes = {}, [], []
    for nome, pasta in PASTAS.items():
        origem = Path(args.laya).absolute() if perfil == 'laya-onnx' and nome == 'ironia' else raiz / pasta
        obrigatorio = 'model.safetensors' if perfil == 'torch' else ('laya.onnx' if perfil == 'laya-onnx' and nome == 'ironia' else 'model.onnx')
        if not (origem / obrigatorio).is_file():
            faltantes.append(nome)
            continue
        copia = destino / nome
        evidencias.append(copiar_com_hashes(origem, copia))
        caminhos[nome] = str(copia)
    if not caminhos:
        return None, evidencias, 'pesos_de_cabecas_ausentes'
    identidade = checkpoint if perfil == 'torch' else _checkpoint_onnx(raiz, checkpoint, perfil.removeprefix('onnx-'))
    if perfil == 'laya-onnx':
        identidade = _digest({f'{nome}/{arquivo}': digest for evidencia in evidencias
                              for nome in [Path(evidencia['copia']).name]
                              for arquivo, digest in evidencia['copias'].items()})
    config = {'perfil': perfil, 'workspace': str(workspace), 'caminhos': caminhos,
              'corpus': str(Path(args.corpus).absolute()), 'checkpoint': identidade,
              'saida': str(destino / 'coleta.json'), 'cabecas_ausentes': faltantes,
              'hashes': {e['origem']: e['originais'] for e in evidencias}}
    for chave in ('fusor', 'manifesto_fusor'):
        valor = getattr(args, chave)
        if valor and Path(valor).is_file():
            copia = destino / ('fusor.joblib' if chave == 'fusor' else 'manifesto-fusor.json')
            evidencias.append(_copiar_arquivo(Path(valor).absolute(), copia))
            config[chave] = str(copia)
    config['fonte_confiavel_fusor'] = args.fonte_confiavel_fusor
    config['sha256_manifesto_fusor'] = args.sha256_manifesto_fusor
    arquivo_config = destino / 'config.json'
    arquivo_config.write_text(json.dumps(config, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return config, evidencias, None


def _originais_preservados(evidencias: list[dict]) -> bool:
    for evidencia in evidencias:
        origem = Path(evidencia['origem'])
        hashes = hashes_arvore(origem) if origem.is_dir() else {origem.name: sha256(origem)}
        evidencia['originais_apos_worker'] = hashes
        if hashes != evidencia['originais']:
            return False
    return True


def _executar_perfil(args, perfil: str, workspace: Path, rodada: Path, checkpoint: str | None) -> tuple[dict, list[dict]]:
    copias = []
    try:
        config, copias, motivo = _preparar_config(args, perfil, workspace, rodada, checkpoint)
        if config is None:
            return {'status': 'nao_verificado', 'motivo': motivo, 'snapshot': None,
                    'coleta': None, 'n_casos': None, 'medicoes': None}, copias
        execucao = executar_isolado('scripts.analise_motores._worker',
                                    ['--config', str(rodada / perfil / 'config.json')], workspace,
                                    parametros={'FRAUS_BACKEND': 'torch' if perfil == 'torch' else 'onnx',
                                                'FRAUS_ONNX_THREADS': '0'},
                                    timeout=args.timeout)
        # Nem stdout nem exceções arbitrárias de bibliotecas são diagnóstico seguro.
        execucao = {k: v for k, v in execucao.items() if k != 'stdout'}
        arquivo = Path(config['saida'])
        if not arquivo.is_file() and arquivo.with_suffix('.parcial.json').is_file():
            arquivo = arquivo.with_suffix('.parcial.json')
        dados = json.loads(arquivo.read_text(encoding='utf-8')) if arquivo.is_file() else None
        preservados = _originais_preservados(copias)
        n = len(dados.get('casos', [])) if dados else None
        completo = bool(dados and dados.get('status') == 'medido' and dados.get('motor_completo')
                        and n == 200 and preservados and execucao['returncode'] == 0)
        status = 'medido' if completo else ('erro' if execucao['returncode'] == 1 or not preservados else 'nao_verificado')
        snapshot = None
        if completo and args.gravar_snapshots:
            if Path(args.corpus).resolve() != (OURO / 'conversas.jsonl').resolve():
                raise ValueError('snapshot versionado exige ouro versionado')
            snapshot = OURO / f'saidas-{perfil}.json'
            _sem_links(snapshot)
            snapshot.write_text(json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        motivo = None if completo else (dados or {}).get('motivo') or (dados or {}).get('categoria_erro') or execucao['categoria_erro'] or 'ouro_ou_motor_incompleto'
        return {'status': status, 'motivo': motivo,
                'snapshot': str(snapshot) if snapshot else None, 'coleta': str(arquivo) if arquivo.is_file() else None,
                'execucao': execucao, 'originais_preservados': preservados, 'n_casos': n,
                'motor_completo': bool(dados and dados.get('motor_completo')),
                'cabecas_ausentes': config['cabecas_ausentes'],
                'categoria_erro': (dados or {}).get('categoria_erro')}, copias
    except Exception:
        return {'status': 'erro', 'motivo': 'preparacao_ou_coleta_recusada',
                'snapshot': None, 'coleta': None, 'n_casos': None, 'categoria_erro': 'preparacao_ou_integridade'}, copias


def main(argv: list[str] | None = None) -> int:
    parser = parser_base(__doc__)
    parser.add_argument('--perfis', nargs='+', choices=PERFIS, default=list(PERFIS))
    parser.add_argument('--modelos', default=str(RAIZ / 'modelos'))
    parser.add_argument('--onnx', default=str(RAIZ / 'modelos-onnx'))
    parser.add_argument('--onnx-fp32')
    parser.add_argument('--onnx-int8')
    parser.add_argument('--laya', default=str(RAIZ / 'modelos-onnx/laya-ironia'))
    parser.add_argument('--fusor', default=str(RAIZ / 'modelos/fusor.joblib'))
    parser.add_argument('--manifesto-fusor')
    parser.add_argument('--fonte-confiavel-fusor')
    parser.add_argument('--sha256-manifesto-fusor')
    parser.add_argument('--corpus', default=str(OURO / 'conversas.jsonl'))
    parser.add_argument('--timeout', type=float, default=0., help='Teto da rodada; 0 usa apenas guardrail de 300 s por carga/passada')
    parser.add_argument('--gravar-snapshots', action='store_true', help='Somente motor real completo e ouro versionado de 200 casos')
    args = parser.parse_args(argv)
    workspace = None
    perfis, comparacoes, evidencias = {}, {}, []
    try:
        workspace = preparar_workspace(args.workspace)
        if args.timeout < 0:
            raise ValueError('timeout da rodada nao pode ser negativo')
        pasta = workspace / 'experimentos/paridade'
        pasta.mkdir(exist_ok=True)
        rodada = Path(tempfile.mkdtemp(prefix='rodada-', dir=pasta))
        checkpoint = _checkpoint_torch(Path(args.modelos).absolute())
        erro, incompleto = False, False
        for perfil in dict.fromkeys(args.perfis):
            medicao, copias = _executar_perfil(args, perfil, workspace, rodada, checkpoint)
            perfis[perfil] = medicao
            evidencias.extend(copias)
            incompleto |= medicao['status'] != 'medido'
            erro |= medicao['status'] == 'erro'
        base_path = perfis.get('torch', {}).get('coleta')
        if base_path:
            base = json.loads(Path(base_path).read_text(encoding='utf-8'))
            for perfil in ('onnx-fp32', 'onnx-int8', 'laya-onnx'):
                caminho = perfis.get(perfil, {}).get('coleta')
                if not caminho:
                    continue
                candidato = json.loads(Path(caminho).read_text(encoding='utf-8'))
                if perfil == 'laya-onnx' or not base.get('checkpoint') or candidato.get('checkpoint') != base.get('checkpoint'):
                    comparacoes[perfil] = {'status': 'nao_verificado', 'motivo': 'modelos_distintos_ou_checkpoint_sem_procedencia', 'metricas': None}
                    incompleto = True
                    continue
                if not base.get('casos') or not candidato.get('casos'):
                    comparacoes[perfil] = {'status': 'nao_verificado', 'motivo': 'corpus_sem_coleta', 'metricas': None}
                    incompleto = True
                    continue
                comparacoes[perfil] = comparar_snapshots(base, candidato, perfil.removeprefix('onnx-'))
                incompleto |= comparacoes[perfil]['aceite']['aprovado'] is None
        status = 'erro' if erro else ('nao_verificado' if incompleto else 'medido')
        dados = resultado('paridade', status, None if status == 'medido' else 'paridade_ou_motor_sem_prerequisitos',
                          condicoes={'backend': list(perfis), 'n': {p: m['n_casos'] for p, m in perfis.items()},
                                     'threads': {'OMP_NUM_THREADS': 1, 'MKL_NUM_THREADS': 1, 'FRAUS_ONNX_THREADS': 0},
                                     'operacao': 'cabecas_features_pontuacao_atribuicao_cinco_repeticoes',
                                     'versoes': versoes(['torch', 'transformers', 'onnxruntime', 'laya'])},
                          artefatos=evidencias, medicoes={'perfis': perfis, 'comparacoes': comparacoes, 'gates_congelados': GATES})
        salvar_resultado(workspace, dados)
        return 1 if erro else (2 if incompleto else 0)
    except Exception:
        if workspace is not None:
            salvar_resultado(workspace, resultado('paridade', 'erro', 'preparacao_ou_coleta_recusada',
                                                 artefatos=evidencias, medicoes={'perfis': perfis, 'comparacoes': comparacoes}))
        else:
            print(json.dumps({'fase': 'paridade', 'status': 'erro', 'motivo': 'workspace_recusado'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
