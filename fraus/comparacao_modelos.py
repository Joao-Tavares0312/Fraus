"""Comparacao pareada de dois classificadores no MESMO conjunto de teste.

"O modelo novo acertou mais" nao e resultado enquanto nao se sabe se a
diferenca sobrevive a outra amostra do mesmo teste. Duas medidas, as duas
pareadas (os dois modelos leem exatamente os mesmos exemplos):

- McNemar exato sobre os exemplos em que SO UM dos modelos acerta -- os
  exemplos em que os dois acertam ou os dois erram nao distinguem ninguem;
- intervalo de confianca por bootstrap da diferenca de F1-macro, porque
  acuracia esconde classe rara e o corpus de emocao e desequilibrado em 43:1.

Parte pura: listas de rotulos e predicoes, sem modelo nenhum.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import comb

import numpy as np


@dataclass(frozen=True)
class ResultadoMcNemar:
    so_a: int
    so_b: int
    p_valor: float


@dataclass(frozen=True)
class ResultadoBootstrap:
    diferenca: float
    ic_inferior: float
    ic_superior: float
    reamostras: int


def f1_macro(rotulos: Sequence[int], preditos: Sequence[int], *, classes: Sequence[int]) -> float:
    """Media simples do F1 por classe; classe sem acerto conta zero."""
    rotulos, preditos = np.asarray(rotulos), np.asarray(preditos)
    f1s = []
    for classe in classes:
        acertos = int(np.sum((rotulos == classe) & (preditos == classe)))
        denominador = int(np.sum(rotulos == classe)) + int(np.sum(preditos == classe))
        f1s.append(2 * acertos / denominador if denominador else 0.0)
    return float(np.mean(f1s))


def mcnemar_exato(acertos_a: Sequence[bool], acertos_b: Sequence[bool]) -> ResultadoMcNemar:
    """Teste binomial exato bilateral sobre os pares discordantes."""
    if len(acertos_a) != len(acertos_b):
        raise ValueError("os dois modelos precisam ser avaliados nos mesmos exemplos")
    so_a = sum(1 for a, b in zip(acertos_a, acertos_b) if a and not b)
    so_b = sum(1 for a, b in zip(acertos_a, acertos_b) if b and not a)
    discordantes = so_a + so_b
    if discordantes == 0:
        return ResultadoMcNemar(0, 0, 1.0)
    cauda = sum(comb(discordantes, i) for i in range(min(so_a, so_b) + 1)) / 2**discordantes
    return ResultadoMcNemar(so_a, so_b, min(1.0, 2 * cauda))


def bootstrap_da_diferenca(
    rotulos: Sequence[int],
    preditos_a: Sequence[int],
    preditos_b: Sequence[int],
    *,
    classes: Sequence[int],
    reamostras: int = 2000,
    semente: int = 42,
) -> ResultadoBootstrap:
    """IC 95% percentil de F1-macro(A) - F1-macro(B), reamostrando exemplos."""
    if not len(rotulos) == len(preditos_a) == len(preditos_b):
        raise ValueError("os dois modelos precisam ser avaliados nos mesmos exemplos")
    rotulos, preditos_a, preditos_b = map(np.asarray, (rotulos, preditos_a, preditos_b))
    gerador = np.random.default_rng(semente)
    diferencas = np.empty(reamostras)
    for i in range(reamostras):
        amostra = gerador.integers(0, len(rotulos), len(rotulos))
        diferencas[i] = f1_macro(rotulos[amostra], preditos_a[amostra], classes=classes) - f1_macro(
            rotulos[amostra], preditos_b[amostra], classes=classes
        )
    inferior, superior = np.percentile(diferencas, [2.5, 97.5])
    return ResultadoBootstrap(
        diferenca=f1_macro(rotulos, preditos_a, classes=classes)
        - f1_macro(rotulos, preditos_b, classes=classes),
        ic_inferior=float(inferior),
        ic_superior=float(superior),
        reamostras=reamostras,
    )


@dataclass(frozen=True)
class ResultadoIntervalo:
    valor: float
    ic_inferior: float
    ic_superior: float
    reamostras: int


def _acertos_por_par(
    rotulos: Sequence[int], preditos: Sequence[int], par_ids: Sequence[str]
) -> dict[str, bool]:
    """Par certo e par com OS DOIS lados certos; par mal formado e erro alto."""
    if not len(rotulos) == len(preditos) == len(par_ids):
        raise ValueError("rotulos, predicoes e pares de tamanhos diferentes")
    lados: dict[str, list[tuple[int, bool]]] = {}
    for rotulo, predito, par in zip(rotulos, preditos, par_ids):
        lados.setdefault(str(par), []).append((int(rotulo), int(predito) == int(rotulo)))
    mal_formados = sorted(
        par for par, itens in lados.items() if sorted(r for r, _ in itens) != [0, 1]
    )
    if mal_formados:
        raise ValueError(f"par sem exatamente um lado de cada rotulo: {mal_formados[:5]}")
    return {par: all(acerto for _, acerto in itens) for par, itens in lados.items()}


def acuracia_por_par(
    rotulos: Sequence[int], preditos: Sequence[int], par_ids: Sequence[str]
) -> float:
    """Fracao de pares com os dois lados certos. O acaso e 25%, nao 50%."""
    acertos = _acertos_por_par(rotulos, preditos, par_ids)
    return sum(acertos.values()) / len(acertos)


def bootstrap_por_par(
    rotulos: Sequence[int],
    preditos: Sequence[int],
    par_ids: Sequence[str],
    *,
    preditos_referencia: Sequence[int] | None = None,
    reamostras: int = 2000,
    semente: int = 42,
) -> ResultadoIntervalo:
    """IC 95% percentil da acuracia por par -- ou da diferenca para a referencia.

    Reamostra PARES, nao frases: os dois lados de um par sao dependentes, e
    reamostrar frase estreitaria o intervalo sem motivo.
    """
    acertos = _acertos_por_par(rotulos, preditos, par_ids)
    pares = sorted(acertos)
    valores = np.array([acertos[p] for p in pares], dtype=float)
    if preditos_referencia is not None:
        referencia = _acertos_por_par(rotulos, preditos_referencia, par_ids)
        valores = valores - np.array([referencia[p] for p in pares], dtype=float)
    gerador = np.random.default_rng(semente)
    medias = np.empty(reamostras)
    for i in range(reamostras):
        medias[i] = valores[gerador.integers(0, len(valores), len(valores))].mean()
    inferior, superior = np.percentile(medias, [2.5, 97.5])
    return ResultadoIntervalo(
        valor=float(valores.mean()),
        ic_inferior=float(inferior),
        ic_superior=float(superior),
        reamostras=reamostras,
    )


def ece(probabilidades: Sequence[float], rotulos: Sequence[int], *, faixas: int = 10) -> float:
    """Erro de calibracao esperado de P(classe 1), em faixas iguais de 0 a 1.

    Media ponderada, por faixa, de |P media - frequencia observada da classe 1|.
    """
    p = np.asarray(probabilidades, dtype=float)
    y = np.asarray(rotulos, dtype=int)
    if len(p) != len(y) or len(p) == 0:
        raise ValueError("probabilidades e rotulos vazios ou de tamanhos diferentes")
    if ((p < 0.0) | (p > 1.0)).any():
        raise ValueError("probabilidade fora de 0..1")
    bordas = np.linspace(0.0, 1.0, faixas + 1)
    indices = np.clip(np.digitize(p, bordas[1:-1], right=True), 0, faixas - 1)
    total = 0.0
    for faixa in range(faixas):
        mascara = indices == faixa
        if mascara.any():
            total += mascara.mean() * abs(p[mascara].mean() - y[mascara].mean())
    return float(total)


# --- O laudo ------------------------------------------------------------------
#
# O que o notebook 07 grava em `comparacao_modelos.json` e a API serve sem
# recalcular nada. Quem monta e `montar_laudo`; quem le confere com
# `validar_laudo`. O relatorio em texto sai do MESMO dicionario, no servidor:
# numero recalculado no navegador e numero que um dia diverge do laudo.

SCHEMA_LAUDO = 1

NOMES_MODELOS = {
    "bertimbau": "BERTimbau fine-tunado",
    "laya_sem_treino": "Laya sem treino",
    "laya_treinado": "Laya treinado",
}


def matriz_de_confusao(
    rotulos: Sequence[int], preditos: Sequence[int], *, classes: Sequence[int]
) -> list[list[int]]:
    """Linha e a classe REAL, coluna e a classe PREDITA, na ordem de `classes`."""
    if len(rotulos) != len(preditos):
        raise ValueError("rotulos e predicoes de tamanhos diferentes")
    posicao = {classe: i for i, classe in enumerate(classes)}
    matriz = [[0] * len(classes) for _ in classes]
    for real, predito in zip(rotulos, preditos):
        for classe in (int(real), int(predito)):
            if classe not in posicao:
                raise ValueError(f"classe {classe} fora das classes da matriz {list(classes)}")
        matriz[posicao[int(real)]][posicao[int(predito)]] += 1
    return matriz


def contagens_por_classe(matriz: Sequence[Sequence[int]], nomes: Sequence[str]) -> list[dict]:
    """VP, FP, FN e VN de cada classe contra o resto, com precisao, recall e F1.

    Precisao de classe que o modelo nunca previu e `None`, nao zero: sem
    predicao nao ha o que medir. O mesmo vale para o recall de classe sem
    exemplo e para o F1 quando falta um dos dois.
    """
    total = sum(sum(linha) for linha in matriz)
    contagens = []
    for i, nome in enumerate(nomes):
        vp = matriz[i][i]
        fn = sum(matriz[i]) - vp
        fp = sum(linha[i] for linha in matriz) - vp
        precisao = vp / (vp + fp) if vp + fp else None
        recall = vp / (vp + fn) if vp + fn else None
        f1 = (
            None
            if precisao is None or recall is None
            else (2 * precisao * recall / (precisao + recall) if precisao + recall else 0.0)
        )
        contagens.append({
            "classe": nome, "exemplos": vp + fn,
            "vp": vp, "fp": fp, "fn": fn, "vn": total - vp - fp - fn,
            "precisao": precisao, "recall": recall, "f1": f1,
        })
    return contagens


def avaliar_conjunto(
    *,
    identificador: str,
    tarefa: str,
    nome: str,
    independente: bool,
    rotulos: Sequence[int],
    preditos_por_modelo: dict[str, Sequence[int]],
    classes: Sequence[int],
    nomes_classes: Sequence[str],
    classes_do_f1: Sequence[int] | None = None,
    candidato: str = "laya_treinado",
    referencia: str = "bertimbau",
    reamostras: int = 2000,
    par_ids: Sequence[str] | None = None,
) -> dict:
    """Um conjunto de teste lido por todos os modelos, pronto para o laudo.

    `independente` diz se NENHUM modelo viu dado da mesma procedencia no
    treino -- e o que separa o XED-pt e a regua do teste interno.

    `classes` sao todas as respostas POSSIVEIS do modelo e definem a matriz.
    `classes_do_f1` sao as que o conjunto de fato contem: o XED-pt nao tem
    `neutro`, e contar o F1 de uma classe sem exemplo puniria todo modelo por
    igual sem medir nada. Predicao de classe ausente continua sendo erro, e
    aparece na matriz.
    """
    classes_do_f1 = list(classes if classes_do_f1 is None else classes_do_f1)
    for modelo, preditos in preditos_por_modelo.items():
        if len(preditos) != len(rotulos):
            raise ValueError(f"{modelo}: {len(preditos)} predicoes para {len(rotulos)} exemplos")
    modelos = {}
    for modelo, preditos in preditos_por_modelo.items():
        matriz = matriz_de_confusao(rotulos, preditos, classes=classes)
        modelos[modelo] = {
            "acuracia": sum(int(p) == int(r) for p, r in zip(preditos, rotulos)) / len(rotulos),
            "f1_macro": f1_macro(rotulos, preditos, classes=classes_do_f1),
            "matriz": matriz,
            "por_classe": contagens_por_classe(matriz, nomes_classes),
        }
    a, b = preditos_por_modelo[candidato], preditos_por_modelo[referencia]
    mc = mcnemar_exato(
        [int(p) == int(r) for p, r in zip(a, rotulos)],
        [int(p) == int(r) for p, r in zip(b, rotulos)],
    )
    bs = bootstrap_da_diferenca(rotulos, a, b, classes=classes_do_f1, reamostras=reamostras)
    if par_ids is not None:
        for modelo, preditos in preditos_por_modelo.items():
            intervalo = bootstrap_por_par(rotulos, preditos, par_ids, reamostras=reamostras)
            modelos[modelo]["acuracia_por_par"] = intervalo.valor
            modelos[modelo]["ic95_por_par"] = [intervalo.ic_inferior, intervalo.ic_superior]
        diferenca = bootstrap_por_par(
            rotulos, a, par_ids, preditos_referencia=b, reamostras=reamostras
        )
    comparacao = {
        "candidato": candidato,
        "referencia": referencia,
        "diferenca_f1_macro": bs.diferenca,
        "ic95": [bs.ic_inferior, bs.ic_superior],
        "mcnemar": {"so_candidato": mc.so_a, "so_referencia": mc.so_b, "p_valor": mc.p_valor},
        # Intervalo que contem o zero nao demonstra vantagem de ninguem.
        "diferenca_demonstrada": not (bs.ic_inferior <= 0.0 <= bs.ic_superior),
    }
    if par_ids is not None:
        comparacao["diferenca_acuracia_por_par"] = diferenca.valor
        comparacao["ic95_diferenca_por_par"] = [diferenca.ic_inferior, diferenca.ic_superior]
        comparacao["por_par_demonstrada"] = not (
            diferenca.ic_inferior <= 0.0 <= diferenca.ic_superior
        )
    return {
        "id": identificador,
        "tarefa": tarefa,
        "nome": nome,
        "independente": independente,
        "exemplos": len(rotulos),
        "classes": list(nomes_classes),
        "modelos": modelos,
        "comparacao": comparacao,
    }


def montar_laudo(
    *,
    conjuntos: list[dict],
    latencia: dict | None,
    procedencia: dict,
    rodada_de_fumaca: bool,
    gerado_em: str,
) -> dict:
    """O dicionario que vira `comparacao_modelos.json`. `latencia` pode faltar."""
    laudo = {
        "schema": SCHEMA_LAUDO,
        "gerado_em": gerado_em,
        "rodada_de_fumaca": bool(rodada_de_fumaca),
        "nomes_modelos": NOMES_MODELOS,
        "conjuntos": conjuntos,
        "latencia": latencia,
        "procedencia": procedencia,
    }
    validar_laudo(laudo)
    return laudo


def validar_laudo(laudo: object) -> None:
    """Recusa o que nao e um laudo deste schema -- a tela nao adivinha formato."""
    if not isinstance(laudo, dict):
        raise ValueError("laudo de comparacao nao e um objeto")
    if laudo.get("schema") != SCHEMA_LAUDO:
        raise ValueError(f"laudo de schema {laudo.get('schema')!r}; esperado {SCHEMA_LAUDO}")
    conjuntos = laudo.get("conjuntos")
    if not isinstance(conjuntos, list) or not conjuntos:
        raise ValueError("laudo sem conjuntos avaliados")
    for conjunto in conjuntos:
        for chave in ("id", "tarefa", "nome", "exemplos", "classes", "modelos", "comparacao"):
            if chave not in conjunto:
                raise ValueError(f"conjunto sem {chave!r}")
    # `ressalvas` e opcional: o que se soube sobre a medicao depois de feita.
    ressalvas = laudo.get("ressalvas", [])
    if not isinstance(ressalvas, list) or not all(
        isinstance(r, str) and r.strip() for r in ressalvas
    ):
        raise ValueError("ressalvas do laudo devem ser uma lista de textos")


def _numero(valor: float | None, casas: int = 3) -> str:
    return "—" if valor is None else f"{valor:.{casas}f}".replace(".", ",")


def _com_sinal(valor: float) -> str:
    return ("+" if valor >= 0 else "−") + _numero(abs(valor))


def relatorio_markdown(laudo: dict) -> str:
    """O laudo por extenso, em Markdown, para anexar a um documento."""
    validar_laudo(laudo)
    nomes = {**NOMES_MODELOS, **laudo.get("nomes_modelos", {})}
    linhas = ["# Comparação de modelos — BERTimbau e Laya", "", f"Gerado em {laudo['gerado_em']}.", ""]
    if laudo.get("rodada_de_fumaca"):
        linhas += [
            "> **Rodada de fumaça.** O Laya treinou poucos minutos, só para provar que o",
            "> caminho funciona. Os números abaixo não são resultado.",
            "",
        ]
    if laudo.get("ressalvas"):
        linhas += ["## Ressalvas", ""]
        linhas += [f"- {ressalva}" for ressalva in laudo["ressalvas"]]
        linhas += [""]
    linhas += [
        "Os modelos leram exatamente os mesmos exemplos em cada conjunto. A comparação",
        "é sempre do candidato contra a referência: diferença de F1-macro com intervalo",
        "de confiança de 95% por bootstrap e teste de McNemar exato. Intervalo que",
        "contém o zero não demonstra vantagem de nenhum dos dois.",
        "",
    ]
    for conjunto in laudo["conjuntos"]:
        procedencia = (
            "nenhum modelo viu dado desta procedência no treino"
            if conjunto.get("independente")
            else "mesma procedência do treino"
        )
        linhas += [
            f"## {conjunto['nome']}",
            "",
            f"{conjunto['exemplos']} exemplos; {procedencia}.",
            "",
            "| Modelo | Acurácia | F1-macro |",
            "|---|---|---|",
        ]
        for modelo, medidas in conjunto["modelos"].items():
            linhas.append(
                f"| {nomes.get(modelo, modelo)} | {_numero(medidas['acuracia'])} "
                f"| {_numero(medidas['f1_macro'])} |"
            )
        comparacao = conjunto["comparacao"]
        candidato = nomes.get(comparacao["candidato"], comparacao["candidato"])
        referencia = nomes.get(comparacao["referencia"], comparacao["referencia"])
        inferior, superior = comparacao["ic95"]
        mcnemar = comparacao["mcnemar"]
        veredito = (
            "diferença demonstrada"
            if comparacao["diferenca_demonstrada"]
            else "sem diferença demonstrada"
        )
        linhas += [
            "",
            f"{candidato} menos {referencia}: {_com_sinal(comparacao['diferenca_f1_macro'])} "
            f"de F1-macro (IC 95% de {_com_sinal(inferior)} a {_com_sinal(superior)}) — "
            f"**{veredito}**. McNemar exato: só o candidato acerta "
            f"{mcnemar['so_candidato']}, só a referência acerta {mcnemar['so_referencia']}, "
            f"p = {_numero(mcnemar['p_valor'], 4)}.",
            "",
        ]
        for modelo, medidas in conjunto["modelos"].items():
            linhas += [
                f"### {nomes.get(modelo, modelo)} — acertos e erros por classe",
                "",
                "| Classe | VP | FP | FN | VN | Precisão | Recall |",
                "|---|---|---|---|---|---|---|",
            ]
            for classe in medidas["por_classe"]:
                linhas.append(
                    f"| {classe['classe']} | {classe['vp']} | {classe['fp']} | {classe['fn']} "
                    f"| {classe['vn']} | {_numero(classe['precisao'])} | {_numero(classe['recall'])} |"
                )
            linhas.append("")
    linhas += ["## Tempo de resposta", ""]
    latencia = laudo.get("latencia")
    if not latencia or not latencia.get("medidas"):
        linhas += ["A latência não foi medida nesta rodada.", ""]
    else:
        linhas += [
            f"Medido em {latencia['hardware']}, uma mensagem por vez, em {latencia['amostra']} "
            "mensagens. Vale para esta máquina; não é o tempo de produção.",
            "",
            "| Modelo | Tarefa | Executor | Mediana | p95 |",
            "|---|---|---|---|---|",
        ]
        for medida in latencia["medidas"]:
            linhas.append(
                f"| {nomes.get(medida['modelo'], medida['modelo'])} | {medida['tarefa']} "
                f"| {medida['executor']} | {_numero(medida['mediana_ms'], 1)} ms "
                f"| {_numero(medida['p95_ms'], 1)} ms |"
            )
        linhas.append("")
    linhas += ["## Procedência", ""]
    procedencia = laudo.get("procedencia") or {}
    if procedencia:
        linhas += [f"- {chave}: {valor}" for chave, valor in procedencia.items()]
    else:
        linhas.append("Não registrada.")
    linhas += [
        "",
        "## Limites",
        "",
        "- O corpus de emoção é tradução automática do GoEmotions; o teste interno mede",
        "  também o quanto cada modelo aprendeu a tradução. O XED-pt não passou por tradução.",
        "- O corpus de ironia foi rotulado por hashtag e procedência, não por anotador.",
        "- A régua de ironia é pequena e autoral: mede dois atalhos conhecidos, não",
        "  desempenho em atendimento real.",
        "- Nenhum destes conjuntos é conversa de cliente real do Fraus.",
        "",
    ]
    return "\n".join(linhas)
