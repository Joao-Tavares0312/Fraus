"""Baixa e confere os pesos que entram na Large Function da Vercel.

Variaveis obrigatorias quando os modelos nao existem no workspace de build:

``FRAUS_MODELOS_URL``
    URL HTTPS de um ZIP com ``modelos-onnx/`` e ``modelos/fusor.joblib``.
``FRAUS_MODELOS_SHA256``
    SHA-256 exato do ZIP. URL sem checksum nunca vira modelo de producao.
``FRAUS_MODELOS_TOKEN``
    Bearer opcional para um objeto privado.
"""

import hashlib
import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
MODELOS = ("satisfacao", "emocao", "ironia")
LIMITE_DESCOMPACTADO = 2 * 1024**3


class ArtefatoDeModelosInvalido(RuntimeError):
    pass


def conferir_checksum(caminho: Path, esperado: str) -> None:
    esperado = esperado.strip().lower()
    if len(esperado) != 64:
        raise ArtefatoDeModelosInvalido("FRAUS_MODELOS_SHA256 nao e um SHA-256 valido")
    hash_ = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            hash_.update(bloco)
    recebido = hash_.hexdigest()
    if recebido != esperado:
        raise ArtefatoDeModelosInvalido(
            f"SHA-256 dos modelos diverge: esperado {esperado}, recebido {recebido}"
        )


def extrair_zip_seguro(pacote: Path, destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    raiz = destino.resolve()
    with zipfile.ZipFile(pacote) as zipado:
        tamanho = sum(item.file_size for item in zipado.infolist())
        if tamanho > LIMITE_DESCOMPACTADO:
            raise ArtefatoDeModelosInvalido(
                f"ZIP descompactaria {tamanho / 1024**3:.2f} GB; limite de seguranca e 2 GB"
            )
        for item in zipado.infolist():
            alvo = (destino / item.filename).resolve()
            if alvo != raiz and raiz not in alvo.parents:
                raise ArtefatoDeModelosInvalido(
                    f"entrada do ZIP aponta para fora do destino: {item.filename}"
                )
        zipado.extractall(destino)


def conferir_modelos(raiz: Path) -> None:
    esperados = [raiz / "modelos" / "fusor.joblib"]
    esperados += [
        raiz / "modelos-onnx" / f"bertimbau-{nome}" / "model.onnx"
        for nome in MODELOS
    ]
    for nome in MODELOS:
        pasta = raiz / "modelos-onnx" / f"bertimbau-{nome}"
        esperados.extend((pasta / "config.json", pasta / "tokenizer_config.json"))
    if (os.environ.get("FRAUS_IRONIA_BACKEND") or "").strip().lower() == "laya-onnx":
        laya = raiz / "modelos-onnx" / "laya-ironia"
        esperados.extend(
            (
                laya / "laya.onnx",
                laya / "manifesto.json",
                laya / "rl_agent_config.json",
                laya / "tokenizer" / "tokenizer.json",
                laya / "tokenizer" / "tokenizer_config.json",
            )
        )
    ausentes = [str(caminho.relative_to(raiz)) for caminho in esperados if not caminho.is_file()]
    if ausentes:
        raise ArtefatoDeModelosInvalido("artefato de modelo ausente: " + ", ".join(ausentes))


def baixar(url: str, destino: Path, token: str | None = None) -> None:
    if not url.startswith("https://"):
        raise ArtefatoDeModelosInvalido("FRAUS_MODELOS_URL precisa usar HTTPS")
    cabecalhos = {"User-Agent": "fraus-build/1"}
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    requisicao = urllib.request.Request(url, headers=cabecalhos)
    with urllib.request.urlopen(requisicao, timeout=60) as resposta, destino.open("wb") as arquivo:
        shutil.copyfileobj(resposta, arquivo, length=1024 * 1024)


def instalar_extraido(extraido: Path, raiz: Path) -> None:
    """Promove bundle completo e restaura o anterior se qualquer move falhar."""
    nomes = ("modelos-onnx", "modelos")
    backups: dict[str, Path] = {}
    instalados: list[Path] = []
    try:
        for nome in nomes:
            destino = raiz / nome
            if destino.exists():
                backup = raiz / f".{nome}.anterior"
                if backup.exists():
                    shutil.rmtree(backup)
                shutil.move(str(destino), backup)
                backups[nome] = backup
        for nome in nomes:
            destino = raiz / nome
            shutil.move(str(extraido / nome), destino)
            instalados.append(destino)
        conferir_modelos(raiz)
    except Exception:
        for destino in reversed(instalados):
            if destino.exists():
                shutil.rmtree(destino)
        for nome, backup in backups.items():
            shutil.move(str(backup), raiz / nome)
        raise
    else:
        for backup in backups.values():
            if backup.exists():
                shutil.rmtree(backup)


def preparar() -> None:
    try:
        conferir_modelos(RAIZ)
        print("modelos ONNX ja presentes e completos")
        return
    except ArtefatoDeModelosInvalido:
        pass

    url = os.environ.get("FRAUS_MODELOS_URL", "")
    checksum = os.environ.get("FRAUS_MODELOS_SHA256", "")
    if not url or not checksum:
        raise ArtefatoDeModelosInvalido(
            "modelos ausentes; defina FRAUS_MODELOS_URL e FRAUS_MODELOS_SHA256 no projeto da API"
        )

    with tempfile.TemporaryDirectory(prefix="fraus-modelos-") as temporario:
        temporario = Path(temporario)
        pacote = temporario / "modelos.zip"
        extraido = temporario / "extraido"
        baixar(url, pacote, os.environ.get("FRAUS_MODELOS_TOKEN"))
        conferir_checksum(pacote, checksum)
        extrair_zip_seguro(pacote, extraido)
        conferir_modelos(extraido)

        instalar_extraido(extraido, RAIZ)
    conferir_modelos(RAIZ)
    print("modelos ONNX baixados, conferidos e prontos para o bundle")


if __name__ == "__main__":
    preparar()
