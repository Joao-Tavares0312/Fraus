"""Laboratório sequencial de desempenho local; não representa latência Vercel."""
from __future__ import annotations

import json
import math
from pathlib import Path
import tempfile

from .comum import (RAIZ, executar_isolado, parser_base, preparar_workspace,
                    resultado, salvar_resultado, versoes)
from .paridade import PERFIS, OURO, _checkpoint_torch, _preparar_config


def resumir_amostras(amostras: list[dict]) -> dict:
    """Percentis apenas dos sucessos; erro/timeout continua no denominador."""
    import numpy as np

    for amostra in amostras:
        for chave in ('duracao_s', 'cpu_s'):
            valor = amostra.get(chave)
            if valor is not None and (not math.isfinite(valor) or valor < 0):
                raise ValueError('medicao_nao_finita_ou_negativa')
        if amostra['status'] not in {'sucesso', 'erro', 'timeout', 'abortado'}:
            raise ValueError('status_de_amostra_invalido')
        if amostra['status'] == 'sucesso' and amostra.get('duracao_s') is None:
            raise ValueError('sucesso_sem_tempo')
    n = len(amostras)
    sucessos = [a for a in amostras if a['status'] == 'sucesso']
    tempos = [a['duracao_s'] for a in sucessos]
    quantis = np.percentile(tempos, [50, 95, 99], method='linear').tolist() if tempos else [None] * 3
    def total(chave):
        valores = [a.get(chave) for a in amostras]
        return sum(valores) if valores and all(v is not None for v in valores) else None
    residencia, cpu = total('duracao_s'), total('cpu_s')
    return {'tentativas': n, 'sucessos': len(sucessos),
            'erros': sum(a['status'] == 'erro' for a in amostras),
            'timeouts': sum(a['status'] == 'timeout' for a in amostras),
            'abortos': sum(a['status'] == 'abortado' for a in amostras),
            'taxa_sucesso': len(sucessos) / n if n else None,
            'p50_s': quantis[0], 'p95_s': quantis[1], 'p99_s': quantis[2],
            'percentil_metodo': 'numpy.linear', 'p99_exploratorio': True,
            'cpu_s_total': cpu, 'residencia_s_total': residencia,
            'cpu_s_por_1000_tentativas': cpu / n * 1000 if cpu is not None else None,
            'residencia_s_por_1000_tentativas': residencia / n * 1000 if residencia is not None else None,
            'escopo_residencia': 'soma_chamadas_sequenciais_exclui_aquecimento_nao_vida_worker',
            'throughput_sucessos_s': len(sucessos) / residencia if sucessos and residencia else None,
            'motivo_metricas_nulas': 'nenhum_sucesso' if not sucessos else None}


def matriz_direta(falas=(1, 5, 20, 100), tokens=(16, 128, 256),
                   cabecas=('texto', 'emocao', 'ironia'), operacoes=('pontuar', 'atribuir', 'analisar')) -> list[dict]:
    return [dict(tipo=tipo, falas=n, tokens_alvo=t, **detalhe)
            for n in falas for t in tokens
            for tipo, detalhe in ([('cabeca', {'cabeca': c, 'operacao': 'prever_mensagens'}) for c in cabecas]
                                  + [('motor', {'operacao': o}) for o in operacoes])]


def completar_aborto(parcial: dict, categoria: str) -> dict:
    """Só a chamada já iniciada entra no denominador; pendentes ficam explícitas."""
    parcial = dict(parcial)
    parcial['amostras'] = list(parcial.get('amostras', []))
    andamento = parcial.get('em_andamento')
    if andamento and andamento.get('fase') == 'warm':
        parcial['amostras'].append({'status': 'timeout' if 'timeout' in categoria else 'abortado',
                                    'duracao_s': None, 'cpu_s': None, 'categoria': categoria})
    parcial.update(status='erro' if categoria == 'subprocesso_recusou' else 'nao_verificado',
                   motivo=categoria, em_andamento=None, resumo=resumir_amostras(parcial['amostras']))
    return parcial


def _executar(config: dict, pasta: Path, workspace: Path, *, api=False, parametros=None) -> dict:
    pasta.mkdir(parents=True, exist_ok=True)
    config = {**config, 'saida': str(pasta / 'coleta.json')}
    arquivo = pasta / 'config.json'
    arquivo.write_text(json.dumps(config, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    execucao = executar_isolado('scripts.analise_motores.' + ('_api_worker' if api else '_desempenho_worker'),
                               ['--config', str(arquivo)], workspace, parametros=parametros, timeout=0)
    coleta = json.loads(Path(config['saida']).read_text(encoding='utf-8')) if Path(config['saida']).is_file() else {}
    categoria = execucao.get('categoria_erro')
    if categoria:
        coleta = completar_aborto(coleta, categoria)
    elif not coleta:
        coleta = {'status': 'erro', 'motivo': 'worker_sem_coleta', 'resumo': resumir_amostras([])}
    if not api:
        n = coleta.get('resumo', {}).get('tentativas', 0)
        coleta['vida_worker_s'] = execucao['duracao_s']
        coleta['vida_worker_s_por_1000_tentativas'] = execucao['duracao_s'] / n * 1000 if n else None
    return {'coleta': coleta, 'arquivo': config['saida'],
            'execucao': {k: v for k, v in execucao.items() if k != 'stdout'}}


def main(argv: list[str] | None = None) -> int:
    parser = parser_base(__doc__)
    parser.add_argument('--cold', type=int, default=5)
    parser.add_argument('--warm', type=int, default=100)
    parser.add_argument('--aquecimentos', type=int, default=3)
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
    parser.add_argument('--falas', nargs='+', type=int, choices=(1, 5, 20, 100), default=[1, 5, 20, 100])
    parser.add_argument('--tokens', nargs='+', type=int, choices=(16, 128, 256), default=[16, 128, 256])
    parser.add_argument('--cabecas', nargs='+', choices=('texto', 'emocao', 'ironia'), default=['texto', 'emocao', 'ironia'])
    parser.add_argument('--operacoes', nargs='+', choices=('pontuar', 'atribuir', 'analisar'), default=['pontuar', 'atribuir', 'analisar'])
    parser.add_argument('--sem-api', action='store_true', help='Recorte explícito; padrão inclui API real loopback')
    parser.add_argument('--threads', type=int, default=1)
    args = parser.parse_args(argv)
    if args.cold < 1 or args.warm < 1 or args.aquecimentos < 0 or args.threads < 1:
        parser.error('cold/warm/threads positivos e aquecimentos nao negativo')
    workspace = preparar_workspace(args.workspace)
    pasta = workspace / 'experimentos/desempenho'
    pasta.mkdir(exist_ok=True)
    rodada = Path(tempfile.mkdtemp(prefix='rodada-', dir=pasta))
    perfis, evidencias = {}, []
    checkpoint = _checkpoint_torch(Path(args.modelos).absolute())
    parametros = {'OMP_NUM_THREADS': str(args.threads), 'MKL_NUM_THREADS': str(args.threads),
                  'FRAUS_ONNX_THREADS': str(args.threads), 'FRAUS_INFERENCIAS_SIMULTANEAS': '1'}
    dados = resultado('desempenho', condicoes={'n': args.warm, 'warm_cold': {'cold': args.cold, 'warm': args.warm, 'aquecimentos': args.aquecimentos},
                      'threads': args.threads, 'operacao': 'matriz_direta_e_api_loopback',
                      'versoes': versoes(['numpy', 'torch', 'transformers', 'onnxruntime', 'laya'])},
                      medicoes={'perfis': perfis, 'producao': None, 'custo_real': None,
                                'p99': 'exploratorio_n100', 'disco_frio': False,
                                'recorte_explicito': {'falas': args.falas, 'tokens': args.tokens, 'cabecas': args.cabecas,
                                                      'operacoes': args.operacoes, 'sem_api': args.sem_api}})
    def salvar():
        dados['artefatos'] = evidencias
        # Checkpoint por célula: não perde as anteriores se a próxima for abortada.
        (rodada / 'resultado.json').write_text(json.dumps(dados, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    for perfil in dict.fromkeys(args.perfis):
        try:
            config, copias, motivo = _preparar_config(args, perfil, workspace, rodada, checkpoint)
            evidencias.extend(copias)
            if config is None:
                perfis[perfil] = {'status': 'nao_verificado', 'motivo': motivo, 'cold': [], 'celulas': [], 'api': None}
                salvar()
                continue
            config.update(cold=args.cold, warm=args.warm, aquecimentos=args.aquecimentos)
            base = rodada / perfil
            medicao = {'status': 'medido', 'motivo': None, 'cold': [], 'celulas': [], 'api': None,
                       'hashes': config['hashes'], 'transitorio_bert_ironia': None,
                       'motivo_transitorio': 'apenas_perfil_laya_pela_fabrica_api' if perfil != 'laya-onnx' else 'ver_eventos_api'}
            perfis[perfil] = medicao
            caminhos_cold = {nome: caminho for nome, caminho in config['caminhos'].items() if nome in args.cabecas}
            for i in range(args.cold):
                medicao['cold'].append(_executar({**config, 'modo': 'cold', 'caminhos': caminhos_cold},
                                                 base / f'cold-{i:02}', workspace, parametros=parametros))
                salvar()
            bloqueio_motor = None
            for i, celula in enumerate(matriz_direta(args.falas, args.tokens, args.cabecas, args.operacoes)):
                if celula['tipo'] == 'cabeca' and celula['cabeca'] not in config['caminhos']:
                    item = {'status': 'nao_verificado', 'motivo': 'cabeca_ausente', 'resumo': resumir_amostras([])}
                    medicao['celulas'].append({'celula': celula, 'coleta': item})
                elif celula['tipo'] == 'motor' and bloqueio_motor:
                    medicao['celulas'].append({'celula': celula, 'coleta': {'status': 'nao_verificado', 'motivo': bloqueio_motor,
                                                                                     'resumo': resumir_amostras([])}})
                else:
                    item = _executar({**config, 'modo': 'warm', 'celula': celula}, base / f'celula-{i:03}', workspace, parametros=parametros)
                    medicao['celulas'].append({'celula': celula, **item})
                    if celula['tipo'] == 'motor' and item['coleta'].get('motivo') in {'fusor_sem_procedencia', 'cabecas_ausentes'}:
                        bloqueio_motor = item['coleta']['motivo']
                salvar()
            if not args.sem_api:
                medicao['api'] = _executar(config, base / 'api', workspace, api=True, parametros=parametros)
                salvar()
            resultados = [r['coleta'] for r in medicao['cold'] + medicao['celulas']]
            if medicao['api']:
                resultados.append(medicao['api']['coleta'])
            if any(r.get('status') == 'erro' for r in resultados):
                medicao.update(status='erro', motivo='matriz_com_erros')
            elif any(r.get('status') != 'medido' for r in resultados):
                medicao.update(status='nao_verificado', motivo='matriz_com_impedimentos')
        except (ValueError, OSError, ImportError):
            perfis.setdefault(perfil, {}).update(status='erro', motivo='preparacao_ou_coleta_recusada')
        salvar()
    erro = any(p['status'] == 'erro' for p in perfis.values())
    incompleto = any(p['status'] != 'medido' for p in perfis.values())
    dados.update(status='erro' if erro else 'nao_verificado' if incompleto else 'medido',
                 motivo='matriz_com_impedimentos' if incompleto else None)
    salvar()
    salvar_resultado(workspace, dados)
    return 1 if erro else 2 if incompleto else 0


if __name__ == '__main__':
    raise SystemExit(main())
