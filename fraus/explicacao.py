"""Explicacao de uma nota por TEMPLATE, a partir dos numeros do proprio fusor.

Sem LLM (invariante 1) e sem texto livre: cada frase e montada de pecas fixas
com os efeitos que `Fusor.efeitos_por_familia` calculou. A explicacao e o
modelo, nao uma historia sobre ele. Nada aqui grava ou corrige nota.
"""

import numpy as np

from fraus.fusor import FAMILIAS

# Abaixo de 1 ponto de score, um efeito nao muda nota 0-10 em caso nenhum que
# importe, e lista-lo seria ruido. Limiar sem procedencia, declarado.
LIMIAR_PONTOS = 1.0
MAXIMO_POR_LADO = 2

ROTULO_FAMILIA = {
    "texto": "o texto do cliente",
    "emoji": "os emojis",
    "tempo": "o ritmo do atendimento",
    "emocao": "a emoção lida no texto",
    "lexico": "o vocabulário (léxico de sentimento)",
    "estilo": "o estilo da escrita",
    "incongruencia": "os sinais de incongruência",
}
assert set(ROTULO_FAMILIA) == set(FAMILIAS)

ROTULO_ASSOCIACAO = "associação no modelo, não causa"
AVISO = (
    "Efeito de cada sinal medido no próprio modelo, trocando o sinal pela média "
    "do treino. Os efeitos não somam a nota, porque a nota não é linear; a soma "
    "exata está no eixo de logit. É " + ROTULO_ASSOCIACAO + ". O sinal de tempo "
    "foi treinado em dados sintéticos."
)


def formatar_duracao(segundos: float) -> str:
    """42 s, 12 min, 3 h, 1 h 30 min -- arredondado, para leitura."""
    if segundos < 60:
        return f"{round(segundos)} s"
    minutos = round(segundos / 60)
    if minutos < 60:
        return f"{minutos} min"
    horas, resto = divmod(minutos, 60)
    return f"{horas} h" if resto == 0 else f"{horas} h {resto} min"


def _pontos(valor: float) -> str:
    return f"{valor:+.1f}".replace(".", ",").replace("-", "−") + " pontos"


def _detalhe(familia: str, features: dict[str, float], ha_latencia: bool) -> str | None:
    if familia != "tempo" or not ha_latencia:
        return None
    return (f"espera mediana de {formatar_duracao(features['latencia_mediana_s'])}; "
            f"primeira resposta em {formatar_duracao(features['latencia_primeira_resposta_s'])}")


def _trecho(item: dict) -> str:
    detalhe = f" ({item['detalhe']})" if item["detalhe"] else ""
    return f"{item['rotulo']}{detalhe}, {_pontos(item['pontos'])}"


def explicar(efeitos: dict[str, float], features: dict[str, float], ha_latencia: bool) -> dict:
    """As duas familias de maior efeito para cada lado, em frases fixas."""
    def itens(filtro, chave):
        escolhidos = sorted(((f, v) for f, v in efeitos.items() if filtro(v)), key=chave)
        return [
            {"familia": f, "rotulo": ROTULO_FAMILIA[f], "pontos": round(v, 1),
             "detalhe": _detalhe(f, features, ha_latencia)}
            for f, v in escolhidos[:MAXIMO_POR_LADO]
        ]

    contra = itens(lambda v: v <= -LIMIAR_PONTOS, lambda par: par[1])
    a_favor = itens(lambda v: v >= LIMIAR_PONTOS, lambda par: -par[1])
    frases = []
    if contra:
        frases.append("Pesou contra: " + "; ".join(_trecho(i) for i in contra) + ".")
    if a_favor:
        frases.append("Pesou a favor: " + "; ".join(_trecho(i) for i in a_favor) + ".")
    if not frases:
        frases.append("Nenhum sinal sozinho moveu a nota em 1 ponto ou mais.")
    return {"frases": frases, "contra": contra, "a_favor": a_favor, "aviso": AVISO}


SEMENTE_DRIVERS = 20261014
GRUPOS = (("detrator", "detratores"), ("promotor", "promotores"))


def _resumo(valores: list[float], gerador) -> dict:
    if not valores:
        return {"n": 0, "media": None, "ic": None}
    media = float(np.mean(valores))
    if len(valores) < 2:
        return {"n": 1, "media": media, "ic": None}
    amostras = gerador.choice(np.asarray(valores), size=(1000, len(valores)), replace=True).mean(axis=1)
    return {"n": len(valores), "media": media,
            "ic": [float(np.percentile(amostras, 2.5)), float(np.percentile(amostras, 97.5))]}


def drivers(linhas, semente: int = SEMENTE_DRIVERS) -> list[dict]:
    """Media da contribuicao por familia em detratores x promotores, com IC 95%
    por bootstrap. `linhas` = [(categoria, {familia: contribuicao})]. Neutro nao
    entra em grupo. Grupo vazio e None, nunca 0 (invariante 2)."""
    gerador = np.random.default_rng(semente)
    return [
        {"familia": familia, **{
            plural: _resumo([c[familia] for cat, c in linhas if cat == categoria], gerador)
            for categoria, plural in GRUPOS}}
        for familia in FAMILIAS
    ]
