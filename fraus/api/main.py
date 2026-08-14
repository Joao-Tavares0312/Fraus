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

import hmac
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from fraus import acesso
from fraus import credencial
from fraus.configuracao import PADROES as CONFIGURACAO_DE_FABRICA
from fraus.configuracao import carregar as carregar_configuracao
from fraus.configuracao import faixas_de
from fraus.configuracao import salvar as salvar_configuracao
from fraus.db import Banco
from fraus.modelos import Conversa, Mensagem
from fraus.fusor import Fusor, montar_features
from fraus.indicadores import (calcular_csat, calcular_nps, categoria_nps,
                               containment_rate, nota_0_10, serie_diaria)
from fraus.ingest.arquivos import ArquivoIlegivelError, extrair
from fraus.ingest.csv_driver import carregar_csv
from fraus.resumo import resumir
from fraus.sinais.palavras import (contar_palavras, pesos_das_palavras,
                                   vocabulario)
from fraus.sinais.emocao import (NOMES_EMOCOES, ClassificadorEmocao,
                                 desprezo_derivado)
from fraus.sinais.emoji import (emojis_com_posicao, linhas_lexicon,
                                score_do_emoji)
from fraus.sinais.ironia import IRONICO, ClassificadorIronia
from fraus.sinais.texto import (INSATISFEITO, NEUTRO, SATISFEITO,
                                ClassificadorTexto)

CAMINHO_MODELO_TEXTO = Path(os.environ.get("FRAUS_CAMINHO_MODELO_TEXTO", "modelos/bertimbau-satisfacao"))
CAMINHO_MODELO_EMOCAO = Path(os.environ.get("FRAUS_CAMINHO_MODELO_EMOCAO", "modelos/bertimbau-emocao"))
CAMINHO_MODELO_IRONIA = Path(os.environ.get("FRAUS_CAMINHO_MODELO_IRONIA", "modelos/bertimbau-ironia"))
CAMINHO_FUSOR = Path(os.environ.get("FRAUS_CAMINHO_FUSOR", "modelos/fusor.joblib"))
CAMINHO_BANCO = Path(os.environ.get("FRAUS_CAMINHO_BANCO", "fraus.db"))

# Exportado pelo notebook 01 (acuracia, F1-macro do BERTimbau). Ausente e
# esperado antes do treino: `/modelo` devolve `metricas: null`, nunca inventa.
# O padrao aponta para dentro da pasta do modelo porque e onde o notebook 01
# de fato grava -- metrica ao lado do peso que ela mediu, nao solta na raiz.
CAMINHO_METRICAS = Path(
    os.environ.get("FRAUS_CAMINHO_METRICAS", "modelos/bertimbau-satisfacao/metricas.json")
)
CAMINHO_METRICAS_EMOCAO = Path(
    os.environ.get("FRAUS_CAMINHO_METRICAS_EMOCAO", "modelos/metricas_emocao.json")
)
CAMINHO_METRICAS_IRONIA = Path(
    os.environ.get("FRAUS_CAMINHO_METRICAS_IRONIA", "modelos/metricas_ironia.json")
)

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

# Raiz unica de onde a importacao pode ler. O endpoint nao tem autenticacao
# (uso local, ver README) -- entao ele nao pode aceitar caminho arbitrario do
# sistema de arquivos: tudo que entra e resolvido DENTRO desta pasta.
RAIZ_IMPORTACAO = Path(os.environ.get("FRAUS_RAIZ_IMPORTACAO", "dados_brutos"))

# Quantos motivos de rejeicao a resposta carrega. O relato existe para o
# operador entender o que ficou de fora, nao para devolver o CSV inteiro.
LIMITE_MOTIVOS = 20


# Tipos de fonte que a ingestao de fato sabe tratar hoje. Aceitar um tipo que
# nenhum adapter le seria cadastrar uma promessa: a tela mostraria uma fonte
# que nunca traz conversa nenhuma.
TIPOS_DE_FONTE = ("csv", "webhook")


class PedidoFonte(BaseModel):
    nome: str
    canal: str
    tipo: str
    variavel_segredo: str | None = None  # NOME da variavel, nunca o segredo


class PedidoAjusteFonte(BaseModel):
    nome: str | None = None
    ativa: bool | None = None


class PedidoImportacao(BaseModel):
    caminho: str  # unico campo aceito: veredito nunca vem do cliente


class PedidoSimulacao(BaseModel):
    texto: str  # unico campo aceito: probabilidade e derivada no servidor


class PedidoAnalise(BaseModel):
    csv: str  # conteudo do arquivo; veredito continua sendo derivado aqui
    nome: str | None = None  # so para escolher o leitor pela extensao


class PedidoChaveAcesso(BaseModel):
    nome: str = Field(min_length=1)


class PedidoIngestao(BaseModel):
    """Atendimento vindo de um sistema externo.

    NAO ha campo de canal, score, nota nem categoria. O canal vem da FONTE
    cadastrada e o veredito e derivado no servidor -- quem manda o dado nunca
    escolhe como ele e contabilizado.
    """

    id: str
    mensagens: list[Mensagem] = Field(min_length=1)
    encerrada_em: datetime | None = None
    escalou_para_humano: bool = False


class Motor:
    """Amarra classificador de texto e fusor num unico ponto de pontuacao.

    Emocao e ironia entram como LEITURA, nunca como julgamento. O fusor foi
    treinado com dezesseis features -- texto, emoji e tempo -- e nenhuma delas
    vem dessas duas cabecas (confira em `fraus.fusor.NOMES_FEATURES`). Elas
    descrevem a fala do cliente sem mover a nota um centesimo.

    Isso PRECISA aparecer em toda resposta que carrega os dois numeros lado a
    lado. Uma tela que mostra "ironia 0,99" encostada num score baixo convida a
    conclusao de que a ironia derrubou a nota, e nao derrubou: o que derrubou
    esta em `contribuicoes`, que so fala das dezesseis. Ligar emocao e ironia ao
    score exigiria retreinar o fusor com elas dentro.

    Os dois classificadores sao OPCIONAIS. Sem eles a API continua pontuando
    igual, porque nada do score depende deles -- os campos saem `None`, que e a
    diferenca honesta entre "o modelo nao rodou" e "o modelo rodou e deu zero".
    """

    def __init__(
        self,
        classificador: ClassificadorTexto,
        fusor: Fusor,
        emocao: ClassificadorEmocao | None = None,
        ironia: ClassificadorIronia | None = None,
    ) -> None:
        self._classificador = classificador
        self._fusor = fusor
        self._emocao = emocao
        self._ironia = ironia

    def _emocao_de(self, textos: list[str]) -> list[dict] | None:
        """Sete probabilidades mais o desprezo da diade, por texto. None sem modelo."""
        if self._emocao is None or not textos:
            return None
        previsoes = self._emocao.prever_mensagens(textos)
        return [
            {
                **{nome: float(p[i]) for i, nome in enumerate(NOMES_EMOCOES)},
                # Oitava emocao de Ekman, derivada da diade raiva+nojo
                # (Plutchik 1980) porque nenhum corpus PT-BR a anota.
                "desprezo": desprezo_derivado(
                    p[NOMES_EMOCOES.index("raiva")], p[NOMES_EMOCOES.index("nojo")]
                ),
            }
            for p in previsoes
        ]

    def _ironia_de(self, textos: list[str]) -> list[float] | None:
        """Probabilidade de ironia por texto. None sem modelo carregado."""
        if self._ironia is None or not textos:
            return None
        return [float(p[IRONICO]) for p in self._ironia.prever_mensagens(textos)]

    def pontuar_conversa(self, conversa) -> float | None:
        if not conversa.tem_sinal_cliente:
            return None  # ausencia de dado nao e insatisfacao
        return self._fusor.pontuar(montar_features(conversa, self._classificador))

    def atribuir_conversa(self, conversa) -> dict:
        """Quebra a nota por mensagem: quem falou o que, e com que probabilidade.

        SO a fala do cliente recebe probabilidade -- bot e humano vem com os
        tres campos nulos, porque o classificador foi treinado em texto de
        cliente e pontuar a fala do bot seria numero inventado. A transcricao
        inteira volta assim mesmo: a interface precisa dela para alinhar o
        `indice` com `/conversas/{id}` sem recontar nada.

        A ordem das classes e a de `fraus.sinais.texto`: 0 insatisfeito,
        1 neutro, 2 satisfeito.

        O classificador e o fusor NAO vazam daqui: o que sai e o resultado ja
        montado, para a rota nao ter que saber que existe modelo por baixo.

        `contribuicoes` e o quanto cada feature pesou NESTA conversa (sinal:
        positivo empurra para satisfeito, negativo para insatisfeito) --
        diferente de `importancias`, que e o peso GLOBAL do modelo. Sem fala
        do cliente nao ha score, entao tambem nao ha contribuicao: `None`.
        """
        indices_do_cliente = [
            indice
            for indice, mensagem in enumerate(conversa.mensagens)
            if mensagem.autor == "cliente"
        ]
        textos_do_cliente = [
            conversa.mensagens[indice].texto for indice in indices_do_cliente
        ]
        probabilidades = self._classificador.prever_mensagens(textos_do_cliente)
        por_indice = dict(zip(indices_do_cliente, probabilidades))

        # Mesma regra das probabilidades de satisfacao: so a fala do CLIENTE.
        # As tres cabecas foram fine-tunadas em texto de cliente, e rodar
        # qualquer uma na fala do bot devolveria numero sem lastro.
        emocoes = self._emocao_de(textos_do_cliente)
        ironias = self._ironia_de(textos_do_cliente)
        emocao_por_indice = dict(zip(indices_do_cliente, emocoes or []))
        ironia_por_indice = dict(zip(indices_do_cliente, ironias or []))

        mensagens = []
        for indice, mensagem in enumerate(conversa.mensagens):
            previsao = por_indice.get(indice)
            mensagens.append(
                {
                    "indice": indice,
                    "autor": mensagem.autor,
                    "texto": mensagem.texto,
                    "prob_insatisfeito": (
                        float(previsao[INSATISFEITO]) if previsao else None
                    ),
                    "prob_neutro": float(previsao[NEUTRO]) if previsao else None,
                    "prob_satisfeito": (
                        float(previsao[SATISFEITO]) if previsao else None
                    ),
                    "emocao": emocao_por_indice.get(indice),
                    "prob_ironia": ironia_por_indice.get(indice),
                }
            )

        contribuicoes = None
        if conversa.tem_sinal_cliente:
            features = montar_features(conversa, self._classificador)
            contribuicoes = self._fusor.contribuicoes(features)

        return {
            "mensagens": mensagens,
            "importancias": self._fusor.importancias(),
            "contribuicoes": contribuicoes,
            # Bandeira explicita para a interface: emocao e ironia vieram, mas
            # NAO estao em `contribuicoes` nem no score. Sem isso a tela nao tem
            # como saber que precisa separar o que descreve do que pontua.
            "sinais_fora_do_score": ["emocao", "prob_ironia"],
        }

    def importancias(self) -> dict:
        """Peso global de cada feature -- usado pela ficha do modelo em `/modelo`."""
        return self._fusor.importancias()

    def analisar_conversa(self, conversa, referencia=None) -> dict:
        """Analise completa de UMA conversa, com peso palavra a palavra.

        E a atribuicao de `atribuir_conversa` mais duas coisas que so fazem
        sentido no exame de um atendimento especifico: o peso de cada palavra
        (por oclusao, ver `fraus.sinais.palavras`) e o vocabulario do cliente
        comparado ao restante do banco.

        SO A FALA DO CLIENTE recebe peso de palavra, pela mesma razao de sempre:
        o classificador foi fine-tunado em texto de cliente. Medir o quanto uma
        palavra do roteiro do bot "empurra a nota" produziria um numero
        bonito e sem lastro.
        """
        atribuicao = self.atribuir_conversa(conversa)
        for mensagem in atribuicao["mensagens"]:
            mensagem["palavras"] = (
                pesos_das_palavras(mensagem["texto"], self._classificador)
                if mensagem["autor"] == "cliente"
                else None
            )

        score = self.pontuar_conversa(conversa)
        return {
            **atribuicao,
            "score": score,
            "vocabulario": vocabulario(conversa, referencia),
        }

    def simular_texto(self, texto: str) -> dict:
        """Roda o classificador de texto sobre uma mensagem avulsa, fora do banco.

        Usado por `/modelo/simular` para deixar o operador testar frases sem
        importar CSV. So mexe no classificador de texto (nao ha conversa, nao
        ha as outras 12 features de tempo/emoji agregadas) -- o classificador
        e o fusor continuam sem vazar para a rota.
        """
        probabilidades = self._classificador.prever_mensagens([texto])[0]
        emojis = [
            {"emoji": emoji, "score": score_do_emoji(emoji), "posicao_relativa": posicao}
            for emoji, posicao in emojis_com_posicao(texto)
        ]
        emocoes = self._emocao_de([texto])
        ironias = self._ironia_de([texto])
        return {
            "prob_insatisfeito": float(probabilidades[INSATISFEITO]),
            "prob_neutro": float(probabilidades[NEUTRO]),
            "prob_satisfeito": float(probabilidades[SATISFEITO]),
            "emojis": emojis,
            # As duas cabecas de leitura. E aqui que a frase irônica se
            # denuncia: "que atendimento maravilhoso, so esperei 3 horas" sai
            # com prob_satisfeito alta E prob_ironia alta ao mesmo tempo -- as
            # duas coisas juntas sao a informacao, e por isso ironia e cabeca
            # separada em vez de mais uma classe de satisfacao.
            "emocao": emocoes[0] if emocoes else None,
            "prob_ironia": ironias[0] if ironias else None,
        }


def resolver_dentro_da_raiz(raiz: Path, caminho_pedido: str) -> Path:
    """Resolve `caminho_pedido` DENTRO de `raiz`, recusando qualquer escape.

    Trata os dois vetores de uma vez: `..` e caminho absoluto (que o operador
    `/` do pathlib faz substituir a raiz inteira). A verificacao de contencao
    e feita sobre os caminhos ja resolvidos -- `Path.resolve()` normaliza
    ligacao simbolica, `..` e maiusculas/minusculas do Windows.
    """
    raiz_resolvida = raiz.resolve()
    alvo = (raiz_resolvida / caminho_pedido).resolve()
    if alvo != raiz_resolvida and raiz_resolvida not in alvo.parents:
        raise HTTPException(
            status_code=400,
            detail=f"caminho fora da raiz de importacao ({raiz_resolvida}): {caminho_pedido}",
        )
    return alvo


def _metricas_de(caminho: Path) -> dict | None:
    """Metricas de treino de uma cabeca, ou None se o notebook ainda nao exportou.

    None, nunca um dicionario vazio ou zerado: "nao medimos" e "medimos zero"
    sao respostas diferentes, e a interface precisa poder dizer a primeira.
    """
    if not caminho.is_file():
        return None
    return json.loads(caminho.read_text(encoding="utf-8"))


def _chave_do_cabecalho(authorization: str | None) -> str:
    """Extrai a chave do `Authorization: Bearer ...`, recusando o resto.

    401 sem `WWW-Authenticate` seria resposta incompleta: o cabecalho e o que
    diz ao cliente COMO se autenticar, e sem ele o integrador so sabe que
    falhou.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="informe a chave da fonte em Authorization: Bearer <chave>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization[len("bearer "):].strip()


def _fonte_autorizada(banco: Banco, chave: str) -> dict:
    """Fonte a que a chave pertence, ou 401/403.

    A MENSAGEM E A MESMA para chave malformada, fonte inexistente e hash que
    nao bate. Distinguir os tres contaria a quem tenta se aquele id de fonte
    existe -- e a conferencia do hash roda mesmo quando a fonte nao foi achada,
    para o tempo de resposta tambem nao contar.

    Fonte desativada e caso separado (403, nao 401): a chave esta certa, o que
    esta desligado e a fonte. Recusar como "chave invalida" mandaria o
    integrador procurar problema onde nao ha.
    """
    negada = HTTPException(
        status_code=401,
        detail="chave invalida",
        headers={"WWW-Authenticate": "Bearer"},
    )

    fonte_id = credencial.fonte_da_chave(chave)
    fonte = banco.buscar_fonte(fonte_id) if fonte_id is not None else None
    guardado = banco.hash_da_chave_da_fonte(fonte_id) if fonte_id is not None else None

    if not credencial.confere(chave, guardado) or fonte is None:
        raise negada
    if not fonte["ativa"]:
        raise HTTPException(
            status_code=403,
            detail=f"a fonte '{fonte['nome']}' esta desativada",
        )
    return fonte


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

    # Vazia e ausente sao a mesma coisa: "Bearer " autorizando seria a pior
    # combinacao possivel de configuracao errada com acesso liberado.
    chave_mestra = chave_mestra or None

    def _e_mestra(chave: str) -> bool:
        if chave_mestra is None:
            return False
        return hmac.compare_digest(chave.encode("utf-8"), chave_mestra.encode("utf-8"))

    def _acesso_autorizado(chave: str) -> bool:
        """Mestra ou chave de acesso valida. Mensagem de recusa e uniforme
        la fora: daqui so sai sim ou nao."""
        if _e_mestra(chave):
            return True
        chave_id = acesso.id_da_chave(chave)
        guardado = banco.hash_da_chave_acesso(chave_id) if chave_id is not None else None
        return credencial.confere(chave, guardado)

    def _exigir_mestra(authorization: str | None) -> None:
        """Gerenciar chaves e privilegio da mestra, nunca de chave de acesso.

        No modo aberto (sem mestra) nao ha o que exigir -- as rotas de
        gerenciamento seguem abertas como o resto, coerente com a decisao de
        ativacao condicionada.

        403, nao 401: quem chega aqui com chave de acesso valida ja passou
        pelo middleware -- a credencial esta certa, o privilegio e que falta.
        """
        if chave_mestra is None:
            return
        chave = _chave_do_cabecalho(authorization)
        if not _e_mestra(chave):
            raise HTTPException(
                status_code=403, detail="esta rota exige a chave mestra"
            )

    if chave_mestra is not None:
        @app.middleware("http")
        async def exigir_chave_de_acesso(request, call_next):
            # /ingestao tem credencial propria (chave de FONTE): uma credencial
            # por rota. OPTIONS e o preflight do navegador -- nao carrega
            # header de autorizacao por definicao.
            if request.url.path == "/ingestao" or request.method == "OPTIONS":
                return await call_next(request)
            cabecalho = request.headers.get("authorization")
            if not cabecalho or not cabecalho.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={"detail": (
                        "informe a chave de acesso em Authorization: Bearer <chave>"
                    )},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if not _acesso_autorizado(cabecalho[len("Bearer "):]):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "chave invalida"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return await call_next(request)

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
    raiz = Path(raiz_importacao) if raiz_importacao is not None else RAIZ_IMPORTACAO

    def faixas_vigentes() -> dict:
        """Faixa de NPS da configuracao vigente, lida a cada requisicao.

        Ler por requisicao (em vez de guardar num atributo do app) e o que
        garante que `/indicadores` e `/conversas` NUNCA discordem: nao existe
        copia da faixa envelhecendo em memoria depois de um PUT.
        """
        return faixas_de(carregar_configuracao(banco))

    def categoria_de(score: float | None, faixas: dict) -> str | None:
        """Categoria DERIVADA NA LEITURA do score gravado e da faixa vigente.

        A coluna `categoria` do banco e o retrato do instante da importacao e
        NAO e lida aqui: mudar a faixa muda a fatia de atendimento ja pontuado,
        e derivar na leitura e o que faz toda rota responder pela mesma faixa
        no mesmo instante -- sem janela de recalculo em massa pela metade. O
        `score`, esse sim resultado do modelo, nunca e recalculado.
        """
        return categoria_nps(score, faixas) if score is not None else None

    @app.get("/saude")
    def saude() -> dict:
        return {"status": "ok"}

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

        faixas = faixas_vigentes()
        for conversa in resultado.conversas:
            score = motor.pontuar_conversa(conversa)
            # A coluna `categoria` e o retrato do instante da importacao; quem
            # le nao a consome (ver `categoria_de`), mas gravar com a faixa
            # vigente evita que o banco inspecionado a mao conte outra historia.
            banco.salvar(conversa, score, categoria_de(score, faixas))

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
    def listar() -> list[dict]:
        """Lista de atendimentos com a ficha operacional de cada um.

        Alem de nota e categoria, cada linha carrega o que `fraus.resumo`
        deriva da conversa: contagem de mensagens por autor, tempo de resposta
        do bot e do humano SEPARADOS, duracao e desfecho. Vem tudo junto de
        proposito -- a tela precisa disso por linha, e busca-los um a um era um
        N+1 contra a API.
        """
        # A `nota` sai daqui derivada no SERVIDOR, junto com score e categoria:
        # e a mesma conversao de `/conversas/{id}`, e a dashboard so a exibe.
        faixas = faixas_vigentes()
        return [
            {
                **linha,
                "categoria": categoria_de(linha["score"], faixas),
                "nota": nota_0_10(linha["score"]) if linha["score"] is not None else None,
                **resumir(conversa),
            }
            for linha, conversa in banco.listar_com_conversa()
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
            "categoria": categoria_de(score, faixas_vigentes()),
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
            "categoria": categoria_de(score, faixas_vigentes()),
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
    def indicadores() -> dict:
        registros = banco.todas()
        conversas = [conversa for conversa, _ in registros]
        scores = [score for _, score in registros if score is not None]
        return {
            "nps": calcular_nps(scores, faixas_vigentes()),
            "csat": calcular_csat(scores),
            "containment_rate": containment_rate(conversas),
            "total_conversas": len(conversas),
            "sem_sinal": len(conversas) - len(scores),
        }

    def _dia_ou_400(valor: str | None, nome: str) -> date | None:
        """AAAA-MM-DD, ou 400 nomeando o parametro -- nunca ignorado em silencio.

        Filtro de periodo malformado que e descartado sem aviso devolveria a
        serie INTEIRA parecendo o recorte pedido, e o grafico mentiria sem
        nenhum sinal de erro.
        """
        if valor is None:
            return None
        try:
            return date.fromisoformat(valor)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"{nome} invalido: esperava AAAA-MM-DD, veio {valor!r}",
            )

    @app.get("/serie-temporal")
    def serie_temporal(de: str | None = None, ate: str | None = None) -> dict:
        """NPS inferido x latencia mediana por dia, com recorte de periodo.

        Existe para tirar da dashboard o N+1 que ela fazia: sem este endpoint,
        montar o grafico exigia baixar a TRANSCRICAO de toda conversa do
        recorte so para ler timestamps. As duas pontas do recorte sao
        INCLUSIVAS, que e como quem opera le "de 01/03 ate 07/03".
        """
        inicio, fim = _dia_ou_400(de, "de"), _dia_ou_400(ate, "ate")
        if inicio and fim and inicio > fim:
            raise HTTPException(
                status_code=400, detail=f"periodo invertido: de {inicio} vem depois de ate {fim}"
            )

        registros = [
            (conversa, score)
            for conversa, score in banco.todas()
            if (inicio is None or conversa.iniciada_em.date() >= inicio)
            and (fim is None or conversa.iniciada_em.date() <= fim)
        ]
        return {
            "de": inicio.isoformat() if inicio else None,
            "ate": fim.isoformat() if fim else None,
            "pontos": serie_diaria(registros, faixas_vigentes()),
        }

    @app.get("/configuracoes")
    def configuracoes() -> dict:
        """Configuracao vigente E a de fabrica -- a tela precisa das duas.

        Sem a de fabrica, "voltar ao padrao" seria um botao que a interface
        teria que preencher com numeros digitados de novo, e digitar de novo e
        exatamente como faixa duplicada nasce.
        """
        return {
            "vigente": carregar_configuracao(banco),
            "fabrica": CONFIGURACAO_DE_FABRICA,
        }

    @app.put("/configuracoes")
    def configurar(pedido: dict) -> dict:
        """Grava as chaves enviadas. Chave desconhecida ou valor invalido e 400.

        O corpo e um dicionario cru de proposito: chave desconhecida precisa
        chegar a validacao para ser NOMEADA no erro, e nao ser descartada em
        silencio por um modelo de entrada tolerante.
        """
        try:
            vigente = salvar_configuracao(banco, pedido)
        except ValueError as erro:
            raise HTTPException(status_code=400, detail=str(erro)) from erro
        return {"vigente": vigente, "fabrica": CONFIGURACAO_DE_FABRICA}

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
    def gerar_chave(fonte_id: int) -> dict:
        """Gera a chave de API da fonte e a devolve EM CLARO uma unica vez.

        Nao ha rota para reler a chave depois, e isso e a feature: o banco
        guarda so o hash, entao um `fraus.db` vazado num backup nao leva
        credencial junto. Perder a chave custa gerar outra.

        Gerar substitui a anterior. Duas chaves validas ao mesmo tempo pareceria
        rotacao sem risco, mas a antiga seguiria aceita sem ninguem saber quem
        ainda a usa.
        """
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
    def revogar_chave(fonte_id: int) -> None:
        """Invalida a chave da fonte. A fonte e as conversas dela continuam."""
        if banco.buscar_fonte(fonte_id) is None:
            raise HTTPException(status_code=404, detail="fonte nao encontrada")
        banco.revogar_chave(fonte_id)

    @app.post("/acesso/chaves", status_code=201)
    def criar_chave_acesso(
        pedido: PedidoChaveAcesso, authorization: str | None = Header(default=None)
    ) -> dict:
        """Gera uma chave de acesso e a devolve EM CLARO uma unica vez."""
        _exigir_mestra(authorization)
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
        _exigir_mestra(authorization)
        return banco.listar_chaves_acesso()

    @app.delete("/acesso/chaves/{chave_id}", status_code=204)
    def revogar_chave_acesso(
        chave_id: int, authorization: str | None = Header(default=None)
    ) -> None:
        _exigir_mestra(authorization)
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
        chave = _chave_do_cabecalho(authorization)
        fonte = _fonte_autorizada(banco, chave)

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
        banco.salvar(conversa, score, categoria_de(score, faixas_vigentes()))
        return {
            "id": conversa.id,
            "canal": conversa.canal,
            "score": score,
            "nota": nota_0_10(score) if score is not None else None,
            "categoria": categoria_de(score, faixas_vigentes()),
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
        metricas = _metricas_de(CAMINHO_METRICAS)
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
                    "metricas": _metricas_de(CAMINHO_METRICAS_EMOCAO),
                    "pontua": False,
                },
                {
                    "nome": "ironia",
                    "classes": ["nao-ironico", "ironico"],
                    "metricas": _metricas_de(CAMINHO_METRICAS_IRONIA),
                    "pontua": False,
                },
            ],
            "faixas_nps": {
                categoria: list(faixa) for categoria, faixa in faixas_vigentes().items()
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

        faixas = faixas_vigentes()
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
                    "categoria": categoria_de(score, faixas),
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
