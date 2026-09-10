"""A regra do EU AI Act que e regra de CODIGO, com guarda executavel.

Reconhecimento de emocao no LOCAL DE TRABALHO e proibido desde fev/2025, sem
excecao comercial. O Fraus classifica sete emocoes e roda sobre conversas de
ATENDIMENTO -- onde o atendente humano tambem aparece no transcript. A unica
coisa que separa o produto legitimo do produto proibido e QUEM ele pontua.

Isso esta escrito em docs/conformidade.md e no CLAUDE.md. Prosa envelhece em
silencio: alguem troca `mensagens_cliente` por `mensagens` num sinal para
"aproveitar mais texto", nenhum teste reclama, e o sistema passa a inferir
emocao de trabalhador. Estes testes fazem a regra falhar alto.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from fraus.modelos import Conversa, Mensagem

BASE = datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc)
RAIZ = Path(__file__).resolve().parents[1]

# Os sinais que leem TEXTO e portanto inferem alguma coisa sobre quem falou.
# `tempo.py` fica fora de proposito: ele mede relogio, nao pessoa.
SINAIS_SEMANTICOS = (
    "texto.py",
    "emocao.py",
    "ironia.py",
    "lexico.py",
    "estilo.py",
    "emoji.py",
    "incongruencia.py",
    "palavras.py",
)


def test_mensagens_cliente_exclui_bot_e_atendente_humano():
    conversa = Conversa(
        id="c1",
        canal="csv",
        iniciada_em=BASE,
        mensagens=[
            Mensagem(autor="cliente", texto="do cliente", enviada_em=BASE),
            Mensagem(autor="bot", texto="do bot", enviada_em=BASE),
            Mensagem(autor="humano", texto="do atendente", enviada_em=BASE),
        ],
    )
    assert [m.texto for m in conversa.mensagens_cliente] == ["do cliente"]


@pytest.mark.parametrize("arquivo", SINAIS_SEMANTICOS)
def test_nenhum_sinal_semantico_le_a_fala_do_atendente(arquivo):
    """Todo sinal que infere algo sobre pessoa le SO `mensagens_cliente`.

    A sonda e grosseira de proposito -- ela olha o texto do modulo, nao o
    comportamento -- porque o comportamento exigiria os tres BERTimbau
    carregados, e a regra precisa falhar em meio segundo de pytest para
    alguem ver antes de commitar.

    Se um sinal legitimamente precisar iterar `conversa.mensagens` (para
    contar turnos, por exemplo), este teste falha e a decisao vira consciente:
    ou o acesso e a contagem e nao a inferencia, e o teste ganha a excecao
    NOMEADA, ou alguem estava prestes a pontuar atendente sem perceber.
    """
    fonte = (RAIZ / "fraus" / "sinais" / arquivo).read_text(encoding="utf-8")
    assert "mensagens_cliente" in fonte, (
        f"{arquivo} le texto e nao passa por `mensagens_cliente`"
    )
    assert "conversa.mensagens" not in fonte.replace("conversa.mensagens_cliente", ""), (
        f"{arquivo} itera a transcricao INTEIRA -- a fala do atendente entraria "
        "na inferencia, e reconhecimento de emocao no local de trabalho e "
        "proibido pelo EU AI Act desde fev/2025. Ver docs/conformidade.md."
    )


def test_o_documento_de_conformidade_existe_e_declara_a_regra():
    """O CLAUDE.md aponta para ele, e apontar para arquivo que sumiu e pior
    que nao apontar: quem le confia na referencia e nao vai conferir."""
    doc = (RAIZ / "docs" / "conformidade.md").read_text(encoding="utf-8")
    assert "não pontua atendentes" in doc
    assert "Art. 50(3)" in doc
