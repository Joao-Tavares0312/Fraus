"""O Motor: classificador de texto e fusor amarrados num ponto de pontuacao.

Dominio puro -- nao sabe que existe HTTP. Vivia dentro de `fraus/api/main.py`
por acidente de crescimento, e a borda da API nao e lugar de regra de modelo:
quem chama o Motor e a rota, nao o contrario.
"""

from fraus.fusor import Fusor, montar_features
from fraus.sinais.emocao import (NOMES_EMOCOES, ClassificadorEmocao,
                                 desprezo_derivado)
from fraus.sinais.emoji import emojis_com_posicao, score_do_emoji
from fraus.sinais.ironia import IRONICO, ClassificadorIronia
from fraus.sinais.palavras import pesos_das_palavras, vocabulario
from fraus.sinais.texto import (INSATISFEITO, NEUTRO, SATISFEITO,
                                ClassificadorTexto)


class Motor:
    """Amarra os tres classificadores e o fusor num unico ponto de pontuacao.

    Emocao e ironia ENTRAM no score desde que o contrato subiu para 35 features
    (21/08/2026). Antes disso elas eram leitura decorativa e esta docstring
    dizia, corretamente, que nao moviam a nota -- nao dizem mais.

    A consequencia pratica: os tres modelos sao obrigatorios. Sem qualquer um
    deles a API nao sobe, e esse e o comportamento correto (invariante 7) --
    servir predicao com vetor incompleto e pior do que estar fora do ar.
    """

    def __init__(
        self,
        classificador: ClassificadorTexto,
        fusor: Fusor,
        emocao: ClassificadorEmocao,
        ironia: ClassificadorIronia,
    ) -> None:
        self._classificador = classificador
        self._fusor = fusor
        self._emocao = emocao
        self._ironia = ironia

    def _emocao_de(self, textos: list[str]) -> list[dict] | None:
        """Sete probabilidades mais o desprezo da diade, por texto.

        `None` quando nao ha texto de cliente para classificar (`not textos`) --
        o modelo em si e obrigatorio desde o contrato de 35 features, entao o
        unico jeito de nao ter previsao aqui e nao ter fala para prever.
        """
        if not textos:
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
        """Probabilidade de ironia por texto.

        `None` quando nao ha texto de cliente para classificar (`not textos`) --
        o modelo e obrigatorio desde o contrato de 35 features.
        """
        if not textos:
            return None
        return [float(p[IRONICO]) for p in self._ironia.prever_mensagens(textos)]

    def pontuar_conversa(self, conversa, curadoria=None) -> float | None:
        """Score 0-100, ou `None` sem fala do cliente.

        `curadoria` chega POR PARAMETRO e o Motor NAO a guarda: ele e construido
        uma vez no boot, e um atributo aqui envelheceria a cada palavra
        cadastrada -- o mesmo defeito que o `lru_cache` dos lexicons teria se a
        curadoria entrasse por la, e o mesmo que a autenticacao ja teve quando o
        middleware so era registrado no boot. Quem a carrega e o `Contexto`, a
        cada requisicao.
        """
        if not conversa.tem_sinal_cliente:
            return None  # ausencia de dado nao e insatisfacao
        return self._fusor.pontuar(
            montar_features(
                conversa, self._classificador, self._emocao, self._ironia, curadoria
            )
        )

    def atribuir_conversa(self, conversa, curadoria=None) -> dict:
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
            # A MESMA curadoria que pontua: se a atribuicao usasse outro lexico
            # que o score, a tela explicaria a nota com evidencia que nao a
            # produziu -- pior que nao explicar.
            features = montar_features(
                conversa, self._classificador, self._emocao, self._ironia, curadoria
            )
            contribuicoes = self._fusor.contribuicoes(features)

        return {
            "mensagens": mensagens,
            "importancias": self._fusor.importancias(),
            "contribuicoes": contribuicoes,
            # Ate 20/08/2026 esta lista trazia ["emocao", "prob_ironia"]: os dois
            # vinham na resposta mas nao entravam no score. Desde o contrato de
            # 35 features (21/08/2026) as duas cabecas ENTRAM em `contribuicoes`
            # e no score, entao a lista esvaziou. O campo continua existindo --
            # "sinais que vieram mas nao entram no score" e uma pergunta valida
            # mesmo com o conjunto vazio hoje, e a interface ja consome o
            # contrato de tipo (`dashboard/lib/api.ts`); sumir com o campo
            # trocaria "nao ha nenhum" por "campo ausente", que e outra coisa.
            "sinais_fora_do_score": [],
        }

    def importancias(self) -> dict:
        """Peso global de cada feature -- usado pela ficha do modelo em `/modelo`."""
        return self._fusor.importancias()

    def eixo_global(self) -> dict:
        """Passthrough do peso global COM sinal -- o grafo da memoria consome."""
        return self._fusor.eixo_global()

    def analisar_conversa(self, conversa, referencia=None, curadoria=None) -> dict:
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
        atribuicao = self.atribuir_conversa(conversa, curadoria)
        for mensagem in atribuicao["mensagens"]:
            mensagem["palavras"] = (
                pesos_das_palavras(mensagem["texto"], self._classificador)
                if mensagem["autor"] == "cliente"
                else None
            )

        score = self.pontuar_conversa(conversa, curadoria)
        return {
            **atribuicao,
            "score": score,
            "vocabulario": vocabulario(conversa, referencia),
        }

    def simular_texto(self, texto: str) -> dict:
        """Roda o classificador de texto sobre uma mensagem avulsa, fora do banco.

        Usado por `/modelo/simular` para deixar o operador testar frases sem
        importar CSV. So mexe no classificador de texto (nao ha conversa, entao
        nao ha as outras 31 features -- tempo, emoji, emocao, lexico, ironia e
        estilo -- que so existem agregadas na conversa) -- o classificador
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
