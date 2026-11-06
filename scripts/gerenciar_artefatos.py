"""Empacota, valida, publica e reverte o bundle de modelos da API.

A URL de escrita só entra por ``FRAUS_ARTEFATO_PUBLICAR_URL`` e nunca é
impressa. Rollback é a republicação explícita de um pacote anterior, depois da
mesma validação de checksum e conteúdo usada na promoção normal.
"""

import argparse
import hashlib
import http.client
import json
import os
import ssl
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from scripts.preparar_modelos_vercel import (
    ArtefatoDeModelosInvalido,
    conferir_checksum,
    conferir_modelos,
    extrair_zip_seguro,
)

PASTAS_ONNX = tuple(f"modelos-onnx/bertimbau-{nome}" for nome in ("satisfacao", "emocao", "ironia"))


def sha256(caminho: Path) -> str:
    hash_ = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            hash_.update(bloco)
    return hash_.hexdigest()


def arquivos_do_bundle(raiz: Path) -> list[tuple[Path, str]]:
    conferir_modelos(raiz)
    arquivos: list[tuple[Path, str]] = []
    for relativa in PASTAS_ONNX:
        pasta = raiz / relativa
        arquivos.extend((item, item.relative_to(raiz).as_posix()) for item in pasta.rglob("*") if item.is_file())
    fusor = raiz / "modelos" / "fusor.joblib"
    arquivos.append((fusor, "modelos/fusor.joblib"))
    for opcional in (
        "modelos/bertimbau-satisfacao/metricas.json",
        "modelos/metricas_emocao.json",
        "modelos/metricas_ironia.json",
    ):
        caminho = raiz / opcional
        if caminho.is_file():
            arquivos.append((caminho, opcional))
    return sorted(arquivos, key=lambda par: par[1])


def empacotar(raiz: Path, destino: Path, versao: str) -> Path:
    if destino.exists():
        raise FileExistsError(f"recuso sobrescrever pacote existente: {destino.name}")
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipado:
        for caminho, nome in arquivos_do_bundle(raiz):
            info = zipfile.ZipInfo(nome, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with caminho.open("rb") as origem, zipado.open(info, "w") as alvo:
                for bloco in iter(lambda: origem.read(1024 * 1024), b""):
                    alvo.write(bloco)
    checksum = sha256(destino)
    manifesto = {
        "schema": 1,
        "versao": versao,
        "arquivo": destino.name,
        "bytes": destino.stat().st_size,
        "sha256": checksum,
        "criado_em": datetime.now(timezone.utc).isoformat(),
    }
    destino.with_suffix(destino.suffix + ".json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    destino.with_suffix(destino.suffix + ".sha256").write_text(
        f"{checksum}  {destino.name}\n", encoding="ascii"
    )
    return destino


def validar(pacote: Path, checksum: str | None = None) -> dict:
    if checksum:
        conferir_checksum(pacote, checksum)
    with tempfile.TemporaryDirectory(prefix="fraus-validar-artefato-") as temporario:
        raiz = Path(temporario)
        extrair_zip_seguro(pacote, raiz)
        conferir_modelos(raiz)
    return {"arquivo": pacote.name, "bytes": pacote.stat().st_size, "sha256": sha256(pacote)}


def publicar(pacote: Path, url: str, token: str | None = None) -> None:
    analisada = urlparse(url)
    if analisada.scheme != "https" or not analisada.hostname:
        raise ValueError("FRAUS_ARTEFATO_PUBLICAR_URL precisa usar HTTPS")
    caminho = analisada.path or "/"
    if analisada.query:
        caminho += "?" + analisada.query
    conexao = http.client.HTTPSConnection(
        analisada.hostname,
        analisada.port or 443,
        timeout=300,
        context=ssl.create_default_context(),
    )
    cabecalhos = {"Content-Length": str(pacote.stat().st_size), "Content-Type": "application/zip"}
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    try:
        conexao.putrequest("PUT", caminho)
        for nome, valor in cabecalhos.items():
            conexao.putheader(nome, valor)
        conexao.endheaders()
        with pacote.open("rb") as arquivo:
            for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
                conexao.send(bloco)
        resposta = conexao.getresponse()
        resposta.read()
        if resposta.status not in {200, 201, 204}:
            raise RuntimeError(f"publicacao recusada pelo armazenamento: HTTP {resposta.status}")
    finally:
        conexao.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="comando", required=True)
    p_empacotar = sub.add_parser("empacotar")
    p_empacotar.add_argument("--raiz", type=Path, default=Path.cwd())
    p_empacotar.add_argument("--saida", type=Path, required=True)
    p_empacotar.add_argument("--versao", required=True)
    for nome in ("validar", "publicar", "rollback"):
        p = sub.add_parser(nome)
        p.add_argument("pacote", type=Path)
        p.add_argument("--sha256")
    args = parser.parse_args()
    if args.comando == "empacotar":
        pacote = empacotar(args.raiz, args.saida, args.versao)
        print(json.dumps({"status": "empacotado", **validar(pacote)}))
        return 0
    resultado = validar(args.pacote, args.sha256)
    if args.comando == "publicar":
        url = os.environ.get("FRAUS_ARTEFATO_PUBLICAR_URL", "")
        if not url:
            raise RuntimeError("FRAUS_ARTEFATO_PUBLICAR_URL nao definida")
        publicar(args.pacote, url, os.environ.get("FRAUS_ARTEFATO_TOKEN"))
        resultado["status"] = "publicado"
    elif args.comando == "rollback":
        # O objeto anterior e imutavel e ja esta publicado. O comando prova que
        # a copia retida corresponde ao checksum antes de o operador trocar os
        # dois secrets de leitura e disparar novo deploy.
        resultado["status"] = "rollback_validado"
    else:
        resultado["status"] = "valido"
    # Nunca inclui URL, token nem cabeçalhos da publicação.
    print(json.dumps(resultado, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
