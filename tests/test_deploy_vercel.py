import hashlib
import zipfile
from pathlib import Path

import pytest

from scripts.preparar_modelos_vercel import (
    ArtefatoDeModelosInvalido,
    conferir_modelos,
    extrair_zip_seguro,
)


RAIZ = Path(__file__).resolve().parents[1]


def test_entrypoint_vercel_expoe_fastapi_real():
    fonte = (RAIZ / "api" / "index.py").read_text(encoding="utf-8")
    assert "from fraus.api.main import app" in fonte
    assert "api_demo" not in fonte


def test_vercel_declara_large_function_e_inclui_modelos():
    fonte = (RAIZ / "vercel.json").read_text(encoding="utf-8")
    for trecho in ("api/index.py", "maxDuration", "300", "modelos-onnx", "modelos/fusor.joblib"):
        assert trecho in fonte


def test_requirements_instala_runtime_onnx_sem_torch():
    requisitos = (RAIZ / "requirements.txt").read_text(encoding="utf-8")
    assert ".[onnx]" in requisitos
    assert ".[torch]" not in requisitos


def test_extracao_recusa_escape_do_zip(tmp_path):
    pacote = tmp_path / "pesos.zip"
    with zipfile.ZipFile(pacote, "w") as zipado:
        zipado.writestr("../segredo.txt", "nao")
    with pytest.raises(ArtefatoDeModelosInvalido, match="fora do destino"):
        extrair_zip_seguro(pacote, tmp_path / "saida")


def test_checksum_incorreto_e_recusado(tmp_path):
    pacote = tmp_path / "pesos.zip"
    pacote.write_bytes(b"conteudo")
    correto = hashlib.sha256(b"conteudo").hexdigest()
    assert correto != "0" * 64
    from scripts.preparar_modelos_vercel import conferir_checksum

    with pytest.raises(ArtefatoDeModelosInvalido, match="SHA-256"):
        conferir_checksum(pacote, "0" * 64)


def test_modelos_incompletos_falham_alto(tmp_path):
    with pytest.raises(ArtefatoDeModelosInvalido, match="ausente"):
        conferir_modelos(tmp_path)
