"""O mapa de features do TypeScript e o contrato do fusor sao duas metades da
mesma verdade -- e so o lado Python tinha guarda.

`tests/test_fusor.py::test_contrato_cobre_todos_os_prefixos_esperados` conhece
os prefixos esperados e ate cita `dashboard/lib/derivacoes.ts` num comentario,
mas nenhum teste atravessava a fronteira de linguagem: nada impedia o mapa TS
de ficar para tras em silencio quando uma familia nova entrasse no vetor. Foi
exatamente o que aconteceu em 03/09/2026 -- a familia `incongruencia_*` (5
features) entrou em `NOMES_FEATURES`, mas `SINAL_POR_PREFIXO` e
`ROTULO_FEATURE` nunca souberam dela. Por um dia, as cinco features caiam no
balde de sobras ("outros") do grafico de pesos, e o rotulo exibido ao usuario
era o proprio nome tecnico em snake_case.

Este teste le `derivacoes.ts` como TEXTO (mesmo padrao de
`tests/test_pii_integracao.py::test_toda_origem_de_dado_real_censura_pii`,
que le arquivos `.py` como texto) e falha se algum prefixo de
`NOMES_FEATURES` nao aparecer em `SINAL_POR_PREFIXO`, ou se alguma chave nao
tiver rotulo em `ROTULO_FEATURE`. Assim a proxima familia nova nao repete o
mesmo silencio.
"""

import pathlib
import re

from fraus.fusor import NOMES_FEATURES

CAMINHO_DERIVACOES = (
    pathlib.Path(__file__).parent.parent / "dashboard" / "lib" / "derivacoes.ts"
)


def _prefixo_de(nome: str) -> str:
    """O prefixo de familia de uma feature, do jeito que `SINAL_POR_PREFIXO` espera.

    A maioria das familias tem prefixo com underscore ("texto_", "emoji_"),
    mas a familia tempo tem dois prefixos SEM underscore: "escalou" e
    "abandonou" sao o nome inteiro da feature, nao um prefixo cortado em "_".
    Uma logica ingenua de `nome.split("_")[0] + "_"` marcaria esses dois como
    "escalou_"/"abandonou_", que nao existe em `SINAL_POR_PREFIXO` -- falso
    positivo. Por isso os dois sao casos especiais aqui, do mesmo jeito que
    sao no arquivo TS.
    """
    if nome in ("escalou", "abandonou"):
        return nome
    return nome.split("_")[0] + "_"


def test_todo_prefixo_de_nomes_features_esta_no_mapa_de_sinal_do_dashboard():
    fonte = CAMINHO_DERIVACOES.read_text(encoding="utf-8")

    prefixos_esperados = {_prefixo_de(nome) for nome in NOMES_FEATURES}

    faltando = [
        prefixo
        for prefixo in prefixos_esperados
        if f'"{prefixo}"' not in fonte
    ]

    assert not faltando, (
        f"prefixo(s) sem entrada em SINAL_POR_PREFIXO (dashboard/lib/derivacoes.ts): "
        f"{faltando}. Toda familia nova de NOMES_FEATURES precisa de uma linha em "
        "SINAL_POR_PREFIXO, senao cai muda no balde 'outros' do grafico de pesos."
    )


def test_toda_feature_de_nomes_features_tem_rotulo_no_dashboard():
    fonte = CAMINHO_DERIVACOES.read_text(encoding="utf-8")

    bloco = re.search(
        r"ROTULO_FEATURE: Record<string, string> = \{(.*?)\n\};",
        fonte,
        re.DOTALL,
    )
    assert bloco, "nao encontrei o bloco ROTULO_FEATURE em derivacoes.ts"
    corpo = bloco.group(1)

    sem_rotulo = [nome for nome in NOMES_FEATURES if f"{nome}:" not in corpo]

    assert not sem_rotulo, (
        f"feature(s) sem entrada em ROTULO_FEATURE (dashboard/lib/derivacoes.ts): "
        f"{sem_rotulo}. Sem rotulo, o usuario ve o nome tecnico em snake_case cru "
        "na tela."
    )
