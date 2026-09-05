"""Os artefatos de treino nao podem depender de onde o processo foi lancado.

O DEFEITO QUE ISTO TRANCA, pago em 04/09/2026: os caminhos de modelo eram
relativos (`modelos/bertimbau-satisfacao`), logo resolvidos contra o diretorio
de trabalho do processo. Um uvicorn lancado de fora da raiz nao encontrava
nenhum dos quatro artefatos, e o `scripts/api_demo.py` -- que escolhe o motor
pela PRESENCA dos arquivos -- caia para o dublê. A dashboard seguiu exibindo
numero sintetico com cara de predicao, e a barra lateral escreveu "API no ar"
o dia inteiro.

O lugar de onde se digita o comando nao pode decidir se voce recebe medicao ou
invencao.
"""

import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _resolvidos_com_cwd(cwd: Path, ambiente: dict[str, str] | None = None) -> dict[str, str]:
    """Resolve os caminhos de artefato num processo com OUTRO cwd.

    Precisa ser subprocesso: `fraus.api.caminhos` calcula os caminhos na
    importacao, entao mudar o cwd depois de importar nao provaria nada.
    """
    # `.resolve()` roda DENTRO do subprocesso, de proposito: um Path relativo
    # tem o mesmo `str()` em qualquer lugar, e so vira endereco de verdade
    # quando alguem o resolve contra um cwd. Resolver aqui fora mediria o cwd
    # do pytest e o teste passaria sempre -- foi o primeiro erro desta suite.
    programa = (
        "import json;"
        "from fraus.api.caminhos import CAMINHO_MODELO_TEXTO as T,"
        " CAMINHO_MODELO_EMOCAO as E, CAMINHO_MODELO_IRONIA as I, CAMINHO_FUSOR as F;"
        "print(json.dumps({'texto': str(T.resolve()), 'emocao': str(E.resolve()),"
        " 'ironia': str(I.resolve()), 'fusor': str(F.resolve())}))"
    )
    env = {**os.environ, "PYTHONPATH": str(RAIZ), **(ambiente or {})}
    saida = subprocess.run(
        [sys.executable, "-c", programa],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    import json

    return json.loads(saida.stdout)


def test_artefatos_resolvem_iguais_de_qualquer_diretorio(tmp_path):
    """Lancar de outro diretorio nao pode mudar para onde os artefatos apontam."""
    da_raiz = _resolvidos_com_cwd(RAIZ)
    de_fora = _resolvidos_com_cwd(tmp_path)
    assert da_raiz == de_fora


def test_artefatos_apontam_para_dentro_do_projeto(tmp_path):
    """E o alvo e a pasta `modelos/` do projeto, nao uma relativa ao cwd."""
    de_fora = _resolvidos_com_cwd(tmp_path)
    for nome, caminho in de_fora.items():
        resolvido = Path(caminho)
        assert resolvido.is_absolute(), f"{nome} nao ficou absoluto: {caminho}"
        assert RAIZ in resolvido.parents, f"{nome} caiu fora do projeto: {resolvido}"


def test_variavel_de_ambiente_continua_mandando(tmp_path):
    """Caminho declarado pelo operador vence, e NAO e reancorado na raiz.

    Quem exporta `FRAUS_CAMINHO_FUSOR` esta dizendo onde o arquivo esta. Mover
    isso para dentro do projeto seria desobedecer a configuracao explicita --
    o conserto do cwd vale para o PADRAO, nao para a escolha declarada.
    """
    escolhido = tmp_path / "outro" / "fusor.joblib"
    de_fora = _resolvidos_com_cwd(
        tmp_path, {"FRAUS_CAMINHO_FUSOR": str(escolhido)}
    )
    assert Path(de_fora["fusor"]) == escolhido
