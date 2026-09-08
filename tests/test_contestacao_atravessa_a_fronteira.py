"""O contrato da contestacao tem duas metades, e so a de Python tinha guarda.

`fraus/contestacao.py` monta o dicionario; `dashboard/lib/api.ts` declara o
tipo dele; `MarcaContestacao.tsx` escreve a frase a partir dos campos. Nada
impedia as duas metades de divergirem em silencio -- foi exatamente o que
aconteceu com a familia `incongruencia_*` em 03/09/2026, quando ela entrou em
`NOMES_FEATURES` e o mapa do TypeScript nunca soube dela.

Este modulo le os arquivos `.tsx`/`.ts` como TEXTO, mesmo padrao de
`tests/test_derivacoes_dashboard.py` e de
`tests/test_pii_integracao.py::test_toda_origem_de_dado_real_censura_pii`. Nao
e typecheck -- e a guarda barata que impede o silencio.
"""

import pathlib
import re

from fraus.contestacao import (LIMIAR_LATENCIA_S, LIMIAR_SCORE, MOTIVO,
                               contestacao)

RAIZ = pathlib.Path(__file__).parent.parent
API_TS = RAIZ / "dashboard" / "lib" / "api.ts"
MARCA_TSX = RAIZ / "dashboard" / "components" / "MarcaContestacao.tsx"


def _chaves_do_servidor() -> set[str]:
    marca = contestacao(99.93, 10800.0)
    assert marca is not None, "o caso canonico parou de contestar"
    return set(marca)


def test_o_tipo_do_TypeScript_declara_as_mesmas_chaves():
    """Campo que o servidor manda e o tipo nao declara e campo que a tela nunca
    vai usar; campo que o tipo declara e o servidor nao manda e `undefined` em
    tempo de execucao com typecheck verde."""
    bloco = re.search(
        r"export type Contestacao = \{(.*?)\n\};", API_TS.read_text(encoding="utf-8"), re.S
    )
    assert bloco is not None, "o tipo `Contestacao` sumiu de dashboard/lib/api.ts"

    declaradas = set(re.findall(r"^\s*(\w+):", bloco.group(1), re.M))
    assert declaradas == _chaves_do_servidor()


def test_o_motivo_do_servidor_e_o_do_tipo():
    """`motivo` e um literal do lado do TypeScript. Renomear so de um lado
    deixaria o `switch` do futuro sem caso e sem erro de compilacao."""
    assert f'"{MOTIVO}"' in API_TS.read_text(encoding="utf-8")


def test_a_tela_nao_redigita_os_limiares():
    """A regra derivada mora no servidor (invariante 3). Os limiares chegam na
    tela pelos campos `limiar_score`/`limiar_s` justamente para que ninguem
    escreva `95` ou `180` no TSX -- foi a duplicacao de regra derivada no
    TypeScript que ja causou divergencia de arredondamento nas fronteiras 6/7 e
    8/9 do NPS."""
    fonte = MARCA_TSX.read_text(encoding="utf-8")
    for limiar in (LIMIAR_SCORE, LIMIAR_LATENCIA_S):
        # `95`/`180` como numero solto no codigo -- nao dentro de uma palavra,
        # nem no comentario de docstring (que cita a regra de proposito).
        codigo = re.sub(r"/\*.*?\*/", "", fonte, flags=re.S)
        assert not re.search(rf"(?<![\w.]){int(limiar)}(?![\w.])", codigo), (
            f"{int(limiar)} aparece no TSX -- o limiar tem de vir da API"
        )


def test_a_marca_nao_depende_de_JavaScript():
    """Ela e renderizada no servidor, a partir dos campos que a API mandou.

    A regra geral vem da vitrine: a etiqueta de honestidade saiu do `Revelar`,
    que nasce com `opacity: 0`, porque numa ferramenta cujo nome e o daimon do
    engano a ressalva nao pode ser a parte que some quando algo falha. Um
    `"use client"` ou um `useState` aqui reabririam esse buraco em silencio.
    """
    fonte = MARCA_TSX.read_text(encoding="utf-8")
    assert '"use client"' not in fonte
    for gancho in ("useState", "useEffect", "whileInView", "motion."):
        assert gancho not in fonte, f"{gancho} faria a marca depender de JS"
