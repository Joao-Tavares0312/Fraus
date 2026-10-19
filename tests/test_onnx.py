"""O backend ONNX: mesma interface, mesma falha alta, mesma ordem de classes.

Estes testes NAO carregam grafo nenhum -- os artefatos convertidos nao entram
no repositorio (pesam 318 MB) e nao foram promovidos. O que da para amarrar sem
eles e o contrato, que e justamente o que uma troca de backend pode quebrar em
silencio.
"""

import numpy as np
import pytest

from fraus.sinais.onnx import (
    ModeloOnnxAusenteError,
    SessaoMultitarefaOnnx,
    SessaoOnnx,
    _softmax,
)


def test_grafo_ausente_falha_alto_e_diz_o_que_fazer(tmp_path):
    """Invariante 7 nao afrouxa por troca de backend -- so muda o arquivo que falta."""
    with pytest.raises(ModeloOnnxAusenteError) as erro:
        SessaoOnnx(tmp_path)
    assert "encolher_modelos" in str(erro.value)


def test_o_softmax_nao_estoura_com_logit_grande():
    """Sem subtrair o maximo, `exp` vira inf e a linha inteira vira nan.

    Com int8 os logits chegam com magnitude diferente da do fp32, entao a
    estabilidade aqui deixa de ser preciosismo teorico.
    """
    saida = _softmax(np.array([[1000.0, 999.0, 1.0]], dtype=np.float32))
    assert not np.isnan(saida).any()
    assert saida.sum() == pytest.approx(1.0)


def test_o_softmax_preserva_a_ORDEM_das_classes():
    """Invariante 8: nenhuma reordenacao acontece na travessia do backend.

    Inverter a ordem nao levanta erro -- faz o sistema pontuar ao contrario em
    silencio, que e a falha mais cara de descobrir do projeto inteiro.
    """
    logits = np.array([[3.0, 1.0, 2.0]], dtype=np.float32)
    (linha,) = _softmax(logits).tolist()
    assert linha.index(max(linha)) == 0  # o maior logit continua sendo o indice 0
    assert linha[0] > linha[2] > linha[1]


def test_o_softmax_soma_um_por_linha():
    saida = _softmax(np.array([[1.0, 2.0, 3.0], [0.0, 0.0, 0.0]], dtype=np.float32))
    assert saida.sum(axis=-1) == pytest.approx([1.0, 1.0])


def test_multitarefa_exige_as_tres_saidas_nomeadas():
    sessao = SessaoMultitarefaOnnx.__new__(SessaoMultitarefaOnnx)
    sessao._tokenizador = lambda *args, **kwargs: {
        "input_ids": np.array([[1, 2]]),
        "attention_mask": np.array([[1, 1]]),
    }
    sessao._entradas = {"input_ids", "attention_mask"}

    class RuntimeFalso:
        def run(self, nomes, entradas):
            assert nomes == ["satisfacao_logits", "emocao_logits", "ironia_logits"]
            return [
                np.array([[1.0, 2.0, 3.0]]),
                np.array([[7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0]]),
                np.array([[4.0, 1.0]]),
            ]

    sessao._sessao = RuntimeFalso()
    resultado = sessao.prever_cabecas(["teste"])

    assert set(resultado) == {"satisfacao", "emocao", "ironia"}
    assert len(resultado["satisfacao"][0]) == 3
    assert len(resultado["emocao"][0]) == 7
    assert len(resultado["ironia"][0]) == 2


def test_a_referencia_torch_do_encolhimento_aplica_a_temperatura_do_artefato(tmp_path):
    """O ONNX aplica a temperatura de `fraus_receita.json`; a referencia tem de aplicar a mesma.

    Sem isso a paridade compara softmax(z/T) com softmax(z) e recusa a conversao
    de qualquer modelo com T != 1 -- em 19/10/2026 o fp32 da ironia deu
    Δp 0,099 por isso, nao por diferenca de executor.
    """
    torch = pytest.importorskip("torch")
    import importlib.util
    import json
    from pathlib import Path

    from transformers import BertConfig, BertForSequenceClassification, BertTokenizerFast

    palavras = ["bom", "ruim", "atendimento"]
    vocab = tmp_path / "vocab.txt"
    vocab.write_text("\n".join(["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", *palavras]))
    modelo_dir = tmp_path / "modelo"
    BertTokenizerFast(vocab_file=str(vocab), do_lower_case=True).save_pretrained(modelo_dir)
    torch.manual_seed(0)
    modelo = BertForSequenceClassification(BertConfig(
        vocab_size=len(palavras) + 5, hidden_size=16, num_hidden_layers=1,
        num_attention_heads=2, intermediate_size=32, num_labels=2,
    ))
    with torch.no_grad():  # logits grandes: T=2 muda a probabilidade de forma visivel
        modelo.classifier.weight.mul_(50)
    modelo.save_pretrained(modelo_dir)
    (modelo_dir / "fraus_receita.json").write_text(json.dumps({"temperatura": 2.0}))

    caminho = Path(__file__).resolve().parents[1] / "scripts" / "encolher_modelos.py"
    especificacao = importlib.util.spec_from_file_location("encolher_modelos", caminho)
    encolher = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(encolher)

    textos = ["atendimento bom", "ruim"]
    obtido = encolher._probabilidades_torch(modelo_dir, textos)

    tokenizador = BertTokenizerFast.from_pretrained(modelo_dir)
    modelo.eval()
    with torch.inference_mode():
        logits = modelo(**tokenizador(textos, padding=True, return_tensors="pt")).logits
    esperado = torch.softmax(logits / 2.0, dim=-1).tolist()
    assert np.allclose(obtido, esperado, atol=1e-6)
