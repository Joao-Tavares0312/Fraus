"""Quem executa os BERTimbau e DECLARADO, nunca deduzido nem trocado em silencio."""

import sys

import pytest

from fraus.api import caminhos
from fraus.api.main import montar_classificadores
from fraus.sinais.onnx import ModeloOnnxAusenteError


def test_padrao_e_torch(monkeypatch):
    monkeypatch.delenv("FRAUS_BACKEND", raising=False)
    assert caminhos.backend_declarado() == "torch"


def test_backend_desconhecido_derruba_o_boot(monkeypatch):
    monkeypatch.setenv("FRAUS_BACKEND", "tensorflow")
    with pytest.raises(ValueError, match="FRAUS_BACKEND"):
        caminhos.backend_declarado()


def test_onnx_sem_grafo_falha_alto_e_nao_cai_para_o_torch(monkeypatch, tmp_path):
    import fraus.api.main as main

    monkeypatch.setattr(main, "CAMINHO_ONNX_TEXTO", tmp_path / "nao-existe")
    with pytest.raises(ModeloOnnxAusenteError):
        montar_classificadores("onnx")


def test_importar_o_motor_nao_arrasta_o_torch():
    """Com FRAUS_BACKEND=onnx a imagem nao tem torch; importar o dominio nao
    pode exigi-lo. Roda em processo novo: este aqui pode ja ter o torch."""
    import subprocess

    codigo = (
        "import sys; import fraus.motor, fraus.api.main; "
        "sys.exit(1 if 'torch' in sys.modules else 0)"
    )
    assert subprocess.run([sys.executable, "-c", codigo]).returncode == 0
