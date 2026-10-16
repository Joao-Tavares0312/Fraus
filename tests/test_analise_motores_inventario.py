"""Inventario local: observacao sem carregar modelos nem executar configuracoes."""
import hashlib
import importlib
import json
import pickle
import struct
import sys
import types
import zipfile
from pathlib import Path

import pytest


def _modulo():
    return importlib.import_module("scripts.analise_motores.inventario")


def _rodar(tmp_path, raiz, *extras):
    workspace = tmp_path / "laboratorio"
    codigo = _modulo().main(["--raiz", str(raiz), "--workspace", str(workspace), *extras])
    arquivo = workspace / "experimentos" / "resultados" / "inventario.json"
    return codigo, json.loads(arquivo.read_text())


def _arquivo(raiz, relativo, conteudo=b"x"):
    caminho = raiz / relativo
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(conteudo)
    return caminho


def test_ausencia_e_conclusao_sem_tamanho_de_modelo_inventado(tmp_path):
    raiz = tmp_path / "repo"
    raiz.mkdir()
    codigo, dados = _rodar(tmp_path, raiz)
    assert codigo == 0 and dados["status"] == "medido"
    assert dados["medicoes"]["arquivos"] == []
    assert dados["medicoes"]["bytes"]["modelos"] is None
    assert dados["medicoes"]["bytes"]["motivo_modelos"]
    assert dados["medicoes"]["bundle_publicado"]["bytes"] is None
    assert all(item["status"] == "ausente" for item in dados["medicoes"]["diretorios"])


def test_joblib_nunca_e_desserializado_nem_saida_recebe_segredos(tmp_path, monkeypatch, capsys):
    raiz = tmp_path / "repo"
    marcador = tmp_path / "executou-pickle"

    class Perigoso:
        def __reduce__(self):
            return (Path.write_text, (marcador, "executado"))

    fusor = _arquivo(raiz, "modelos/fusor.joblib", pickle.dumps(Perigoso()))
    monkeypatch.setenv("FRAUS_CHAVE_ACESSO", "SEGREDO_NAO_VAZAR")
    codigo, dados = _rodar(tmp_path, raiz)
    assert codigo == 0 and not marcador.exists()
    item = next(a for a in dados["medicoes"]["arquivos"] if a["caminho"] == "modelos/fusor.joblib")
    assert item["sha256"] == hashlib.sha256(fusor.read_bytes()).hexdigest()
    assert item["bytes"] == fusor.stat().st_size
    assert item["inspecao"]["n_features"] is None
    assert item["inspecao"]["classes"] is None
    assert item["inspecao"]["_sklearn_version"] is None
    assert item["inspecao"]["motivo"]
    assert "SEGREDO_NAO_VAZAR" not in json.dumps(dados) + capsys.readouterr().out


def test_nao_segue_symlink_em_arquivo_ou_diretorio(tmp_path):
    raiz = tmp_path / "repo"
    origem = _arquivo(tmp_path, "fora/secreto.bin", b"nao inventariar")
    (raiz / "modelos").mkdir(parents=True)
    (raiz / "modelos" / "bertimbau-satisfacao").symlink_to(origem.parent, target_is_directory=True)
    (raiz / "modelos" / "fusor.joblib").symlink_to(origem)
    _arquivo(raiz, "outros/nao-declarado.bin", b"ignorar")
    codigo, dados = _rodar(tmp_path, raiz)
    assert codigo == 0
    assert dados["medicoes"]["arquivos"] == []
    assert dados["medicoes"]["recusas"]
    assert "secreto.bin" not in json.dumps(dados)


def test_safetensors_cabecalho_dimensoes_e_duplicatas(tmp_path):
    raiz = tmp_path / "repo"
    cabecalho = json.dumps({"peso": {"dtype": "F32", "shape": [2, 3], "data_offsets": [0, 24]}, "__metadata__": {"token": "NAO_PUBLICAR"}}).encode()
    conteudo = struct.pack("<Q", len(cabecalho)) + cabecalho + b"\0" * 24
    _arquivo(raiz, "modelos/bertimbau-satisfacao/model.safetensors", conteudo)
    _arquivo(raiz, "modelos/bertimbau-emocao/model.safetensors", conteudo)
    codigo, dados = _rodar(tmp_path, raiz)
    assert codigo == 0
    arquivos = dados["medicoes"]["arquivos"]
    assert arquivos[0]["inspecao"]["tensores"] == [{"nome": "peso", "dtype": "F32", "dimensoes": [2, 3], "offsets": [0, 24]}]
    assert len(dados["medicoes"]["duplicatas"]) == 1
    assert "NAO_PUBLICAR" not in json.dumps(dados)


def test_safetensors_recusa_cabecalho_gigante_sem_alocar(tmp_path):
    raiz = tmp_path / "repo"
    _arquivo(raiz, "modelos/bertimbau-ironia/model.safetensors", struct.pack("<Q", 2**63))
    codigo, dados = _rodar(tmp_path, raiz)
    assert codigo == 0
    inspecao = dados["medicoes"]["arquivos"][0]["inspecao"]
    assert inspecao["status"] == "nao_verificado" and inspecao["motivo"]


def test_zip_lista_sem_extrair_e_mantem_publicado_desconhecido(tmp_path):
    raiz = tmp_path / "repo"
    raiz.mkdir()
    pacote = tmp_path / "modelos.zip"
    with zipfile.ZipFile(pacote, "w") as arquivo:
        arquivo.writestr("../../escape.txt", "perigo")
        arquivo.writestr("modelos/fusor.joblib", b"abc")
    codigo, dados = _rodar(tmp_path, raiz, "--pacote", str(pacote))
    assert codigo == 0 and not (tmp_path / "escape.txt").exists()
    zip_ = dados["medicoes"]["pacote"]
    assert zip_["bytes_descompactados"] == 9
    assert len(zip_["membros"]) == 2
    assert zip_["membros"][0]["caminho_seguro"] is False
    assert dados["medicoes"]["bundle_publicado"]["bytes"] is None


def test_configuracoes_preservam_so_campos_permitidos(tmp_path, monkeypatch):
    raiz = tmp_path / "repo"
    _arquivo(raiz, "pyproject.toml", b'[project]\nname="fraus"\nversion="0.1.0"\ndependencies=["joblib>=1.4", "privado @ https://usuario:SENHA@example.test/pkg"]\n')
    _arquivo(raiz, "uv.lock", b'version=1\n[[package]]\nname="joblib"\nversion="1.4.2"\nsource={registry="https://SENHA@example.test"}\n')
    _arquivo(raiz, "vercel.json", json.dumps({"installCommand": "curl https://SENHA@example.test", "env": {"FRAUS_TOKEN": "SENHA"}, "functions": {"api/index.py": {"maxDuration": 300, "includeFiles": "**"}}}).encode())
    _arquivo(raiz, "fraus/api/amostra.py", b'import os\nchave = os.environ.get("FRAUS_CHAVE_MESTRA")\n')
    codigo, dados = _rodar(tmp_path, raiz)
    assert codigo == 0 and "SENHA" not in json.dumps(dados)
    assert "FRAUS_CHAVE_MESTRA" in dados["medicoes"]["variaveis_ambiente"]
    configuracao = next(c for c in dados["medicoes"]["configuracoes"] if c["caminho"] == "vercel.json")
    assert configuracao["dados"]["funcoes"][0]["maxDuration"] == 300
    assert "comando" not in configuracao["dados"]


def test_onnx_inspeciona_sem_sessao_nem_external_data(tmp_path, monkeypatch):
    raiz = tmp_path / "repo"
    _arquivo(raiz, "modelos-onnx/bertimbau-satisfacao/model.onnx", b"grafo")
    chamadas = []
    modelo = types.SimpleNamespace(ir_version=8, opset_import=[types.SimpleNamespace(domain="", version=17)], graph=types.SimpleNamespace(input=[], output=[], initializer=[], node=[], sparse_initializer=[]))

    def carregar(caminho, *, load_external_data):
        chamadas.append(load_external_data)
        assert load_external_data is False
        return modelo

    monkeypatch.setitem(sys.modules, "onnx", types.SimpleNamespace(load=carregar))
    monkeypatch.setitem(sys.modules, "onnxruntime", None)
    codigo, dados = _rodar(tmp_path, raiz, "--inspecionar-onnx")
    assert codigo == 0 and chamadas == [False]
    inspecao = dados["medicoes"]["arquivos"][0]["inspecao"]
    assert inspecao["ir_version"] == 8 and inspecao["opsets"][0]["versao"] == 17


def test_onnx_ausente_e_metadados_nao_impedem_inventario(tmp_path, monkeypatch):
    raiz = tmp_path / "repo"
    _arquivo(raiz, "modelos-onnx/bertimbau-emocao/model.onnx", b"grafo")
    monkeypatch.setitem(sys.modules, "onnx", None)
    codigo, dados = _rodar(tmp_path, raiz, "--inspecionar-onnx")
    assert codigo == 0
    assert dados["medicoes"]["arquivos"][0]["inspecao"]["status"] == "nao_verificado"
    assert dados["medicoes"]["dependencias"]


def test_raiz_e_workspace_symlink_recusados_sem_imprimir_alvo(tmp_path, capsys):
    raiz = tmp_path / "repo"
    raiz.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(raiz, target_is_directory=True)
    assert _modulo().main(["--raiz", str(alias), "--workspace", str(tmp_path / "lab")]) == 2
    assert str(raiz) not in capsys.readouterr().out


def test_workspace_na_raiz_inspecionada_nao_cria_diretorio(tmp_path):
    raiz = tmp_path / "repo"
    raiz.mkdir()
    workspace = raiz / "laboratorio"
    assert _modulo().main(["--raiz", str(raiz), "--workspace", str(workspace)]) == 2
    assert not workspace.exists()


def test_ignora_ocultos_e_preserva_bytes_dos_artefatos(tmp_path):
    raiz = tmp_path / "repo"
    peso = _arquivo(raiz, "modelos/fusor.joblib", b"nao desserializar")
    _arquivo(raiz, "modelos/.env", b"SEGREDO_NAO_LER")
    _arquivo(raiz, "modelos/.privado/chave.txt", b"SEGREDO_NAO_LER")
    antes = hashlib.sha256(peso.read_bytes()).hexdigest()
    codigo, dados = _rodar(tmp_path, raiz)
    assert codigo == 0
    assert [a["caminho"] for a in dados["medicoes"]["arquivos"]] == ["modelos/fusor.joblib"]
    assert hashlib.sha256(peso.read_bytes()).hexdigest() == antes
    assert "SEGREDO_NAO_LER" not in json.dumps(dados)
