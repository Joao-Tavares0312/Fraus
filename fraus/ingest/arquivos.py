"""Le o arquivo que chegou -- csv, xlsx, docx ou pdf -- e devolve conversas.

Cada formato entra por onde ele de fato consegue:

- **csv / xlsx**: tabela. Tentam o layout canonico do Fraus e, se ele nao
  estiver la, o export da Totalk. Trazem horario, entao a conversa e pontuada
  normalmente.
- **json / jsonl / txt de WhatsApp / csv de estrutura desconhecida**: desde
  14/09/2026 caem no mapeador (`fraus.ingest.mapeador`), que descobre qual
  coluna e o texto, o autor, a data e a conversa, e relata o que inferiu. Um
  export novo nao pede adaptador novo.
- **docx / pdf / txt em prosa**: prosa. Viram transcricao (`fraus.ingest.transcricao`), que
  quase nunca carrega horario -- e sem horario NAO HA NOTA, so a leitura por
  mensagem. Ver o modulo de transcricao para o porque.

O ERRO E O PRODUTO PRINCIPAL DAQUI. Um arquivo que nao entra e o caso comum,
nao a excecao: gente exporta do sistema que tem, nao do formato que o Fraus
pede. Recusar dizendo so "formato invalido" obriga a pessoa a adivinhar. Toda
recusa nesta camada nomeia o que se esperava e o que se achou.
"""

import csv
import io
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fraus.fuso import no_fuso_do_produto

from fraus.ingest import leitores, mapeador, totalk
from fraus.ingest.csv_driver import carregar_linhas
from fraus.ingest.transcricao import ler as ler_transcricao
from fraus.modelos import Conversa
from fraus.seguranca.pii import censurar_pii

# Linhas da tabela devolvidas na previa para o analista conferir as colunas.
LINHAS_DE_AMOSTRA = 5

EXTENSOES = {
    ".csv": "csv",
    ".xlsx": "xlsx",
    ".xlsm": "xlsx",
    ".docx": "docx",
    ".pdf": "pdf",
    ".tsv": "csv",
    ".json": "json",
    ".jsonl": "json",
    ".txt": "txt",
}

COLUNAS_CANONICAS = {
    "conversa_id", "canal", "autor", "texto", "enviada_em", "escalou_para_humano",
}

# Teto de celulas lidas de uma planilha. Sem ele, uma pasta com uma coluna
# esticada ate a linha um milhao viraria um milhao de linhas vazias.
TETO_LINHAS_PLANILHA = 50_000

# --- guarda de bomba zip ----------------------------------------------------
#
# xlsx e docx sao pacotes ZIP, e ZIP declara no cabecalho quanto cada membro vai
# ocupar DEPOIS de descomprimido. Os tetos de upload (`TETO_CORPO`,
# `TETO_ARQUIVO_ANALISE`) medem o arquivo comprimido e por isso nao veem nada:
# 190 KB legitimos e 190 KB de bomba tem o mesmo tamanho na porta de entrada.
# Medido em 02/09/2026 contra a instalacao publicada: 190 KB -> 64,8 MB -> 20,4 s
# de CPU. `TETO_LINHAS_PLANILHA` chegava tarde -- o `load_workbook` parseia
# `xl/sharedStrings.xml` inteiro antes de a primeira linha existir.
#
# 40 MB descomprimidos: uma planilha de 50k linhas de conversa fica uma ordem de
# grandeza abaixo disso; e o teto e do PACOTE, nao de um membro, porque distribuir
# a carga entre muitos arquivinhos e o jeito obvio de escapar de um teto por membro.
TETO_DESCOMPRIMIDO = 40 * 1024 * 1024

# XML de planilha comprime bem de verdade -- 20x ou 30x e rotina em documento
# legitimo. 200x nao e documento, e alavanca: e o ponto em que alguem paga bytes
# de menos por CPU nossa de mais.
RAZAO_MAXIMA_ZIP = 200

_MEMBRO_MINIMO_PARA_RAZAO = 64 * 1024
"""Abaixo disto a razao nao diz nada: um membro de 200 bytes que comprime a 2
tem razao 100 e custa nada. So o total manda nos arquivos pequenos."""


class ArquivoIlegivelError(ValueError):
    """O arquivo nao pode ser lido. A mensagem SEMPRE diz o que se esperava."""


@dataclass
class Extracao:
    conversas: list[Conversa]
    formato: str
    """Como o arquivo foi interpretado -- 'csv canonico', 'export Totalk', ..."""
    tem_tempo: bool
    """Falso quando nao ha horario: sem ele nao ha latencia, logo nao ha nota."""
    avisos: list[str] = field(default_factory=list)
    rejeitadas: list[dict] = field(default_factory=list)
    mapeamento: dict | None = None
    """So quando as colunas foram INFERIDAS: papel -> coluna, confianca e motivo.
    None para formato reconhecido (Fraus, Totalk, transcricao), que nao tem o
    que conferir."""
    amostra: list[list[str]] = field(default_factory=list)
    """Primeiras linhas, JA censuradas -- a previa mostra dado de cliente real."""
    perfil: dict | None = None
    """O perfil salvo que decidiu o mapeamento, quando houve um."""
    tem_data: bool = True
    """Falso quando o arquivo traz a hora e nao o dia (transcricao em prosa): o
    dia das conversas e o do envio. Quem grava nao pode por esse dia no id."""
    id_do_arquivo: bool = False
    """Verdadeiro quando o id nao veio do dado: arquivo sem coluna de conversa,
    ou transcricao. O id e um nome de enfeite e quem grava precisa trocar --
    ver `fraus/api/identidade.py`."""


@dataclass
class OpcoesDeLeitura:
    """O que quem chama sabe sobre o arquivo e a heuristica nao sabe."""

    forcado: dict[str, str | None] | None = None
    ordem_data: str | None = None
    perfil_para: Callable[[str], dict | None] | None = None
    """Busca perfil por assinatura de colunas. Injetado para `ingest` nao
    conhecer o banco."""


def _extensao(nome: str) -> str:
    ponto = nome.rfind(".")
    if ponto < 0:
        raise ArquivoIlegivelError(
            f"o arquivo '{nome}' nao tem extensao. Aceitos: "
            f"{', '.join(sorted(EXTENSOES))}."
        )
    sufixo = nome[ponto:].lower()
    if sufixo not in EXTENSOES:
        raise ArquivoIlegivelError(
            f"nao sei ler '{sufixo}'. Aceitos: {', '.join(sorted(EXTENSOES))}."
        )
    return EXTENSOES[sufixo]


def _recusar_bomba_zip(dados: bytes, formato: str) -> None:
    """Recusa o pacote pelo CABECALHO, sem descomprimir um byte.

    O `zipfile` le o diretorio central, que ja traz `file_size` e
    `compress_size` de cada membro -- e o custo disso e proporcional ao numero
    de membros, nao ao conteudo. E por isso que a guarda pode vir antes do
    parse, que e onde o dano acontece.

    ZIP QUEBRADO NAO E PROBLEMA DAQUI: quem sabe explicar 'planilha ilegivel' e
    o `load_workbook`, com a mensagem que ja existe. Aqui o `BadZipFile` volta
    calado para nao sequestrar aquela recusa.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(dados)) as pacote:
            membros = pacote.infolist()
    except zipfile.BadZipFile:
        return

    total = sum(membro.file_size for membro in membros)
    if total > TETO_DESCOMPRIMIDO:
        raise ArquivoIlegivelError(
            f"este {formato} declara {total / 1024 / 1024:.1f} MB descomprimidos, "
            f"acima do teto de {TETO_DESCOMPRIMIDO // 1024 // 1024} MB. Um arquivo "
            "de conversas fica muito abaixo disso -- confira se a exportacao nao "
            "trouxe planilha inteira junto."
        )
    for membro in membros:
        if membro.compress_size <= 0 or membro.file_size < _MEMBRO_MINIMO_PARA_RAZAO:
            continue
        razao = membro.file_size / membro.compress_size
        if razao > RAZAO_MAXIMA_ZIP:
            raise ArquivoIlegivelError(
                f"este {formato} tem um item ('{membro.filename}') que infla "
                f"{razao:.0f}x ao ser aberto -- {membro.file_size / 1024 / 1024:.1f} MB "
                f"vindos de {membro.compress_size / 1024:.0f} kB. Acima da razao "
                f"maxima de {RAZAO_MAXIMA_ZIP}x, o arquivo e recusado sem ser lido."
            )


def _linhas_da_planilha(dados: bytes) -> list[list[str]]:
    _recusar_bomba_zip(dados, "xlsx")
    try:
        from openpyxl import load_workbook
    except ImportError as erro:  # pragma: no cover - dependencia declarada
        raise ArquivoIlegivelError("suporte a xlsx indisponivel neste servidor") from erro

    try:
        pasta = load_workbook(io.BytesIO(dados), read_only=True, data_only=True)
    except Exception as erro:
        raise ArquivoIlegivelError(f"planilha ilegivel: {erro}") from erro

    aba = pasta[pasta.sheetnames[0]]
    linhas = []
    for numero, celulas in enumerate(aba.iter_rows(values_only=True)):
        if numero >= TETO_LINHAS_PLANILHA:
            break
        # Data vira texto ISO: o driver canonico le `datetime.fromisoformat`, e
        # o str() de um datetime do Excel sai em formato que ele nao aceita.
        valores = [
            v.isoformat() if isinstance(v, datetime) else ("" if v is None else str(v))
            for v in celulas
        ]
        if any(valor.strip() for valor in valores):
            linhas.append(valores)
    pasta.close()
    if not linhas:
        raise ArquivoIlegivelError("a primeira aba da planilha esta vazia")
    return linhas


def _texto_do_docx(dados: bytes) -> str:
    # docx e o MESMO pacote ZIP do xlsx -- guardar so um lado deixaria a porta
    # aberta trocando a extensao.
    _recusar_bomba_zip(dados, "docx")
    try:
        import docx
    except ImportError as erro:  # pragma: no cover
        raise ArquivoIlegivelError("suporte a docx indisponivel neste servidor") from erro
    try:
        documento = docx.Document(io.BytesIO(dados))
    except Exception as erro:
        raise ArquivoIlegivelError(f"documento Word ilegivel: {erro}") from erro

    partes = [paragrafo.text for paragrafo in documento.paragraphs]
    # Transcricao em Word costuma vir em TABELA, uma linha por fala.
    for tabela in documento.tables:
        for linha in tabela.rows:
            celulas = [celula.text.strip() for celula in linha.cells if celula.text.strip()]
            if celulas:
                partes.append(": ".join(celulas) if len(celulas) > 1 else celulas[0])
    return "\n".join(partes)


# Uma tabela so e candidata a conversa com cabecalho e pelo menos duas falas.
LINHAS_MINIMAS_TABELA_DOCX = 3


def _tabela_do_docx(dados: bytes) -> list[list[str]] | None:
    """A maior tabela do documento, se ela tiver cara de tabela -- ou None.

    Transcricao exportada para Word costuma vir em TABELA com a hora numa
    coluna. `_texto_do_docx` junta as celulas em "a: b" para a leitura em
    prosa, e ali a hora vira parte do texto: a conversa ficava sem nota
    mesmo tendo horario. Devolver a tabela deixa o mapeador achar a coluna.

    Celula mesclada o python-docx repete por coluna; linha inteiramente vazia
    sai. Quem decide se a tabela e de CONVERSA e o mapeador, nao esta funcao.
    """
    import docx

    try:
        documento = docx.Document(io.BytesIO(dados))
    except Exception:
        return None
    melhor: list[list[str]] | None = None
    for tabela in documento.tables:
        linhas = [
            [celula.text.strip() for celula in linha.cells]
            for linha in tabela.rows
        ]
        linhas = [linha for linha in linhas if any(linha)]
        if len(linhas) < LINHAS_MINIMAS_TABELA_DOCX or len(linhas[0]) < 2:
            continue
        if melhor is None or len(linhas) > len(melhor):
            melhor = linhas
    return melhor


def _texto_do_pdf(dados: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as erro:  # pragma: no cover
        raise ArquivoIlegivelError("suporte a pdf indisponivel neste servidor") from erro
    try:
        leitor = PdfReader(io.BytesIO(dados))
        if leitor.is_encrypted:
            raise ArquivoIlegivelError(
                "o PDF esta protegido por senha. Salve uma copia sem senha e envie de novo."
            )
        texto = "\n".join((pagina.extract_text() or "") for pagina in leitor.pages)
    except ArquivoIlegivelError:
        raise
    except Exception as erro:
        raise ArquivoIlegivelError(f"PDF ilegivel: {erro}") from erro

    if not texto.strip():
        raise ArquivoIlegivelError(
            "o PDF nao tem texto extraivel -- provavelmente e uma imagem digitalizada. "
            "O Fraus nao faz OCR: envie a transcricao em texto, .docx ou .csv."
        )
    return texto


def _de_tabela(
    linhas: list[list[str]], origem: str, opcoes: OpcoesDeLeitura | None = None
) -> Extracao:
    """Tenta o layout canonico, o export da Totalk e, por fim, o mapeador.

    Mapeamento confirmado pelo analista pula os dois reconhecimentos: quem
    confirmou colunas quer ESSA leitura, nao a que o nome das colunas sugere.
    """
    opcoes = opcoes or OpcoesDeLeitura()
    cabecalho = {str(c).strip() for c in linhas[0]}
    if opcoes.forcado:
        return _mapeada(linhas[0], linhas[1:], origem, opcoes)

    if COLUNAS_CANONICAS <= cabecalho:
        saida = io.StringIO(newline="")
        csv.writer(saida, lineterminator="\n").writerows(linhas)
        saida.seek(0)
        resultado = carregar_linhas(saida)
        return Extracao(
            conversas=resultado.conversas,
            formato=f"{origem} no formato do Fraus",
            tem_tempo=True,
            rejeitadas=[linha.model_dump() for linha in resultado.rejeitadas],
        )

    if {"Mensagem/Quem enviou", "Conversa"} <= cabecalho:
        saida = io.StringIO(newline="")
        csv.writer(saida, lineterminator="\n").writerows(linhas)
        saida.seek(0)
        resultado = totalk.converter(saida)
        avisos = []
        if resultado.agentes_detectados:
            avisos.append(
                "Atendentes humanos inferidos pela assinatura da mensagem: "
                + ", ".join(resultado.agentes_detectados)
                + ". A taxa de contenção depende disso."
            )
        if resultado.mensagens_sem_prefixo:
            avisos.append(
                f"{resultado.mensagens_sem_prefixo} mensagem(ns) da empresa sem "
                "assinatura foram contadas como bot."
            )
        return Extracao(
            conversas=resultado.conversas,
            formato="export da Totalk",
            tem_tempo=True,
            avisos=avisos,
            rejeitadas=[linha.model_dump() for linha in resultado.ignoradas],
        )

    return _mapeada(linhas[0], linhas[1:], origem, opcoes)


def _mapeada(
    colunas: list[str], linhas: list[list[str]], origem: str, opcoes: OpcoesDeLeitura | None = None
) -> Extracao:
    """Estrutura desconhecida: o mapeador descobre os papeis e relata o que inferiu.

    Ordem de autoridade: o que veio confirmado nesta requisicao, depois o
    perfil salvo para esta assinatura de colunas, depois a heuristica.
    """
    opcoes = opcoes or OpcoesDeLeitura()
    colunas = [str(c).strip() for c in colunas]
    forcado, ordem_data, perfil = opcoes.forcado, opcoes.ordem_data, None
    if forcado is None and opcoes.perfil_para is not None:
        perfil = opcoes.perfil_para(mapeador.assinatura(colunas))
        if perfil is not None:
            forcado = perfil["papeis"]
            ordem_data = ordem_data or perfil.get("ordem_data")
    try:
        resultado = mapeador.converter(colunas, linhas, origem, forcado, ordem_data)
    except mapeador.MapeamentoInsuficienteError as erro:
        faltando = sorted(COLUNAS_CANONICAS - {str(c).strip() for c in colunas})
        raise ArquivoIlegivelError(
            f"{erro} Se preferir o formato do Fraus, faltam: {', '.join(faltando)}. "
            "Também aceito o export da Totalk ('Mensagem/Quem enviou' e 'Conversa')."
        ) from erro
    mapa = resultado.mapeamento
    avisos = list(resultado.avisos)
    if perfil is not None:
        avisos.insert(0, f"Apliquei o perfil salvo “{perfil['nome']}”, que casa com as colunas deste arquivo.")
    return Extracao(
        conversas=resultado.conversas,
        formato=f"{origem} com colunas inferidas",
        tem_tempo=resultado.tem_tempo,
        id_do_arquivo="conversa_id" not in mapa.papeis,
        avisos=avisos,
        rejeitadas=resultado.rejeitadas,
        mapeamento={
            "colunas": mapa.colunas,
            "assinatura": mapeador.assinatura(mapa.colunas),
            "papeis": {
                papel: {"coluna": a.coluna, "confianca": a.confianca, "motivo": a.motivo}
                for papel, a in mapa.papeis.items()
            },
            "ordem_data": mapa.ordem_data,
            "data_ambigua": mapa.data_ambigua,
        },
        amostra=[
            [censurar_pii(str(celula)) for celula in linha]
            for linha in linhas[:LINHAS_DE_AMOSTRA]
        ],
        perfil={"id": perfil["id"], "nome": perfil["nome"]} if perfil else None,
    )


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _de_prosa(texto: str, nome: str, origem: str) -> Extracao:
    # A transcricao traz, no maximo, a hora. O dia e o do envio, e os dois sao
    # do relogio de quem enviou: ate 02/10/2026 "22:30" era lido como UTC e a
    # conversa aparecia tres horas antes, as vezes no dia anterior.
    inicio = no_fuso_do_produto(_agora()).replace(microsecond=0)
    transcricao = ler_transcricao(texto, inicio)

    if not transcricao.mensagens:
        exemplo = "Cliente: bom dia\nAtendente: bom dia, como posso ajudar?"
        achados = (
            f" Rótulos que encontrei e não reconheci: {', '.join(transcricao.rotulos_ignorados[:5])}."
            if transcricao.rotulos_ignorados
            else ""
        )
        raise ArquivoIlegivelError(
            f"não achei nenhuma fala em {origem}. Espero linhas no formato "
            f"'Autor: mensagem', com o autor sendo cliente, bot ou atendente."
            f"{achados} Exemplo:\n{exemplo}"
        )

    avisos = []
    if not transcricao.tem_tempo:
        avisos.append(
            "Sem horário nas mensagens: não há latência para medir, e latência "
            "é feature do fusor. Por isso esta conversa NÃO "
            "recebe nota — preencher o tempo com zero faria o modelo ler como se "
            "toda resposta tivesse sido instantânea, e a nota sairia melhor do "
            "que a verdade. A leitura por mensagem (classificação, emoção, ironia "
            "e peso das palavras) vale normalmente."
        )
    else:
        avisos.append(
            "O arquivo traz a hora de cada fala, mas não o dia: a conversa fica "
            "registrada no dia do envio. A latência e a nota não dependem disso; "
            "a posição na série diária, sim."
        )
    if transcricao.rotulos_ignorados:
        avisos.append(
            "Rótulos não reconhecidos, tratados como continuação da fala anterior: "
            + ", ".join(sorted(set(transcricao.rotulos_ignorados))[:5])
        )

    conversa = Conversa(
        id=nome.rsplit(".", 1)[0][:80] or "transcricao",
        canal=origem,
        iniciada_em=transcricao.mensagens[0].enviada_em,
        encerrada_em=transcricao.mensagens[-1].enviada_em,
        escalou_para_humano=any(m.autor == "humano" for m in transcricao.mensagens),
        mensagens=transcricao.mensagens,
    )
    return Extracao(
        conversas=[conversa],
        formato=f"transcrição em {origem}",
        tem_tempo=transcricao.tem_tempo,
        avisos=avisos,
        tem_data=False,
        id_do_arquivo=True,
    )


def extrair(nome: str, dados: bytes, opcoes: OpcoesDeLeitura | None = None) -> Extracao:
    """Ponto unico de entrada: decide pelo nome e le pelo conteudo."""
    formato = _extensao(nome)

    if formato == "csv":
        # Export de Windows costuma sair em cp1252/latin-1, e o Excel pt-BR
        # separa por `;`. Os dois sao resolvidos no leitor, nao recusados.
        texto, _ = leitores.decodificar(dados)
        try:
            (cabecalho, corpo), _ = leitores.tabela_de_csv(texto)
            if not cabecalho:
                raise ArquivoIlegivelError("o CSV esta vazio")
            return _de_tabela([cabecalho, *corpo], "CSV", opcoes)
        except csv.Error as erro:
            # O modulo `csv` desiste do ARQUIVO, nao de uma linha: aspas que
            # abrem e nao fecham engolem o resto do texto num campo so, e ele
            # estoura o teto de 131072 caracteres por campo. Ate 02/10/2026
            # isso subia cru -- nem as rotas nem `extrair_ou_400` conhecem
            # `csv.Error` -- e um export plausivel virava 500. O `try` cobre os
            # tres pontos que leem CSV: a deteccao de delimitador e a tabela
            # (`leitores`) e a releitura no layout canonico (`csv_driver`).
            raise ArquivoIlegivelError(
                f"CSV ilegível: o leitor desistiu do arquivo ({erro}). Quase "
                "sempre são aspas que abrem e não fecham no texto de uma "
                "mensagem, e o resto do arquivo vira um campo só. Aspas dentro "
                'do texto se escrevem dobradas ("").'
            ) from erro

    if formato == "json":
        texto, _ = leitores.decodificar(dados)
        try:
            colunas, linhas = leitores.tabela_de_json(texto)
        except ValueError as erro:
            raise ArquivoIlegivelError(
                "JSON ilegivel: nem um documento JSON nem JSON Lines (um objeto por linha)."
            ) from erro
        if not linhas:
            raise ArquivoIlegivelError(
                "não achei nenhuma lista de registros no JSON. Espero uma lista de "
                "mensagens, ex.: [{\"autor\": \"cliente\", \"texto\": \"oi\", \"data\": \"...\"}]."
            )
        return _de_tabela([colunas, *linhas], "JSON", opcoes)

    if formato == "txt":
        texto, _ = leitores.decodificar(dados)
        whatsapp = leitores.tabela_de_whatsapp(texto)
        if whatsapp is not None:
            colunas, linhas = whatsapp
            return _mapeada(colunas, linhas, "WhatsApp", opcoes)
        return _de_prosa(texto, nome, "txt")

    if formato == "xlsx":
        return _de_tabela(_linhas_da_planilha(dados), "planilha", opcoes)

    if formato == "docx":
        texto = _texto_do_docx(dados)  # guarda de bomba zip vem aqui, antes
        tabela = _tabela_do_docx(dados)
        # Primeira linha com "Cliente"/"Bot"/"Atendente" numa celula e FALA, nao
        # cabecalho: a tabela de uma linha por fala sem titulo de coluna. Pelo
        # mapeador ela perderia a primeira fala calada; como prosa, nao perde.
        if tabela is not None and any(mapeador.papel_do_valor(c) for c in tabela[0]):
            tabela = None
        if tabela is not None:
            try:
                extracao = _mapeada(tabela[0], tabela[1:], "docx", opcoes)
            except ArquivoIlegivelError:
                # A tabela nao e de conversa (itens, valores, assinatura):
                # o documento segue como transcricao, como sempre foi.
                pass
            else:
                extracao.formato = "tabela em docx com colunas inferidas"
                return extracao
        return _de_prosa(texto, nome, "docx")

    return _de_prosa(_texto_do_pdf(dados), nome, "pdf")
