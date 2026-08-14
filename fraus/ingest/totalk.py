"""Adaptador do export da Totalk (app.totalk.chat) para o modelo canonico.

POR QUE ISTO E UM ADAPTADOR E NAO MAIS UM FORMATO DO `csv_driver`. O driver
canonico le UM formato, e e ele que define o que o Fraus considera uma
conversa. Ensinar o driver a reconhecer o layout de cada fornecedor faria o
nucleo do sistema conhecer nomes de produto, e cada fornecedor novo mexeria no
codigo que decide o que entra no banco. Adaptadores traduzem para o canonico e
morrem na borda.

O QUE O EXPORT DA TOTALK TEM E O CANONICO NAO: nome do contato, telefone,
Instagram, e-mail. Nada disso e traduzido -- nao ha campo para eles no modelo
canonico e o modelo nao os usa. Uma conversa que entra no Fraus carrega o
texto, quem falou e quando. E deliberado: o que nao entra nao vaza.

TRES INFERENCIAS, e todas sao relatadas em vez de silenciosas:

1. **A data e MM/DD/YYYY**, nao DD/MM. Foi verificado no export de 2026-05:
   o primeiro campo e sempre `05` e o segundo varia de 01 a 22. Ler como
   DD/MM espalharia as mensagens por cinco meses diferentes e a LATENCIA --
   que e feature do fusor -- sairia absurda, sem nenhum erro aparecer.
2. **O fuso nao vem no arquivo.** Ele entra por parametro. Fuso errado nao
   muda latencia (todos os instantes deslocam junto), mas muda o DIA de cada
   conversa, e a serie temporal agrega por dia.
3. **Bot ou humano** sai do prefixo `*Nome:*` do conteudo. Prefixo igual ao
   nome da conta e automacao; nome de pessoa e atendente; sem prefixo conta
   como bot. E heuristica, e ela importa: taxa de contencao e
   `escalou_para_humano` dependem dela. Por isso `converter` devolve o que
   inferiu, para quem opera conferir e corrigir a lista de agentes.
"""

import csv
import io
import re
import unicodedata
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ValidationError

from fraus.modelos import Conversa, Mensagem

COLUNAS = (
    "Conta/Nome",
    "Mensagem/Data de criação",
    "Mensagem/Quem enviou",
    "Mensagem/Conteúdo",
    "Conversa",
)

# `De: <quem> Para: <quem>`. O nome pode ter espacos, entao o corte e no
# " Para: " literal.
DIRECAO = re.compile(r"^De:\s*(?P<de>.+?)\s+Para:\s*(?P<para>.+?)\s*$")

# `*Carol:*` no inicio do conteudo -- quem, do lado da empresa, escreveu.
PREFIXO_AGENTE = re.compile(r"^\*([^*\n]+):\*")

# O id da conversa vive na URL da coluna `Conversa`, como `id=<uuid>`.
ID_NA_URL = re.compile(r"[?&]id=([0-9a-fA-F-]+)")

FORMATO_DATA = "%m/%d/%Y %H:%M:%S"

# America/Sao_Paulo. Fixo em -03:00 de proposito: o Brasil nao tem horario de
# verao desde 2019, entao nao ha transicao para errar, e depender do banco de
# fusos do sistema tornaria a conversao dependente da maquina que a rodou.
FUSO_PADRAO = timezone(timedelta(hours=-3))


class LinhaIgnorada(BaseModel):
    numero_linha: int
    motivo: str


class ResultadoTotalk(BaseModel):
    conversas: list[Conversa]
    ignoradas: list[LinhaIgnorada]
    # O que a heuristica decidiu, para conferencia humana.
    agentes_detectados: list[str]
    mensagens_sem_prefixo: int


def _normalizar(texto: str) -> str:
    """Minuscula, sem acento e sem espaco extra -- para comparar nomes."""
    sem_acento = unicodedata.normalize("NFKD", texto.strip().lower())
    limpo = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", limpo)


def _e_a_propria_conta(nome: str, conta: str) -> bool:
    """A assinatura e a empresa se assinando, e nao uma pessoa?

    Igualdade exata nao basta: no export de 2026-05 a conta e "BANDEIRAS
    WORKSPACE COWORKING" e a automacao assina "*Bandeiras Coworking:*" -- forma
    curta do mesmo nome. Comparando por igualdade, a automacao virava
    "atendente humano" e inflava o escalonamento, que e feature do fusor.

    A regra e conter: todas as palavras da assinatura aparecem no nome da
    conta. "bandeiras coworking" cabe dentro de "bandeiras workspace
    coworking"; "carol" e "daniela azevedo" nao cabem em lugar nenhum.

    Continua sendo heuristica -- uma atendente chamada "Workspace" seria lida
    como automacao. E por isso que `--agente` existe e que o resultado sempre
    relata o que inferiu.
    """
    palavras_conta = set(conta.split())
    palavras_nome = set(nome.split())
    return bool(palavras_nome) and palavras_nome <= palavras_conta


def converter(
    arquivo: Iterable[str],
    fuso: timezone = FUSO_PADRAO,
    agentes_humanos: Iterable[str] | None = None,
) -> ResultadoTotalk:
    """Traduz o export para conversas canonicas.

    `agentes_humanos` sobrescreve a heuristica: quem estiver nesta lista conta
    como atendente, e todo o resto do lado da empresa conta como bot. Passar a
    lista e o caminho certo quando a operacao a conhece -- a inferencia existe
    para quando nao se conhece, nao para substituir o que se sabe.
    """
    explicitos = {_normalizar(nome) for nome in (agentes_humanos or [])}

    por_conversa: dict[str, list[tuple[Mensagem, bool]]] = {}
    canais: dict[str, str] = {}
    ignoradas: list[LinhaIgnorada] = []
    agentes: set[str] = set()
    sem_prefixo = 0

    for numero_linha, linha in enumerate(csv.DictReader(arquivo), start=2):
        faltando = [coluna for coluna in COLUNAS if coluna not in linha]
        if faltando:
            # Coluna estrutural ausente e defeito do ARQUIVO, nao da linha:
            # propaga, como o driver canonico ja faz.
            raise KeyError(faltando[0])

        achado = ID_NA_URL.search(linha["Conversa"] or "")
        if achado is None:
            ignoradas.append(
                LinhaIgnorada(
                    numero_linha=numero_linha,
                    motivo="sem id de conversa na coluna 'Conversa'",
                )
            )
            continue
        conversa_id = achado.group(1)

        direcao = DIRECAO.match(linha["Mensagem/Quem enviou"] or "")
        if direcao is None:
            ignoradas.append(
                LinhaIgnorada(
                    numero_linha=numero_linha,
                    motivo=f"'Mensagem/Quem enviou' fora do padrao "
                           f"'De: X Para: Y': {linha['Mensagem/Quem enviou']!r}",
                )
            )
            continue

        try:
            enviada_em = datetime.strptime(
                (linha["Mensagem/Data de criação"] or "").strip(), FORMATO_DATA
            ).replace(tzinfo=fuso)
        except ValueError as erro:
            ignoradas.append(
                LinhaIgnorada(numero_linha=numero_linha, motivo=f"data invalida: {erro}")
            )
            continue

        conta = _normalizar(linha["Conta/Nome"] or "")
        texto = (linha["Mensagem/Conteúdo"] or "").strip()
        da_empresa = _normalizar(direcao.group("de")) == conta

        prefixo = PREFIXO_AGENTE.match(texto)
        if da_empresa:
            if prefixo is None:
                sem_prefixo += 1
                autor = "bot"
            else:
                nome = _normalizar(prefixo.group(1))
                if explicitos:
                    autor = "humano" if nome in explicitos else "bot"
                elif _e_a_propria_conta(nome, conta):
                    autor = "bot"
                else:
                    autor = "humano"
                    agentes.add(prefixo.group(1).strip())
        else:
            autor = "cliente"

        if not texto:
            ignoradas.append(
                LinhaIgnorada(numero_linha=numero_linha, motivo="conteudo vazio")
            )
            continue

        try:
            mensagem = Mensagem(autor=autor, texto=texto, enviada_em=enviada_em)
        except ValidationError as erro:
            ignoradas.append(LinhaIgnorada(numero_linha=numero_linha, motivo=str(erro)))
            continue

        por_conversa.setdefault(conversa_id, []).append((mensagem, autor == "humano"))
        canais.setdefault(conversa_id, (linha.get("Canal/Plataforma") or "totalk").strip().lower())

    conversas = []
    for conversa_id, itens in por_conversa.items():
        itens.sort(key=lambda item: item[0].enviada_em)
        mensagens = [mensagem for mensagem, _ in itens]
        conversas.append(
            Conversa(
                id=conversa_id,
                canal=canais[conversa_id] or "totalk",
                iniciada_em=mensagens[0].enviada_em,
                encerrada_em=mensagens[-1].enviada_em,
                # Escalou se ALGUM atendente falou. O export nao tem um campo
                # de escalonamento; a presenca de pessoa atendendo e a unica
                # evidencia que o arquivo carrega.
                escalou_para_humano=any(humano for _, humano in itens),
                mensagens=mensagens,
            )
        )

    return ResultadoTotalk(
        conversas=conversas,
        ignoradas=ignoradas,
        agentes_detectados=sorted(agentes),
        mensagens_sem_prefixo=sem_prefixo,
    )


def converter_texto(conteudo: str, **kwargs) -> ResultadoTotalk:
    return converter(io.StringIO(conteudo, newline=""), **kwargs)


def para_csv_canonico(conversas: list[Conversa]) -> str:
    """Escreve as conversas no formato que `fraus.ingest.csv_driver` le.

    A saida passa pela importacao normal do Fraus -- com o relato de rejeicao
    que ela ja faz -- em vez de o adaptador escrever direto no banco. Uma
    entrada por um caminho que pula as validacoes do driver seria uma segunda
    porta com regras proprias.
    """
    saida = io.StringIO(newline="")
    escritor = csv.writer(saida, lineterminator="\n")
    escritor.writerow(
        ["conversa_id", "canal", "autor", "texto", "enviada_em", "escalou_para_humano"]
    )
    for conversa in conversas:
        for mensagem in conversa.mensagens:
            escritor.writerow([
                conversa.id,
                conversa.canal,
                mensagem.autor,
                mensagem.texto,
                mensagem.enviada_em.isoformat(),
                "true" if conversa.escalou_para_humano else "false",
            ])
    return saida.getvalue()
