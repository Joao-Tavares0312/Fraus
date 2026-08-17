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
from fraus.api.rotas import modelo, ingestao, integracoes, acesso, configuracoes, saude
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
    @app.post("/conversas/importar")
    def importar(pedido: PedidoImportacao) -> dict:
        caminho = resolver_dentro_da_raiz(raiz, pedido.caminho)
        if not caminho.is_file():
            raise HTTPException(status_code=400, detail=f"arquivo nao encontrado: {caminho}")

        try:
            resultado = carregar_csv(caminho)
        except KeyError as erro:
            # Coluna estrutural ausente. O driver deixa o KeyError propagar de
            # proposito (erro de esquema nao e dado sujo de uma linha), mas a
            # borda HTTP nao pode devolver 500 cru: o operador precisa saber
            # QUAL coluna falta para consertar o arquivo.
            raise HTTPException(
                status_code=400,
                detail=f"coluna ausente no CSV: {erro.args[0]}",
            ) from erro

        faixas = ctx.faixas_vigentes()
        for conversa in resultado.conversas:
            score = motor.pontuar_conversa(conversa)
            # A coluna `categoria` e o retrato do instante da importacao; quem
            # le nao a consome (ver `categoria_de`), mas gravar com a faixa
            # vigente evita que o banco inspecionado a mao conte outra historia.
            banco.salvar(conversa, score, ctx.categoria_de(score, faixas))

        # "Motivo registrado" (spec 9) tem que CHEGAR a alguem: a contagem
        # sozinha nao diz o que ficou de fora.
        motivos = [linha.model_dump() for linha in resultado.rejeitadas[:LIMITE_MOTIVOS]]

        # O historico guarda o MESMO que a resposta devolve. Sem ele,
        # "importado com sucesso" e alegacao sem lastro: some da tela no
        # instante seguinte e ninguem consegue mais dizer o que ficou de fora.
        banco.registrar_importacao(
            ocorrida_em=datetime.now(timezone.utc).isoformat(),
            arquivo=caminho.name,
            aceitas=len(resultado.conversas),
            rejeitadas=len(resultado.rejeitadas),
            motivos=motivos,
        )

        return {
            "importadas": len(resultado.conversas),
            "rejeitadas": len(resultado.rejeitadas),
            "motivos": motivos,
        }

    @app.get("/conversas")
    def listar(de: str | None = None, ate: str | None = None) -> list[dict]:
        """Lista de atendimentos com a ficha operacional de cada um.

        Alem de nota e categoria, cada linha carrega o que `fraus.resumo`
        deriva da conversa: contagem de mensagens por autor, tempo de resposta
        do bot e do humano SEPARADOS, duracao e desfecho. Vem tudo junto de
        proposito -- a tela precisa disso por linha, e busca-los um a um era um
        N+1 contra a API.

        `de`/`ate` recortam por dia de inicio, pontas INCLUSIVAS -- o mesmo
        contrato do /serie-temporal. Sem filtro, a lista inteira, como sempre.
        """
        inicio, fim = recorte_ou_400(de, ate)
        # A `nota` sai daqui derivada no SERVIDOR, junto com score e categoria:
        # e a mesma conversao de `/conversas/{id}`, e a dashboard so a exibe.
        faixas = ctx.faixas_vigentes()
        return [
            {
                **linha,
                "categoria": ctx.categoria_de(linha["score"], faixas),
                "nota": nota_0_10(linha["score"]) if linha["score"] is not None else None,
                **resumir(conversa),
            }
            for linha, conversa in banco.listar_com_conversa()
            if no_recorte(conversa.iniciada_em, inicio, fim)
        ]

    @app.get("/conversas/{conversa_id}")
    def detalhar(conversa_id: str) -> dict:
        achado = banco.buscar(conversa_id)
        if achado is None:
            raise HTTPException(status_code=404, detail="conversa nao encontrada")
        conversa, score, _categoria_gravada = achado
        return {
            **conversa.model_dump(mode="json"),
            "score": score,
            "categoria": ctx.categoria_de(score, ctx.faixas_vigentes()),
            "nota": nota_0_10(score) if score is not None else None,
            # A MESMA ficha operacional de `/conversas`, pela mesma funcao. A
            # lista e o detalhe nao podem calcular tempo de resposta por
            # caminhos diferentes: seria a divergencia que a nota derivada no
            # servidor ja existe para evitar, repetida na coluna do lado.
            **resumir(conversa),
        }

    @app.get("/conversas/{conversa_id}/atribuicao")
    def atribuir(conversa_id: str) -> dict:
        """Quais falas puxaram a nota para baixo e quais puxaram para cima.

        Score, categoria e nota saem do que o SERVIDOR ja gravou na
        importacao -- nao sao repontuados aqui. Repontuar criaria uma segunda
        fonte de verdade que poderia divergir de `/conversas/{id}` se o fusor
        em disco mudasse entre a importacao e a leitura.
        """
        achado = banco.buscar(conversa_id)
        if achado is None:
            raise HTTPException(status_code=404, detail="conversa nao encontrada")
        conversa, score, _categoria_gravada = achado
        atribuicao = motor.atribuir_conversa(conversa)
        return {
            "conversa_id": conversa.id,
            "score": score,
            "nota": nota_0_10(score) if score is not None else None,
            "categoria": ctx.categoria_de(score, ctx.faixas_vigentes()),
            "mensagens": atribuicao["mensagens"],
            "importancias": atribuicao["importancias"],
            "contribuicoes": atribuicao["contribuicoes"],
            # Quais campos das mensagens sao LEITURA e nao entram no score.
            # Vem do motor, nao de uma constante daqui: um motor sem as cabecas
            # de emocao/ironia devolve lista vazia, e a tela nao promete um
            # painel que ela nao tem dado para preencher.
            "sinais_fora_do_score": atribuicao.get("sinais_fora_do_score", []),
        }

    @app.get("/indicadores")
    def indicadores(de: str | None = None, ate: str | None = None) -> dict:
        """Indicadores agregados, com recorte opcional de periodo.

        Com `de`/`ate`, os numeros respondem SO pelo recorte -- e o que tira
        da dashboard a agregacao no cliente que ela fazia com filtro ativo.
        `tempo_mediano_resposta_s` e derivado dos timestamps na leitura
        (latencia nunca e persistida) e vem `null` sem nenhum par
        cliente -> resposta, nunca zero.
        """
        registros = ctx.registros_do_recorte(de, ate)
        conversas = [conversa for conversa, _ in registros]
        scores = [score for _, score in registros if score is not None]
        return {
            "nps": calcular_nps(scores, ctx.faixas_vigentes()),
            "csat": calcular_csat(scores),
            "containment_rate": containment_rate(conversas),
            "total_conversas": len(conversas),
            "sem_sinal": len(conversas) - len(scores),
            "tempo_mediano_resposta_s": tempo_mediano_resposta(registros),
        }

    @app.get("/lexico")
    def lexico(de: str | None = None, ate: str | None = None) -> dict:
        """Palavras e emojis caracteristicos por categoria, no recorte pedido.

        Existia so no cliente, que baixava toda transcricao para contar -- o
        ultimo N+1 da visao geral. A ordenacao e por DISTINCAO: o termo que
        aparece em toda parte nao explica classe nenhuma.
        """
        registros = ctx.registros_do_recorte(de, ate)
        return {"classes": lexico_por_classe(registros, ctx.faixas_vigentes())}

    @app.get("/serie-temporal")
    def serie_temporal(de: str | None = None, ate: str | None = None) -> dict:
        """NPS inferido x latencia mediana por dia, com recorte de periodo.

        Existe para tirar da dashboard o N+1 que ela fazia: sem este endpoint,
        montar o grafico exigia baixar a TRANSCRICAO de toda conversa do
        recorte so para ler timestamps. As duas pontas do recorte sao
        INCLUSIVAS, que e como quem opera le "de 01/03 ate 07/03".
        """
        inicio, fim = recorte_ou_400(de, ate)
        registros = [
            (conversa, score)
            for conversa, score in banco.todas()
            if no_recorte(conversa.iniciada_em, inicio, fim)
        ]
        return {
            "de": inicio.isoformat() if inicio else None,
            "ate": fim.isoformat() if fim else None,
            "pontos": serie_diaria(registros, ctx.faixas_vigentes()),
        }

    app.include_router(acesso.router)
    app.include_router(configuracoes.router)
    app.include_router(ingestao.router)
    app.include_router(integracoes.router)
    app.include_router(modelo.router)
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
