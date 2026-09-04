"""/conversas -- os atendimentos: como entram, como saem listados e detalhados.

A importacao le arquivo de DENTRO da raiz configurada e recusa qualquer
escape. Score e categoria sao derivados no servidor em toda entrada, e a
categoria e derivada de novo na LEITURA, da faixa vigente -- e o que faz a
lista e o detalhe nunca discordarem depois de um PUT em /configuracoes.

A lista carrega a ficha operacional de cada atendimento (contagem por autor,
tempo de resposta do bot e do humano separados, duracao, desfecho) de
proposito: a tela precisa disso por linha, e busca-la uma a uma era um N+1
contra a propria API.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from fraus.api.caminhos import resolver_dentro_da_raiz
from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import PedidoImportacao
from fraus.api.periodo import no_recorte, recorte_ou_400
from fraus.indicadores import nota_0_10
from fraus.ingest.csv_driver import carregar_csv
from fraus.resumo import resumir

# Quantos motivos de rejeicao a resposta carrega. O relato existe para o
# operador entender o que ficou de fora, nao para devolver o CSV inteiro.
LIMITE_MOTIVOS = 20

router = APIRouter()


@router.post("/conversas/importar")
def importar(
    pedido: PedidoImportacao, ctx: Contexto = Depends(obter_contexto)
) -> dict:
    caminho = resolver_dentro_da_raiz(ctx.raiz, pedido.caminho)
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
    # UMA leitura de curadoria por importacao, e e a MESMA que grava a versao:
    # reler abriria janela para a conversa ser pontuada com um lexico e marcada
    # com a versao de outro -- o defeito exato que a versao existe para impedir.
    curadoria = ctx.curadoria_vigente()
    for conversa in resultado.conversas:
        score = ctx.motor.pontuar_conversa(conversa, curadoria)
        # A coluna `categoria` e o retrato do instante da importacao; quem
        # le nao a consome (ver `categoria_de`), mas gravar com a faixa
        # vigente evita que o banco inspecionado a mao conte outra historia.
        ctx.banco.salvar(
            conversa,
            score,
            ctx.categoria_de(score, faixas),
            lexico_versao=curadoria.versao,
        )

    # "Motivo registrado" (spec 9) tem que CHEGAR a alguem: a contagem
    # sozinha nao diz o que ficou de fora.
    motivos = [linha.model_dump() for linha in resultado.rejeitadas[:LIMITE_MOTIVOS]]

    # O historico guarda o MESMO que a resposta devolve. Sem ele,
    # "importado com sucesso" e alegacao sem lastro: some da tela no
    # instante seguinte e ninguem consegue mais dizer o que ficou de fora.
    ctx.banco.registrar_importacao(
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


@router.post("/conversas/repontuar")
def repontuar(ctx: Contexto = Depends(obter_contexto)) -> dict:
    """Repontua o banco inteiro com o lexico vigente.

    O que ela conserta: o `score` e gravado na importacao, entao curar uma
    palavra nao mexe no que ja existe -- e um banco com conversas pontuadas
    antes e depois soma duas reguas no mesmo agregado. Esta rota e o unico jeito
    de zerar essa divergencia sem reimportar.

    UMA leitura de faixa e UMA de curadoria para o lote inteiro, fora do laco:
    ler por conversa abriria janela para o lote comecar com uma configuracao e
    terminar com outra -- que e a regua misturada de novo, agora dentro da rota
    que existe para acabar com ela.

    LIMITACAO DECLARADA: repontuar roda os TRES BERTimbau de novo por conversa.
    O vetor e de 38 features e o fusor exige as 38 -- nao existe recalcular so
    as tres lexicas e as cinco de emoji sem o resto. Em dezenas de atendimentos
    sao segundos; em milhares vira trabalho de fila, e a fila nao existe aqui.
    A rota e SINCRONA de proposito: uma fila que ninguem observa seria pior que
    uma espera que se ve.
    """
    curadoria = ctx.curadoria_vigente()
    faixas = ctx.faixas_vigentes()
    quantas = 0
    for conversa, _ in ctx.banco.todas():
        score = ctx.motor.pontuar_conversa(conversa, curadoria)
        ctx.banco.salvar(
            conversa,
            score,
            ctx.categoria_de(score, faixas),
            lexico_versao=curadoria.versao,
        )
        quantas += 1
    return {"repontuadas": quantas}


@router.get("/conversas")
def listar(
    de: str | None = None,
    ate: str | None = None,
    ctx: Contexto = Depends(obter_contexto),
) -> list[dict]:
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
        for linha, conversa in ctx.banco.listar_com_conversa()
        if no_recorte(conversa.iniciada_em, inicio, fim)
    ]


@router.get("/conversas/{conversa_id}")
def detalhar(
    conversa_id: str, ctx: Contexto = Depends(obter_contexto)
) -> dict:
    achado = ctx.banco.buscar(conversa_id)
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


@router.get("/conversas/{conversa_id}/atribuicao")
def atribuir(
    conversa_id: str, ctx: Contexto = Depends(obter_contexto)
) -> dict:
    """Quais falas puxaram a nota para baixo e quais puxaram para cima.

    Score, categoria e nota saem do que o SERVIDOR ja gravou na
    importacao -- nao sao repontuados aqui. Repontuar criaria uma segunda
    fonte de verdade que poderia divergir de `/conversas/{id}` se o fusor
    em disco mudasse entre a importacao e a leitura.
    """
    achado = ctx.banco.buscar(conversa_id)
    if achado is None:
        raise HTTPException(status_code=404, detail="conversa nao encontrada")
    conversa, score, _categoria_gravada = achado
    atribuicao = ctx.motor.atribuir_conversa(conversa)
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
