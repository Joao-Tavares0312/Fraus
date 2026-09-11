"""O roteiro de deploy nao pode mandar rodar o que nao existe -- nem o que nao
existe NA MAQUINA em que ele foi escrito.

`docs/hospedagem.md` e executado por uma pessoa numa sessao ssh, sob pressao,
contra uma maquina recem-criada. Um comando errado ali nao falha rapido e perto:
ele falha no meio do caminho, com metade da VM configurada, e o proximo passo
mente sobre o motivo.

Duas armadilhas ja aconteceram e sao o que estes testes prendem:

1. O roteiro pedia `rsync`, e o **Git Bash do Windows nao tem `rsync`** -- o
   passo 4 falharia na maquina de quem escreveu o projeto.
2. Script citado na documentacao e renomeado; a doc segue apontando para o
   nome antigo, e ninguem descobre ate alguem tentar seguir o roteiro.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
ROTEIRO = RAIZ / "docs" / "hospedagem.md"
SCRIPTS = [
    RAIZ / "scripts" / "provisionar_oracle.sh",
    RAIZ / "scripts" / "abrir_portas_oracle.py",
]


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda s: s.name)
def test_o_roteiro_cita_scripts_que_existem(script):
    """Renomear um script sem mexer na doc publica um comando que nao roda."""
    assert script.exists(), f"{script.name} nao existe"
    assert script.name in ROTEIRO.read_text(encoding="utf-8"), (
        f"{script.name} existe mas o roteiro nao o menciona -- automacao que "
        "ninguem descobre e automacao que ninguem usa"
    )


def test_o_roteiro_nao_manda_usar_rsync():
    """O Git Bash do Windows nao traz `rsync`, e e o shell deste projeto.

    A sonda olha so os blocos de comando: a prosa EXPLICA por que o rsync saiu,
    e um teste que casasse a explicacao mediria a documentacao em vez do
    comportamento -- erro que este arquivo de testes ja cometeu uma vez, em
    `test_documentacao.py`.
    """
    linhas = ROTEIRO.read_text(encoding="utf-8").splitlines()
    dentro, achados = False, []
    for numero, linha in enumerate(linhas, 1):
        if linha.lstrip().startswith("```"):
            dentro = not dentro
            continue
        if dentro and re.search(r"\brsync\b", linha):
            achados.append(f"linha {numero}: {linha.strip()}")
    assert achados == [], (
        "o roteiro manda rodar rsync, que nao existe no Git Bash do Windows: "
        f"{achados}"
    )


def _bash_de_verdade() -> str | None:
    """Um `bash` que realmente executa, nao so um nome no PATH.

    No Windows, `shutil.which("bash")` encontra primeiro o STUB DA WSL em
    `System32` -- que nao e um shell: e um lancador que falha se nenhuma
    distribuicao estiver instalada (e, nesta maquina, falha mesmo com uma).
    Confiar no `which` fazia este teste reprovar um script sintaticamente
    correto, culpando o arquivo por um defeito do ambiente.

    Por isso a sonda TESTA o candidato antes de usa-lo, e prefere o Git Bash.
    """
    candidatos = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        shutil.which("bash"),
    ]
    for candidato in candidatos:
        if not candidato or not Path(candidato).exists():
            continue
        try:
            if subprocess.run([candidato, "-c", "exit 0"], timeout=30).returncode == 0:
                return candidato
        except (OSError, subprocess.SubprocessError):
            continue
    return None


def test_o_script_de_provisionamento_faz_parse():
    """`bash -n` le o script inteiro sem executar nada.

    Um erro de sintaxe aqui so apareceria com a VM ja de pe e o relogio
    correndo -- que e o pior momento possivel para descobrir um `fi` faltando.
    """
    bash = _bash_de_verdade()
    if bash is None:
        pytest.skip("nenhum bash executavel nesta maquina")
    processo = subprocess.run(
        [bash, "-n", str(SCRIPTS[0])],
        capture_output=True,
        text=True,
    )
    assert processo.returncode == 0, processo.stderr


def test_a_imagem_instala_o_projeto_em_vez_de_listar_dependencia_a_mao():
    """Lista de dependencia escrita a mao no Dockerfile envelhece em silencio.

    Ate 11/09/2026 o Dockerfile mantinha uma copia manual das dependencias, em
    paralelo a do `pyproject.toml`. As duas divergiram: faltavam `pyjwt`,
    `openpyxl`, `python-docx`, `pypdf` e `python-multipart`. A imagem
    CONSTRUIA sem reclamar -- e so morria no boot, com `ModuleNotFoundError:
    No module named 'jwt'`, a uma distancia enorme da causa.

    Quem acrescenta uma dependencia mexe no pyproject e nao tem motivo nenhum
    para lembrar deste arquivo. A unica defesa que funciona e nao haver duas
    listas.
    """
    linhas = [
        linha
        for linha in (RAIZ / "Dockerfile").read_text(encoding="utf-8").splitlines()
        if not linha.lstrip().startswith("#")
    ]
    dockerfile = "\n".join(linhas)

    assert "pip install --no-cache-dir ." in dockerfile, (
        "o Dockerfile precisa instalar o PROJETO (`pip install .`), e nao "
        "repetir as dependencias do pyproject.toml"
    )

    # O torch e a excecao legitima: ele precisa de tratamento por arquitetura
    # (indice de CPU no x86, pin de versao no ARM) e por isso vem antes.
    import tomllib

    declaradas = tomllib.loads(
        (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]["dependencies"]

    # SO as linhas de instalacao. Procurar o nome do pacote no arquivo inteiro
    # acusaria `uvicorn` (que aparece no CMD) e `joblib` (no caminho
    # `/modelos/fusor.joblib` do ENV) -- mencao nao e instalacao, e uma sonda
    # que confunde as duas mede texto em vez de comportamento.
    instalacoes = "\n".join(
        linha.lower() for linha in linhas if "pip install" in linha
    )
    repetidas = [
        spec
        for spec in declaradas
        if not spec.lower().startswith("torch")
        and re.split(r"[<>=!\[ ]", spec.strip())[0].lower() in instalacoes
    ]
    assert repetidas == [], (
        f"dependencia repetida no Dockerfile fora do pyproject: {repetidas}"
    )


def test_o_script_nao_regera_segredo_em_execucao_repetida():
    """A regra que torna o script seguro de repetir, presa no arquivo.

    Recriar a `FRAUS_CHAVE_MESTRA` numa segunda execucao invalidaria a
    `FRAUS_CHAVE_ACESSO` que a dashboard usa -- sem erro no momento, e com o
    sintoma ("401 em tudo") aparecendo horas depois, longe da causa. E o tipo
    de defeito que so se evita de proposito.
    """
    texto = SCRIPTS[0].read_text(encoding="utf-8")
    assert "if [ -f ~/fraus/.env ]" in texto, (
        "o script precisa preservar um .env existente antes de gerar segredo"
    )
