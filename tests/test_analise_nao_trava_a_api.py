"""`/analisar/arquivo` nao pode pensar DENTRO do event loop.

A ROTA E `async` POR NECESSIDADE: ler um upload exige `await`. Mas o que ela
faz depois -- parsear a planilha e rodar BERTimbau por palavra do cliente -- e
CPU pura e sincrona. Chamado direto de dentro de uma funcao `async`, esse
trabalho roda NA THREAD DO EVENT LOOP, e enquanto ele dura o uvicorn nao
atende mais nenhuma requisicao.

POR QUE ISSO E UM BUG DE VERDADE, E NAO "ficou um pouco lento": a dashboard
pergunta `/saude` de tempos em tempos para saber se a API esta viva. Com o
loop preso, essa pergunta fica na fila -- e a tela pinta "API fora do ar" no
meio de uma analise que esta indo perfeitamente bem. Um `.xlsx` de verdade
congelava a instalacao por minutos e o proxy do Next derrubava a conexao por
tempo esgotado, com a API viva o tempo todo. O sintoma acusa a peca errada, e
foi assim que este bug chegou a producao.

A rota irma `/analisar` nunca teve o problema porque e `def` comum, e o
FastAPI manda toda rota sincrona para o threadpool. A assimetria entre as duas
era acidental.

POR QUE O TESTE OLHA A THREAD, E NAO O RELOGIO. A primeira versao disparava a
analise e um `/saude` em paralelo, cronometrando o segundo. Ela PASSOU no
codigo bloqueante: a rota tem `await`s no comeco (a leitura do upload), entao
o `/saude` era atendido antes de a analise sequer alcancar a parte de CPU. Um
teste de corrida precisaria acertar uma janela que ele mesmo nao controla --
mediria sorte, nao comportamento.

A identidade da thread mede a propriedade DIRETAMENTE, sem janela e sem
piscar: se o trabalho pesado corre na thread do loop, o servidor congela; se
corre em qualquer outra, nao congela. Isso nao e detalhe de implementacao --
e o requisito, dito com precisao. Trocar `run_in_threadpool` por outro
mecanismo que tire o trabalho do loop mantem este teste verde.
"""

import asyncio
import threading

import httpx

from fraus.api.main import criar_app
from fraus.db import Banco
from tests.test_api import MotorFalso

CSV = (
    "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\n"
    "c1,whatsapp,cliente,demorou demais,2026-09-01T10:00:00+00:00,false\n"
    "c1,whatsapp,bot,desculpe pela espera,2026-09-01T10:01:00+00:00,false\n"
)


class MotorEspiao(MotorFalso):
    """O duble da suite, anotando em QUE THREAD foi chamado.

    Herda em vez de reimplementar: a forma do que `analisar_conversa` devolve
    e contrato de `montar_analise`, e uma copia aqui envelheceria em silencio
    no dia em que a rota pedisse mais uma chave -- o teste quebraria por forma
    errada, e nao pelo que ele existe para medir.
    """

    def __init__(self) -> None:
        self.thread_da_analise: int | None = None

    def analisar_conversa(self, conversa, referencia=None, curadoria=None) -> dict:
        self.thread_da_analise = threading.get_ident()
        return super().analisar_conversa(conversa, referencia)


def test_analise_de_arquivo_nao_roda_na_thread_do_event_loop(tmp_path):
    """`asyncio.run` em vez do marcador do pytest-asyncio: e o unico teste
    async da suite, e nao vale uma dependencia nova de desenvolvimento."""
    motor = MotorEspiao()
    resposta, thread_do_loop = asyncio.run(_analisar(tmp_path, motor))

    assert resposta.status_code == 200, resposta.text
    assert motor.thread_da_analise is not None, "o motor nem chegou a ser chamado"
    assert motor.thread_da_analise != thread_do_loop, (
        "a analise rodou na thread do event loop: enquanto ela pensa, a API "
        "nao responde mais nada -- nem /saude, que e o que faz a dashboard "
        "anunciar 'API fora do ar' no meio de uma analise saudavel."
    )


async def _analisar(tmp_path, motor):
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    app = criar_app(banco=banco, motor=motor, raiz_importacao=tmp_path)

    # Lido AQUI DENTRO, ja no loop: e a thread que o `asyncio.run` usa para
    # rodar esta corrotina, que e exatamente a que o uvicorn dedica ao loop.
    thread_do_loop = threading.get_ident()

    transporte = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transporte, base_url="http://teste") as cliente:
        resposta = await cliente.post(
            "/analisar/arquivo",
            files={"arquivo": ("conversa.csv", CSV.encode("utf-8"), "text/csv")},
            timeout=30.0,
        )
    return resposta, thread_do_loop
