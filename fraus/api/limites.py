"""O teto de CORPO da requisicao -- a unica trava que age antes do parse.

Os tetos das rotas (`TETO_ARQUIVO_ANALISE` e afins) sao conferidos DENTRO do
handler, e ate aqui isso parecia suficiente. Nao era: quando o handler de
`/analisar/arquivo` comeca a rodar, o FastAPI ja resolveu o `UploadFile` --
ou seja, o multipart ja foi lido por inteiro e ja escorreu para um arquivo
temporario em disco. O `if len(dados) > TETO` da rota recusava um upload que a
maquina ja tinha pago para receber; ele protegia a CPU do BERTimbau, que era a
intencao declarada, e nunca a memoria nem o disco.

Este middleware e o unico lugar do caminho que roda ANTES do corpo ser lido, e
por isso e o unico que pode recusar sem pagar. Ele olha o `Content-Length`
declarado e responde 413 antes de qualquer parse.

CORPO SEM `Content-Length` (`chunked`) nao tem o que conferir antes de ler, e
ate 15/09/2026 passava por aqui sem ser medido: rota que le JSON ou
`request.body()` (ingestao, webhook) materializava o corpo inteiro antes de
qualquer teto. Agora o `receive` do ASGI e embrulhado e CONTA os bytes enquanto
eles chegam -- no primeiro pedaco que estoura o teto a leitura para e a resposta
e 413. O teto de cada rota continua existindo por dentro, para o que e menor
que 2 MB e ainda assim grande demais para ela.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Teto global de corpo. Folgado DE PROPOSITO: ele nao existe para substituir o
# teto de nenhuma rota, e sim para que nenhuma requisicao chegue absurda ao
# parse. O maior teto de rota do projeto e o de `/analisar` (200 kB); 2 MB
# deixa espaco para o envelope multipart e para o crescimento de `/ingestao`
# sem que este numero precise ser revisitado a cada rota nova.
TETO_CORPO = 2_000_000


class _CorpoGrandeDemais(BaseException):
    """Levantada de dentro do `receive` embrulhado, capturada no middleware.

    `BaseException`, e nao `Exception`, POR NECESSIDADE: o FastAPI embrulha
    qualquer `Exception` do parse do corpo num 400 "error parsing the body", e o
    413 viraria um 400 que culpa o formato por um problema de tamanho.
    """


def _recusa(status: int, detalhe: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detalhe})


def _acima_do_teto(tamanho: int) -> JSONResponse:
    return _recusa(
        413,
        f"corpo de {tamanho // 1024} kB, acima do limite de {TETO_CORPO // 1024} kB.",
    )


class _TetoDeCorpo:
    """Middleware ASGI puro: o `@app.middleware` do Starlette nao alcanca o
    `receive`, e e no `receive` que um corpo sem tamanho declarado se mede."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        cabecalhos = dict(scope.get("headers") or [])
        declarado = cabecalhos.get(b"content-length")
        if declarado is not None:
            try:
                tamanho = int(declarado)
            except ValueError:
                # Content-Length que nao e numero e requisicao malformada. 400
                # aqui, e nao um `pass` silencioso: deixar passar seria abrir a
                # excecao exata que alguem usaria para pular o teto.
                await _recusa(400, "Content-Length invalido")(scope, receive, send)
                return
            if tamanho > TETO_CORPO:
                await _acima_do_teto(tamanho)(scope, receive, send)
                return

        recebidos = 0
        resposta_comecou = False

        async def receive_contado():
            nonlocal recebidos
            mensagem = await receive()
            if mensagem["type"] == "http.request":
                recebidos += len(mensagem.get("body", b""))
                if recebidos > TETO_CORPO:
                    raise _CorpoGrandeDemais()
            return mensagem

        async def send_marcado(mensagem):
            nonlocal resposta_comecou
            if mensagem["type"] == "http.response.start":
                resposta_comecou = True
            await send(mensagem)

        try:
            await self.app(scope, receive_contado, send_marcado)
        except _CorpoGrandeDemais:
            if resposta_comecou:  # pragma: no cover - rota que responde antes de ler
                raise
            await _acima_do_teto(recebidos)(scope, receive, send)


def registrar_middleware_de_corpo(app: FastAPI) -> None:
    """Recusa 413 por `Content-Length` acima do teto, antes de ler o corpo, e
    por bytes contados quando o corpo chega sem tamanho declarado."""
    app.add_middleware(_TetoDeCorpo)
