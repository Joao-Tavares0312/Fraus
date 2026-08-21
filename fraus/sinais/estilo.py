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
