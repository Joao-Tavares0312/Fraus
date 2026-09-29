import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from scripts.preparar_modelos_vercel import (
    ArtefatoDeModelosInvalido,
    conferir_modelos,
    extrair_zip_seguro,
    instalar_extraido,
    sobrepor_laya_se_declarada,
)
from scripts.gerenciar_artefatos import empacotar, main as gerenciar_artefatos, validar


RAIZ = Path(__file__).resolve().parents[1]


def test_entrypoint_vercel_expoe_fastapi_real():
    fonte = (RAIZ / "api" / "index.py").read_text(encoding="utf-8")
    assert "from fraus.api.main import criar_app_padrao" in fonte
    assert "class AplicacaoPreguicosa" in fonte
    assert "api_demo" not in fonte


def test_vercel_declara_large_function_e_inclui_modelos():
    fonte = (RAIZ / "vercel.json").read_text(encoding="utf-8")
    for trecho in ("api/index.py", "maxDuration", "300", '"includeFiles": "**"'):
        assert trecho in fonte
    configuracao = json.loads(fonte)
    assert "--no-deps laya==0.3.21" in configuracao["installCommand"]


def test_dashboard_tem_configuracao_vercel_independente():
    configuracao = json.loads(
        (RAIZ / "dashboard" / "vercel.json").read_text(encoding="utf-8")
    )

    assert configuracao["framework"] == "nextjs"
    assert configuracao["buildCommand"] == "npm run build"


def test_workflow_da_api_e_manual_protegido_e_faz_smoke_finito():
    fonte = (RAIZ / ".github" / "workflows" / "api-deploy.yml").read_text(
        encoding="utf-8"
    )
    assert "workflow_dispatch:" in fonte
    assert "environment: production-api" in fonte
    assert "cancel-in-progress: false" in fonte
    assert "vercel@60.1.3" in fonte
    assert "--prebuilt --prod" in fonte
    assert "scripts/smoke_deploy.py" in fonte
    assert "schedule:" not in fonte


def test_requirements_instala_runtime_onnx_sem_torch():
    requisitos = (RAIZ / "requirements.txt").read_text(encoding="utf-8")
    assert ".[onnx]" in requisitos
    assert ".[torch]" not in requisitos
    projeto = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    dependencias_principais = projeto.split("[project.optional-dependencies]", 1)[0]
    assert '"onnxruntime>=1.20"' in dependencias_principais
    assert '"torch>=2.3"' not in dependencias_principais


def test_ignore_da_vercel_nao_remove_o_modulo_de_dominio():
    linhas = (RAIZ / ".vercelignore").read_text(encoding="utf-8").splitlines()
    assert "modelos*" not in linhas
    assert "/modelos*/" in linhas


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


def test_backend_laya_onnx_exige_grafo_e_tokenizador(tmp_path, monkeypatch):
    _artefatos_minimos(tmp_path)
    monkeypatch.setenv("FRAUS_IRONIA_BACKEND", "laya-onnx")
    with pytest.raises(ArtefatoDeModelosInvalido, match="laya.onnx"):
        conferir_modelos(tmp_path)

    laya = tmp_path / "modelos-onnx" / "laya-ironia"
    (laya / "tokenizer").mkdir(parents=True)
    for relativo in (
        "laya.onnx",
        "manifesto.json",
        "rl_agent_config.json",
        "tokenizer/tokenizer.json",
        "tokenizer/tokenizer_config.json",
    ):
        (laya / relativo).write_text("{}")
    (laya / "manifesto.json").write_text('{"formato": "int8"}')
    conferir_modelos(tmp_path)

    (laya / "manifesto.json").write_text('{"formato": "fp32"}')
    with pytest.raises(ArtefatoDeModelosInvalido, match="laya.onnx.data"):
        conferir_modelos(tmp_path)
    (laya / "laya.onnx.data").write_bytes(b"pesos")
    conferir_modelos(tmp_path)


def test_backend_laya_onnx_exige_url_e_checksum_separados(tmp_path, monkeypatch):
    monkeypatch.setenv("FRAUS_IRONIA_BACKEND", "laya-onnx")
    monkeypatch.delenv("FRAUS_LAYA_MODELO_URL", raising=False)
    monkeypatch.delenv("FRAUS_LAYA_MODELO_SHA256", raising=False)

    with pytest.raises(ArtefatoDeModelosInvalido, match="FRAUS_LAYA_MODELO_URL"):
        sobrepor_laya_se_declarada(tmp_path, tmp_path)


def _artefatos_minimos(raiz: Path) -> None:
    (raiz / "modelos").mkdir(parents=True)
    (raiz / "modelos" / "fusor.joblib").write_bytes(b"fusor")
    for nome in ("satisfacao", "emocao", "ironia"):
        pasta = raiz / "modelos-onnx" / f"bertimbau-{nome}"
        pasta.mkdir(parents=True)
        (pasta / "model.onnx").write_bytes(nome.encode())
        (pasta / "config.json").write_text("{}")
        (pasta / "tokenizer_config.json").write_text("{}")


def test_empacotamento_e_deterministico_e_validavel(tmp_path):
    _artefatos_minimos(tmp_path)
    primeiro = empacotar(tmp_path, tmp_path / "v1.zip", "v1")
    segundo = empacotar(tmp_path, tmp_path / "v1-copia.zip", "v1")

    assert hashlib.sha256(primeiro.read_bytes()).digest() == hashlib.sha256(segundo.read_bytes()).digest()
    resultado = validar(primeiro)
    assert resultado["sha256"]
    manifesto = json.loads((tmp_path / "v1.zip.json").read_text())
    assert manifesto["sha256"] == resultado["sha256"]


def test_empacotamento_recusa_sobrescrever(tmp_path):
    _artefatos_minimos(tmp_path)
    destino = tmp_path / "existente.zip"
    destino.write_bytes(b"nao apagar")
    with pytest.raises(FileExistsError, match="recuso sobrescrever"):
        empacotar(tmp_path, destino, "v1")


def test_rollback_so_valida_objeto_retido_sem_exigir_url(tmp_path, monkeypatch, capsys):
    _artefatos_minimos(tmp_path)
    pacote = empacotar(tmp_path, tmp_path / "anterior.zip", "anterior")
    monkeypatch.delenv("FRAUS_ARTEFATO_PUBLICAR_URL", raising=False)
    monkeypatch.setattr("sys.argv", ["gerenciar_artefatos.py", "rollback", str(pacote)])

    assert gerenciar_artefatos() == 0
    saida = json.loads(capsys.readouterr().out)
    assert saida["status"] == "rollback_validado"


def test_promocao_local_restaura_bundle_anterior_se_move_falhar(tmp_path, monkeypatch):
    atual = tmp_path / "atual"
    novo = tmp_path / "novo"
    _artefatos_minimos(atual)
    _artefatos_minimos(novo)
    (atual / "modelos" / "marcador").write_text("anterior")
    move_real = __import__("shutil").move
    chamadas = 0

    def falhar_no_ultimo_move(origem, destino):
        nonlocal chamadas
        chamadas += 1
        if chamadas == 4:
            raise OSError("disco cheio")
        return move_real(origem, destino)

    monkeypatch.setattr("scripts.preparar_modelos_vercel.shutil.move", falhar_no_ultimo_move)
    with pytest.raises(OSError, match="disco cheio"):
        instalar_extraido(novo, atual)

    assert (atual / "modelos" / "marcador").read_text() == "anterior"
    conferir_modelos(atual)
