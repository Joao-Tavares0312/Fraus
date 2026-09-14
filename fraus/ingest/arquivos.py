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
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fraus.ingest import leitores, mapeador, totalk
from fraus.ingest.csv_driver import carregar_linhas
from fraus.ingest.transcricao import ler as ler_transcricao
from fraus.modelos import Conversa

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


def _de_tabela(linhas: list[list[str]], origem: str) -> Extracao:
    """Tenta o layout canonico e, se nao for ele, o export da Totalk."""
    cabecalho = {str(c).strip() for c in linhas[0]}

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

    return _mapeada(linhas[0], linhas[1:], origem)


def _mapeada(colunas: list[str], linhas: list[list[str]], origem: str) -> Extracao:
    """Estrutura desconhecida: o mapeador descobre os papeis e relata o que inferiu."""
    try:
        resultado = mapeador.converter([str(c).strip() for c in colunas], linhas, origem)
    except mapeador.MapeamentoInsuficienteError as erro:
        faltando = sorted(COLUNAS_CANONICAS - {str(c).strip() for c in colunas})
        raise ArquivoIlegivelError(
            f"{erro} Se preferir o formato do Fraus, faltam: {', '.join(faltando)}. "
            "Também aceito o export da Totalk ('Mensagem/Quem enviou' e 'Conversa')."
        ) from erro
    return Extracao(
        conversas=resultado.conversas,
        formato=f"{origem} com colunas inferidas",
        tem_tempo=resultado.tem_tempo,
        avisos=resultado.avisos,
        rejeitadas=resultado.rejeitadas,
    )


def _de_prosa(texto: str, nome: str, origem: str) -> Extracao:
    inicio = datetime.now(timezone.utc).replace(microsecond=0)
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
    )


def extrair(nome: str, dados: bytes) -> Extracao:
    """Ponto unico de entrada: decide pelo nome e le pelo conteudo."""
    formato = _extensao(nome)

    if formato == "csv":
        # Export de Windows costuma sair em cp1252/latin-1, e o Excel pt-BR
        # separa por `;`. Os dois sao resolvidos no leitor, nao recusados.
        texto, _ = leitores.decodificar(dados)
        (cabecalho, corpo), _ = leitores.tabela_de_csv(texto)
        if not cabecalho:
            raise ArquivoIlegivelError("o CSV esta vazio")
        return _de_tabela([cabecalho, *corpo], "CSV")

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
        return _de_tabela([colunas, *linhas], "JSON")

    if formato == "txt":
        texto, _ = leitores.decodificar(dados)
        whatsapp = leitores.tabela_de_whatsapp(texto)
        if whatsapp is not None:
            colunas, linhas = whatsapp
            return _mapeada(colunas, linhas, "WhatsApp")
        return _de_prosa(texto, nome, "txt")

    if formato == "xlsx":
        return _de_tabela(_linhas_da_planilha(dados), "planilha")

    if formato == "docx":
        return _de_prosa(_texto_do_docx(dados), nome, "docx")

    return _de_prosa(_texto_do_pdf(dados), nome, "pdf")
