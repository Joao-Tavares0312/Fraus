"""Baixa e higieniza os corpora publicos que deram origem ao treino do IDPT.

Os arquivos ficam fora do repositorio. Cada URL aponta para um commit imutavel
e cada blob Git e validado antes de qualquer linha entrar no corpus combinado.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import unicodedata
from urllib.request import urlopen

REV_TWEETS = "b735dd95e92adacb73ed27b2a243d5461d7fda93"
REV_NOTICIAS = "ee699075fb1e6578ee61721c7c69d7fa0112b49c"

FONTES = (
    ("tweets_ironicos", "fabio-ricardo/deteccao-ironia", REV_TWEETS,
     "ironia.csv", "1934ca879ba5c50cf45433ec83557dd6f66eee1a", 1),
    ("tweets_nao_ironicos", "fabio-ricardo/deteccao-ironia", REV_TWEETS,
     "nao-ironico.csv", "7e484ce9bbc5db0e69e0603c399e002462cd0e52", 0),
    ("noticias_estadao", "schuberty/PLNCrawler", REV_NOTICIAS,
     "datasets/estadao.json", "c2b413af9ac6a73a9813fe50858de815c42ed79a", 0),
    ("noticias_sensacionalista", "schuberty/PLNCrawler", REV_NOTICIAS,
     "datasets/sensacionalista.json", "fd4b54f614771df571d0ee6dd73c16bc0a6f7c05", 1),
    ("noticias_piaui_herald", "schuberty/PLNCrawler", REV_NOTICIAS,
     "datasets/the_piaui_herald.json", "17c82abc826de183102241f970262515e9062084", 1),
)

_ROTULO_VAZADO = re.compile(r"(?iu)(?<!\w)#\s*(?:ironia|irônico|ironico|sarcasmo|sarcasm)\b")
_ESPACO = re.compile(r"\s+")
_CAMPOS_TEXTO = ("texto", "text", "tweet", "title", "titulo", "headline", "content", "noticia")
_CAMPOS_AUTOR = ("autor", "author", "username", "user", "screen_name")


def git_blob_sha1(dados: bytes) -> str:
    return hashlib.sha1(f"blob {len(dados)}\0".encode() + dados).hexdigest()


def limpar_texto(texto: object) -> str:
    texto = unicodedata.normalize("NFC", str(texto or ""))
    texto = _ROTULO_VAZADO.sub(" ", texto)
    return _ESPACO.sub(" ", texto).strip(" ,;:-")


def _valor(registro: dict, candidatos: tuple[str, ...]):
    por_nome = {str(k).lower(): v for k, v in registro.items()}
    return next((por_nome[n] for n in candidatos if por_nome.get(n)), None)


def _registros_json(valor):
    if isinstance(valor, dict):
        if _valor(valor, _CAMPOS_TEXTO) is not None:
            yield valor
        else:
            for filho in valor.values():
                yield from _registros_json(filho)
    elif isinstance(valor, list):
        for filho in valor:
            yield from _registros_json(filho)


def ler_arquivo(caminho: Path, rotulo: int):
    if caminho.suffix == ".json":
        bruto = caminho.read_text(encoding="utf-8-sig")
        try:
            documentos = (json.loads(bruto),)
        except json.JSONDecodeError as erro:
            # Os crawlers publicos do IDPT usam a extensao `.json`, mas gravam
            # um objeto por linha (JSONL). So aceitamos esse segundo formato
            # quando a falha foi "dados extras"; JSON realmente truncado deve
            # continuar falhando alto em vez de perder registros em silencio.
            if erro.msg != "Extra data":
                raise
            documentos = tuple(
                json.loads(linha) for linha in bruto.splitlines() if linha.strip()
            )
        for documento in documentos:
            for registro in _registros_json(documento):
                yield _valor(registro, _CAMPOS_TEXTO), _valor(registro, _CAMPOS_AUTOR)
        return

    texto = caminho.read_text(encoding="utf-8-sig", errors="replace")
    amostra = texto[:8192]
    try:
        dialeto = csv.Sniffer().sniff(amostra, delimiters=",;\t|")
    except csv.Error:
        dialeto = csv.excel
    linhas = list(csv.reader(io.StringIO(texto), dialect=dialeto))
    if not linhas:
        return
    cabecalho = [c.strip().lower() for c in linhas[0]]
    tem_cabecalho = any(c in _CAMPOS_TEXTO + _CAMPOS_AUTOR for c in cabecalho)
    if tem_cabecalho:
        for registro in csv.DictReader(io.StringIO(texto), dialect=dialeto):
            yield _valor(registro, _CAMPOS_TEXTO), _valor(registro, _CAMPOS_AUTOR)
    else:
        # Os CSV originais de tweets sao listas: a coluna textual mais longa
        # e preferivel a IDs/indices, sem depender de um cabecalho inexistente.
        for linha in linhas:
            yield max(linha, key=len, default=""), None


def baixar(destino: Path, repo: str, revisao: str, caminho: str, blob: str) -> Path:
    arquivo = destino / repo.replace("/", "_") / caminho
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    if not arquivo.exists():
        url = f"https://raw.githubusercontent.com/{repo}/{revisao}/{caminho}"
        with urlopen(url, timeout=120) as resposta:  # noqa: S310 - host fixo acima
            arquivo.write_bytes(resposta.read())
    atual = git_blob_sha1(arquivo.read_bytes())
    if atual != blob:
        arquivo.unlink(missing_ok=True)
        raise RuntimeError(f"checksum Git divergente em {caminho}: {atual} != {blob}")
    return arquivo


def preparar(destino: Path) -> dict:
    linhas = []
    manifestos = []
    for origem, repo, revisao, caminho, blob, rotulo in FONTES:
        arquivo = baixar(destino, repo, revisao, caminho, blob)
        antes = len(linhas)
        for texto, autor in ler_arquivo(arquivo, rotulo):
            limpo = limpar_texto(texto)
            if limpo:
                linhas.append({"texto": limpo, "rotulo": rotulo, "fonte": origem,
                               "autor": limpar_texto(autor) if autor else ""})
        manifestos.append({"fonte": origem, "repositorio": repo, "revisao": revisao,
                           "caminho": caminho, "git_blob_sha1": blob,
                           "linhas_lidas": len(linhas) - antes, "licenca_codigo": "MIT"})

    # Mesmo texto com dois rotulos e ambiguidade, nao um voto para escolher.
    por_texto: dict[str, list[dict]] = {}
    for linha in linhas:
        chave = _ESPACO.sub(" ", linha["texto"].casefold()).strip()
        por_texto.setdefault(chave, []).append(linha)
    conflitos = {k for k, vs in por_texto.items() if len({v["rotulo"] for v in vs}) > 1}
    unicos = [vs[0] for k, vs in por_texto.items() if k not in conflitos]

    saida = destino / "corpus_ironia_limpo.csv"
    with saida.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=("texto", "rotulo", "fonte", "autor"))
        escritor.writeheader()
        escritor.writerows(unicos)
    manifesto = {"fontes": manifestos, "exemplos": len(unicos),
                 "duplicatas_removidas": len(linhas) - len(por_texto),
                 "conflitos_removidos": len(conflitos),
                 "nota_licenca": "MIT cobre os repositorios; direitos dos textos de terceiros permanecem com seus autores/publicadores."}
    (destino / "procedencia_ironia.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifesto


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destino", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(preparar(args.destino), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
