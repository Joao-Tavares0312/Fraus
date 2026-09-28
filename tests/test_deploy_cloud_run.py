"""Guardas do deploy serverless da API real.

O Cloud Run tem disco efemero e injeta a porta em ``PORT``. Os modelos nao
podem entrar na imagem: alem de tornar cada build enorme, isso consumiria o
armazenamento gratuito do Artifact Registry. Estas sondas prendem as decisoes
que fazem o deploy caber na franquia gratuita.
"""

from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
DOCKERFILE = RAIZ / "Dockerfile"
BUILD = RAIZ / "cloudbuild.yaml"
SCRIPT = RAIZ / "scripts" / "configurar_cloud_run.ps1"
DOCKERIGNORE = RAIZ / ".dockerignore"
GCLOUDIGNORE = RAIZ / ".gcloudignore"


def test_cloud_run_usa_a_porta_injetada_pelo_ambiente():
    texto = DOCKERFILE.read_text(encoding="utf-8")
    assert "${PORT:-8000}" in texto


def test_build_cloud_run_declara_backend_onnx():
    texto = BUILD.read_text(encoding="utf-8")
    assert "BACKEND=onnx" in texto
    assert "modelos-onnx" not in texto
    assert "modelos/" not in texto


def test_deploy_monta_pesos_em_volume_e_limita_custo():
    texto = SCRIPT.read_text(encoding="utf-8")
    exigidos = [
        "type=cloud-storage",
        "readonly=true",
        "--memory=2Gi",
        "--cpu=1",
        "--concurrency=1",
        "--max-instances=1",
        "--min-instances=0",
        "FRAUS_BACKEND=onnx",
        "FRAUS_DATABASE_URL=fraus-database-url:latest",
    ]
    for trecho in exigidos:
        assert trecho in texto, f"configuracao ausente no deploy: {trecho}"


def test_segredos_nao_entram_como_argumentos_do_script():
    texto = SCRIPT.read_text(encoding="utf-8")
    parametros = texto.split(")", 1)[0]
    assert "DatabaseUrl" not in parametros
    assert "ChaveMestra" not in parametros
    assert "JwtSegredo" not in parametros


def test_pesos_nao_entram_no_contexto_de_build():
    for arquivo in (DOCKERIGNORE, GCLOUDIGNORE):
        texto = arquivo.read_text(encoding="utf-8")
        assert "modelos*" in texto, f"{arquivo.name} enviaria gigabytes de pesos"
        assert ".env" in texto, f"{arquivo.name} poderia enviar segredos ao build"
