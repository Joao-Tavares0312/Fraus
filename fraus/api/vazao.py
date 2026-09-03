"""Teto de tentativas em `/auth/entrar` e `/auth/registrar`.

O CUSTO E O PROBLEMA, nao o acerto. `usuarios.CUSTO_N = 2**14` (fraus/usuarios.py)
faz cada derivacao scrypt pedir ~16 MB, e `/auth/entrar` deriva MESMO para
e-mail inexistente -- decisao correta contra ataque de TEMPO (nao vazar quais
e-mails tem conta), mas ela vira alavanca de DoS quando a rota esta publicada.
As duas rotas sao ISENTAS de chave de acesso por desenho: sao exatamente as
rotas de quem ainda nao tem credencial nenhuma (ver `seguranca.ISENTAS`), entao
nao havia nada entre um anonimo e o consumo de memoria da maquina. Esta
instalacao ja ficou sem RAM uma vez, em 02/09/2026, publicada por tunel.

E TAMBEM defesa contra forca bruta de senha, mas essa e a consequencia menor:
scrypt ja torna a adivinhacao cara por tentativa. O que o teto compra e o
SERVIDOR continuar de pe.

POR IP, EM PROCESSO, NAO DISTRIBUIDO. Isto nao e defesa contra botnet -- essa
defesa mora na borda (Cloudflare/proxy), e nao esta implementada aqui de
proposito: duplicar um rate limit que a borda ja faz melhor seria o tipo de
abstracao que o projeto evita. O que este modulo cobre e o caso que de fato
derrubou o servidor: um unico IP, um laco de shell.
"""

import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# 20 tentativas por minuto e generoso para uso humano (ninguem erra a senha
# vinte vezes em sessenta segundos) e caro para quem tenta esgotar CPU: no
# maximo 20 derivacoes de scrypt por IP por janela, ~320 KB de pico em vez de
# um laco sem fim.
TENTATIVAS_POR_JANELA = 20
JANELA_S = 60.0

CAMINHOS_LIMITADOS = ("/auth/entrar", "/auth/registrar")


class LimitadorDeVazao:
    """Janela deslizante por IP, em memoria. Reinicia com o processo -- que e
    aceitavel: o ataque que isto corta e o de UMA sessao continua, e um
    reinicio de deploy ja e uma pausa maior que a janela inteira."""

    def __init__(self, tentativas: int = TENTATIVAS_POR_JANELA, janela_s: float = JANELA_S):
        self._tentativas = tentativas
        self._janela_s = janela_s
        self._historico: dict[str, deque[float]] = defaultdict(deque)

    def permite(self, identidade: str, agora: float) -> bool:
        fila = self._historico[identidade]
        limite = agora - self._janela_s
        while fila and fila[0] <= limite:
            fila.popleft()
        if len(fila) >= self._tentativas:
            return False
        fila.append(agora)
        return True

    def proxima_vaga_em(self, identidade: str, agora: float) -> int:
        """Segundos ate a tentativa mais antiga da janela expirar -- o
        `Retry-After` que diz a quem opera QUANDO tentar de novo, em vez de
        deixar a unica pista ser "continue batendo e ve"."""
        fila = self._historico[identidade]
        if not fila:
            return 1
        return max(1, int(fila[0] + self._janela_s - agora) + 1)


def registrar_middleware_de_vazao(app: FastAPI) -> None:
    """So as duas rotas caras e isentas de credencial. Estender a leitura
    faria a dashboard, que dispara varias chamadas por render, se
    auto-bloquear -- o mesmo motivo pelo qual `/saude` fica de fora do
    middleware de chave de acesso."""
    limitador = LimitadorDeVazao()

    @app.middleware("http")
    async def limitar_tentativas_de_autenticacao(request: Request, call_next):
        caminho = request.url.path.rstrip("/")
        if caminho not in CAMINHOS_LIMITADOS or request.method != "POST":
            return await call_next(request)

        # `request.client.host`: e a ponta TCP mais proxima, o unico dado que
        # nao pode ser forjado pelo lado de fora. Atras de um proxy real
        # (Cloudflare Tunnel inclusive) ele e o IP do proxy, nao do visitante
        # final -- o que faz o teto valer POR INSTALACAO nesse caso, ainda
        # protegendo o servidor do laco de uma sessao, so que compartilhando a
        # janela entre visitantes distintos. Ler X-Forwarded-For confiaria num
        # cabecalho que o cliente controla, e um atacante rotacionando o valor
        # dele voltaria a furar o teto -- pior que a limitacao atual.
        identidade = request.client.host if request.client else "desconhecido"
        agora = time.monotonic()

        if not limitador.permite(identidade, agora):
            return JSONResponse(
                status_code=429,
                content={"detail": "muitas tentativas -- aguarde antes de tentar de novo"},
                headers={"Retry-After": str(limitador.proxima_vaga_em(identidade, agora))},
            )
        return await call_next(request)
