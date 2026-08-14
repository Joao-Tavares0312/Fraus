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

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from fraus.configuracao import PADROES as CONFIGURACAO_DE_FABRICA
from fraus.configuracao import carregar as carregar_configuracao
from fraus.configuracao import faixas_de
from fraus.configuracao import salvar as salvar_configuracao
from fraus.db import Banco
from fraus.fusor import Fusor, montar_features
from fraus.indicadores import (calcular_csat, calcular_nps, categoria_nps,
                               containment_rate, nota_0_10, serie_diaria)
from fraus.ingest.csv_driver import carregar_csv
from fraus.sinais.emoji import (emojis_com_posicao, linhas_lexicon,
                                score_do_emoji)
from fraus.sinais.texto import (INSATISFEITO, NEUTRO, SATISFEITO,
                                ClassificadorTexto)

CAMINHO_MODELO_TEXTO = Path(os.environ.get("FRAUS_CAMINHO_MODELO_TEXTO", "modelos/bertimbau-satisfacao"))
CAMINHO_FUSOR = Path(os.environ.get("FRAUS_CAMINHO_FUSOR", "modelos/fusor.joblib"))
CAMINHO_BANCO = Path(os.environ.get("FRAUS_CAMINHO_BANCO", "fraus.db"))

# Exportado pelo notebook 01 (acuracia, F1-macro do BERTimbau). Ausente e
# esperado antes do treino: `/modelo` devolve `metricas: null`, nunca inventa.
CAMINHO_METRICAS = Path(os.environ.get("FRAUS_CAMINHO_METRICAS", "modelos/metricas.json"))

# Teto de tamanho do texto aceito por /modelo/simular -- nao e limite de
# modelo (BERTimbau trunca em TAMANHO_MAXIMO tokens), e limite de payload.
TETO_TEXTO_SIMULACAO = 2000

# Teto de itens que /modelo/lexicon devolve por pagina, mesmo se pedirem mais.
TETO_LEXICON = 200

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


class Motor:
    """Amarra classificador de texto e fusor num unico ponto de pontuacao."""

    def __init__(self, classificador: ClassificadorTexto, fusor: Fusor) -> None:
        self._classificador = classificador
        self._fusor = fusor

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
        probabilidades = self._classificador.prever_mensagens(
            [conversa.mensagens[indice].texto for indice in indices_do_cliente]
        )
        por_indice = dict(zip(indices_do_cliente, probabilidades))

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
        }

    def importancias(self) -> dict:
        """Peso global de cada feature -- usado pela ficha do modelo em `/modelo`."""
        return self._fusor.importancias()

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
        return {
            "prob_insatisfeito": float(probabilidades[INSATISFEITO]),
            "prob_neutro": float(probabilidades[NEUTRO]),
            "prob_satisfeito": float(probabilidades[SATISFEITO]),
            "emojis": emojis,
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


def _fonte_publica(fonte: dict) -> dict:
    """Fonte como ela pode sair pela rede: o segredo nao acompanha.

    So o NOME da variavel de ambiente e o fato de ela estar definida. A
    verificacao e feita na LEITURA, nao no cadastro: a variavel pode aparecer
    ou sumir do ambiente depois, e responder pelo que era verdade no cadastro
    seria mentir sobre o estado atual.
    """
    variavel = fonte["variavel_segredo"]
    return {**fonte, "configurada": bool(variavel and os.environ.get(variavel))}


def criar_app(banco: Banco, motor, raiz_importacao: Path | None = None) -> FastAPI:
    app = FastAPI(title="Fraus", version="0.1.0")
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
        # A `nota` sai daqui derivada no SERVIDOR, junto com score e categoria:
        # e a mesma conversao de `/conversas/{id}`, e a dashboard so a exibe.
        faixas = faixas_vigentes()
        return [
            {
                **linha,
                "categoria": categoria_de(linha["score"], faixas),
                "nota": nota_0_10(linha["score"]) if linha["score"] is not None else None,
            }
            for linha in banco.listar()
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
        metricas = None
        if CAMINHO_METRICAS.is_file():
            metricas = json.loads(CAMINHO_METRICAS.read_text(encoding="utf-8"))
        return {
            "importancias": motor.importancias(),
            "metricas": metricas,
            "classes": ["insatisfeito", "neutro", "satisfeito"],
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
    motor = Motor(classificador, fusor)
    banco = Banco(CAMINHO_BANCO)
    banco.migrar()
    return criar_app(banco=banco, motor=motor)


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
