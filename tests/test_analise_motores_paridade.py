"""Contratos observáveis dos coletores offline; dublês somente neste arquivo."""
import hashlib
import json
from pathlib import Path

import pytest

from scripts.analise_motores import paridade
from scripts.analise_motores import _worker as worker


def _snapshot(perfil='torch', checkpoint='mesmo'):
    return {'perfil': perfil, 'checkpoint': checkpoint, 'motor_completo': True,
            'casos': [
                {'id': 'sem', 'probabilidades': None, 'classe': None, 'score': None, 'nota': None, 'categoria': None},
                {'id': 'a', 'probabilidades': {'texto': [[.6, .3, .1]]}, 'classe': 0, 'score': 10., 'nota': 1, 'categoria': 'detrator'},
                {'id': 'b', 'probabilidades': {'texto': [[.1, .3, .6]]}, 'classe': 2, 'score': 90., 'nota': 9, 'categoria': 'promotor'}]}


def test_paridade_preserva_nulls_denominadores_ids_e_flips():
    base, candidato = _snapshot(), _snapshot('onnx-fp32')
    candidato['casos'][1].update(probabilidades={'texto': [[.2, .7, .1]]}, classe=1, score=11., nota=2)
    candidato['casos'][2]['categoria'] = 'neutro'
    comparacao = paridade.comparar_snapshots(base, candidato, 'fp32')
    assert comparacao['probabilidade']['n'] == 6
    assert comparacao['probabilidade']['max_delta'] == pytest.approx(.4)
    assert comparacao['score']['n'] == 2
    assert comparacao['score']['ids_nulos'] == ['sem']
    assert comparacao['classe']['ids_flips'] == ['a']
    assert comparacao['nota']['ids_flips'] == ['a']
    assert comparacao['categoria']['ids_flips'] == ['b']
    assert comparacao['aceite']['aprovado'] is False


def test_modelos_distintos_nao_sao_equivalencia():
    with pytest.raises(ValueError, match='checkpoint'):
        paridade.comparar_snapshots(_snapshot(), _snapshot('laya-onnx', 'outro'), 'fp32')


def test_ids_ou_formas_desalinhados_sao_recusados():
    candidato = _snapshot('onnx-fp32')
    candidato['casos'][1]['id'] = 'inesperado'
    with pytest.raises(ValueError, match='alinhamento'):
        paridade.comparar_snapshots(_snapshot(), candidato, 'fp32')
    candidato = _snapshot('onnx-fp32')
    candidato['casos'][1]['probabilidades']['texto'][0].pop()
    with pytest.raises(ValueError, match='alinhamento'):
        paridade.comparar_snapshots(_snapshot(), candidato, 'fp32')


def test_int8_sem_holdout_nao_recebe_aceite():
    comparacao = paridade.comparar_snapshots(_snapshot(), _snapshot('onnx-int8'), 'int8')
    assert comparacao['aceite']['aprovado'] is None
    assert comparacao['aceite']['queda_f1_macro'] is None


def test_previsoes_reutilizadas_exigem_textos_e_indices_identicos():
    memoria = worker.PrevisoesAlinhadas(['a', 'b'], [[.2, .8], [.9, .1]])
    assert memoria.prever_mensagens(['a', 'b']) == [[.2, .8], [.9, .1]]
    with pytest.raises(ValueError, match='alinhamento'):
        memoria.prever_mensagens(['b', 'a'])
    with pytest.raises(ValueError, match='alinhamento'):
        worker.PrevisoesAlinhadas(['a'], [])


def test_repeticoes_distinguem_igualdade_exata_de_tolerancia():
    valores = [[[.2, .8]], [[.2, .8]], [[.2000001, .7999999]], [[.2, .8]], [[.2, .8]]]
    resumo = worker.resumir_repeticoes(valores)
    assert resumo['n'] == 5
    assert resumo['igualdade_exata'] is False
    assert resumo['max_delta'] == pytest.approx(.0000001)
    assert worker.resumir_repeticoes([valores[0]] * 5)['igualdade_exata'] is True


def test_fusor_sem_procedencia_nunca_e_carregado(tmp_path, monkeypatch):
    import fraus.fusor
    caminho = tmp_path / 'fusor.joblib'
    caminho.write_bytes(b'pickle desconhecido')
    monkeypatch.setattr(fraus.fusor.Fusor, 'carregar', lambda *_: pytest.fail('desserializacao indevida'))
    assert worker.carregar_fusor_confiavel({'fusor': str(caminho)}) is None
    manifesto = tmp_path / 'manifesto.json'
    manifesto.write_text(json.dumps({'sha256': hashlib.sha256(caminho.read_bytes()).hexdigest()}))
    assert worker.carregar_fusor_confiavel({'fusor': str(caminho), 'manifesto_fusor': str(manifesto)}) is None


def test_copias_tem_hash_igual_inode_distinto_e_recusam_links(tmp_path):
    origem = tmp_path / 'origem'
    origem.mkdir()
    peso = origem / 'model.safetensors'
    peso.write_bytes(b'cabecalho')
    destino = tmp_path / 'copia'
    evidencia = paridade.copiar_com_hashes(origem, destino)
    assert evidencia['originais'] == evidencia['copias']
    assert peso.stat().st_ino != (destino / peso.name).stat().st_ino
    (origem / 'link').symlink_to(peso)
    with pytest.raises(ValueError, match='symlink'):
        paridade.copiar_com_hashes(origem, tmp_path / 'recusada')


def test_corpus_invalido_recusa_timezone_naive_e_lista_vazia(tmp_path):
    caminho = tmp_path / 'ouro.jsonl'
    valida = {'id': 'a', 'canal': 'teste', 'iniciada_em': '2026-10-16T00:00:00+00:00',
              'mensagens': [{'autor': 'cliente', 'texto': 'oi', 'enviada_em': '2026-10-16T00:00:01+00:00'}]}
    caminho.write_text(json.dumps({'id': 'a', 'conversa': valida}) + '\n')
    assert worker.carregar_corpus(caminho)[0]['conversa'].id == 'a'
    for campo in ('mensagens', 'enviada_em', 'iniciada_em'):
        invalida = json.loads(json.dumps(valida))
        if campo == 'mensagens':
            invalida['mensagens'] = []
        elif campo == 'enviada_em':
            invalida['mensagens'][0][campo] = '2026-10-16T00:00:01'
        else:
            invalida[campo] = '2026-10-16T00:00:00'
        caminho.write_text(json.dumps({'id': 'a', 'conversa': invalida}) + '\n')
        with pytest.raises(ValueError):
            worker.carregar_corpus(caminho)


def test_ausencia_de_artefatos_nao_fabrica_snapshot(tmp_path):
    workspace = tmp_path / 'ws'
    assert paridade.main(['--workspace', str(workspace), '--perfis', 'onnx-fp32',
                          '--onnx', str(tmp_path / 'ausente'), '--modelos', str(tmp_path / 'ausente')]) == 2
    dados = json.loads((workspace / 'experimentos/resultados/paridade.json').read_text())
    assert dados['status'] == 'nao_verificado'
    assert dados['medicoes']['perfis']['onnx-fp32']['snapshot'] is None
    assert not list(workspace.rglob('saidas-*.json'))


def test_worker_sem_corpus_mede_bordas_cinco_vezes_sem_motor(tmp_path, monkeypatch):
    class Cabeca:
        def __init__(self):
            self.textos = []
        def prever_mensagens(self, textos):
            self.textos.append(list(textos))
            return [[.1, .2, .7] for _ in textos]
    cabeca = Cabeca()
    monkeypatch.setattr(worker, 'carregar_perfil', lambda config: {'texto': cabeca})
    dados = worker.coletar_perfil({'perfil': 'torch', 'checkpoint': 'teste', 'corpus': str(tmp_path / 'nao-existe')})
    assert dados['motor_completo'] is False
    assert len(dados['bordas']) == 4
    assert all(caso['repeticoes']['n'] == 5 for caso in dados['bordas'])
    assert any('maravilha' in texto for lote in cabeca.textos for texto in lote)
    assert any(len(texto.split()) > 192 for lote in cabeca.textos for texto in lote)
    assert dados['casos'] == []


def test_worker_erros_nao_expoem_mensagem_arbitraria(tmp_path, monkeypatch, capsys):
    config = tmp_path / 'config.json'
    config.write_text(json.dumps({'perfil': 'torch', 'saida': str(tmp_path / 'resultado.json')}))
    def falhar(_):
        raise RuntimeError('TOKEN_SECRETO https://privado.invalid')
    monkeypatch.setattr(worker, 'coletar_perfil', falhar)
    assert worker.main(['--config', str(config)]) == 1
    texto = (tmp_path / 'resultado.json').read_text() + capsys.readouterr().out
    assert 'TOKEN_SECRETO' not in texto and 'privado.invalid' not in texto
    assert json.loads((tmp_path / 'resultado.json').read_text())['categoria_erro'] == 'carga_ou_inferencia'


def test_features_reais_sem_pickle_preservam_indices_nulls_e_log1p(tmp_path, monkeypatch):
    from fraus.fusor import NOMES_FEATURES, FEATURES_EM_LOG, vetorizar
    class Cabeca:
        def __init__(self, valores):
            self.valores = valores
            self.lotes = []
        def prever_mensagens(self, textos):
            self.lotes.append(list(textos))
            return [self.valores[:] for _ in textos]
    cabecas = {'texto': Cabeca([.1, .2, .7]), 'emocao': Cabeca([1 / 7] * 7), 'ironia': Cabeca([.8, .2])}
    monkeypatch.setattr(worker, 'carregar_perfil', lambda _: cabecas)
    base = {'canal': 'sintetico', 'iniciada_em': '2026-10-16T00:00:00+00:00',
            'encerrada_em': '2026-10-16T00:05:00+00:00'}
    registros = []
    for identificador, mensagens in (
        ('sem', [('bot', 'TEXTO EXCLUSIVO DO BOT')]),
        ('cortesia', [('cliente', 'ok, obrigado')]),
        ('sinal', [('cliente', 'Minha entrega foi ótima!'), ('bot', 'TEXTO EXCLUSIVO DO BOT'),
                   ('cliente', 'Foi muito bom receber ajuda.')]),
    ):
        conversa = {**base, 'id': identificador, 'mensagens': [
            {'autor': autor, 'texto': texto, 'enviada_em': f'2026-10-16T00:0{i}:00+00:00'}
            for i, (autor, texto) in enumerate(mensagens)]}
        registros.append({'id': identificador, 'conversa': conversa})
    corpus = tmp_path / 'corpus.jsonl'
    corpus.write_text('\n'.join(json.dumps(r) for r in registros) + '\n')
    dados = worker.coletar_perfil({'perfil': 'torch', 'corpus': str(corpus)})
    sem, cortesia, sinal = dados['casos']
    for caso in (sem, cortesia):
        assert caso['features'] is None and caso['vetor'] is None
        assert caso['score'] is None and caso['nota'] is None and caso['categoria'] is None
    assert sem['motivo_sem_sinal'] == 'sem_fala_do_cliente'
    assert cortesia['motivo_sem_sinal'] == 'so_cortesia'
    assert sinal['indices_cliente'] == [0, 2]
    assert list(sinal['features']) == list(NOMES_FEATURES)
    assert sinal['vetor'] == vetorizar(sinal['features'])
    assert any(sinal['features'][nome] > sinal['vetor'][list(NOMES_FEATURES).index(nome)] for nome in FEATURES_EM_LOG)
    assert sinal['repeticoes_motor']['igualdade_exata'] is True
    assert sinal['score'] is None and dados['motor_completo'] is False
    assert not any('TEXTO EXCLUSIVO DO BOT' in lote for cabeca in cabecas.values() for lote in cabeca.lotes)


def test_nan_e_recusado_antes_de_publicar_metricas():
    candidato = _snapshot('onnx-fp32')
    candidato['casos'][1]['probabilidades']['texto'][0][0] = float('nan')
    with pytest.raises(ValueError, match='finito'):
        paridade.comparar_snapshots(_snapshot(), candidato, 'fp32')


def test_fusor_com_manifesto_recente_e_hash_autoafirmado_continua_recusado(tmp_path, monkeypatch):
    import fraus.fusor
    fusor = tmp_path / 'fusor.joblib'
    fusor.write_bytes(b'nao deve executar')
    manifesto = tmp_path / 'manifesto.json'
    manifesto.write_text(json.dumps({'sha256': hashlib.sha256(fusor.read_bytes()).hexdigest(),
                                     'fonte': 'fonte-declarada', 'emitido_em': '2026-10-16T01:00:00+00:00'}))
    monkeypatch.setattr(fraus.fusor.Fusor, 'carregar', lambda *_: pytest.fail('pickle recente nao autorizado'))
    config = {'workspace': str(tmp_path), 'fusor': str(fusor), 'manifesto_fusor': str(manifesto),
              'fonte_confiavel_fusor': 'fonte-declarada',
              'sha256_manifesto_fusor': hashlib.sha256(manifesto.read_bytes()).hexdigest()}
    assert worker.carregar_fusor_confiavel(config) is None


def test_worker_recusa_saida_fora_workspace_sem_escrever(tmp_path):
    workspace = tmp_path / 'ws'
    workspace.mkdir()
    saida = tmp_path / 'protegido.json'
    config = workspace / 'config.json'
    config.write_text(json.dumps({'workspace': str(workspace), 'saida': str(saida)}))
    assert worker.main(['--config', str(config)]) == 1
    assert not saida.exists()
