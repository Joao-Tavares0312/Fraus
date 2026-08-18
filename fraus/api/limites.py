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

O que ele NAO resolve, e vale dizer em voz alta em vez de fingir cobertura:
cliente que omite o `Content-Length` (corpo em `chunked`) passa por aqui sem
ser medido, porque nao ha o que medir antes de ler. Para esse caso a defesa
continua sendo o teto da rota -- que agora aborta a leitura no primeiro byte
excedente em vez de materializar o arquivo inteiro. Duas camadas, cada uma
cobrindo o furo da outra.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Teto global de corpo. Folgado DE PROPOSITO: ele nao existe para substituir o
# teto de nenhuma rota, e sim para que nenhuma requisicao chegue absurda ao
# parse. O maior teto de rota do projeto e o de `/analisar` (200 kB); 2 MB
# deixa espaco para o envelope multipart e para o crescimento de `/ingestao`
# sem que este numero precise ser revisitado a cada rota nova.
TETO_CORPO = 2_000_000


def registrar_middleware_de_corpo(app: FastAPI) -> None:
    """Recusa 413 por `Content-Length` acima do teto, antes de ler o corpo."""

    @app.middleware("http")
    async def limitar_corpo(request, call_next):
        declarado = request.headers.get("content-length")
        if declarado is not None:
            try:
                tamanho = int(declarado)
            except ValueError:
                # Content-Length que nao e numero e requisicao malformada. 400
                # aqui, e nao um `pass` silencioso: deixar passar seria abrir a
                # excecao exata que alguem usaria para pular o teto.
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Content-Length invalido"},
                )
            if tamanho > TETO_CORPO:
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": (
                            f"corpo de {tamanho // 1024} kB, acima do limite de "
                            f"{TETO_CORPO // 1024} kB."
                        )
                    },
                )
        return await call_next(request)
