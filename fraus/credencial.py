"""Chave de API de uma fonte de integracao: gerar, guardar e conferir.

A chave existe para um sistema DE FORA empurrar atendimento para dentro do
Fraus -- e o unico caminho de escrita que nao depende de alguem com acesso ao
disco da maquina.

QUATRO DECISOES, e o motivo de cada uma:

1. **O segredo e mostrado UMA vez e nunca mais.** O banco guarda so o hash. Se
   o `fraus.db` vazar num backup, as chaves nao vao junto -- e a mesma razao
   pela qual `variavel_segredo` guarda o NOME da variavel de ambiente e nunca o
   valor. Perder a chave custa gerar outra, que e barato; guardar o segredo
   recuperavel custa o dia em que o arquivo vaza.

2. **SHA-256 puro, sem bcrypt/argon2.** Parece errado e nao e: os algoritmos
   lentos existem para senha, que tem pouca entropia e morre em ataque de
   dicionario. Aqui o segredo sao 32 bytes de `secrets.token_hex`, sorteados --
   nao ha dicionario que chegue perto, e o custo de um KDF lento seria pago em
   TODA requisicao de ingestao sem comprar seguranca nenhuma.

3. **A chave carrega o id da fonte em texto claro.** Sem isso, conferir uma
   chave exigiria varrer todas as fontes comparando hash. Com o id, a busca e
   direta e o unico segredo e a metade sorteada. O prefixo `frs_` tambem serve
   para varredura de segredo em repositorio reconhecer o que e.

4. **Comparacao em tempo constante.** `==` em bytes vaza, pelo tempo, quantos
   caracteres bateram, e isso e suficiente para descobrir o hash byte a byte.
   `hmac.compare_digest` nao vaza.

LIMITE HONESTO DO QUE ISTO PROTEGE: a chave `frs_` autentica UMA FONTE na rota
de ingestao, e nada mais. Ela nao da leitura, nao da acesso a `/integracoes` e
nao e a credencial de quem OPERA a ferramenta -- essa e a chave de acesso
`fra_` derivada da mestra `frm_` (`fraus/api/seguranca.py`), ou a sessao de
usuario (`fraus/api/rotas/auth.py`). Quem alcanca a API JA AUTENTICADO como
operador pode gerar uma chave de fonte nova para si; e a mesma pessoa que ja
podia ler tudo, entao a chave nao e a fronteira ali.

Este arquivo dizia, ate 08/09/2026, que "o resto da API continua sem
autenticacao, porque o Fraus roda local". Era verdade quando foi escrito e
deixou de ser com a chave de acesso (25/08/2026) e o login de usuario
(31/08/2026). Ficou aqui tempo demais afirmando que a porta da frente estava
aberta quando ela nao estava mais -- e docstring de modulo de seguranca que
mente e pior que docstring nenhum, porque o proximo a ler decide com base nela.

O TETO DE VAZAO da rota de ingestao conta POR FONTE, e nao pela chave crua:
`fonte_da_chave` le o id sem conferir hash nenhum. Ver `fraus/api/vazao.py`.
"""

import hashlib
import hmac
import secrets

PREFIXO = "frs"

# 32 bytes = 256 bits de entropia. Muito acima do que um ataque online alcanca,
# e o custo de carregar uma chave maior e zero.
BYTES_DO_SEGREDO = 32


def gerar(fonte_id: int) -> tuple[str, str]:
    """Cria uma chave nova. Devolve `(chave_em_claro, hash)`.

    O texto em claro sai daqui e NUNCA e persistido -- a rota devolve ele uma
    unica vez, na resposta, e o que fica no banco e o hash.
    """
    segredo = secrets.token_hex(BYTES_DO_SEGREDO)
    chave = f"{PREFIXO}_{fonte_id}_{segredo}"
    return chave, hash_da_chave(chave)


def hash_da_chave(chave: str) -> str:
    return hashlib.sha256(chave.encode("utf-8")).hexdigest()


def fonte_da_chave(chave: str) -> int | None:
    """Le o id da fonte embutido na chave, sem confiar nele.

    Devolve `None` para qualquer coisa fora do formato. O id serve so para
    ACHAR a fonte; quem autoriza e a conferencia do hash, entao um id forjado
    apenas aponta para uma fonte cujo hash nao vai bater.
    """
    partes = chave.split("_")
    if len(partes) != 3 or partes[0] != PREFIXO:
        return None
    try:
        return int(partes[1])
    except ValueError:
        return None


def confere(chave: str, hash_guardado: str | None) -> bool:
    """Compara em tempo constante. Fonte sem chave gerada nunca autoriza."""
    if not hash_guardado:
        return False
    return hmac.compare_digest(hash_da_chave(chave), hash_guardado)


def dica(chave: str) -> str:
    """Os ultimos quatro caracteres, para a tela identificar a chave depois.

    So o SUFIXO, e so quatro: serve para o operador reconhecer qual chave esta
    em uso ("termina em 3f9a") sem que o pedaco exibido ajude a adivinhar o
    resto. Prefixo seria pior -- ele e a parte que um ataque tentaria primeiro.
    """
    return chave[-4:]
