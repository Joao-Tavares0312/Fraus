"""Contratos do laboratório HTTP; dublês existem só nestes testes."""
from pathlib import Path

import pytest

from scripts.analise_motores import _api_worker as api


def config_externa(tmp_path):
    return {'workspace': str(tmp_path), 'perfil': 'torch', 'caminhos': {},
            'saida': str(tmp_path / 'api.json'), 'cold': 1, 'warm': 2, 'aquecimentos': 1}


def test_estatistica_inclui_erros_e_timeout_no_denominador():
    amostras = [{'status_code': 200, 'duracao_s': 1., 'categoria_erro': None},
                {'status_code': 500, 'duracao_s': 2., 'categoria_erro': 'http'},
                {'status_code': None, 'duracao_s': 3., 'categoria_erro': 'timeout'}]
    resumo = api.resumir_http(amostras, residencia_s=6.)
    assert resumo['n'] == 3 and resumo['sucessos'] == 1
    assert resumo['erros'] == 2 and resumo['timeouts'] == 1
    assert resumo['taxa_sucesso'] == pytest.approx(1 / 3)
    assert resumo['latencia_s']['p50'] == 2.
    assert resumo['throughput_sucessos_s'] == pytest.approx(1 / 6)
    assert resumo['amostras'] == amostras


def test_sem_sucesso_nao_fabrica_throughput():
    resumo = api.resumir_http([{'status_code': 400, 'duracao_s': .1,
                               'categoria_erro': 'http'}], residencia_s=.1)
    assert resumo['throughput_sucessos_s'] is None
    assert resumo['latencia_sucessos_s'] is None
    assert resumo['recusas_400'] == 1


def test_recusa_url_config_e_caminhos_fora_workspace(tmp_path):
    config = config_externa(tmp_path)
    with pytest.raises(ValueError):
        api.validar_config({**config, 'url': 'https://exemplo.invalid'})
    with pytest.raises(ValueError):
        api.validar_config({**config, 'saida': str(tmp_path.parent / 'fora.json')})
    with pytest.raises(ValueError):
        api.validar_config({**config, 'caminhos': {'texto': str(Path(__file__).parent)}})
    link = tmp_path / 'link'
    link.symlink_to(tmp_path.parent, target_is_directory=True)
    with pytest.raises(ValueError):
        api.validar_config({**config, 'saida': str(link / 'fora.json')})


def test_sem_manifesto_nao_chama_factory(tmp_path):
    config = config_externa(tmp_path)
    chamadas = []
    construir = api.fabrica_guardada(config, lambda: chamadas.append(True))
    with pytest.raises(api.PreRequisitoAusente):
        construir()
    assert chamadas == []


def test_csv_canonico_tem_n_clientes_e_vinte_conversas_para_repontuar():
    import csv
    import io
    linhas = list(csv.DictReader(io.StringIO(api.csv_sintetico(100))))
    assert len(linhas) == 100
    assert {linha['autor'] for linha in linhas} == {'cliente'}
    assert len({linha['conversa_id'] for linha in linhas}) == 1
    assert all('+' in linha['enviada_em'] for linha in linhas)
    lote = list(csv.DictReader(io.StringIO(api.csv_sintetico(1, conversas=20))))
    assert len({linha['conversa_id'] for linha in lote}) == 20


def test_readiness_e_recusa_reais_sem_fusor_nao_aquecem(tmp_path):
    dados = api.coletar_api(config_externa(tmp_path))
    assert dados['status'] == 'nao_verificado'
    assert dados['motivo'] == 'fusor_sem_procedencia'
    assert dados['motor_completo'] is False
    assert dados['sondas']['readiness_antes']['status_code'] == 503
    assert dados['sondas']['recusa_100']['status_code'] == 400
    assert dados['sondas']['readiness_depois']['estado_motor'] == 'frio'
    assert dados['sondas']['construcoes_motor'] == 0
    assert dados['repontuacao']['status'] == 'nao_verificado'
    assert all(c['status'] == 'nao_verificado' for c in dados['celulas']
               if c['mensagens_cliente'] != 100)
    recusa = next(c for c in dados['celulas'] if c['mensagens_cliente'] == 100)
    assert recusa['status'] == 'medido' and recusa['n'] == 2
    assert recusa['operacao'] == 'recusa_400_nao_inferencia'
    assert len(recusa['aquecimentos_excluidos']) == 1
    assert recusa['recusas_400'] == 2 and recusa['sucessos'] == 0
    assert recusa['throughput_sucessos_s'] is None
    concorrencia = [c for c in dados['concorrencia'] if c['mensagens_cliente'] == 100]
    assert [c['clientes'] for c in concorrencia] == [1, 2, 4, 8]
    for celula in concorrencia:
        assert celula['status'] == 'medido'
        assert celula['n'] == celula['clientes'] * 20
        assert celula['recusas_400'] == celula['n'] == celula['erros']
        assert celula['throughput_sucessos_s'] is None
        assert celula['readiness']
        assert all(s['status_code'] == 503 and s['estado_motor'] == 'frio'
                   for s in celula['readiness'])
        assert all('total' in a['server_timing_ms'] for a in celula['amostras'])
    assert dados['sondas']['construcoes_motor_total'] == 0
    assert all(s['construcoes_motor'] == 0 for s in dados['recursos']['servidores'])
    assert dados['recursos']['servidores'][0]['banco_fechado'] is True
    assert dados['recursos']['servidores'][0]['rss_amostras']
    assert dados['recursos']['cliente']['rss_bytes'] is not None
    assert dados['rede'] == {'host': '127.0.0.1', 'porta': 'efemera', 'workers': 1,
                            'trust_env': False, 'redirects': False}


def test_server_timing_apenas_metricas_conhecidas():
    assert api.ler_server_timing('total;dur=12.5, inferencia;dur=10, segredo;dur=99') == {
        'total': 12.5, 'inferencia': 10.}
    assert api.ler_server_timing('total;dur=nan, carga_modelo;dur=inf, consulta_db;dur=-2') == {}


@pytest.mark.parametrize('status', [400, 500])
def test_concorrencia_tem_vinte_tentativas_por_cliente_e_preserva_erros(monkeypatch, status):
    import contextlib
    import threading
    chamadas = []
    trava = threading.Lock()

    @contextlib.contextmanager
    def cliente_local(url):
        assert url == 'http://127.0.0.1:12345'
        yield object()

    def pedido(cliente, metodo, caminho, **kwargs):
        with trava:
            chamadas.append((metodo, caminho))
        return {'status_code': status if metodo == 'POST' else 503, 'duracao_s': .001,
                'categoria_erro': 'http', 'server_timing_ms': {}}

    monkeypatch.setattr(api, 'cliente_loopback', cliente_local)
    monkeypatch.setattr(api, '_pedido', pedido)
    dados = api.medir_concorrencia('http://127.0.0.1:12345', 5, 4)
    assert dados['n'] == 80 and dados['erros'] == 80
    assert dados['throughput_sucessos_s'] is None
    assert dados['inicio_sincronizado'] is True
    assert len([c for c in chamadas if c == ('POST', '/analisar')]) == 80
    assert {a['cliente'] for a in dados['amostras']} == {0, 1, 2, 3}
    assert dados['readiness']
    assert dados['recusas_400'] == (80 if status == 400 else 0)


def test_repontuacao_aguarda_get_terminal_nao_confunde_202_com_fim(monkeypatch):
    import contextlib
    from types import SimpleNamespace
    respostas = iter([
        {'status_code': 202, 'categoria_erro': None},
        {'status_code': 200, 'categoria_erro': None, 'estado': 'rodando', 'total': 20, 'feitas': 2},
        {'status_code': 200, 'categoria_erro': None, 'estado': 'concluido', 'total': 20, 'feitas': 20},
    ])
    metodos = []

    def pedido(cliente, metodo, caminho, **kwargs):
        metodos.append(metodo)
        return next(respostas)

    monkeypatch.setattr(api, 'cliente_loopback', lambda url: contextlib.nullcontext(object()))
    monkeypatch.setattr(api, '_pedido', pedido)
    monkeypatch.setattr(api.time, 'sleep', lambda segundos: None)
    dados = api._repontuar(SimpleNamespace(url='http://127.0.0.1:12345'))
    assert metodos == ['POST', 'GET', 'GET']
    assert dados['status'] == 'medido'
    assert dados['terminal']['feitas'] == 20
    assert dados['duracao_completa_s'] is not None
