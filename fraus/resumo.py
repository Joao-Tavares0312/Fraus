"""Resumo operacional de uma conversa: quem falou, quanto esperou, como acabou.

Isto NAO e sinal do modelo. Nenhuma funcao daqui alimenta feature nenhuma --
tudo aqui existe para a lista de atendimentos parar de ser cinco colunas que
nao respondem "o que aconteceu neste atendimento?".

Duas regras que este modulo segue e que o resto do projeto ja seguia:

1. **Latencia sai de `fraus.sinais.tempo`, nunca de uma conta local.** A regra
   de "quanto o cliente esperou" e a MESMA que virou feature do fusor. Uma
   segunda definicao aqui faria a tabela mostrar um numero que o modelo nunca
   viu.
2. **Ausencia devolve `None`, nunca zero.** Conversa sem resposta humana tem
   `latencia_mediana_humano_s` nulo, e nao 0.0. Zero, na coluna de tempo de
   resposta, se le como "respondeu instantaneamente" -- que e o oposto do que
   aconteceu.
"""

from statistics import median

from fraus.evidencia import evidencia_fraca, motivos_de_evidencia_fraca
from fraus.modelos import Conversa
from fraus.sinais.tempo import RESPONDENTES, latencias_da_conversa


def latencias_por_respondente(conversa: Conversa) -> dict[str, list[float]]:
    """Esperas do cliente, separadas por QUEM respondeu.

    A separacao importa porque as duas medias contam historias diferentes e a
    media unica as apaga: bot que responde em 2s e humano que responde em 4min
    viram "1min30", um numero que nao descreve nenhum dos dois. Numa operacao
    com escalonamento, e a fila do humano que dói.

    A regra de emparelhamento e a de `latencias_da_conversa`: cada fala do
    cliente casa com a PROXIMA fala de um respondente, e falas seguidas do
    cliente sem resposta no meio nao contam espera nenhuma.
    """
    por_autor: dict[str, list[float]] = {autor: [] for autor in sorted(RESPONDENTES)}
    mensagens = conversa.mensagens

    for indice, mensagem in enumerate(mensagens):
        if mensagem.autor != "cliente":
            continue
        for seguinte in mensagens[indice + 1:]:
            if seguinte.autor in RESPONDENTES:
                espera = (seguinte.enviada_em - mensagem.enviada_em).total_seconds()
                por_autor[seguinte.autor].append(espera)
                break

    return por_autor


def _mediana_ou_nada(valores: list[float]) -> float | None:
    return median(valores) if valores else None


def desfecho(conversa: Conversa) -> str:
    """Como o atendimento terminou, derivado so do que esta nos dados.

    A ORDEM DE PRECEDENCIA e a definicao -- um atendimento pode satisfazer mais
    de uma condicao, e a primeira que casar vence:

    1. `sem_sinal` -- o cliente nao falou. Nao ha atendimento a avaliar, e essa
       e a informacao mais importante sobre a conversa.
    2. `escalada` -- passou para atendente humano. Vence "concluida" de
       proposito: uma escalada que terminou bem ainda e uma escalada, e apagar
       isso esconderia justamente o custo que a operacao quer medir.
    3. `sem_resposta` -- a ultima fala e do CLIENTE e ninguem respondeu. E o
       desfecho mais grave que da para provar pelos dados.
    4. `encerrada` -- tem `encerrada_em` e o respondente falou por ultimo.
    5. `em_aberto` -- nao tem `encerrada_em`.

    O que NAO existe aqui e um estado "resolvida". Resolucao e julgamento sobre
    o problema do cliente, e nao ha nada no dado que a sustente -- inventar o
    rotulo faria a tela afirmar o que ninguem mediu. `encerrada` diz o que de
    fato se sabe: a conversa fechou.
    """
    if not conversa.tem_sinal_cliente:
        return "sem_sinal"
    if conversa.escalou_para_humano:
        return "escalada"
    if conversa.mensagens[-1].autor == "cliente":
        return "sem_resposta"
    if conversa.encerrada_em is not None:
        return "encerrada"
    return "em_aberto"


def resumir(conversa: Conversa) -> dict:
    """Ficha operacional da conversa, pronta para a lista de atendimentos."""
    latencias = latencias_da_conversa(conversa)
    por_respondente = latencias_por_respondente(conversa)
    fim = conversa.encerrada_em or conversa.mensagens[-1].enviada_em

    contagem = {"cliente": 0, "bot": 0, "humano": 0}
    for mensagem in conversa.mensagens:
        contagem[mensagem.autor] += 1

    return {
        "qtd_mensagens": len(conversa.mensagens),
        "qtd_cliente": contagem["cliente"],
        "qtd_bot": contagem["bot"],
        "qtd_humano": contagem["humano"],
        # Primeira espera do cliente, independente de quem respondeu: e a
        # unica latencia que todo atendimento com sinal possui.
        "latencia_primeira_resposta_s": latencias[0] if latencias else None,
        "latencia_mediana_s": _mediana_ou_nada(latencias),
        "latencia_mediana_bot_s": _mediana_ou_nada(por_respondente["bot"]),
        "latencia_mediana_humano_s": _mediana_ou_nada(por_respondente["humano"]),
        "duracao_s": (fim - conversa.iniciada_em).total_seconds(),
        "escalou_para_humano": conversa.escalou_para_humano,
        "encerrada_em": conversa.encerrada_em.isoformat() if conversa.encerrada_em else None,
        "desfecho": desfecho(conversa),
        # A TERCEIRA FORMA da nota: "tem dado, e nao ha evidencia suficiente
        # para afirmar" -- distinta de "sem sinal", que ja tem a cabeca
        # vazada. Derivada no SERVIDOR (invariante 3) e a partir de evidencia
        # OBSERVAVEL, nunca da probabilidade do modelo: probabilidade nao
        # calibrada nao e confianca. Ver `fraus/evidencia.py`.
        "evidencia_fraca": evidencia_fraca(conversa),
        "motivos_evidencia_fraca": motivos_de_evidencia_fraca(conversa),
    }
