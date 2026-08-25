"""A autenticacao se liga sozinha na PRIMEIRA subida, e grava as chaves em disco.

O QUE MUDOU, E POR QUE. Antes a API subia ABERTA e ligar era um clique na tela.
Isso punha a decisao de seguranca nas maos de quem so queria usar o produto: um
Fraus recem-clonado servia o banco de atendimentos inteiro a quem alcancasse a
porta, e continuava assim ate alguem lembrar do botao. Gerar credencial e
trabalho do PROJETO, nao do usuario -- ele nao deveria precisar saber que uma
chave mestra existe para estar protegido por ela.

Entao a primeira subida gera a mestra e uma chave de acesso para a dashboard, e
escreve as duas num arquivo local. O usuario nao digita nada, nao clica em nada,
e nao ve chave nenhuma a menos que abra o arquivo.

A ORDEM IMPORTA, e e o coracao deste modulo: o arquivo e escrito ANTES de o hash
da mestra ir para o banco. Se a escrita falhar (disco cheio, pasta somente
leitura), nada e gravado e a API sobe aberta com um aviso -- porque ligar a
autenticacao guardando a unica copia da chave em lugar nenhum trancaria o dono
para fora da propria instalacao no primeiro boot. Uma API aberta com aviso e um
problema; uma API fechada cuja chave nao existe em lugar nenhum e um tijolo.

QUANDO NAO ACONTECE:
- ja ha mestra no banco (nao e primeira subida);
- `FRAUS_CHAVE_MESTRA` esta no ambiente (a variavel vence a gravada, e gerar
  uma segunda credencial que perde para ela seria escrever no arquivo uma chave
  que nao abre nada).
"""

import os
from datetime import datetime, timezone
from pathlib import Path

from fraus import acesso, credencial
from fraus.db import Banco

CABECALHO = """# Credenciais da API do Fraus -- geradas na primeira subida.
#
# NAO versione este arquivo. Ele e a UNICA copia em claro destas chaves: o
# banco guarda apenas o hash delas, e apagar isto aqui as perde para sempre.
#
# chave_mestra  administra: emite e revoga chaves de acesso, e troca a si mesma.
# chave_acesso  apenas le. E a que a dashboard apresenta.
#
# Perdeu a mestra? `uv run python scripts/resetar_mestra.py` reabre a API para
# ligar de novo -- as chaves de acesso continuam valendo.
"""


def escrever_credenciais(caminho: Path, mestra: str, chave_de_acesso: str) -> None:
    """Grava o arquivo de credenciais. Levanta se nao conseguir escrever."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conteudo = (
        f"{CABECALHO}\n"
        f"chave_mestra={mestra}\n"
        f"chave_acesso={chave_de_acesso}\n"
    )
    # `O_EXCL` e nao truncar: se o arquivo ja existe, alguem tem credencial
    # anterior ali e sobrescrever apagaria a unica copia dela. Chegar aqui com o
    # arquivo existente significa banco novo com arquivo velho -- caso em que o
    # certo e falhar e deixar o operador decidir, nao escolher por ele qual
    # copia morre. (`O_CREAT|O_EXCL` levanta `FileExistsError`, subclasse de
    # `OSError`, entao o tratamento de quem chama continua valendo.)
    #
    # `0o600` E O CONSERTO DE 25/08/2026: `open(caminho, "x")` respeita o umask
    # e criava o arquivo 0o644 num POSIX tipico -- a UNICA copia em claro da
    # chave mestra legivel por qualquer usuario da maquina. O modo entra na
    # CRIACAO, e nao num `chmod` depois, porque entre criar e ajustar existe uma
    # janela em que o arquivo ja tem o segredo e ainda tem a permissao larga.
    #
    # Em Windows o bit de grupo/outros nao existe (quem manda e a ACL herdada da
    # pasta) e o Python so distingue gravavel de somente-leitura; passar o modo
    # ali nao machuca e mantem um caminho de codigo so.
    descritor = os.open(caminho, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
        arquivo.write(conteudo)


def ligar_no_primeiro_uso(
    banco: Banco, caminho: Path, chave_do_ambiente: str | None
) -> Path | None:
    """Liga a autenticacao se esta for a primeira subida. Devolve onde gravou.

    `None` quando nao havia o que fazer (ja ligada, ou mestra no ambiente) e
    tambem quando a escrita falhou -- nos dois casos nada e gravado no banco.
    O chamador decide o que dizer; aqui so se decide o que FAZER.
    """
    if chave_do_ambiente is not None:
        return None
    if banco.hash_da_chave_mestra() is not None:
        return None

    agora = datetime.now(timezone.utc).isoformat()
    mestra, mestra_hash = acesso.gerar_mestra()

    # A linha da chave de acesso precisa existir antes do segredo: a chave
    # embute o id dela (ver `acesso.gerar`).
    registro = banco.criar_chave_acesso(nome="dashboard", criada_em=agora)
    chave_de_acesso, hash_de_acesso = acesso.gerar(registro["id"])

    try:
        escrever_credenciais(caminho, mestra, chave_de_acesso)
    except OSError:
        # Sem arquivo nao ha copia da chave. Desfaz a linha criada e sai sem
        # gravar a mestra: a API sobe ABERTA, que e recuperavel, em vez de
        # fechada com a credencial perdida, que nao e.
        banco.apagar_chave_acesso(registro["id"])
        return None

    banco.gravar_chave_acesso(
        registro["id"], chave_hash=hash_de_acesso, dica=credencial.dica(chave_de_acesso)
    )
    # A mestra por ULTIMO: e ela que faz o middleware passar a exigir chave, e
    # so faz sentido exigir depois de a credencial estar gravada e em disco.
    banco.gravar_chave_mestra(
        chave_hash=mestra_hash, dica=credencial.dica(mestra), criada_em=agora
    )
    return caminho
