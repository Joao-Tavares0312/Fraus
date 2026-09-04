"""API do Fraus -- a MONTAGEM do app. As rotas moram em `fraus/api/rotas/`.

Aqui so acontecem quatro coisas: montar o `Contexto` com as dependencias
reais, registrar os middlewares NA ORDEM certa, incluir os routers de cada
dominio e expor o `app`. Rota nenhuma e definida neste arquivo -- ele cresceu
para 1367 linhas quando eram todas closures daqui, e a fronteira do que cada
dominio faz vive no modulo dele.

Score e categoria SAO SEMPRE derivados no servidor: campos vindos do corpo da
requisicao que se parecam com veredito sao ignorados por construcao.

O objeto `app` de nivel de modulo (consumido por `uvicorn fraus.api.main:app`)
e construido com dependencias REAIS -- Banco em disco e Motor com
ClassificadorTexto/Fusor carregados do disco -- e deve falhar alto no import
se o modelo ou o fusor nao existirem (ModeloAusenteError e equivalente do
fusor propagam sem fallback: servir predicao sem modelo carregado e pior do
que estar fora do ar).

`app` e resolvido de forma preguicosa via `__getattr__` de modulo (PEP 562):
so e construido quando algo de fato acessa o atributo `app` (como o uvicorn
faz ao importar `fraus.api.main:app`). O import puro do modulo -- o que os
testes fazem ao importar `criar_app` -- nunca dispara essa construcao, porque
`app` nao existe como atributo normal do modulo.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fraus.api.caminhos import (CAMINHO_BANCO, CAMINHO_CHAVES, CAMINHO_FUSOR,
                                DESTINO_BANCO,
                                CAMINHO_MODELO_EMOCAO, CAMINHO_MODELO_IRONIA,
                                CAMINHO_MODELO_TEXTO, RAIZ_IMPORTACAO)
from fraus.api.contexto import Contexto
from fraus.api.primeiro_uso import ligar_no_primeiro_uso
from fraus.api.limites import TETO_CORPO, registrar_middleware_de_corpo  # TETO_CORPO reexportado para os testes
from fraus.api.esquemas import TIPOS_DE_FONTE  # reexportado: os testes o importam daqui
from fraus.api.rotas import (acesso, analise, auth, configuracoes, conversas,
                             grafo, indicadores, ingestao, integracoes, lexico,
                             modelo, saude, webhook)
# Reexportados: os testes os importam daqui desde antes da quebra em modulos,
# e mudar de onde se importa um teto seria mexer no contrato de quem consome
# sem nenhum ganho.
from fraus.api.rotas.analise import (TETO_ARQUIVO_ANALISE,
                                     TETO_CONVERSAS_ANALISE)
from fraus.api.rotas.modelo import TETO_LEXICON, TETO_TEXTO_SIMULACAO
from fraus.api.seguranca import registrar_middleware_de_acesso
from fraus.api.vazao import registrar_middleware_de_vazao
from fraus.db import Banco
from fraus.fusor import Fusor
from fraus.motor import Motor  # reexportado: `from fraus.api.main import Motor` segue valendo
from fraus.sinais.emocao import ClassificadorEmocao
from fraus.sinais.ironia import ClassificadorIronia
from fraus.sinais.texto import ClassificadorTexto

# Origens que o NAVEGADOR pode usar para falar com a API.
#
# A dashboard NAO esta mais entre elas: todo caminho dela -- inclusive o que
# roda no navegador -- passa pelo proxy do Next (`/api/fraus/...`), que fala
# com a API de servidor para servidor. Isto aqui vale para quem chama a API
# direto do navegador (um curl no console, uma ferramenta de terceiro), e
# continua existindo como defesa em profundidade.
#
# Lista explicita, nunca `*`: esta API le o banco de atendimentos e pode estar
# aberta (uso local, ver README), entao qualquer pagina aberta no mesmo
# navegador poderia varrer as conversas. `FRAUS_ORIGENS` sobrescreve, separado
# por virgula, para quando a dashboard rodar em outra porta ou maquina.
#
# `allow_headers` NAO inclui `Authorization` de proposito: com a dashboard
# inteira no proxy, ninguem precisa mandar credencial do navegador, e liberar
# o cabecalho convidaria a fazer justamente isso -- que e como uma chave de
# acesso acabaria dentro do bundle JS.
ORIGENS_PADRAO = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
)


def origens_liberadas() -> list[str]:
    bruto = os.environ.get("FRAUS_ORIGENS")
    if not bruto:
        return list(ORIGENS_PADRAO)
    return [pedaco.strip() for pedaco in bruto.split(",") if pedaco.strip()]


def criar_app(
    banco: Banco,
    motor,
    raiz_importacao: Path | None = None,
    chave_mestra: str | None = None,
    jwt_segredo: str | None = None,
    codigo_dev: str | None = None,
    codigo_convite: str | None = None,
) -> FastAPI:
    app = FastAPI(title="Fraus", version="0.1.0")

    ctx = Contexto(
        banco=banco,
        motor=motor,
        raiz=Path(raiz_importacao) if raiz_importacao is not None else RAIZ_IMPORTACAO,
        # Vazia e ausente sao a mesma coisa: "Bearer " autorizando seria a pior
        # combinacao possivel de configuracao errada com acesso liberado.
        chave_mestra=chave_mestra or None,
        # Mesma regra para os segredos da autenticacao de usuario.
        jwt_segredo=jwt_segredo or None,
        codigo_dev=codigo_dev or None,
        # Vazio e ausente sao a mesma coisa aqui tambem: um convite vazio
        # exigiria uma string vazia para cadastrar, que e pior do que nao
        # exigir nada -- pareceria fechado e estaria aberto.
        codigo_convite=codigo_convite or None,
    )
    # Como as rotas alcancam o contexto: `Depends(obter_contexto)` le daqui.
    app.state.contexto = ctx

    # Registrado ANTES do de acesso -- em Starlette o ultimo registrado e o
    # mais externo, entao este fica por DENTRO, e o 413 sai de uma requisicao
    # que ja passou pela credencial. E a ordem certa: o teto de corpo defende
    # o parse, nao a autenticacao, e um 413 respondido antes do 401 diria a
    # quem nao tem chave o tamanho que a API aceita.
    registrar_middleware_de_corpo(app)

    # Por DENTRO do teto de corpo (registrado antes, logo mais externo) e por
    # FORA do de acesso (registrado depois, logo mais interno): a vazao barra
    # a tentativa cara -- o scrypt -- antes dela rodar, mas depois de o corpo
    # ja ter passado pelo teto de tamanho. `/auth/entrar` e `/auth/registrar`
    # sao isentas do middleware de chave de qualquer forma, entao a ordem
    # entre os dois nao muda o resultado para elas; importa e vir antes das
    # ROTAS, onde o custo de fato acontece.
    registrar_middleware_de_vazao(app)

    registrar_middleware_de_acesso(app, ctx)

    # O CORS precisa ficar POR FORA do middleware de chave: em Starlette, o
    # middleware adicionado por ULTIMO e o mais externo, entao registrar o
    # CORS depois garante que o preflight (sem header de autorizacao, por
    # definicao) e respondido pelo CORS antes de chegar no 401 do middleware.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origens_liberadas(),
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )

    app.include_router(saude.router)
    app.include_router(conversas.router)
    app.include_router(indicadores.router)
    app.include_router(configuracoes.router)
    app.include_router(integracoes.router)
    app.include_router(acesso.router)
    app.include_router(ingestao.router)
    app.include_router(modelo.router)
    app.include_router(analise.router)
    app.include_router(grafo.router)
    app.include_router(lexico.router)
    app.include_router(webhook.router)
    app.include_router(auth.router)

    return app


def criar_app_padrao() -> FastAPI:
    """Monta o app com dependencias reais. Falha alto se modelo/fusor faltarem.

    Carrega classificador e fusor ANTES de tocar no banco: se a inicializacao
    vai falhar por modelo ausente, ela precisa falhar sem sujar o disco com um
    `fraus.db` de schema vazio.
    """
    classificador = ClassificadorTexto(CAMINHO_MODELO_TEXTO)  # propaga ModeloAusenteError
    fusor = Fusor.carregar(CAMINHO_FUSOR)  # propaga FileNotFoundError se o .joblib faltar

    # Emocao entra no vetor desde a subida do contrato para 35 features
    # (21/08/2026), e e tao obrigatoria quanto o classificador de texto:
    # ausencia propaga ModeloAusenteError, do mesmo jeito que ClassificadorTexto
    # ja faz -- servir predicao com vetor incompleto e pior que estar fora do ar
    # (invariante 7). O contrato subiu de novo, para 38, em 04/09/2026, quando a
    # ironia SAIU do vetor (medida no corpus de treino, ela funciona como
    # detector de sentimento positivo, nao de ironia -- ver docs/handoff.md).
    # A cabeca de ironia continua obrigatoria mesmo assim: ela nao alimenta mais
    # o fusor, mas alimenta a leitura por mensagem (`prob_ironia` na API), que a
    # tela de atendimento e a de analise mostram. Faltar o modelo tira essa
    # leitura do ar, e o mesmo motivo do invariante 7 vale para ela.
    emocao = ClassificadorEmocao(CAMINHO_MODELO_EMOCAO)
    ironia = ClassificadorIronia(CAMINHO_MODELO_IRONIA)

    motor = Motor(classificador, fusor, emocao, ironia)
    banco = Banco(DESTINO_BANCO)
    banco.migrar()

    chave_mestra = os.environ.get("FRAUS_CHAVE_MESTRA") or None

    # PRIMEIRA subida: gera mestra e chave de acesso e as grava em disco, para
    # a instalacao nascer fechada sem ninguem precisar clicar em nada. Nao roda
    # aqui dentro de `criar_app` de proposito: quem monta o app com dependencias
    # proprias (os testes, o `api_demo`) nao deve ganhar credencial de brinde.
    gravadas = ligar_no_primeiro_uso(banco, CAMINHO_CHAVES, chave_mestra)
    if gravadas is not None:
        print(
            f"Primeira subida: autenticacao LIGADA.\n"
            f"  Mestra e chave de acesso gravadas em: {gravadas.resolve()}\n"
            f"  Esta e a unica copia em claro delas -- o banco guarda so o hash."
        )
    elif chave_mestra is None and banco.hash_da_chave_mestra() is None:
        # Cai aqui quando o arquivo NAO pode ser escrito: nada foi gravado, e a
        # API sobe aberta. Aberta com aviso e recuperavel; fechada com a chave
        # perdida no primeiro boot, nao.
        print(
            f"AVISO: API sem autenticacao. Nao foi possivel escrever "
            f"{CAMINHO_CHAVES} -- ligar sem guardar a chave em lugar nenhum "
            f"trancaria voce para fora. Corrija a permissao e suba de novo, ou "
            f"defina FRAUS_CHAVE_MESTRA."
        )

    return criar_app(
        banco=banco,
        motor=motor,
        chave_mestra=chave_mestra,
        # Autenticacao de usuario (spec 2026-08-31): segredos do ambiente,
        # nunca do banco. Sem FRAUS_JWT_SEGREDO o login responde 503 dizendo o
        # que falta; sem FRAUS_CODIGO_DEV nenhum cadastro nasce dev.
        jwt_segredo=os.environ.get("FRAUS_JWT_SEGREDO") or None,
        codigo_dev=os.environ.get("FRAUS_CODIGO_DEV") or None,
        # Sem esta variavel o cadastro segue ABERTO -- o comportamento de
        # sempre, certo para quem roda em casa. Definir e a decisao de quem
        # publica a API na internet.
        codigo_convite=os.environ.get("FRAUS_CODIGO_CONVITE") or None,
    )


def __getattr__(nome: str):
    """PEP 562: resolve `app` sob demanda, so quando algo acessa o atributo.

    Mantem o import puro do modulo barato (o que os testes fazem ao importar
    `criar_app`) e ainda assim expoe `app` para `uvicorn fraus.api.main:app`,
    que acessa o atributo de verdade -- disparando a construcao real e
    deixando ModeloAusenteError/erro do fusor propagarem.
    """
    if nome == "app":
        return criar_app_padrao()
    raise AttributeError(f"modulo {__name__!r} nao tem atributo {nome!r}")
