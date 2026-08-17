"""/modelo e /analisar -- o que o modelo pensa, e o que ele pensa DESTE arquivo.

`/modelo` e a ficha do que esta carregado: pesos globais, metricas de treino
de cada cabeca, faixas vigentes e lexicon de emoji. Metrica ausente vem
`null`, nunca um numero inventado.

`/analisar` examina um arquivo SEM gravar nada -- nem a conversa, nem o
score, nem o arquivo. E o que a separa da importacao: aqui se pergunta "o que
o modelo acha disto?", nao "passe a considerar isto nos indicadores".
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from fraus.api.caminhos import (CAMINHO_METRICAS, CAMINHO_METRICAS_EMOCAO,
                                CAMINHO_METRICAS_IRONIA, metricas_de)
from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import PedidoAnalise, PedidoSimulacao
from fraus.indicadores import nota_0_10
from fraus.ingest.arquivos import ArquivoIlegivelError, extrair
from fraus.resumo import resumir
from fraus.sinais.emoji import linhas_lexicon, score_do_emoji
from fraus.sinais.emocao import NOMES_EMOCOES
from fraus.sinais.palavras import contar_palavras

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
LIMITE_LEXICON_PADRAO = 50

# Quantos motivos de rejeicao a resposta carrega. O relato existe para o
# operador entender o que ficou de fora, nao para devolver o arquivo inteiro.
LIMITE_MOTIVOS = 20

router = APIRouter()


@router.get("/modelo")
def modelo(ctx: Contexto = Depends(obter_contexto)) -> dict:
    """Ficha do modelo: pesos globais, metricas de treino, faixas e lexicon.

    `metricas` e null quando o notebook 01 ainda nao exportou o arquivo --
    nunca um valor inventado. As faixas de NPS saem da configuracao
    vigente, a MESMA fonte que alimenta a categoria de cada atendimento --
    faixa duplicada em dois lugares ja foi defeito deste projeto uma vez.
    """
    metricas = metricas_de(CAMINHO_METRICAS)
    return {
        "importancias": ctx.motor.importancias(),
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


@router.get("/modelo/lexicon")
def lexicon(
    busca: str | None = None, limite: int = LIMITE_LEXICON_PADRAO, deslocamento: int = 0,
    ctx: Contexto = Depends(obter_contexto),
) -> dict:
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


@router.post("/modelo/simular")
def simular(
    pedido: PedidoSimulacao, ctx: Contexto = Depends(obter_contexto)
) -> dict:
    """Roda o classificador numa frase avulsa -- nao persiste nada no banco."""
    texto = pedido.texto
    if not texto.strip():
        raise HTTPException(status_code=400, detail="texto vazio")
    if len(texto) > TETO_TEXTO_SIMULACAO:
        raise HTTPException(
            status_code=400,
            detail=f"texto acima do limite de {TETO_TEXTO_SIMULACAO} caracteres",
        )

    resultado = ctx.motor.simular_texto(texto)
    return {
        "texto": texto,
        "prob_insatisfeito": resultado["prob_insatisfeito"],
        "prob_neutro": resultado["prob_neutro"],
        "prob_satisfeito": resultado["prob_satisfeito"],
        "emojis": resultado["emojis"],
        "emocao": resultado.get("emocao"),
        "prob_ironia": resultado.get("prob_ironia"),
    }


@router.post("/analisar")
def analisar(
    pedido: PedidoAnalise, ctx: Contexto = Depends(obter_contexto)
) -> dict:
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

    extracao = extrair_ou_400(pedido.nome or "conversa.csv", pedido.csv.encode("utf-8"))
    return montar_analise(ctx, extracao)


@router.post("/analisar/arquivo")
async def analisar_arquivo(
    arquivo: UploadFile = File(...), ctx: Contexto = Depends(obter_contexto)
) -> dict:
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

    extracao = extrair_ou_400(arquivo.filename or "arquivo", dados)
    return montar_analise(ctx, extracao)


def extrair_ou_400(nome: str, dados: bytes):
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


def montar_analise(ctx: Contexto, extracao) -> dict:
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
            for conversa, _score in ctx.banco.todas()
            for mensagem in conversa.mensagens_cliente
        ]
    )

    faixas = ctx.faixas_vigentes()
    analisadas = resultado.conversas[:TETO_CONVERSAS_ANALISE]
    analises = []
    for conversa in analisadas:
        analise = ctx.motor.analisar_conversa(conversa, referencia)

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
        "referencia_conversas": len(ctx.banco.listar()),
        # Como o arquivo foi entendido, e o que a leitura teve que inferir.
        # A tela mostra isto SEMPRE, nao so quando da errado: analise cuja
        # procedencia nao aparece e numero sem lastro.
        "formato": resultado.formato,
        "tem_tempo": resultado.tem_tempo,
        "avisos": resultado.avisos,
    }
