"""Sinal de tempo.

Latencia entra como FEATURE aprendida, nunca como penalidade linear: o efeito
sobre satisfacao e nao-linear (CSAT pico entre 5-10s, queda de 2-3 pontos por
minuto extra, 57% de abandono acima de 3min) e moderado por contexto --
indicador de digitacao e suporte emocional atenuam o dano
(From Seconds to Sentiments, IJHCI 2025).

Nada aqui e persistido: tudo deriva dos timestamps do modelo canonico.
"""

from statistics import median

from fraus.modelos import Conversa

RESPONDENTES = {"bot", "humano"}


def _percentil(valores: list[float], fracao: float) -> float:
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    indice = min(int(fracao * len(ordenados)), len(ordenados) - 1)
    return ordenados[indice]


def latencias_da_conversa(conversa: Conversa) -> list[float]:
    """Intervalo de cada mensagem do cliente ate a proxima resposta.

    PUBLICA de proposito: a serie temporal (`fraus.indicadores.serie_diaria`) e
    a transcricao da dashboard precisam da MESMA regra que vira feature do
    modelo. Duas definicoes de latencia -- uma para treinar, outra para exibir
    -- fariam o grafico contar uma historia que o fusor nunca viu.
    """
    latencias = []
    mensagens = conversa.mensagens
    for indice, mensagem in enumerate(mensagens):
        if mensagem.autor != "cliente":
            continue
        for seguinte in mensagens[indice + 1:]:
            if seguinte.autor in RESPONDENTES:
                latencias.append((seguinte.enviada_em - mensagem.enviada_em).total_seconds())
                break
    return latencias


def features_tempo(conversa: Conversa) -> dict[str, float]:
    latencias = latencias_da_conversa(conversa)
    fim = conversa.encerrada_em or conversa.mensagens[-1].enviada_em
    ultima = conversa.mensagens[-1]

    return {
        "latencia_mediana_s": median(latencias) if latencias else 0.0,
        "latencia_p90_s": _percentil(latencias, 0.9),
        "latencia_primeira_resposta_s": latencias[0] if latencias else 0.0,
        "duracao_total_s": (fim - conversa.iniciada_em).total_seconds(),
        "qtd_turnos_cliente": float(len(conversa.mensagens_cliente)),
        "escalou": 1.0 if conversa.escalou_para_humano else 0.0,
        "abandonou": 1.0 if ultima.autor in RESPONDENTES else 0.0,
    }
