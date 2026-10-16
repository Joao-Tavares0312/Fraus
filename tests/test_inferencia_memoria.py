"""Lotes aceitos não podem exigir uma ativação proporcional ao atendimento inteiro."""
from pathlib import Path

import numpy as np
import pytest

from fraus.sinais.onnx import SessaoOnnx, SessaoMultitarefaOnnx, _softmax


class Tokenizador:
    def __call__(self, textos, **opcoes):
        ids = np.asarray([[int(t), 1, 0] for t in textos], dtype=np.int64)
        return {'input_ids': ids, 'attention_mask': (ids != 0).astype(np.int64)}


class RuntimeComOrcamento:
    """Simula falha de capacidade sem alocar gigabytes no teste de contrato."""
    def run(self, nomes, entradas):
        ids = entradas['input_ids'][:, 0].astype(np.float32)
        if len(ids) > 4:
            raise MemoryError('ativacao acima do orcamento')
        dimensoes = [3] if nomes is None else [3, 7, 2]
        return [np.stack([np.sin(ids + i) for i in range(d)], axis=1) for d in dimensoes]


def _sessao(classe):
    sessao = classe.__new__(classe)
    sessao._tokenizador = Tokenizador()
    sessao._entradas = {'input_ids', 'attention_mask'}
    sessao._sessao = RuntimeComOrcamento()
    return sessao


@pytest.mark.parametrize('n', [0, 1, 4, 5, 40, 61])
def test_lote_grande_preserva_todas_probabilidades_e_ordem_sem_estourar(n):
    textos = [str(i) for i in range(n)]
    saida = _sessao(SessaoOnnx).prever(textos)
    ids = np.arange(n, dtype=np.float32)
    esperado = _softmax(np.stack([np.sin(ids + i) for i in range(3)], axis=1)).tolist() if n else []
    assert saida == esperado


@pytest.mark.parametrize('n', [0, 5, 61])
def test_multitarefa_preserva_alinhamento_das_tres_cabecas_com_cauda(n):
    saida = _sessao(SessaoMultitarefaOnnx).prever_cabecas([str(i) for i in range(n)])
    ids = np.arange(n, dtype=np.float32)
    esperado = {nome: _softmax(np.stack([np.sin(ids + i) for i in range(d)], axis=1)).tolist() if n else []
                for nome, d in [('satisfacao', 3), ('emocao', 7), ('ironia', 2)]}
    assert saida == esperado


@pytest.mark.parametrize('backend', ['torch', 'onnx'])
def test_falha_da_cabeca_selecionada_nao_e_mascarada_por_artefato_obsoleto(monkeypatch, tmp_path, backend):
    from fraus.api import main
    from fraus.sinais import onnx, ironia_laya
    from fraus.sinais.texto import ModeloAusenteError

    class FalhaLaya(RuntimeError):
        pass

    def carregar_bert(caminho):
        if Path(caminho).name == 'ironia-nao-usada':
            raise ModeloAusenteError('artefato obsoleto ausente')
        return object()

    def carregar_laya():
        raise FalhaLaya('cabeca selecionada indisponivel')

    monkeypatch.setenv('FRAUS_IRONIA_BACKEND', 'laya-onnx' if backend == 'onnx' else 'laya')
    monkeypatch.setattr(main, 'ClassificadorTexto', carregar_bert)
    monkeypatch.setattr(main, 'ClassificadorEmocao', carregar_bert)
    monkeypatch.setattr(main, 'ClassificadorIronia', carregar_bert)
    monkeypatch.setattr(onnx, 'ClassificadorOnnx', carregar_bert)
    monkeypatch.setattr(main, 'CAMINHO_MODELO_IRONIA', tmp_path / 'ironia-nao-usada')
    monkeypatch.setattr(main, 'CAMINHO_ONNX_IRONIA', tmp_path / 'ironia-nao-usada')
    monkeypatch.setattr(ironia_laya, 'obter_classificador_ironia_laya_declarado', carregar_laya)
    with pytest.raises(FalhaLaya, match='cabeca selecionada indisponivel'):
        main.montar_classificadores(backend)
