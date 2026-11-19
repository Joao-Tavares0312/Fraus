"""Contratos do laboratório; os dublês nunca entram nas medições reais."""
import json
from contextlib import nullcontext

import pytest

from scripts.analise_motores import desempenho
from scripts.analise_motores import _desempenho_worker as worker


def test_percentis_lineares_denominador_e_custo():
    amostras = [{'status': 'sucesso', 'duracao_s': x, 'cpu_s': x / 2} for x in (1., 2., 3., 4.)]
    amostras += [{'status': 'erro', 'duracao_s': 5., 'cpu_s': 1.},
                 {'status': 'timeout', 'duracao_s': 300., 'cpu_s': None}]
    r = desempenho.resumir_amostras(amostras)
    assert r['tentativas'] == 6 and r['sucessos'] == 4
    assert r['erros'] == 1 and r['timeouts'] == 1
    assert r['p50_s'] == 2.5
    assert r['p95_s'] == pytest.approx(3.85)
    assert r['p99_s'] == pytest.approx(3.97)
    assert r['taxa_sucesso'] == 4 / 6
    assert r['cpu_s_por_1000_tentativas'] is None  # CPU desconhecida não vira zero.
    assert r['residencia_s_por_1000_tentativas'] == pytest.approx(315 / 6 * 1000)


def test_sem_sucesso_nao_fabrica_metricas():
    r = desempenho.resumir_amostras([{'status': 'timeout', 'duracao_s': None, 'cpu_s': None}])
    assert r['tentativas'] == 1 and r['sucessos'] == 0
    assert r['p50_s'] is r['p95_s'] is r['p99_s'] is None
    assert r['throughput_sucessos_s'] is None
    assert desempenho.resumir_amostras([])['taxa_sucesso'] is None
    with pytest.raises(ValueError):
        desempenho.resumir_amostras([{'status': 'sucesso', 'duracao_s': float('nan'), 'cpu_s': 1}])


def test_matriz_completa_sem_confundir_heads_com_motor():
    matriz = desempenho.matriz_direta()
    assert len(matriz) == 72
    assert {c['falas'] for c in matriz} == {1, 5, 20, 100}
    assert {c['tokens_alvo'] for c in matriz} == {16, 128, 256}
    assert {c['operacao'] for c in matriz if c['tipo'] == 'motor'} == {'pontuar', 'atribuir', 'analisar'}
    assert {c['cabeca'] for c in matriz if c['tipo'] == 'cabeca'} == {'texto', 'emocao', 'ironia'}


def test_aquecimentos_excluidos_e_checkpoint_incremental(tmp_path, monkeypatch):
    chamadas, checkpoints = [], []
    monkeypatch.setattr(worker, 'prazo_operacao', lambda **kw: nullcontext())
    def operacao():
        chamadas.append(1)
        if len(chamadas) == 5:
            raise RuntimeError('segredo arbitrario que nao pode sair')
    r = worker.medir_repeticoes(operacao, warm=4, aquecimentos=3,
                                checkpoint=lambda dados: checkpoints.append(json.loads(json.dumps(dados))))
    assert len(chamadas) == 7
    assert len(r['aquecimentos']) == 3
    assert len(r['amostras']) == 4
    assert r['resumo']['tentativas'] == 4
    assert r['resumo']['sucessos'] == 3
    assert checkpoints[-1]['resumo']['tentativas'] == 4
    assert 'segredo' not in json.dumps(r)


def test_abortada_conta_chamada_em_andamento_e_nao_inventa_pendentes():
    parcial = {'amostras': [{'status': 'sucesso', 'duracao_s': 1., 'cpu_s': .5}],
               'em_andamento': {'fase': 'warm', 'indice': 1}, 'aquecimentos': []}
    r = desempenho.completar_aborto(parcial, 'timeout_operacao')
    assert r['resumo']['tentativas'] == 2
    assert r['resumo']['timeouts'] == 1
    assert r['amostras'][-1]['duracao_s'] is None
    assert r['amostras'][-1]['cpu_s'] is None


def test_tokens_contados_pelo_tokenizador_e_truncamento():
    class Tokenizador:
        def __call__(self, texto, **kwargs):
            ids = [101] + list(range(len(texto.split()))) + [102]
            if kwargs.get('truncation'):
                ids = ids[:kwargs['max_length']]
            return {'input_ids': ids}
    texto, dados = worker.texto_sintetico(Tokenizador(), 256)
    assert dados['tokens_sem_truncar'] == 256
    assert dados['tokens_retidos'] == 192 and dados['truncado'] is True
    assert len(texto.split()) == 254


def test_prerequisito_fusor_nao_construido(monkeypatch):
    monkeypatch.setattr(worker, 'carregar_fusor_confiavel', lambda config: None)
    r = worker.coletar({'workspace': '/tmp/lab', 'perfil': 'torch',
                        'celula': {'tipo': 'motor', 'operacao': 'pontuar', 'falas': 1, 'tokens_alvo': 16}})
    assert r['status'] == 'nao_verificado'
    assert r['motivo'] == 'fusor_sem_procedencia'
    assert r['resumo']['p50_s'] is None




def test_conversa_sintetica_respeita_modelo_canonico():
    conversa = worker._conversa('Meu pedido continua sem solução.', 5)
    assert len(conversa.mensagens_cliente) == 5
    assert len(conversa.mensagens) == 10
    assert conversa.iniciada_em.tzinfo is not None
    assert conversa.encerrada_em > conversa.iniciada_em


def test_orquestrador_registra_ausencia_sem_executar_worker(tmp_path, monkeypatch):
    workspace = tmp_path / 'workspace'
    monkeypatch.setattr(desempenho, '_checkpoint_torch', lambda pasta: None)
    monkeypatch.setattr(desempenho, '_preparar_config',
                        lambda *args: (None, [], 'pesos_de_cabecas_ausentes'))
    def proibido(*args, **kwargs):
        raise AssertionError('nao ha pesos para medir')
    monkeypatch.setattr(desempenho, 'executar_isolado', proibido)
    assert desempenho.main(['--workspace', str(workspace), '--perfis', 'torch']) == 2
    dados = json.loads((workspace / 'experimentos/resultados/desempenho.json').read_text())
    perfil = dados['medicoes']['perfis']['torch']
    assert perfil['cold'] == [] and perfil['celulas'] == []
    assert perfil['api'] is None and perfil['status'] == 'nao_verificado'


def test_supervisor_preserva_parcial_sem_stdout(tmp_path, monkeypatch):
    workspace = tmp_path / 'workspace'
    pasta = workspace / 'celula'
    def executar(modulo, argumentos, ws, **kwargs):
        assert kwargs['timeout'] == 0
        config = json.loads((pasta / 'config.json').read_text())
        parcial = {'amostras': [], 'em_andamento': {'fase': 'warm', 'indice': 0}}
        from pathlib import Path
        Path(config['saida']).write_text(json.dumps(parcial))
        return {'returncode': 124, 'categoria_erro': 'timeout_operacao',
                'duracao_s': 300., 'stdout': 'SEGREDO'}
    monkeypatch.setattr(desempenho, 'executar_isolado', executar)
    r = desempenho._executar({}, pasta, workspace)
    assert r['coleta']['resumo']['tentativas'] == 1
    assert r['coleta']['resumo']['timeouts'] == 1
    assert 'SEGREDO' not in json.dumps(r)


def test_eventos_inclusivos_exclusivos_sem_somar_sobreposicao(monkeypatch):
    tempos = iter([0., 1., 2., 5., 9.])
    monkeypatch.setattr(worker.time, 'perf_counter', lambda: next(tempos))
    eventos = worker.EventosCarga(lambda: None)
    with eventos.etapa('pai'):
        with eventos.etapa('filho'):
            pass
    pai, filho = eventos.eventos
    assert pai['inclusivo_s'] == 8
    assert filho['inclusivo_s'] == 3
    assert pai['exclusivo_s'] == 5


