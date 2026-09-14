"""/analisar -- o que o modelo acha DESTE arquivo, sem gravar nada.

Nada daqui entra no banco: nem a conversa, nem o score, nem o arquivo. E o que
separa esta rota da importacao -- aqui se pergunta "o que o modelo acha
disto?", nao "passe a considerar isto nos indicadores". Um arquivo analisado
nao muda o NPS de ninguem.

Sao duas portas para a mesma analise: `/analisar` recebe o conteudo no corpo
JSON, e `/analisar/arquivo` recebe multipart -- porque formato binario
(planilha, PDF) nao cabe em JSON, e obrigar base64 inflaria o corpo em um
terco por nada.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.esquemas import PedidoAnalise
from fraus.indicadores import nota_0_10
from fraus.ingest.arquivos import ArquivoIlegivelError, extrair
from fraus.resumo import resumir
from fraus.sinais.palavras import contar_palavras

# Tetos de /analisar. A rota roda BERTimbau uma vez por palavra de cliente
# (oclusao), entao o custo cresce com o tamanho do arquivo -- sem teto, um CSV
# de lote inteiro penduraria a requisicao em CPU. Os dois limites recusam alto
# e explicam, em vez de aceitar e demorar minutos sem sinal de vida.
TETO_ARQUIVO_ANALISE = 200_000
TETO_CONVERSAS_ANALISE = 10

# Teto de MENSAGENS DE CLIENTE por analise -- o unico dos tres que limita o que
# de fato custa.
#
# POR QUE ELE PRECISOU EXISTIR. Os outros dois tetos medem grandezas que nao
# governam o tempo: 200 kB e o tamanho do arquivo (um xlsx comprime, e 125 kB
# ja carregam milhares de mensagens) e 10 e o numero de conversas (que podem ter
# 5 ou 500 mensagens cada). Medido em producao: um arquivo dentro dos dois tetos
# levou 314 SEGUNDOS -- 10 conversas, 600 mensagens, 2964 palavras de cliente a
# ~106 ms cada. O proxy da dashboard desiste aos 60 s, entao a tela mostrava
# "API nao respondeu" para uma API que estava viva e trabalhando.
#
# 40 mensagens cabem com folga nos 60 s do proxy pela medicao acima. O numero e
# do PRODUTO, nao da maquina: esta tela examina UM atendimento, e o texto dela
# ja manda quem tem lote usar a importacao.
TETO_MENSAGENS_CLIENTE_ANALISE = 40

# Quanto se le por vez ao medir um upload. Grande o bastante para nao
# multiplicar chamadas num arquivo legitimo, pequeno o bastante para o
# excedente que chega a entrar na memoria nunca passar disso.
PEDACO_DE_LEITURA = 64 * 1024

# Quantos motivos de rejeicao a resposta carrega. O relato existe para o
# operador entender o que ficou de fora, nao para devolver o arquivo inteiro.
LIMITE_MOTIVOS = 20

router = APIRouter()


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
    """Mesma analise, aceitando csv, xlsx, json, txt, docx ou pdf.

    Existe separada de `/analisar` porque formato binario nao cabe em JSON:
    planilha e PDF nao sao texto, e obrigar o cliente a codificar em base64
    inflaria o corpo em um terco por nada.

    Nada daqui e GRAVADO: nem a conversa, nem o score, nem o arquivo. Nao ha
    `open()` de escrita em lugar nenhum deste caminho.

    Nao confundir com "nenhum byte toca o disco", que e o que esta docstring
    prometia e nao era verdade: o `UploadFile` do Starlette escorre para um
    arquivo temporario acima de ~1 MB, e isso acontece no parse do multipart,
    ANTES deste corpo rodar. Quem impede um upload absurdo de chegar ate la e
    o teto de `Content-Length` em `fraus.api.limites`; o teto daqui recusa o
    que passou por ele, e o temporario e descartado pelo Starlette ao fim da
    requisicao.
    """
    dados = await ler_ate_o_teto(arquivo, TETO_ARQUIVO_ANALISE)
    if not dados:
        raise HTTPException(status_code=400, detail="arquivo vazio")

    # O TRABALHO PESADO SAI DO EVENT LOOP, e este e o ponto todo desta rota.
    #
    # Esta funcao e `async` por necessidade -- ler o upload exige `await`. Mas
    # `extrair` parseia planilha/PDF e `montar_analise` roda BERTimbau uma vez
    # por palavra do cliente, e as duas sao CPU pura e sincrona. Chamadas
    # DIRETO daqui, elas rodam DENTRO do event loop: enquanto duram, o uvicorn
    # nao atende mais nenhuma requisicao -- nem `/saude`.
    #
    # O efeito nao e "fica um pouco lento": a dashboard pergunta `/saude` de
    # tempos em tempos, aquela pergunta fica presa na fila, e a tela pinta
    # "API fora do ar" no meio de uma analise que esta indo bem. Um xlsx de
    # verdade congelava a instalacao inteira por minutos, e o proxy do Next
    # derrubava a conexao por tempo esgotado -- com a API viva o tempo todo.
    #
    # `run_in_threadpool` e o que a rota irmã `/analisar` ja ganha de graca por
    # ser `def` comum: o FastAPI manda toda rota sincrona para o threadpool
    # justamente por isso. A assimetria entre as duas era acidental, nao uma
    # decisao -- e so uma delas pagava o preco.
    return await run_in_threadpool(
        _extrair_e_analisar, ctx, arquivo.filename or "arquivo", dados
    )


def _extrair_e_analisar(ctx: Contexto, nome: str, dados: bytes) -> dict:
    """As duas etapas de CPU, juntas, para uma ida so ao threadpool.

    Separadas seriam dois saltos de contexto sem ganho nenhum: nada entre elas
    precisa do event loop de volta.
    """
    return montar_analise(ctx, extrair_ou_400(nome, dados))


async def ler_ate_o_teto(arquivo: UploadFile, teto: int) -> bytes:
    """Le o upload em pedacos e para no primeiro byte acima do teto.

    `await arquivo.read()` sem argumento materializa o upload INTEIRO na
    memoria antes de qualquer conferencia -- o teto era conferido na linha
    seguinte, ja tendo pago o custo que ele existia para evitar. Lendo em
    pedacos, o que entra na memoria nunca passa do teto mais um pedaco.

    A mensagem NAO afirma o tamanho do arquivo, e a diferenca importa: a
    leitura parou antes do fim, entao esse numero nao existe aqui. Dizer "seu
    arquivo tem N kB" a partir do que se leu ate desistir seria inventar um
    dado -- exatamente o tipo de numero com confianca sem lastro que este
    projeto existe para nao produzir.
    """
    pedacos: list[bytes] = []
    lidos = 0
    while pedaco := await arquivo.read(PEDACO_DE_LEITURA):
        lidos += len(pedaco)
        if lidos > teto:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"arquivo acima do limite de {teto // 1024} kB. Esta tela "
                    "examina um atendimento por vez; para um lote, use a "
                    "importacao."
                ),
            )
        pedacos.append(pedaco)
    return b"".join(pedacos)


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


def cabem_no_orcamento(conversas: list) -> tuple[list, int]:
    """Quantas conversas cabem no teto de mensagens, e quantas mensagens sao.

    O CORTE E POR CONVERSA INTEIRA, e essa e a decisao que governa a funcao.
    Cortar mensagens no MEIO de uma conversa caberia no mesmo orcamento e
    produziria um score calculado sobre meia conversa -- exibido, na tela, com
    a mesma cara de um score completo. Numero errado apresentado como certo e
    pior do que numero nenhum, entao o que entra, entra inteiro.

    So a fala do CLIENTE conta: e ela que paga a oclusao (uma passada de
    BERTimbau por palavra, ver `fraus.sinais.palavras`). Mensagem de bot e
    lida uma vez e nao entra no orcamento.

    A primeira conversa entra SEMPRE, mesmo estourando o teto. Devolver lista
    vazia porque o unico atendimento do arquivo e grande demais transformaria
    "e grande" em "nao da para ver nada", e quem chama nao teria como saber a
    diferenca. Cabe a rota decidir o que fazer com o estouro -- aqui so se
    mede.
    """
    escolhidas: list = []
    total = 0
    for conversa in conversas:
        quantas = len(conversa.mensagens_cliente)
        if escolhidas and total + quantas > TETO_MENSAGENS_CLIENTE_ANALISE:
            break
        escolhidas.append(conversa)
        total += quantas
    return escolhidas, total


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
    analisadas, mensagens_cliente = cabem_no_orcamento(
        resultado.conversas[:TETO_CONVERSAS_ANALISE]
    )

    # UM atendimento sozinho acima do teto e o unico caso que o corte por
    # conversa inteira nao resolve -- nao ha o que deixar de fora sem deixar
    # tudo de fora. A recusa e explicita e diz OS DOIS numeros, porque
    # "arquivo grande demais" sem quantidade nao diz o que cortar.
    #
    # Ela e um 400 e nao uma analise parcial: parcial exigiria cortar dentro da
    # conversa, que e exatamente o que `cabem_no_orcamento` existe para nao
    # fazer. E e um 400 e nao um 502 por tempo esgotado -- que era o que
    # acontecia antes, e culpava a rede por uma decisao de produto.
    if mensagens_cliente > TETO_MENSAGENS_CLIENTE_ANALISE:
        raise HTTPException(
            status_code=400,
            detail=(
                f"este atendimento tem {mensagens_cliente} mensagens do cliente, "
                f"acima do limite de {TETO_MENSAGENS_CLIENTE_ANALISE} desta tela. "
                "Cada palavra do cliente custa uma passada do modelo, e um "
                "atendimento deste tamanho levaria minutos. Para um volume "
                "assim, use a importacao."
            ),
        )
    analises = []
    for conversa in analisadas:
        analise = ctx.motor.analisar_conversa(conversa, referencia)

        # SEM HORARIO, SEM NOTA. Latencia e uma das 38 features do
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
        # Quantas mensagens de cliente entraram, e qual era o orcamento. Os
        # DOIS numeros, e nao so um aviso de "cortei": com eles a tela explica
        # por que quatro conversas de um arquivo de nove ficaram de fora, e a
        # pessoa entende que o corte foi por TAMANHO e nao por defeito no
        # arquivo dela. `conversas_analisadas` menor que `conversas_no_arquivo`
        # ja aparecia; o que faltava era o porque.
        "mensagens_cliente_analisadas": mensagens_cliente,
        "teto_mensagens_cliente": TETO_MENSAGENS_CLIENTE_ANALISE,
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
