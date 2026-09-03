"""xlsx e docx sao ZIP, e ZIP mente sobre o proprio tamanho.

O ATAQUE, medido em 02/09/2026 contra a instalacao publicada: 190 KB de upload
viraram 64,8 MB descomprimidos e 20,4 s de CPU. Passava nos DOIS tetos que
existiam porque ambos medem o arquivo COMPRIMIDO -- `TETO_CORPO`
(fraus/api/limites.py) e `TETO_ARQUIVO_ANALISE` (rotas/analise.py).

`TETO_LINHAS_PLANILHA` nao ajudava: ele corta o laco de linhas, e o
`load_workbook` ja parseou `xl/sharedStrings.xml` INTEIRO antes de a primeira
linha sair. O teto certo existia, no estagio errado do pipeline.

E nao adianta ser assincrono: `run_in_threadpool` tira do event loop, mas o
parse e Python puro e segura a GIL -- algumas requisicoes concorrentes travam o
processo inteiro. Por isso a recusa e ANTES de abrir, olhando o cabecalho do
ZIP, que ja declara os dois tamanhos sem descomprimir nada.

DOIS CRITERIOS, e nenhum sozinho basta:

- **Total descomprimido** pega o zip grande e honesto (raso, sem grande razao).
- **Razao** pega o zip pequeno e mentiroso, que passaria longe do total mas
  transforma 190 KB em minutos de CPU.
"""

import io
import zipfile

import pytest

from fraus.ingest.arquivos import (
    ArquivoIlegivelError,
    RAZAO_MAXIMA_ZIP,
    TETO_DESCOMPRIMIDO,
    extrair,
)
from tests.test_arquivos import _docx, _xlsx, CABECALHO


def _zip_com(nome_interno: str, conteudo: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as pacote:
        pacote.writestr(nome_interno, conteudo)
    return buffer.getvalue()


# `b"a" * n` comprime a uma razao absurda -- e exatamente o que a bomba faz.
BOMBA = _zip_com("xl/sharedStrings.xml", b"a" * (TETO_DESCOMPRIMIDO + 1))


@pytest.mark.parametrize("nome", ["ataque.xlsx", "ataque.docx"])
def test_a_bomba_e_recusada_nos_dois_formatos_de_zip(nome):
    """docx e xlsx sao o MESMO pacote ZIP: consertar so um deixaria a porta
    aberta com outra extensao."""
    with pytest.raises(ArquivoIlegivelError) as erro:
        extrair(nome, BOMBA)
    assert "descomprimido" in str(erro.value)


def test_a_recusa_e_barata_e_nao_descomprime_nada():
    """O upload da bomba e pequeno; o teste so tem valor se ele terminar sem
    materializar os bytes. Rodar em tempo de teste normal ja e a prova -- se a
    recusa acontecesse depois do parse, este arquivo levaria dezenas de
    segundos."""
    assert len(BOMBA) < 200_000
    with pytest.raises(ArquivoIlegivelError):
        extrair("ataque.xlsx", BOMBA)


def test_razao_absurda_e_recusada_mesmo_abaixo_do_total():
    """O segundo criterio. Este pacote nao chega perto do teto de bytes, mas
    infla centenas de vezes -- e o custo e CPU, nao memoria."""
    tamanho = TETO_DESCOMPRIMIDO // 4
    pacote = _zip_com("xl/sharedStrings.xml", b"a" * tamanho)
    with zipfile.ZipFile(io.BytesIO(pacote)) as zf:
        info = zf.infolist()[0]
        assert info.file_size < TETO_DESCOMPRIMIDO
        assert info.file_size / info.compress_size > RAZAO_MAXIMA_ZIP

    with pytest.raises(ArquivoIlegivelError) as erro:
        extrair("ataque.xlsx", pacote)
    assert "razao" in str(erro.value) or "descomprimido" in str(erro.value)


def test_a_mensagem_nomeia_o_que_se_esperava():
    """A regra do modulo: toda recusa desta camada diz o que se esperava e o
    que se achou. 'arquivo invalido' obrigaria a pessoa a adivinhar."""
    with pytest.raises(ArquivoIlegivelError) as erro:
        extrair("ataque.xlsx", BOMBA)
    texto = str(erro.value)
    assert "MB" in texto


# --- o que NAO pode mudar ---------------------------------------------------


def test_planilha_legitima_continua_entrando():
    dados = _xlsx([
        CABECALHO.split(","),
        ["c1", "whatsapp", "cliente", "bom dia", "2026-03-01T10:00:00+00:00", "false"],
        ["c1", "whatsapp", "bot", "ola!", "2026-03-01T10:00:30+00:00", "false"],
    ])
    extracao = extrair("planilha.xlsx", dados)
    assert len(extracao.conversas) == 1


def test_docx_legitimo_continua_entrando():
    extracao = extrair("conversa.docx", _docx("Cliente: bom dia\nAtendente: ola!"))
    assert extracao.conversas


def test_arquivo_que_nem_zip_e_continua_dando_a_mensagem_de_sempre():
    """Um .xlsx que nao e ZIP nenhum e defeito de ARQUIVO, e a mensagem que
    explica isso ja existia. A guarda nova nao pode sequestra-la."""
    with pytest.raises(ArquivoIlegivelError) as erro:
        extrair("quebrado.xlsx", b"isto nao e um zip")
    assert "ilegivel" in str(erro.value)


def test_csv_e_pdf_nao_passam_pela_guarda_de_zip():
    """A guarda e dos formatos empacotados. CSV nao e ZIP, e mandar um CSV
    grande pela porta de tras nao pode virar 'razao de compressao'."""
    linhas = [CABECALHO]
    linhas += [
        f"c1,whatsapp,cliente,mensagem {n},2026-03-01T10:{n:02d}:00+00:00,false"
        for n in range(30)
    ]
    extracao = extrair("grande.csv", "\n".join(linhas).encode("utf-8"))
    assert extracao.conversas
