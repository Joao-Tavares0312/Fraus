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

from fraus.api.rotas import configuracoes, saude
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
from fraus import acesso
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

# Teto de tamanho do texto aceito por /modelo/simular -- nao e limite de
# modelo (BERTimbau trunca em TAMANHO_MAXIMO tokens), e limite de payload.
TETO_TEXTO_SIMULACAO = 2000

# Teto de itens que /modelo/lexicon devolve por pagina, mesmo se pedirem mais.
TETO_LEXICON = 200

# Tetos de /analisar. A rota roda BERTimbau uma vez por palavra de cliente
# (oclusao), entao o custo cresce com o tamanho do arquivo -- sem teto, um CSV
# de lote inteiro penduraria a requisicao em CPU. Os dois limites recusam alto
# e explicam, em vez de aceitar e demorar minutos sem sinal de vida.
TETO_ARQUIVO_ANALISE = 200_000
TETO_CONVERSAS_ANALISE = 10

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


LIMITE_LEXICON_PADRAO = 50

# Quantos motivos de rejeicao a resposta carrega. O relato existe para o
# operador entender o que ficou de fora, nao para devolver o CSV inteiro.
LIMITE_MOTIVOS = 20


def _fonte_publica(fonte: dict) -> dict:
    """Fonte como ela pode sair pela rede: o segredo nao acompanha.

    So o NOME da variavel de ambiente e o fato de ela estar definida. A
    verificacao e feita na LEITURA, nao no cadastro: a variavel pode aparecer
    ou sumir do ambiente depois, e responder pelo que era verdade no cadastro
    seria mentir sobre o estado atual.
    """
    variavel = fonte["variavel_segredo"]
    return {**fonte, "configurada": bool(variavel and os.environ.get(variavel))}


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

    @app.get("/integracoes/fontes")
    def listar_fontes() -> list[dict]:
        """Fontes cadastradas, cada uma com `configurada` derivado do ambiente.

        `configurada` responde apenas SE a variavel de ambiente existe. O valor
        do segredo nunca sai daqui -- nem parcial, nem mascarado: mascara e
        vazamento de tamanho e de prefixo por um caminho mais lento.
        """
        return [_fonte_publica(fonte) for fonte in banco.listar_fontes()]

    @app.post("/integracoes/fontes", status_code=201)
    def criar_fonte(pedido: PedidoFonte) -> dict:
        nome = pedido.nome.strip()
        if not nome:
            raise HTTPException(status_code=400, detail="nome da fonte vazio")
        canal = pedido.canal.strip()
        if not canal:
            raise HTTPException(status_code=400, detail="canal da fonte vazio")
        if pedido.tipo not in TIPOS_DE_FONTE:
            raise HTTPException(
                status_code=400,
                detail=f"tipo de fonte desconhecido: {pedido.tipo} "
                       f"(esperado: {', '.join(TIPOS_DE_FONTE)})",
            )
        fonte = banco.criar_fonte(
            nome=nome,
            canal=canal,
            tipo=pedido.tipo,
            variavel_segredo=(pedido.variavel_segredo or "").strip() or None,
            criada_em=datetime.now(timezone.utc).isoformat(),
        )
        return _fonte_publica(fonte)

    @app.patch("/integracoes/fontes/{fonte_id}")
    def ajustar_fonte(fonte_id: int, pedido: PedidoAjusteFonte) -> dict:
        if banco.buscar_fonte(fonte_id) is None:
            raise HTTPException(status_code=404, detail="fonte nao encontrada")
        nome = None
        if pedido.nome is not None:
            nome = pedido.nome.strip()
            if not nome:
                raise HTTPException(status_code=400, detail="nome da fonte vazio")
        return _fonte_publica(banco.atualizar_fonte(fonte_id, nome=nome, ativa=pedido.ativa))

    @app.delete("/integracoes/fontes/{fonte_id}", status_code=204)
    def apagar_fonte(fonte_id: int) -> None:
        """Remove o CADASTRO da fonte. Nenhuma conversa e apagada junto.

        Conversa que ja entrou e dado de atendimento medido; a fonte e so o
        registro de por onde ele entrou. Apagar a origem nao pode reescrever o
        historico -- e por isso que nao ha exclusao em cascata aqui.
        """
        if not banco.apagar_fonte(fonte_id):
            raise HTTPException(status_code=404, detail="fonte nao encontrada")

    @app.post("/integracoes/fontes/{fonte_id}/chave", status_code=201)
    def gerar_chave(
        fonte_id: int, authorization: str | None = Header(default=None)
    ) -> dict:
        """Gera a chave de API da fonte e a devolve EM CLARO uma unica vez.

        Nao ha rota para reler a chave depois, e isso e a feature: o banco
        guarda so o hash, entao um `fraus.db` vazado num backup nao leva
        credencial junto. Perder a chave custa gerar outra.

        Gerar substitui a anterior. Duas chaves validas ao mesmo tempo pareceria
        rotacao sem risco, mas a antiga seguiria aceita sem ninguem saber quem
        ainda a usa.
        """
        exigir_mestra(ctx, authorization)
        if banco.buscar_fonte(fonte_id) is None:
            raise HTTPException(status_code=404, detail="fonte nao encontrada")

        chave, chave_hash = credencial.gerar(fonte_id)
        fonte = banco.gravar_chave(
            fonte_id,
            chave_hash=chave_hash,
            dica=credencial.dica(chave),
            criada_em=datetime.now(timezone.utc).isoformat(),
        )
        return {
            "fonte": _fonte_publica(fonte),
            # Unica vez que este campo existe em qualquer resposta da API.
            "chave": chave,
            "aviso": (
                "Guarde agora: esta chave nao pode ser lida de novo. "
                "O servidor guarda apenas o hash dela."
            ),
        }

    @app.delete("/integracoes/fontes/{fonte_id}/chave", status_code=204)
    def revogar_chave(
        fonte_id: int, authorization: str | None = Header(default=None)
    ) -> None:
        """Invalida a chave da fonte. A fonte e as conversas dela continuam."""
        exigir_mestra(ctx, authorization)
        if banco.buscar_fonte(fonte_id) is None:
            raise HTTPException(status_code=404, detail="fonte nao encontrada")
        banco.revogar_chave(fonte_id)

    @app.post("/acesso/chaves", status_code=201)
    def criar_chave_acesso(
        pedido: PedidoChaveAcesso, authorization: str | None = Header(default=None)
    ) -> dict:
        """Gera uma chave de acesso e a devolve EM CLARO uma unica vez."""
        exigir_mestra(ctx, authorization)
        registro = banco.criar_chave_acesso(
            nome=pedido.nome,
            criada_em=datetime.now(timezone.utc).isoformat(),
        )
        chave, chave_hash = acesso.gerar(registro["id"])
        banco.gravar_chave_acesso(
            registro["id"], chave_hash=chave_hash, dica=credencial.dica(chave)
        )
        return {
            **registro,
            "dica": credencial.dica(chave),
            "chave": chave,
            "aviso": (
                "Guarde agora: esta chave não pode ser lida de novo. "
                "Revogue e gere outra se perdê-la."
            ),
        }

    @app.get("/acesso/chaves")
    def listar_chaves_acesso(authorization: str | None = Header(default=None)) -> list[dict]:
        exigir_mestra(ctx, authorization)
        return banco.listar_chaves_acesso()

    @app.delete("/acesso/chaves/{chave_id}", status_code=204)
    def revogar_chave_acesso(
        chave_id: int, authorization: str | None = Header(default=None)
    ) -> None:
        exigir_mestra(ctx, authorization)
        if not banco.apagar_chave_acesso(chave_id):
            raise HTTPException(status_code=404, detail="chave nao encontrada")

    @app.post("/ingestao", status_code=201)
    def ingerir(pedido: PedidoIngestao, authorization: str | None = Header(default=None)) -> dict:
        """Recebe atendimento de um sistema EXTERNO, autenticado por chave.

        E o unico caminho de escrita que nao exige acesso ao disco da maquina:
        a importacao le arquivo de uma pasta local, e isto aqui aceita a
        conversa pela rede.

        O CANAL e o da FONTE cadastrada, nao o que veio no corpo: quem manda o
        dado nao escolhe em que canal ele e contabilizado, do mesmo jeito que
        nao escolhe o proprio score. Fonte desativada recusa -- o interruptor
        da tela de Integracoes precisa de fato desligar alguma coisa.

        Score e categoria sao derivados aqui, como em toda entrada.
        """
        chave = chave_do_cabecalho(authorization)
        fonte = fonte_autorizada(ctx.banco, chave)

        try:
            conversa = Conversa(
                id=pedido.id,
                canal=fonte["canal"],
                iniciada_em=pedido.mensagens[0].enviada_em,
                encerrada_em=pedido.encerrada_em,
                escalou_para_humano=pedido.escalou_para_humano,
                mensagens=sorted(pedido.mensagens, key=lambda m: m.enviada_em),
            )
        except ValidationError as erro:
            raise HTTPException(status_code=400, detail=str(erro)) from erro

        score = motor.pontuar_conversa(conversa)
        banco.salvar(conversa, score, ctx.categoria_de(score, ctx.faixas_vigentes()))
        return {
            "id": conversa.id,
            "canal": conversa.canal,
            "score": score,
            "nota": nota_0_10(score) if score is not None else None,
            "categoria": ctx.categoria_de(score, ctx.faixas_vigentes()),
            "fonte": fonte["nome"],
        }

    @app.get("/integracoes/tipos")
    def tipos_de_fonte() -> list[dict]:
        """Os tipos que a ingestao sabe tratar HOJE.

        Existe para a interface parar de manter a propria copia da lista. Ela
        mantinha, e a copia so ficaria errada no dia em que um tipo novo
        entrasse aqui: o formulario seguiria oferecendo dois, e o terceiro
        existiria na API sem existir na tela -- divergencia que nao levanta
        erro nenhum, so some da vista.
        """
        return [
            {
                "valor": "csv",
                "rotulo": "CSV",
                "ajuda": "arquivo importado por POST /conversas/importar",
            },
            {
                "valor": "webhook",
                "rotulo": "Webhook",
                "ajuda": "recebe eventos da plataforma",
            },
        ]

    @app.get("/integracoes/arquivos")
    def arquivos_importaveis() -> dict:
        """Os CSV disponiveis na raiz de importacao.

        A rota de importacao aceita um caminho RELATIVO a raiz e recusa
        qualquer escape. Sem esta listagem, quem opera precisava adivinhar o
        nome do arquivo ou sair da interface para olhar a pasta -- e digitar
        nome de arquivo de memoria e como um caminho errado vira "arquivo nao
        encontrado" sem ninguem entender por que.

        Devolve NOME e tamanho, nunca caminho absoluto: o cliente nao precisa
        saber onde a pasta fica no disco, e a resposta nao vaza a arvore da
        maquina. A busca desce em subpastas porque a raiz pode ser organizada
        por mes ou canal.
        """
        raiz_resolvida = raiz.resolve()
        if not raiz_resolvida.is_dir():
            return {"raiz": raiz_resolvida.name, "arquivos": []}

        arquivos = []
        for caminho in sorted(raiz_resolvida.rglob("*.csv")):
            if not caminho.is_file():
                continue
            arquivos.append(
                {
                    "caminho": caminho.relative_to(raiz_resolvida).as_posix(),
                    "bytes": caminho.stat().st_size,
                }
            )
        return {"raiz": raiz_resolvida.name, "arquivos": arquivos}

    @app.get("/integracoes/importacoes")
    def listar_importacoes() -> list[dict]:
        """Historico de importacao, mais recente primeiro.

        Registra so o que a ingestao chegou a processar: arquivo recusado na
        porta (caminho fora da raiz, coluna estrutural ausente) nao virou
        importacao nenhuma, e listar como tal seria contar uma tentativa como
        evento de dado.
        """
        return banco.listar_importacoes()

    @app.get("/modelo")
    def modelo() -> dict:
        """Ficha do modelo: pesos globais, metricas de treino, faixas e lexicon.

        `metricas` e null quando o notebook 01 ainda nao exportou o arquivo --
        nunca um valor inventado. As faixas de NPS saem da configuracao
        vigente, a MESMA fonte que alimenta a categoria de cada atendimento --
        faixa duplicada em dois lugares ja foi defeito deste projeto uma vez.
        """
        metricas = metricas_de(CAMINHO_METRICAS)
        return {
            "importancias": motor.importancias(),
            "metricas": metricas,
            "classes": ["insatisfeito", "neutro", "satisfeito"],
            # As tres cabecas, cada uma com a metrica que ela de fato mediu e a
            # limitacao que essa metrica esconde. `pontua` separa quem decide a
            # nota de quem so descreve: hoje so a satisfacao entra no fusor.
            "cabecas": [
                {
                    "nome": "satisfacao",
                    "classes": ["insatisfeito", "neutro", "satisfeito"],
                    "metricas": metricas,
                    "pontua": True,
                },
                {
                    "nome": "emocao",
                    "classes": [*NOMES_EMOCOES, "desprezo"],
                    "metricas": metricas_de(CAMINHO_METRICAS_EMOCAO),
                    "pontua": False,
                },
                {
                    "nome": "ironia",
                    "classes": ["nao-ironico", "ironico"],
                    "metricas": metricas_de(CAMINHO_METRICAS_IRONIA),
                    "pontua": False,
                },
            ],
            "faixas_nps": {
                categoria: list(faixa) for categoria, faixa in ctx.faixas_vigentes().items()
            },
            "total_emojis_lexicon": len(linhas_lexicon()),
        }

    @app.get("/modelo/lexicon")
    def lexicon(busca: str | None = None, limite: int = LIMITE_LEXICON_PADRAO, deslocamento: int = 0) -> dict:
        """Pagina o lexicon de emoji, ordenado por total de anotacoes.

        `score` reaproveita `score_do_emoji` -- a mesma fonte usada no sinal
        de emoji e na simulacao, para nunca divergir da formula real.
        """
        limite_efetivo = max(0, min(limite, TETO_LEXICON))
        deslocamento_efetivo = max(0, deslocamento)

        linhas = linhas_lexicon()
        if busca:
            linhas = [linha for linha in linhas if linha["emoji"] == busca]
        linhas_ordenadas = sorted(
            linhas,
            key=lambda linha: linha["negativo"] + linha["neutro"] + linha["positivo"],
            reverse=True,
        )
        pagina = linhas_ordenadas[deslocamento_efetivo:deslocamento_efetivo + limite_efetivo]

        return {
            "total": len(linhas_ordenadas),
            "itens": [
                {
                    "emoji": linha["emoji"],
                    "score": score_do_emoji(linha["emoji"]),
                    "negativo": linha["negativo"],
                    "neutro": linha["neutro"],
                    "positivo": linha["positivo"],
                }
                for linha in pagina
            ],
        }

    @app.post("/modelo/simular")
    def simular(pedido: PedidoSimulacao) -> dict:
        """Roda o classificador numa frase avulsa -- nao persiste nada no banco."""
        texto = pedido.texto
        if not texto.strip():
            raise HTTPException(status_code=400, detail="texto vazio")
        if len(texto) > TETO_TEXTO_SIMULACAO:
            raise HTTPException(
                status_code=400,
                detail=f"texto acima do limite de {TETO_TEXTO_SIMULACAO} caracteres",
            )

        resultado = motor.simular_texto(texto)
        return {
            "texto": texto,
            "prob_insatisfeito": resultado["prob_insatisfeito"],
            "prob_neutro": resultado["prob_neutro"],
            "prob_satisfeito": resultado["prob_satisfeito"],
            "emojis": resultado["emojis"],
            "emocao": resultado.get("emocao"),
            "prob_ironia": resultado.get("prob_ironia"),
        }

    @app.post("/analisar")
    def analisar(pedido: PedidoAnalise) -> dict:
        """Analisa um arquivo de conversa SEM gravar nada.

        Nada daqui entra no banco: nem a conversa, nem o score, nem o arquivo.
        E o que separa esta rota da importacao -- aqui se pergunta "o que o
        modelo acha disto?", nao "passe a considerar isto nos indicadores". Um
        arquivo analisado nao muda o NPS de ninguem.

        O conteudo chega no corpo e e interpretado em memoria, entao a rota
        NAO abre a superficie de escrita que fez a tela de Integracoes recusar
        upload: nenhum byte toca o disco.

        A comparacao de vocabulario usa o banco como referencia -- e o que
        permite dizer "esta palavra aparece o triplo do normal AQUI". Com o
        banco vazio nao ha referencia, e o campo `destaque` sai nulo em vez de
        fingir uma media.
        """
        if not pedido.csv.strip():
            raise HTTPException(status_code=400, detail="arquivo vazio")
        if len(pedido.csv) > TETO_ARQUIVO_ANALISE:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"arquivo acima do limite de {TETO_ARQUIVO_ANALISE} caracteres. "
                    "Esta rota examina um atendimento por vez; para um lote, use a importacao."
                ),
            )

        extracao = _extrair_ou_400(pedido.nome or "conversa.csv", pedido.csv.encode("utf-8"))
        return _montar_analise(extracao)

    @app.post("/analisar/arquivo")
    async def analisar_arquivo(arquivo: UploadFile = File(...)) -> dict:
        """Mesma analise, aceitando csv, xlsx, docx ou pdf.

        Existe separada de `/analisar` porque formato binario nao cabe em JSON:
        planilha e PDF nao sao texto, e obrigar o cliente a codificar em base64
        inflaria o corpo em um terco por nada.

        Continua sem gravar coisa alguma -- os bytes sao lidos em memoria e
        descartados. Nao ha `open()` de escrita em lugar nenhum deste caminho.
        """
        dados = await arquivo.read()
        if not dados:
            raise HTTPException(status_code=400, detail="arquivo vazio")
        if len(dados) > TETO_ARQUIVO_ANALISE:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"arquivo de {len(dados) // 1024} kB, acima do limite de "
                    f"{TETO_ARQUIVO_ANALISE // 1024} kB. Esta tela examina um "
                    "atendimento por vez; para um lote, use a importacao."
                ),
            )

        extracao = _extrair_ou_400(arquivo.filename or "arquivo", dados)
        return _montar_analise(extracao)

    def _extrair_ou_400(nome: str, dados: bytes):
        """Traduz toda falha de leitura em 400 que NOMEIA o que se esperava.

        Arquivo que nao entra e o caso comum, nao a excecao: as pessoas
        exportam do sistema que tem, nao do formato que o Fraus pede. Um 500 ou
        um "formato invalido" seco obrigaria a adivinhar qual e o problema.
        """
        try:
            return extrair(nome, dados)
        except ArquivoIlegivelError as erro:
            raise HTTPException(status_code=400, detail=str(erro)) from erro
        except KeyError as erro:
            raise HTTPException(
                status_code=400, detail=f"coluna ausente no arquivo: {erro.args[0]}"
            ) from erro

    def _montar_analise(extracao) -> dict:
        resultado = extracao
        if not resultado.conversas:
            raise HTTPException(
                status_code=400,
                detail=(
                    "nenhuma conversa valida no arquivo. Esperado um CSV/planilha com as "
                    "colunas conversa_id, canal, autor, texto, enviada_em, "
                    "escalou_para_humano, ou uma transcricao com linhas 'Autor: mensagem'."
                ),
            )

        # Referencia de frequencia: a fala de cliente de TODO o banco. O custo
        # e uma varredura por analise, aceitavel na ordem de grandeza deste
        # projeto e o ponto a trocar por um indice se deixar de ser.
        referencia = contar_palavras(
            [
                mensagem.texto
                for conversa, _score in banco.todas()
                for mensagem in conversa.mensagens_cliente
            ]
        )

        faixas = ctx.faixas_vigentes()
        analisadas = resultado.conversas[:TETO_CONVERSAS_ANALISE]
        analises = []
        for conversa in analisadas:
            analise = motor.analisar_conversa(conversa, referencia)

            # SEM HORARIO, SEM NOTA. Latencia e uma das dezesseis features do
            # fusor, com peso aprendido. Numa transcricao de Word ou PDF sem
            # relogio, esses campos sairiam zerados -- e zero nao e neutro: o
            # modelo aprendeu que resposta rapida acompanha cliente satisfeito,
            # entao a conversa entraria como se toda resposta tivesse sido
            # instantanea e a nota sairia melhor do que a verdade, sem erro
            # nenhum aparecer. A leitura por mensagem (classificacao, emocao,
            # ironia, peso de palavra) nao depende de tempo e continua valendo.
            score = analise["score"] if resultado.tem_tempo else None

            analises.append(
                {
                    "conversa": conversa.model_dump(mode="json"),
                    "score": score,
                    "nota": nota_0_10(score) if score is not None else None,
                    "categoria": ctx.categoria_de(score, faixas),
                    "mensagens": analise["mensagens"],
                    "contribuicoes": analise["contribuicoes"],
                    "importancias": analise["importancias"],
                    # Do motor, nao de constante: motor sem as cabecas de
                    # emocao/ironia devolve lista vazia, e a tela nao promete
                    # um painel que nao tem dado para preencher.
                    "sinais_fora_do_score": analise.get("sinais_fora_do_score", []),
                    "vocabulario": analise["vocabulario"],
                    **resumir(conversa),
                }
            )

        return {
            "analises": analises,
            # Relato do que ficou de FORA, na mesma linha do que a importacao
            # ja faz: silenciar o corte faria o operador achar que analisou o
            # arquivo inteiro.
            "conversas_no_arquivo": len(resultado.conversas),
            "conversas_analisadas": len(analisadas),
            "rejeitadas": resultado.rejeitadas[:LIMITE_MOTIVOS],
            "total_rejeitadas": len(resultado.rejeitadas),
            "referencia_conversas": len(banco.listar()),
            # Como o arquivo foi entendido, e o que a leitura teve que inferir.
            # A tela mostra isto SEMPRE, nao so quando da errado: analise cuja
            # procedencia nao aparece e numero sem lastro.
            "formato": resultado.formato,
            "tem_tempo": resultado.tem_tempo,
            "avisos": resultado.avisos,
        }

    app.include_router(saude.router)
    app.include_router(configuracoes.router)

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
