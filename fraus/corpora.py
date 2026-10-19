"""Leitores dos corpora de treino e de teste, compartilhados por notebooks e benchmark.

Quem treina e quem mede leem o corpus pelo MESMO codigo: o notebook no Colab
e o `scripts/benchmark_motores.py` na CPU chegam ao mesmo teste, e a
`impressao_dos_textos` dele confere isso. So stdlib (`csv`, `zipfile`), para
rodar igual nos dois lugares; baixar o arquivo e responsabilidade de quem chama.

A ordem das classes de satisfacao e a da invariante 8: 0 insatisfeito,
1 neutro, 2 satisfeito.
"""

from __future__ import annotations

import csv
import io
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from fraus.sinais.emocao import NOMES_EMOCOES

CLASSES_SATISFACAO = ["insatisfeito", "neutro", "satisfeito"]

URL_B2W = "https://raw.githubusercontent.com/americanas-tech/b2w-reviews01/main/B2W-Reviews01.csv"
URL_XED_PT = (
    "https://raw.githubusercontent.com/Helsinki-NLP/XED/master/Projections/pt-projections.tsv"
)
# Duarte et al. (2025), PROPOR 2026. Registro Zenodo 18022568, CC BY 4.0.
URL_CONSUMERBR = "https://zenodo.org/records/18022568/files/ConsumerBR.zip?download=1"

# Plutchik no XED: 1 anger, 2 anticipation, 3 disgust, 4 fear, 5 joy,
# 6 sadness, 7 surprise, 8 trust. Anticipation e trust nao tem par em Ekman.
_XED_PARA_EKMAN = {"1": "raiva", "3": "nojo", "4": "medo", "5": "alegria", "6": "tristeza",
                   "7": "surpresa"}


@dataclass
class Exemplos:
    textos: list[str] = field(default_factory=list)
    rotulos: list[int] = field(default_factory=list)
    grupos: list[str] | None = None
    nomes_classes: list[str] = field(default_factory=list)


def rotulo_por_estrelas(nota: object) -> int | None:
    """1-2 insatisfeito, 3 neutro, 4-5 satisfeito; fora da escala e `None`."""
    if isinstance(nota, str):
        nota = nota.strip()
        if not nota.isdigit():
            return None
        nota = int(nota)
    if isinstance(nota, bool) or not isinstance(nota, int) or not 1 <= nota <= 5:
        return None
    return 0 if nota <= 2 else (1 if nota == 3 else 2)


def _permitir_campo_longo() -> None:
    # Reclamacao do ConsumerBR passa dos 128 KiB padrao do modulo csv.
    csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def ler_b2w(caminho: str | Path) -> Exemplos:
    """B2W-Reviews01: texto da review, nota 1-5, agrupado por produto.

    O agrupamento impede que reviews do mesmo produto caiam dos dois lados da
    divisao -- o modelo aprenderia o produto, nao a satisfacao.
    """
    _permitir_campo_longo()
    ex = Exemplos(grupos=[], nomes_classes=list(CLASSES_SATISFACAO))
    with open(caminho, newline="", encoding="utf-8") as arquivo:
        for linha in csv.DictReader(arquivo):
            texto = (linha.get("review_text") or "").strip()
            rotulo = rotulo_por_estrelas(linha.get("overall_rating"))
            if not texto or rotulo is None:
                continue
            ex.textos.append(texto)
            ex.rotulos.append(rotulo)
            ex.grupos.append((linha.get("product_id") or "").strip())
    return ex


def ler_consumerbr(caminho_zip: str | Path, *, limite: int | None = None) -> Exemplos:
    """ConsumerBR: o COMENTARIO da avaliacao com a nota 1-5, agrupado por empresa.

    Nao a reclamacao: ela e escrita antes da resolucao e quase sempre e
    negativa, enquanto a nota mede o desfecho. Rotular a reclamacao com a nota
    seria rotulo falso. O comentario e escrito junto com a nota.
    """
    _permitir_campo_longo()
    ex = Exemplos(grupos=[], nomes_classes=list(CLASSES_SATISFACAO))
    with zipfile.ZipFile(caminho_zip) as pacote:
        membros = [m for m in pacote.namelist() if m.lower().endswith(".csv")]
        if len(membros) != 1:
            raise ValueError(f"esperava um CSV no pacote do ConsumerBR, achei {membros}")
        with pacote.open(membros[0]) as bruto:
            leitor = csv.DictReader(io.TextIOWrapper(bruto, encoding="utf-8", newline=""))
            for linha in leitor:
                texto = (linha.get("avaliacao_comentario") or "").strip()
                rotulo = rotulo_por_estrelas(linha.get("avaliacao_nota"))
                if not texto or rotulo is None:
                    continue
                ex.textos.append(texto)
                ex.rotulos.append(rotulo)
                ex.grupos.append((linha.get("empresa") or "").strip())
                if limite is not None and len(ex.textos) >= limite:
                    break
    return ex


def ler_xed_pt(caminho: str | Path) -> Exemplos:
    """XED-pt (Ohman et al., 2020): legenda de filme, Plutchik reduzido a Ekman.

    Rotulos PROJETADOS de outras linguas, portugues europeu e sem `neutro`.
    Frase com mais de uma classe Ekman, ou so anticipation/trust, sai.
    """
    ex = Exemplos(nomes_classes=list(NOMES_EMOCOES))
    with open(caminho, newline="", encoding="utf-8") as arquivo:
        for linha in csv.reader(arquivo, delimiter="\t"):
            if len(linha) < 2:
                continue
            frase = linha[0].strip()
            classes = {
                _XED_PARA_EKMAN[c.strip()] for c in linha[1].split(",")
                if c.strip() in _XED_PARA_EKMAN
            }
            if not frase or len(classes) != 1:
                continue
            ex.textos.append(frase)
            ex.rotulos.append(NOMES_EMOCOES.index(classes.pop()))
    return ex


_INGLES_PARA_EKMAN = {"joy": "alegria", "sadness": "tristeza", "anger": "raiva", "fear": "medo",
                      "disgust": "nojo", "surprise": "surpresa"}

URL_GOEMOTIONS_PTBR = (
    "https://huggingface.co/datasets/antoniomenezes/go_emotions_ptbr/resolve/main/"
    "goemotions_{}_pt.csv"
)
URL_EKMAN = (
    "https://raw.githubusercontent.com/google-research/google-research/master/"
    "goemotions/data/ekman_mapping.json"
)


def ler_goemotions_ptbr(
    caminhos: list[str | Path], mapa_ekman: dict[str, list[str]], *, limiar_anotadores: int = 2
) -> Exemplos:
    """GoEmotions-PT (traducao automatica), votos somados por id, reduzido a Ekman + neutro.

    A mesma regra do notebook 03 ate 19/10/2026: linha `example_very_unclear`
    nao vota; uma classe fina conta com `limiar_anotadores` votos; exemplo que
    termina com mais de uma classe Ekman sai. O grupo e o autor do Reddit.
    """
    fina_para_ekman = {
        fina: _INGLES_PARA_EKMAN[grossa] for grossa, finas in mapa_ekman.items() for fina in finas
    }
    fina_para_ekman["neutral"] = "neutro"
    if set(fina_para_ekman.values()) != set(NOMES_EMOCOES):
        raise ValueError("o mapa Ekman nao cobre as classes de NOMES_EMOCOES")
    _permitir_campo_longo()
    votos: dict[str, dict[str, int]] = {}
    texto_de: dict[str, str] = {}
    autor_de: dict[str, str] = {}
    for caminho in caminhos:
        with open(caminho, newline="", encoding="utf-8") as arquivo:
            for linha in csv.DictReader(arquivo):
                if (linha.get("example_very_unclear") or "").strip().lower() == "true":
                    continue
                ident = linha["id"]
                texto_de.setdefault(ident, (linha.get("texto") or "").strip())
                autor = (linha.get("author") or "").strip()
                # "[deleted]" nao e uma pessoa: vira linha sem autor, grupo proprio.
                autor_de.setdefault(ident, "" if autor == "[deleted]" else autor)
                contagem = votos.setdefault(ident, {})
                for fina in fina_para_ekman:
                    if (linha.get(fina) or "0").strip() == "1":
                        contagem[fina] = contagem.get(fina, 0) + 1
    ex = Exemplos(grupos=[], nomes_classes=list(NOMES_EMOCOES))
    for ident, contagem in votos.items():
        classes = {fina_para_ekman[f] for f, n in contagem.items() if n >= limiar_anotadores}
        if len(classes) != 1 or not texto_de[ident]:
            continue
        ex.textos.append(texto_de[ident])
        ex.rotulos.append(NOMES_EMOCOES.index(classes.pop()))
        ex.grupos.append(autor_de[ident])
    return ex


URL_MULTIPICO = (
    "https://huggingface.co/datasets/Multilingual-Perspectivist-NLU/MultiPICo/resolve/main/"
    "multipico_anonimized.csv"
)
CLASSES_IRONIA = ["nao_ironico", "ironico"]


def ler_multipico(
    caminho: str | Path, *, idioma: str = "pt", variedade: str | None = None
) -> Exemplos:
    """MultiPICo (Casola et al., ACL 2024), CC BY 4.0: pares post-resposta de Reddit e Twitter.

    Rotulo por MAIORIA dos anotadores de cada par; empate sai. O texto e a
    RESPOSTA, que e o que o sinal le no atendimento (a mensagem do cliente).
    Ironico e nao ironico vem das mesmas fontes -- ao contrario do IDPT, a
    procedencia nao entrega o rotulo. Grupo = post, para que respostas ao mesmo
    post nao caiam dos dois lados.
    """
    _permitir_campo_longo()
    votos: dict[tuple[str, str], list[int]] = {}
    texto_de: dict[tuple[str, str], str] = {}
    with open(caminho, newline="", encoding="utf-8") as arquivo:
        for linha in csv.DictReader(arquivo):
            if linha.get("language") != idioma:
                continue
            if variedade is not None and linha.get("language_variety") != variedade:
                continue
            rotulo = (linha.get("label") or "").strip()
            if rotulo not in ("0", "1"):
                continue
            chave = (linha["post_id"], linha["reply_id"])
            votos.setdefault(chave, []).append(int(rotulo))
            texto_de.setdefault(chave, (linha.get("reply") or "").strip())
    ex = Exemplos(grupos=[], nomes_classes=list(CLASSES_IRONIA))
    for chave, lista in votos.items():
        ironicos = sum(lista)
        if 2 * ironicos == len(lista) or not texto_de[chave]:
            continue
        ex.textos.append(texto_de[chave])
        ex.rotulos.append(int(2 * ironicos > len(lista)))
        ex.grupos.append(chave[0])
    return ex

# Corpus pequeno (~1,9 mil pares): teste maior que o padrao para o IC nao
# ficar largo demais. Notebook e benchmark usam ESTAS fracoes.
FRACOES_MULTIPICO = {"fracao_val": 0.15, "fracao_teste": 0.25}
