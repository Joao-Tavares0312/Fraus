import hashlib
import json
import re
import zipfile
from pathlib import Path

import pytest

from scripts.preparar_modelos_vercel import (
    ArtefatoDeModelosInvalido,
    conferir_modelos,
    extrair_zip_seguro,
    instalar_extraido,
)
from scripts.gerenciar_artefatos import empacotar, main as gerenciar_artefatos, validar


RAIZ = Path(__file__).resolve().parents[1]


def test_entrypoints_vercel_expoem_fastapi_real_com_e_sem_motor():
    leve = (RAIZ / "api" / "index.py").read_text(encoding="utf-8")
    motor = (RAIZ / "api" / "motor.py").read_text(encoding="utf-8")
    for fonte in (leve, motor):
        assert "from fraus.api.main import criar_app_padrao" in fonte
        assert "api_demo" not in fonte
    assert "com_motor=False" in leve
    assert "com_motor=False" not in motor


def _destino(rewrites, caminho):
    for regra in rewrites:
        if re.fullmatch(regra["source"], caminho):
            return regra["destination"]
    return None


def test_rotas_de_modelo_vao_para_a_funcao_do_motor():
    configuracao = json.loads((RAIZ / "vercel.json").read_text(encoding="utf-8"))
    assert "laya" not in configuracao["installCommand"]
    funcoes = configuracao["functions"]
    assert "modelos-onnx/**" in funcoes["api/index.py"]["excludeFiles"]
    assert funcoes["api/motor.py"]["includeFiles"] == "**"

    rewrites = configuracao["rewrites"]
    no_motor = [
        "/saude", "/saude/prontidao", "/saude/deriva", "/analisar", "/analisar/registrar",
        "/analisar/previa", "/analisar/arquivo", "/ingestao", "/ingestao/",
        "/integracoes/webhook/3", "/conversas/importar", "/conversas/repontuar",
        "/conversas/abc/atribuicao", "/conversas/a/b/contrafactual", "/conversas/abc/confianca",
        "/indicadores/drivers", "/indicadores/confianca", "/grafo", "/modelo", "/modelo/simular",
        "/operacao/replay/x", "/operacao/laboratorio/cenario", "/operacao/laboratorio/comparar",
    ]
    na_leve = [
        "/auth/eu", "/auth/estado", "/conversas", "/conversas/abc", "/conversas/importar/previa",
        "/indicadores", "/serie-temporal", "/configuracoes", "/modelo/lexicon", "/lexico/curado",
        "/integracoes/fontes", "/operacao/equipes", "/operacao/radar", "/anotacao/tok",
    ]
    for caminho in no_motor:
        assert _destino(rewrites, caminho) == "/api/motor", caminho
    for caminho in na_leve:
        assert _destino(rewrites, caminho) == "/api/index", caminho


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


def test_ignore_da_vercel_nao_remove_dados_do_pacote_fraus():
    """`fraus/dados/` vai na funcao: a rota publica de anotacao le
    `regua_ironia_rascunho.csv` em runtime, e o lexico/SentiLex tambem. A
    conferencia usa a mesma semantica de padrao do git que a Vercel segue."""
    import shutil
    import subprocess

    if shutil.which("git") is None or not (RAIZ / ".git").exists():
        pytest.skip("sem git para aplicar o .vercelignore")
    ignorados = subprocess.run(
        ["git", "ls-files", "-i", "-c", "--exclude-from=.vercelignore", "fraus/"],
        cwd=RAIZ, capture_output=True, text=True, check=True,
    ).stdout.split()
    assert ignorados == []
    versionados = subprocess.run(
        ["git", "ls-files", "fraus/dados/regua_ironia_rascunho.csv"],
        cwd=RAIZ, capture_output=True, text=True, check=True,
    ).stdout.split()
    assert versionados == ["fraus/dados/regua_ironia_rascunho.csv"]
