"""Sinal de estilo: a FORMA da escrita, nao o conteudo dela.

Caixa alta, pontuacao repetida, alongamento de caractere, palavrao e censura
carregam intensidade que nenhum dos outros sinais captura. E deterministico de
proposito: o BERTimbau nao aprende enfase porque o B2W-Reviews01 -- resenha
moderada de e-commerce -- praticamente nao contem gritaria nem xingamento.
Modelo nao aprende fenomeno que o corpus nao tem, e mais epocas sobre o mesmo
texto so reproduzem o mesmo artefato. Ver a spec de 21/08/2026.

Le apenas as falas do cliente, coerente com os demais sinais: enfase do bot nao
e enfase do cliente.
"""

import csv
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

CAMINHO_PALAVROES = Path(__file__).parent.parent / "dados" / "palavroes_ptbr.csv"

INTENSIDADE_POR_NOME = {"leve": 0.33, "medio": 0.66, "pesado": 1.0}


@lru_cache(maxsize=1)
def carregar_palavroes() -> dict[str, tuple[float, bool]]:
    """Termo normalizado -> (intensidade, dirigido a pessoa).

    A gradacao existe porque "que droga" e "vai tomar no cu" nao sao o mesmo
    evento, e o alvo existe porque xingar o PRODUTO e reclamacao enquanto
    xingar o ATENDENTE e ruptura da conversa.
    """
    tabela: dict[str, tuple[float, bool]] = {}
    with CAMINHO_PALAVROES.open(encoding="utf-8", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            termo = linha["termo"].strip().lower()
            if not termo:
                continue
            tabela[termo] = (
                INTENSIDADE_POR_NOME[linha["intensidade"].strip()],
                linha["alvo"].strip() == "pessoa",
            )
    return tabela


# Simbolos usados para mascarar palavrao. `!` e `?` NAO entram: eles sao
# enfase, medida por `estilo_pontuacao_enfatica`, e incluir aqui faria "!!!"
# contar como xingamento censurado.
SIMBOLOS_CENSURA = set("*@#$%&0134")

# Homoglifos: o que o cliente digita -> a letra que ele quis dizer. Sem isso o
# lexicon erra TODA ocorrencia censurada, que e justamente a mais interessante.
HOMOGLIFOS = str.maketrans({
    "@": "a", "4": "a",
    "0": "o",
    # "!" NAO entra aqui: `PALAVRA` nao o inclui, entao ele nunca chega a uma
    # palavra -- e mapeamento inalcancavel e some numa refatoracao futura.
    "1": "i",
    "3": "e",
    "$": "s", "5": "s",
    "*": "",
    "#": "", "%": "", "&": "",
})

# Separador de palavra que PRESERVA simbolo de censura: `\w` sozinho quebraria
# "p*rra" em "p" e "rra" e a censura sumiria antes de ser contada.
PALAVRA = re.compile(r"[\w" + re.escape("*@#$%&") + r"]+", re.UNICODE)


def normalizar(palavra: str) -> str:
    """Minusculas, sem acento, homoglifos revertidos.

    Roda DEPOIS de `tem_censura`, nunca antes: ela apaga exatamente a marca que
    a outra funcao precisa ver.
    """
    sem_acento = "".join(
        c
        for c in unicodedata.normalize("NFD", palavra.lower())
        if unicodedata.category(c) != "Mn"
    )
    return sem_acento.translate(HOMOGLIFOS)


def tem_censura(palavra: str) -> bool:
    """A palavra mistura letra e simbolo de mascara, ou e so simbolo.

    Autocensura e raiva COM autocontrole -- estado diferente de raiva crua, e
    por isso tem feature propria em vez de virar so mais um palavrao.
    """
    if not palavra:
        return False
    simbolos = sum(1 for c in palavra if c in SIMBOLOS_CENSURA)
    if simbolos == 0:
        return False
    letras = sum(1 for c in palavra if c.isalpha())
    # So simbolo (`#@$%`) e censura pura; letra + simbolo (`p*rra`) tambem.
    # Numero sozinho ("2024") nao e: precisa de letra junto ou de nenhum
    # caractere alfanumerico fora dos simbolos.
    return letras > 0 or all(c in SIMBOLOS_CENSURA for c in palavra)
