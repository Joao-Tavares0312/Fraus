"""O tokenizador do backend ONNX: o MESMO resultado, sem importar `transformers`.

`from transformers import AutoTokenizer` custava de 2 a 3,5 s num processo
frio (medido em 20/11/2026) -- mais que abrir uma sessao ONNX -- so para chegar
na biblioteca `tokenizers`, que e quem tokeniza de fato. O backend passou a
ler o `tokenizer.json` direto.

A troca so vale se a codificacao for IDENTICA: um id diferente muda a entrada
do modelo sem erro nenhum, e os modelos estao congelados. Por isso o teste que
manda aqui e o de equivalencia, id por id, contra o `AutoTokenizer`.
"""

import json
import subprocess
import sys

import numpy as np
import pytest

from fraus.sinais.onnx import TAMANHO_MAXIMO, TokenizadorOnnx

VOCABULARIO = [
    "[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]",
    "o", "pedido", "nao", "não", "chegou", "pessimo", "péssimo", "obrigado", "ok",
    "atendimento", "##s", "##o", "##u", "##mento", "!", "?", ",", ".", "A", "a", "N",
    "Ã", "##Ã", "##O", "é", "e", "c", "##h", "##e", "##g", "p", "##é", "##ss", "##i", "##m",
]

TEXTOS = [
    "o pedido não chegou",
    "PÉSSIMO atendimento!!!",
    "ok, obrigado 🙂",
    "",
    "   ",
    "NÃO chegou?",
    "palavra_que_nao_existe 12345",
    "o pedido " * 400,  # passa do teto: tem de truncar igual
    "linha\ncom\tquebra e  espaços",
    "acentuação péssimo e pessimo",
]


@pytest.fixture(scope="module")
def diretorio(tmp_path_factory):
    """Um BERT de mentira com as MESMAS pecas dos artefatos reais.

    WordPiece, `BertNormalizer` sem caixa baixa e sem tirar acento, e o
    pos-processador [CLS] A [SEP] -- a configuracao do BERTimbau cased.
    """
    from tokenizers import Tokenizer, models, normalizers, pre_tokenizers, processors

    pasta = tmp_path_factory.mktemp("tokenizador")
    tokenizador = Tokenizer(models.WordPiece(
        {termo: indice for indice, termo in enumerate(VOCABULARIO)}, unk_token="[UNK]"))
    tokenizador.normalizer = normalizers.BertNormalizer(
        clean_text=True, handle_chinese_chars=True, strip_accents=None, lowercase=False)
    tokenizador.pre_tokenizer = pre_tokenizers.BertPreTokenizer()
    tokenizador.post_processor = processors.TemplateProcessing(
        single="[CLS] $A [SEP]", pair="[CLS] $A [SEP] $B:1 [SEP]:1",
        special_tokens=[("[CLS]", 2), ("[SEP]", 3)])
    tokenizador.save(str(pasta / "tokenizer.json"))
    (pasta / "tokenizer_config.json").write_text(json.dumps({
        "tokenizer_class": "BertTokenizer", "do_lower_case": False, "strip_accents": None,
        "tokenize_chinese_chars": True, "cls_token": "[CLS]", "sep_token": "[SEP]",
        "pad_token": "[PAD]", "unk_token": "[UNK]", "mask_token": "[MASK]",
    }))
    (pasta / "special_tokens_map.json").write_text(json.dumps({
        "cls_token": "[CLS]", "sep_token": "[SEP]", "pad_token": "[PAD]",
        "unk_token": "[UNK]", "mask_token": "[MASK]",
    }))
    (pasta / "vocab.txt").write_text("\n".join(VOCABULARIO) + "\n")
    return pasta


def test_codifica_identico_ao_autotokenizer(diretorio):
    from transformers import AutoTokenizer

    referencia = AutoTokenizer.from_pretrained(str(diretorio))(
        TEXTOS, truncation=True, max_length=TAMANHO_MAXIMO, padding=True, return_tensors="np")

    obtido = TokenizadorOnnx(diretorio)(TEXTOS)

    assert set(obtido) == set(referencia)
    for nome in referencia:
        np.testing.assert_array_equal(obtido[nome], referencia[nome], err_msg=nome)


def test_um_texto_sozinho_tambem_bate(diretorio):
    """O preenchimento depende do lote: cada texto sozinho e outro caso."""
    from transformers import AutoTokenizer

    referencia = AutoTokenizer.from_pretrained(str(diretorio))
    tokenizador = TokenizadorOnnx(diretorio)
    for texto in TEXTOS:
        esperado = referencia(
            [texto], truncation=True, max_length=TAMANHO_MAXIMO, padding=True, return_tensors="np")
        obtido = tokenizador([texto])
        for nome in esperado:
            np.testing.assert_array_equal(obtido[nome], esperado[nome], err_msg=f"{nome}: {texto[:30]!r}")


def test_trunca_no_teto_e_devolve_inteiros(diretorio):
    obtido = TokenizadorOnnx(diretorio)(["o pedido " * 400, "ok"])

    assert obtido["input_ids"].shape == (2, TAMANHO_MAXIMO)
    assert obtido["attention_mask"][1].sum() == 3  # [CLS] ok [SEP]; o resto e preenchimento
    assert all(valor.dtype == np.int64 for valor in obtido.values())


def test_sem_tokenizer_json_falha_alto(tmp_path):
    """Invariante 7: artefato incompleto nao vira tokenizador improvisado."""
    with pytest.raises(FileNotFoundError):
        TokenizadorOnnx(tmp_path)


def test_tokenizar_nao_arrasta_o_transformers(diretorio):
    """A razao de ser da troca: o import caro nao pode voltar por descuido."""
    codigo = (
        "import sys\n"
        "from fraus.sinais.onnx import TokenizadorOnnx\n"
        f"TokenizadorOnnx({str(diretorio)!r})(['ok'])\n"
        "assert 'transformers' not in sys.modules, 'transformers foi importado'\n"
        "assert 'torch' not in sys.modules, 'torch foi importado'\n"
    )
    resultado = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr
