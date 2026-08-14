"""Le o arquivo que chegou -- csv, xlsx, docx ou pdf -- e devolve conversas.

Cada formato entra por onde ele de fato consegue:

- **csv / xlsx**: tabela. Tentam o layout canonico do Fraus e, se ele nao
  estiver la, o export da Totalk. Trazem horario, entao a conversa e pontuada
  normalmente.
- **docx / pdf**: prosa. Viram transcricao (`fraus.ingest.transcricao`), que
  quase nunca carrega horario -- e sem horario NAO HA NOTA, so a leitura por
  mensagem. Ver o modulo de transcricao para o porque.

O ERRO E O PRODUTO PRINCIPAL DAQUI. Um arquivo que nao entra e o caso comum,
nao a excecao: gente exporta do sistema que tem, nao do formato que o Fraus
pede. Recusar dizendo so "formato invalido" obriga a pessoa a adivinhar. Toda
recusa nesta camada nomeia o que se esperava e o que se achou.
"""

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fraus.ingest import totalk
from fraus.ingest.csv_driver import carregar_linhas
from fraus.ingest.transcricao import ler as ler_transcricao
from fraus.modelos import Conversa

EXTENSOES = {
    ".csv": "csv",
    ".xlsx": "xlsx",
    ".xlsm": "xlsx",
    ".docx": "docx",
    ".pdf": "pdf",
}

COLUNAS_CANONICAS = {
    "conversa_id", "canal", "autor", "texto", "enviada_em", "escalou_para_humano",
}

# Teto de celulas lidas de uma planilha. Sem ele, uma pasta com uma coluna
# esticada ate a linha um milhao viraria um milhao de linhas vazias.
TETO_LINHAS_PLANILHA = 50_000


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


def _linhas_da_planilha(dados: bytes) -> list[list[str]]:
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

    faltando = sorted(COLUNAS_CANONICAS - cabecalho)
    raise ArquivoIlegivelError(
        f"não reconheci as colunas de {origem}. Faltam, para o formato do Fraus: "
        f"{', '.join(faltando)}. Encontrei: {', '.join(sorted(cabecalho)[:10])}"
        + ("…" if len(cabecalho) > 10 else "")
        + ". Também aceito o export da Totalk, que precisa de 'Mensagem/Quem enviou' e 'Conversa'."
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
            "Sem horário nas mensagens: não há latência para medir, e latência é "
            "uma das dezesseis features do fusor. Por isso esta conversa NÃO "
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
        try:
            texto = dados.decode("utf-8-sig")
        except UnicodeDecodeError:
            # Export de Windows costuma sair em latin-1. Tentar e melhor que
            # recusar um arquivo que so tem acento em outra tabela.
            try:
                texto = dados.decode("latin-1")
            except UnicodeDecodeError as erro:
                raise ArquivoIlegivelError(f"CSV com codificacao ilegivel: {erro}") from erro
        linhas = [linha for linha in csv.reader(io.StringIO(texto, newline="")) if any(linha)]
        if not linhas:
            raise ArquivoIlegivelError("o CSV esta vazio")
        return _de_tabela(linhas, "CSV")

    if formato == "xlsx":
        return _de_tabela(_linhas_da_planilha(dados), "planilha")

    if formato == "docx":
        return _de_prosa(_texto_do_docx(dados), nome, "docx")

    return _de_prosa(_texto_do_pdf(dados), nome, "pdf")
