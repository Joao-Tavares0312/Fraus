"""API do Dolos.

Score e categoria SAO SEMPRE derivados no servidor: campos vindos do corpo da
requisicao que se pareçam com veredito sao ignorados por construcao -- o modelo
de entrada so aceita `caminho`.

O objeto `app` de nivel de modulo (consumido por `uvicorn dolos.api.main:app`)
e construido com dependencias REAIS -- Banco em disco e Motor com
ClassificadorTexto/Fusor carregados do disco -- e deve falhar alto no import
se o modelo ou o fusor nao existirem (ModeloAusenteError e equivalente do
fusor propagam sem fallback: servir predicao sem modelo carregado e pior do
que estar fora do ar).

`app` e resolvido de forma preguicosa via `__getattr__` de modulo (PEP 562):
so e construido quando algo de fato acessa o atributo `app` (como o uvicorn
faz ao importar `dolos.api.main:app`). O import puro do modulo -- o que os
testes fazem ao importar `criar_app` -- nunca dispara essa construcao, porque
`app` nao existe como atributo normal do modulo.
"""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from dolos.db import Banco
from dolos.fusor import Fusor, montar_features
from dolos.indicadores import (calcular_csat, calcular_nps, categoria_nps,
                               containment_rate, nota_0_10)
from dolos.ingest.csv_driver import carregar_csv
from dolos.sinais.texto import (INSATISFEITO, NEUTRO, SATISFEITO,
                                ClassificadorTexto)

CAMINHO_MODELO_TEXTO = Path(os.environ.get("DOLOS_CAMINHO_MODELO_TEXTO", "modelos/bertimbau-satisfacao"))
CAMINHO_FUSOR = Path(os.environ.get("DOLOS_CAMINHO_FUSOR", "modelos/fusor.joblib"))
CAMINHO_BANCO = Path(os.environ.get("DOLOS_CAMINHO_BANCO", "dolos.db"))

# Raiz unica de onde a importacao pode ler. O endpoint nao tem autenticacao
# (uso local, ver README) -- entao ele nao pode aceitar caminho arbitrario do
# sistema de arquivos: tudo que entra e resolvido DENTRO desta pasta.
RAIZ_IMPORTACAO = Path(os.environ.get("DOLOS_RAIZ_IMPORTACAO", "dados_brutos"))

# Quantos motivos de rejeicao a resposta carrega. O relato existe para o
# operador entender o que ficou de fora, nao para devolver o CSV inteiro.
LIMITE_MOTIVOS = 20


class PedidoImportacao(BaseModel):
    caminho: str  # unico campo aceito: veredito nunca vem do cliente


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

        A ordem das classes e a de `dolos.sinais.texto`: 0 insatisfeito,
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


def criar_app(banco: Banco, motor, raiz_importacao: Path | None = None) -> FastAPI:
    app = FastAPI(title="Dolos", version="0.1.0")
    raiz = Path(raiz_importacao) if raiz_importacao is not None else RAIZ_IMPORTACAO

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

        for conversa in resultado.conversas:
            score = motor.pontuar_conversa(conversa)
            categoria = categoria_nps(score) if score is not None else None
            banco.salvar(conversa, score, categoria)

        # "Motivo registrado" (spec 9) tem que CHEGAR a alguem: a contagem
        # sozinha nao diz o que ficou de fora.
        return {
            "importadas": len(resultado.conversas),
            "rejeitadas": len(resultado.rejeitadas),
            "motivos": [
                linha.model_dump() for linha in resultado.rejeitadas[:LIMITE_MOTIVOS]
            ],
        }

    @app.get("/conversas")
    def listar() -> list[dict]:
        # A `nota` sai daqui derivada no SERVIDOR, junto com score e categoria:
        # e a mesma conversao de `/conversas/{id}`, e a dashboard so a exibe.
        return [
            {**linha, "nota": nota_0_10(linha["score"]) if linha["score"] is not None else None}
            for linha in banco.listar()
        ]

    @app.get("/conversas/{conversa_id}")
    def detalhar(conversa_id: str) -> dict:
        achado = banco.buscar(conversa_id)
        if achado is None:
            raise HTTPException(status_code=404, detail="conversa nao encontrada")
        conversa, score, categoria = achado
        return {
            **conversa.model_dump(mode="json"),
            "score": score,
            "categoria": categoria,
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
        conversa, score, categoria = achado
        atribuicao = motor.atribuir_conversa(conversa)
        return {
            "conversa_id": conversa.id,
            "score": score,
            "nota": nota_0_10(score) if score is not None else None,
            "categoria": categoria,
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
            "nps": calcular_nps(scores),
            "csat": calcular_csat(scores),
            "containment_rate": containment_rate(conversas),
            "total_conversas": len(conversas),
            "sem_sinal": len(conversas) - len(scores),
        }

    return app


def criar_app_padrao() -> FastAPI:
    """Monta o app com dependencias reais. Falha alto se modelo/fusor faltarem.

    Carrega classificador e fusor ANTES de tocar no banco: se a inicializacao
    vai falhar por modelo ausente, ela precisa falhar sem sujar o disco com um
    `dolos.db` de schema vazio.
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
    `criar_app`) e ainda assim expoe `app` para `uvicorn dolos.api.main:app`,
    que acessa o atributo de verdade -- disparando a construcao real e
    deixando ModeloAusenteError/erro do fusor propagarem.
    """
    if nome == "app":
        return criar_app_padrao()
    raise AttributeError(f"modulo {__name__!r} nao tem atributo {nome!r}")
