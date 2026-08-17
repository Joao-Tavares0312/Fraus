"""API do Fraus.

Score e categoria SAO SEMPRE derivados no servidor: campos vindos do corpo da
requisicao que se pareçam com veredito sao ignorados por construcao -- o modelo
de entrada so aceita `caminho`.

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
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from fraus.api.rotas.modelo import (TETO_ARQUIVO_ANALISE,  # reexportados: os testes os importam daqui
                                    TETO_CONVERSAS_ANALISE,
                                    TETO_LEXICON,
                                    TETO_TEXTO_SIMULACAO)
from fraus.api.rotas import conversas, indicadores, modelo, ingestao, integracoes, acesso, configuracoes, saude
from fraus.api.seguranca import (chave_do_cabecalho, exigir_mestra,
                                 fonte_autorizada,
                                 registrar_middleware_de_acesso)
from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.caminhos import (CAMINHO_BANCO, CAMINHO_FUSOR,
                                CAMINHO_METRICAS, CAMINHO_METRICAS_EMOCAO,
                                CAMINHO_METRICAS_IRONIA, CAMINHO_MODELO_EMOCAO,
                                CAMINHO_MODELO_IRONIA, CAMINHO_MODELO_TEXTO,
                                RAIZ_IMPORTACAO, metricas_de,
                                resolver_dentro_da_raiz)
from fraus.api.periodo import dia_ou_400, no_recorte, recorte_ou_400
from fraus.api.esquemas import (TIPOS_DE_FONTE, PedidoAjusteFonte,
                                PedidoAnalise, PedidoChaveAcesso,
                                PedidoFonte, PedidoImportacao,
                                PedidoIngestao, PedidoSimulacao)
from fraus import credencial
from fraus.configuracao import PADROES as CONFIGURACAO_DE_FABRICA
from fraus.configuracao import carregar as carregar_configuracao
from fraus.configuracao import faixas_de
from fraus.configuracao import salvar as salvar_configuracao
from fraus.db import Banco
from fraus.modelos import Conversa
from fraus.fusor import Fusor
from fraus.indicadores import (calcular_csat, calcular_nps, categoria_nps,
                               containment_rate, lexico_por_classe, nota_0_10,
                               serie_diaria, tempo_mediano_resposta)
from fraus.ingest.arquivos import ArquivoIlegivelError, extrair
from fraus.ingest.csv_driver import carregar_csv
from fraus.resumo import resumir
from fraus.motor import Motor  # reexportado: `from fraus.api.main import Motor` segue valendo
from fraus.sinais.palavras import contar_palavras
from fraus.sinais.emocao import NOMES_EMOCOES, ClassificadorEmocao
from fraus.sinais.emoji import linhas_lexicon, score_do_emoji
from fraus.sinais.ironia import ClassificadorIronia
from fraus.sinais.texto import ClassificadorTexto




# Origens que o NAVEGADOR pode usar para falar com a API. A dashboard busca
# `/saude` e `/modelo/simular` do lado do cliente, e sem isso o navegador
# bloqueia o pedido antes de ele sair -- a tela mostra "Failed to fetch"
# enquanto a API responde 200 no curl.
#
# Lista explicita, nunca `*`: esta API le o banco de atendimentos e nao tem
# autenticacao (uso local, ver README), entao qualquer pagina aberta no mesmo
# navegador poderia varrer as conversas. `FRAUS_ORIGENS` sobrescreve, separado
# por virgula, para quando a dashboard rodar em outra porta ou maquina.
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



# Quantos motivos de rejeicao a resposta carrega. O relato existe para o
# operador entender o que ficou de fora, nao para devolver o CSV inteiro.
LIMITE_MOTIVOS = 20


def criar_app(
    banco: Banco,
    motor,
    raiz_importacao: Path | None = None,
    chave_mestra: str | None = None,
) -> FastAPI:
    app = FastAPI(title="Fraus", version="0.1.0")

    ctx = Contexto(
        banco=banco,
        motor=motor,
        raiz=Path(raiz_importacao) if raiz_importacao is not None else RAIZ_IMPORTACAO,
        # Vazia e ausente sao a mesma coisa: "Bearer " autorizando seria a pior
        # combinacao possivel de configuracao errada com acesso liberado.
        chave_mestra=chave_mestra or None,
    )
    app.state.contexto = ctx
    chave_mestra = ctx.chave_mestra
    raiz = ctx.raiz

    registrar_middleware_de_acesso(app, ctx)

    # O CORS precisa ficar POR FORA do middleware de chave: em Starlette, o
    # middleware adicionado por ULTIMO e o mais externo, entao registrar o
    # CORS depois garante que o preflight (sem header de autorizacao, por
    # definicao) e respondido pelo CORS antes de chegar no bloco 401 acima.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origens_liberadas(),
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )
    app.include_router(acesso.router)
    app.include_router(conversas.router)
    app.include_router(indicadores.router)
    app.include_router(configuracoes.router)
    app.include_router(ingestao.router)
    app.include_router(integracoes.router)
    app.include_router(modelo.router)
    app.include_router(indicadores.router)
    app.include_router(conversas.router)
    app.include_router(saude.router)

    return app


def criar_app_padrao() -> FastAPI:
    """Monta o app com dependencias reais. Falha alto se modelo/fusor faltarem.

    Carrega classificador e fusor ANTES de tocar no banco: se a inicializacao
    vai falhar por modelo ausente, ela precisa falhar sem sujar o disco com um
    `fraus.db` de schema vazio.
    """
    classificador = ClassificadorTexto(CAMINHO_MODELO_TEXTO)  # propaga ModeloAusenteError
    fusor = Fusor.carregar(CAMINHO_FUSOR)  # propaga FileNotFoundError se o .joblib faltar

    # Emocao e ironia sobem se estiverem no disco, e a ausencia NAO derruba a
    # API -- ao contrario da satisfacao, que e obrigatoria. A assimetria e
    # deliberada: sem satisfacao nao ha nota, e servir predicao sem modelo e
    # pior que estar fora do ar; sem emocao/ironia o score sai identico, porque
    # nenhuma das duas entra no fusor. Elas somem da tela, e so.
    emocao = ClassificadorEmocao(CAMINHO_MODELO_EMOCAO) if CAMINHO_MODELO_EMOCAO.is_dir() else None
    ironia = ClassificadorIronia(CAMINHO_MODELO_IRONIA) if CAMINHO_MODELO_IRONIA.is_dir() else None

    motor = Motor(classificador, fusor, emocao=emocao, ironia=ironia)
    banco = Banco(CAMINHO_BANCO)
    banco.migrar()

    chave_mestra = os.environ.get("FRAUS_CHAVE_MESTRA") or None
    if chave_mestra is None:
        print(
            "AVISO: API sem autenticacao (uso local). "
            "Defina FRAUS_CHAVE_MESTRA para exigir chave em todas as rotas."
        )
    return criar_app(banco=banco, motor=motor, chave_mestra=chave_mestra)


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
