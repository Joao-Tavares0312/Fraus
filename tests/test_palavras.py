"""Testes do peso por palavra e do vocabulario da conversa.

O classificador entra como DUBLÊ deterministico: o que se testa aqui e a
mecanica da oclusao -- apagou a palavra certa? o sinal do peso aponta para o
lado certo? -- e nao a opiniao do BERTimbau, que muda a cada retreino e
tornaria o teste uma fotografia inutil.
"""

from collections import Counter
from datetime import datetime, timedelta, timezone

from fraus.modelos import Conversa, Mensagem
from fraus.sinais.palavras import (TETO_PALAVRAS_POR_MENSAGEM, contar_palavras,
                                   normalizar, pesos_das_palavras,
                                   vocabulario)

INICIO = datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)


class ClassificadorDuble:
    """Devolve satisfacao proporcional a quantas vezes "otimo" aparece.

    Assim o peso esperado de cada palavra e conhecido de antemao: so "otimo"
    pode ter peso, e apagar qualquer outra palavra nao muda nada.
    """

    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        previsoes = []
        for texto in textos:
            bons = texto.lower().count("otimo")
            satisfeito = min(0.9, 0.1 + 0.4 * bons)
            previsoes.append([1.0 - satisfeito - 0.05, 0.05, satisfeito])
        return previsoes


def _conversa(textos_do_cliente: list[str]) -> Conversa:
    mensagens = []
    for indice, texto in enumerate(textos_do_cliente):
        mensagens.append(
            Mensagem(autor="cliente", texto=texto, enviada_em=INICIO + timedelta(seconds=indice * 10))
        )
        mensagens.append(
            Mensagem(autor="bot", texto="resposta padrao do bot", enviada_em=INICIO + timedelta(seconds=indice * 10 + 5))
        )
    return Conversa(
        id="c1", canal="webchat", iniciada_em=INICIO, mensagens=mensagens
    )


def test_palavra_decisiva_recebe_peso_positivo_e_as_outras_ficam_em_zero():
    """O peso e a diferenca que a palavra faz -- as demais nao fazem nenhuma."""
    pesos = pesos_das_palavras("o suporte foi otimo hoje", ClassificadorDuble())
    por_palavra = {p["palavra"]: p["peso"] for p in pesos}

    assert por_palavra["otimo"] > 0.5, "apagar a palavra decisiva tinha que derrubar a leitura"
    for neutra in ("o", "suporte", "foi", "hoje"):
        assert por_palavra[neutra] == 0.0


def test_posicao_da_palavra_permite_grifar_sem_retokenizar():
    """A interface grifa por indice; recontar do lado dela abriria divergencia."""
    texto = "o suporte foi otimo hoje"
    for peso in pesos_das_palavras(texto, ClassificadorDuble()):
        assert texto[peso["inicio"]:peso["fim"]] == peso["palavra"]


def test_texto_sem_palavra_nenhuma_nao_quebra():
    assert pesos_das_palavras("!!! ???", ClassificadorDuble()) == []


def test_acima_do_teto_a_palavra_vem_sem_medida_e_nao_com_peso_zero():
    """`None` e "nao medimos"; `0.0` seria "medimos e nao importou"."""
    texto = " ".join(f"palavra{i}" for i in range(TETO_PALAVRAS_POR_MENSAGEM + 5))
    pesos = pesos_das_palavras(texto, ClassificadorDuble())

    medidas = [p for p in pesos if p["peso"] is not None]
    sem_medida = [p for p in pesos if p["peso"] is None]
    assert len(medidas) == TETO_PALAVRAS_POR_MENSAGEM
    assert len(sem_medida) == 5


# ---------------------------------------------------------------------------
# vocabulario


def test_ignora_palavra_funcional_e_numero_solto():
    contagem = contar_palavras(["o cliente pediu 3 vezes o reembolso de novo"])
    assert "o" not in contagem and "de" not in contagem
    assert "3" not in contagem
    assert contagem["reembolso"] == 1
    assert contagem["cliente"] == 1


def test_normaliza_acento_para_nao_contar_a_mesma_palavra_duas_vezes():
    assert normalizar("Não") == normalizar("nao") == "nao"
    contagem = contar_palavras(["reembolso", "REEMBOLSO", "Reembolso"])
    assert contagem["reembolso"] == 3


def test_so_a_fala_do_cliente_entra_no_vocabulario():
    """O texto do bot e roteiro: conta-lo mediria o script, nao o cliente."""
    conversa = _conversa(["quero reembolso do reembolso"])
    palavras = {item["palavra"] for item in vocabulario(conversa)}

    assert "reembolso" in palavras
    assert "resposta" not in palavras  # veio so da fala do bot
    assert "padrao" not in palavras


def test_destaque_diz_quantas_vezes_acima_do_normal_a_palavra_esta():
    """E o campo que responde "o que ESTA conversa tem de diferente"."""
    conversa = _conversa(["reembolso reembolso"])
    # Na referencia, "reembolso" e 1 em 100 palavras; aqui e 2 em 2.
    referencia = Counter({"reembolso": 1, "outra": 99})

    item = next(i for i in vocabulario(conversa, referencia) if i["palavra"] == "reembolso")
    assert item["vezes"] == 2
    assert item["destaque"] == 100.0


def test_palavra_ausente_da_referencia_tem_destaque_nulo_e_nao_um():
    """Sem base de comparacao, 1.0 afirmaria "igual a media" sem ter medido."""
    conversa = _conversa(["estorno imediato"])
    item = next(
        i for i in vocabulario(conversa, Counter({"outra": 10})) if i["palavra"] == "estorno"
    )
    assert item["destaque"] is None


def test_conversa_sem_fala_do_cliente_nao_tem_vocabulario():
    conversa = Conversa(
        id="mudo",
        canal="webchat",
        iniciada_em=INICIO,
        mensagens=[Mensagem(autor="bot", texto="ola tudo bem", enviada_em=INICIO)],
    )
    assert vocabulario(conversa) == []
