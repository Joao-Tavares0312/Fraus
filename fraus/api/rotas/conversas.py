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

from fastapi import APIRouter, Depends, HTTPException, Request

from fraus.api.caminhos import resolver_dentro_da_raiz
from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import PedidoImportacao, PedidoPreviaImportacao
from fraus.api.identidade import id_pelo_caminho, no_dia_ja_gravado
from fraus.api.rotas.analise import resumo_da_previa
from fraus.api.periodo import no_recorte, recorte_ou_400
from fraus.api.repontuacao import RepontuacaoEmAndamento
from fraus.contestacao import contestacao
from fraus.indicadores import nota_0_10
from fraus.ingest.arquivos import ArquivoIlegivelError, OpcoesDeLeitura, extrair
from fraus.ingest.mapeador import ORDENS_DE_DATA
from fraus.resumo import resumir

# Quantos motivos de rejeicao a resposta carrega. O relato existe para o
# operador entender o que ficou de fora, nao para devolver o CSV inteiro.
LIMITE_MOTIVOS = 20

# Teto do arquivo lido do disco para importar. A analise avulsa tem 200 kB
# porque roda oclusao por palavra; a importacao roda o motor uma vez por
# conversa, e um lote de verdade e maior. 20 MB cobre meses de export de
# atendimento e ainda impede que um arquivo errado na pasta seja lido inteiro
# para a memoria.
TETO_ARQUIVO_IMPORTACAO = 20 * 1024 * 1024

router = APIRouter()


def _ler_para_importar(
    ctx: Contexto,
    caminho_pedido: str,
    forcado: dict[str, str | None] | None = None,
    ordem_data: str | None = None,
):
    """Resolve o caminho dentro da raiz e le por `extrair` -- a mesma leitura da analise.

    O perfil salvo entra SEMPRE (`perfil_para`): e o unico jeito de uma coluna
    inferida chegar ao banco. Um segundo leitor so para a importacao aceitaria
    coisas diferentes das que a tela de Analisar mostra, e a previa mentiria.
    """
    caminho = resolver_dentro_da_raiz(ctx.raiz, caminho_pedido)
    if not caminho.is_file():
        raise HTTPException(status_code=400, detail=f"arquivo nao encontrado: {caminho}")
    if caminho.stat().st_size > TETO_ARQUIVO_IMPORTACAO:
        raise HTTPException(
            status_code=400,
            detail=(
                f"arquivo acima do teto de {TETO_ARQUIVO_IMPORTACAO // 1024 // 1024} MB "
                "para importacao. Divida o export por periodo."
            ),
        )
    if ordem_data is not None and ordem_data not in ORDENS_DE_DATA:
        raise HTTPException(
            status_code=400, detail=f"ordem_data precisa ser {' ou '.join(ORDENS_DE_DATA)}"
        )
    opcoes = OpcoesDeLeitura(
        forcado=forcado or None,
        ordem_data=ordem_data,
        perfil_para=ctx.banco.perfil_por_assinatura,
    )
    try:
        return caminho, extrair(caminho.name, caminho.read_bytes(), opcoes)
    except ArquivoIlegivelError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro
    except KeyError as erro:
        # Coluna estrutural ausente num formato reconhecido: defeito do
        # ARQUIVO, e o operador precisa saber QUAL coluna falta.
        raise HTTPException(
            status_code=400, detail=f"coluna ausente no arquivo: {erro.args[0]}"
        ) from erro


def _exige_confirmacao(extracao) -> bool:
    """Colunas inferidas pela heuristica, sem perfil que o analista confirmou."""
    return extracao.mapeamento is not None and extracao.perfil is None


@router.post("/conversas/importar/previa")
def previa_da_importacao(
    pedido: PedidoPreviaImportacao, ctx: Contexto = Depends(obter_contexto)
) -> dict:
    """Como o arquivo da pasta SERIA importado -- sem modelo e sem gravar nada.

    `exige_confirmacao` diz se a importacao vai recusar: colunas inferidas so
    entram no banco depois de viraram perfil. O ajuste em `mapeamento` serve
    para conferir na tela; ele nao grava perfil nem vale para a importacao.
    """
    _, extracao = _ler_para_importar(ctx, pedido.caminho, pedido.mapeamento, pedido.ordem_data)
    return {**resumo_da_previa(extracao), "exige_confirmacao": _exige_confirmacao(extracao)}


@router.post("/conversas/importar")
def importar(
    pedido: PedidoImportacao, ctx: Contexto = Depends(obter_contexto)
) -> dict:
    """Importa um arquivo da pasta, em qualquer formato que a leitura aceite.

    DUAS RECUSAS que a analise avulsa nao faz, porque aqui o resultado GRAVA
    e entra no NPS de todo mundo:

    - **colunas inferidas sem perfil confirmado -> 409.** Na tela de Analisar,
      inferencia vira aviso; no banco, viraria indicador contaminado que
      ninguem ve. O caminho e conferir na previa e salvar o perfil.
    - **arquivo sem horario -> 400.** Sem horario nao ha nota, e o banco nao
      tem como guardar "tem fala mas nao tem nota": `score: null` ja significa
      "sem fala do cliente" (invariante 2). Gravar assim mentiria.

    O corpo continua so com `caminho` (invariante 3): o mapeamento que vale
    para gravar e o do perfil, nunca um que chegue na requisicao.
    """
    caminho, resultado = _ler_para_importar(ctx, pedido.caminho)
    if not resultado.tem_tempo:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{caminho.name} não traz horário nas mensagens ({resultado.formato}). "
                "Sem horário não há latência nem nota, e o banco não guarda atendimento "
                "sem nota: use a tela de Analisar para ler este arquivo."
            ),
        )
    if _exige_confirmacao(resultado):
        raise HTTPException(
            status_code=409,
            detail=(
                f"as colunas de {caminho.name} foram inferidas e ainda não foram "
                "confirmadas. Confira na prévia da importação e salve o perfil de "
                "mapeamento — só coluna confirmada entra no banco."
            ),
        )

    conversas = resultado.conversas
    if resultado.id_do_arquivo:
        # O arquivo nao trouxe id: o leitor devolveu "conversa" (ou o nome do
        # arquivo), e gravar assim faria o proximo arquivo apagar este.
        identificador = id_pelo_caminho(caminho.relative_to(ctx.raiz.resolve()))
        gravada = None if resultado.tem_data else ctx.banco.buscar(identificador)
        conversas = [
            no_dia_ja_gravado(c, gravada[0] if gravada else None).model_copy(
                update={"id": identificador})
            for c in conversas
        ]

    faixas = ctx.faixas_vigentes()
    # UMA leitura de curadoria por importacao, e e a MESMA que grava a versao:
    # reler abriria janela para a conversa ser pontuada com um lexico e marcada
    # com a versao de outro -- o defeito exato que a versao existe para impedir.
    curadoria = ctx.curadoria_vigente()
    regua = ctx.regua_vigente()
    for conversa in conversas:
        score = ctx.motor.pontuar_conversa(conversa, curadoria)
        # A coluna `categoria` e o retrato do instante da importacao; quem
        # le nao a consome (ver `categoria_de`), mas gravar com a faixa
        # vigente evita que o banco inspecionado a mao conte outra historia.
        ctx.banco.salvar(
            conversa,
            score,
            ctx.categoria_de(score, faixas),
            lexico_versao=curadoria.versao,
            regua=regua,
        )

    # "Motivo registrado" (spec 9) tem que CHEGAR a alguem: a contagem
    # sozinha nao diz o que ficou de fora.
    motivos = resultado.rejeitadas[:LIMITE_MOTIVOS]

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


@router.post("/conversas/repontuar", status_code=202)
def repontuar(request: Request, ctx: Contexto = Depends(obter_contexto)) -> dict:
    """Repontua o banco inteiro com o lexico vigente -- em segundo plano.

    O que ela conserta: o `score` e gravado na importacao, entao curar uma
    palavra (ou trocar o fusor) nao mexe no que ja existe -- e um banco com
    conversas pontuadas antes e depois soma duas reguas no mesmo agregado. Esta
    rota e o unico jeito de zerar essa divergencia sem reimportar.

    Responde 202 com o `total` e sai; o progresso e `GET` nesta mesma rota. Ver
    `fraus/api/repontuacao.py` para o porque de nao ser mais sincrona, e para o
    que acontece se a API reiniciar no meio. 409 se ja houver uma rodando.
    """
    try:
        return request.app.state.repontuacao.iniciar(ctx)
    except RepontuacaoEmAndamento:
        raise HTTPException(
            status_code=409,
            detail="ja ha uma repontuacao em andamento; acompanhe por GET /conversas/repontuar",
        )


@router.get("/conversas/repontuar")
def progresso_da_repontuacao(request: Request) -> dict:
    """Estado da ultima repontuacao deste processo. 404 se nunca houve uma."""
    ctx = request.app.state.contexto
    estado = request.app.state.repontuacao.estado(ctx.banco)
    if estado is None:
        raise HTTPException(status_code=404, detail="nenhuma repontuacao desde que a API subiu")
    return estado


@router.get("/conversas")
def listar(
    de: str | None = None,
    ate: str | None = None,
    limite: int | None = None,
    deslocamento: int = 0,
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
    if limite is not None and not 1 <= limite <= 500:
        raise HTTPException(status_code=400, detail="limite precisa estar entre 1 e 500")
    if deslocamento < 0:
        raise HTTPException(status_code=400, detail="deslocamento nao pode ser negativo")
    # A `nota` sai daqui derivada no SERVIDOR, junto com score e categoria:
    # e a mesma conversao de `/conversas/{id}`, e a dashboard so a exibe.
    faixas = ctx.faixas_vigentes()
    return [
        _com_derivacoes(linha["score"], ctx.categoria_de(linha["score"], faixas), linha, conversa)
        for linha, conversa in ctx.banco.listar_com_conversa(
            de=inicio.isoformat() if inicio else None,
            ate=fim.isoformat() if fim else None,
            limite=limite,
            deslocamento=deslocamento,
        )
    ]


def _com_derivacoes(score, categoria, base: dict, conversa) -> dict:
    """A ficha derivada NA LEITURA, identica para a lista e para o detalhe.

    As duas rotas passam por aqui de proposito: a lista e o detalhe nao podem
    derivar nota, categoria ou contestacao por caminhos diferentes -- e a mesma
    razao pela qual `resumir` ja era compartilhada pelas duas.

    A `contestacao` sai do `score` gravado e da `latencia_mediana_s` que
    `resumir` acabou de derivar dos timestamps. Nenhum dos dois custa uma
    chamada de modelo, e nenhum dos dois esta persistido como veredito -- por
    isso a marca vale retroativamente para o que ja esta no banco.
    """
    ficha = resumir(conversa)
    return {
        **base,
        "categoria": categoria,
        "nota": nota_0_10(score) if score is not None else None,
        **ficha,
        "contestacao": contestacao(score, ficha["latencia_mediana_s"]),
        "motivo_sem_sinal": conversa.motivo_sem_sinal,
    }


# AS DUAS ROTAS POR ID USAM `:path`, E A ORDEM DELAS E CONTRATO (02/10/2026).
#
# O id de uma conversa ingerida e `fonte:<n>:<id externo>`, e o id externo e
# do sistema de origem: protocolo com barra (`2026/000123`) e comum. Com
# `{conversa_id}` simples a barra nao casava, e a conversa aparecia na lista
# sem detalhe nem atribuicao -- 404 nas duas.
#
# `:path` casa QUALQUER resto do caminho, entao:
#
# - `/atribuicao` vem ANTES do detalhe. Na ordem inversa o detalhe engoliria
#   `c1/atribuicao` como se fosse um id.
# - as irmas de caminho fixo (`/conversas/repontuar`) continuam declaradas
#   ACIMA destas duas. Rota GET nova sob `/conversas/` entra la em cima tambem.
#
# O que sobra e declarado: o DETALHE de um id externo que termine em
# `/atribuicao` cai na rota de atribuicao.
@router.get("/conversas/{conversa_id:path}/atribuicao")
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
    versoes = ctx.banco.regua_da_conversa(conversa_id)
    vigente = (ctx.curadoria_vigente().versao, ctx.regua_vigente())
    if versoes != vigente:
        raise HTTPException(
            status_code=409,
            detail=(
                "a conversa foi pontuada com outra versao do lexico ou do modelo; "
                "repontue antes de gerar uma explicacao, para nao explicar uma nota "
                "historica com sinais atuais"
            ),
        )
    atribuicao = ctx.motor.atribuir_conversa(
        conversa, curadoria=ctx.curadoria_vigente()
    )
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


@router.get("/conversas/{conversa_id:path}")
def detalhar(
    conversa_id: str, ctx: Contexto = Depends(obter_contexto)
) -> dict:
    achado = ctx.banco.buscar(conversa_id)
    if achado is None:
        raise HTTPException(status_code=404, detail="conversa nao encontrada")
    conversa, score, _categoria_gravada = achado
    # A MESMA ficha derivada de `/conversas`, pela mesma funcao. A lista e o
    # detalhe nao podem calcular tempo de resposta -- nem contestacao -- por
    # caminhos diferentes: seria a divergencia que a nota derivada no servidor
    # ja existe para evitar, repetida na coluna do lado.
    return _com_derivacoes(
        score,
        ctx.categoria_de(score, ctx.faixas_vigentes()),
        {**conversa.model_dump(mode="json"), "score": score},
        conversa,
    )
