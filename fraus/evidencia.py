"""Evidencia fraca: tem dado, e nao ha material suficiente para afirmar.

A interface tinha DUAS formas -- cabeca cheia (medido) e cabeca vazada (nao
medido, `CabecaVazada.tsx`). Faltava a terceira, e o buraco era visivel: uma
conversa cujo cliente escreveu so "ok" saia CHEIA, com a mesma confianca
visual de uma conversa de 40 turnos.

    cheia      medido, com evidencia
    tracejada  medido, evidencia fraca
    vazada     nao medido

O QUE ESTE MODULO NAO FAZ, e e a decisao mais importante dele: nao usa a
probabilidade do modelo. Probabilidade nao calibrada NAO E CONFIANCA, e
apresenta-la como se fosse seria a desonestidade exata que este projeto recusa
em todo lugar -- calibrar exige retreino, que esta fora de escopo. A medida
aqui e EVIDENCIA OBSERVAVEL: quantas vezes o cliente falou e quanto ele
escreveu. Auditavel por quem abrir o transcript, e defensavel sem apelar para
propriedade nenhuma do modelo.

Pelo mesmo motivo o campo se chama `evidencia_fraca`, e nao `confianca`: o
segundo nome prometeria uma calibracao que nao existe.
"""

from fraus.modelos import Conversa

# Abaixo disto, a fala do cliente nao sustenta uma nota.
#
# O numero e ASSUMIDAMENTE convencional -- nao ha literatura que fixe um
# minimo de palavras para inferencia de satisfacao em atendimento, e inventar
# procedencia seria pior que declarar a ausencia dela. Ele esta calibrado para
# alcancar o caso que motivou a feature ("ok", "obrigado", "sim") sem tocar
# uma reclamacao curta de verdade ("o produto veio quebrado" ja tem 5). Se
# mover, mova aqui: o front nao redigita este numero.
PALAVRAS_MINIMAS = 5

# Uma unica fala do cliente nao da contexto para nada: sem segunda mensagem
# nao existe evolucao de humor no atendimento, e a nota inteira pende de uma
# frase.
MENSAGENS_MINIMAS = 2


def motivos_de_evidencia_fraca(
    conversa: Conversa, palavras_minimas: int = PALAVRAS_MINIMAS
) -> list[str]:
    """Por que a evidencia desta conversa e fraca -- em texto, nao em codigo.

    "Evidencia fraca" sozinho nao aciona ninguem; "uma unica mensagem do
    cliente" aciona. A tela imprime estes motivos ao lado da forma, porque
    forma sozinha obriga o leitor a conhecer a convencao -- a mesma regra que
    faz `CabecaVazada` exigir rotulo textual.

    Lista vazia = evidencia suficiente.
    """
    mensagens = conversa.mensagens_cliente
    # `tem_sinal_cliente`, nao `mensagens`: so cortesia ("ok, obrigado") e
    # ausencia de sinal desde 15/09/2026, e ausencia nao tem motivo de fraqueza.
    if not conversa.tem_sinal_cliente:
        return []

    motivos = []
    if len(mensagens) < MENSAGENS_MINIMAS:
        motivos.append("uma unica mensagem do cliente")

    # Contar PALAVRAS, e nao so mensagens: "ok" / "sim" / "ta" sao tres
    # mensagens e o mesmo vazio dividido em tres.
    palavras = sum(len(m.texto.split()) for m in mensagens)
    if palavras < palavras_minimas:
        motivos.append(f"menos de {palavras_minimas} palavras do cliente")
    return motivos


def evidencia_fraca(
    conversa: Conversa, palavras_minimas: int = PALAVRAS_MINIMAS
) -> bool | None:
    """A conversa tem score, mas pouca fala para sustenta-lo?

    `None` sem fala nenhuma do cliente -- e o estado "sem sinal", que ja tem
    forma propria. "Sem sinal" e "sinal fraco" sao coisas DIFERENTES, e
    confundi-las na interface perderia a distincao que o produto inteiro
    defende: ausencia nao e um valor baixo.
    """
    if not conversa.tem_sinal_cliente:
        return None
    return bool(motivos_de_evidencia_fraca(conversa, palavras_minimas))
