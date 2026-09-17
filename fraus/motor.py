"""O Motor: classificador de texto e fusor amarrados num ponto de pontuacao.

Dominio puro -- nao sabe que existe HTTP. Vivia dentro de `fraus/api/main.py`
por acidente de crescimento, e a borda da API nao e lugar de regra de modelo:
quem chama o Motor e a rota, nao o contrario.
"""

import hashlib
import os
import threading

from fraus.deriva import resumo_de_deriva
from fraus.fusor import Fusor, montar_features
from fraus.sinais.emocao import (NOMES_EMOCOES, ClassificadorEmocao,
                                 desprezo_derivado)
from fraus.sinais.emoji import emojis_com_posicao, score_do_emoji
from fraus.sinais.estilo import estilo_da_mensagem
from fraus.sinais.ironia import IRONICO, ClassificadorIronia
from fraus.sinais.palavras import pesos_das_palavras, vocabulario
from fraus.sinais.texto import (INSATISFEITO, NEUTRO, SATISFEITO,
                                ClassificadorTexto)


class _Guardado:
    """Classificador atras de um semaforo compartilhado pelas tres cabecas.

    O FastAPI atende rota sincrona num threadpool de ate 40 threads, e cada
    passada do torch ja usa todos os nucleos por dentro. Quatro requisicoes
    rodando BERTimbau juntas nao terminam quatro vezes mais rapido: disputam os
    mesmos nucleos e TODAS ficam lentas. Com o teto, a fila fica do lado de
    fora do modelo e a latencia de cada passada volta a ser previsivel.
    """

    def __init__(self, classificador, semaforo: threading.Semaphore) -> None:
        self._classificador = classificador
        self._semaforo = semaforo

    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        with self._semaforo:
            return self._classificador.prever_mensagens(textos)


class _GuardadoMultitarefa:
    """Serializa a unica passagem que produz as tres cabecas."""

    def __init__(self, classificador, semaforo: threading.Semaphore) -> None:
        self._classificador = classificador
        self._semaforo = semaforo

    def prever_cabecas(self, textos: list[str]) -> dict:
        with self._semaforo:
            return self._classificador.prever_cabecas(textos)


class _Memoria:
    """Previsoes de UMA pergunta ao Motor, para nao classificar a mesma fala 2x.

    A chave e a LISTA inteira de textos, e nao cada texto: o BERTimbau roda em
    lote com padding pela mensagem mais longa, e a mesma frase em lotes
    diferentes pode sair com diferenca de arredondamento. Reaproveitar so o
    lote identico garante numero identico ao de antes -- o que muda e so
    quantas vezes a conta e feita.

    Vive o tempo de uma chamada e morre com ela: nunca e atributo do Motor,
    pelo mesmo motivo que a curadoria nao e.
    """

    def __init__(self, classificador) -> None:
        self._classificador = classificador
        self._lotes: dict[tuple[str, ...], list[list[float]]] = {}

    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        chave = tuple(textos)
        if chave not in self._lotes:
            self._lotes[chave] = self._classificador.prever_mensagens(textos)
        return self._lotes[chave]


class _Precalculado:
    """Resultado de uma passagem multitarefa com interface de classificador."""

    def __init__(self, resultado: list[list[float]]) -> None:
        self._resultado = resultado

    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        return self._resultado


class Motor:
    """Amarra os tres classificadores e o fusor num unico ponto de pontuacao.

    Emocao ENTRA no score desde que o contrato subiu para 35 features
    (21/08/2026); antes disso era leitura decorativa. A ironia entrou junto em
    21/08/2026 mas SAIU de novo em 04/09/2026: o corpus de treino faz a cabeca
    funcionar como detector de sentimento positivo, nao de ironia (ver
    `fraus/fusor.py`, comentario de `NOMES_FEATURES`) -- ela volta a ser
    leitura decorativa, so que agora POR DECISAO, nao por falta de features.

    A consequencia pratica: os tres modelos continuam obrigatorios mesmo a
    ironia nao pontuando mais -- ela ainda e lida por mensagem e devolvida na
    atribuicao. Sem qualquer um dos tres a API nao sobe, e esse e o
    comportamento correto (invariante 7) -- servir predicao com vetor
    incompleto, ou omitir um sinal que a tela promete mostrar, e pior do que
    estar fora do ar.
    """

    def __init__(
        self,
        classificador: ClassificadorTexto,
        fusor: Fusor,
        emocao: ClassificadorEmocao,
        ironia: ClassificadorIronia,
    ) -> None:
        # Quantas passadas de modelo ao mesmo tempo, somando as tres cabecas.
        # 1 e o certo para CPU: o torch ja paraleliza cada passada por dentro.
        semaforo = threading.Semaphore(
            int(os.environ.get("FRAUS_INFERENCIAS_SIMULTANEAS", "1"))
        )
        candidatos = [
            getattr(c, "multitarefa", None)
            for c in (classificador, emocao, ironia)
        ]
        self._multitarefa = (
            _GuardadoMultitarefa(candidatos[0], semaforo)
            if candidatos[0] is not None and all(c is candidatos[0] for c in candidatos)
            else None
        )
        self._classificador = _Guardado(classificador, semaforo)
        self._fusor = fusor
        self._emocao = _Guardado(emocao, semaforo)
        self._ironia = _Guardado(ironia, semaforo)

    def _prever_todas(self, textos: list[str]) -> dict | None:
        return self._multitarefa.prever_cabecas(textos) if self._multitarefa else None

    def _emocao_de(self, textos: list[str], classificador=None) -> list[dict] | None:
        """Sete probabilidades mais o desprezo da diade, por texto.

        `None` quando nao ha texto de cliente para classificar (`not textos`) --
        o modelo em si e obrigatorio desde o contrato de 35 features, entao o
        unico jeito de nao ter previsao aqui e nao ter fala para prever.
        """
        if not textos:
            return None
        previsoes = (classificador or self._emocao).prever_mensagens(textos)
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
        textos = [m.texto for m in conversa.mensagens if m.autor == "cliente"]
        todas = self._prever_todas(textos)
        texto = _Precalculado(todas["satisfacao"]) if todas else self._classificador
        emocao = _Precalculado(todas["emocao"]) if todas else self._emocao
        return self._fusor.pontuar(montar_features(conversa, texto, emocao, curadoria))

    def atribuir_conversa(self, conversa, curadoria=None) -> dict:
        return self._atribuir(conversa, curadoria)[0]

    def _atribuir(self, conversa, curadoria=None) -> tuple[dict, dict | None]:
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
        todas = self._prever_todas(textos_do_cliente)
        texto = _Memoria(
            _Precalculado(todas["satisfacao"]) if todas else self._classificador
        )
        emocao = _Memoria(_Precalculado(todas["emocao"]) if todas else self._emocao)
        probabilidades = texto.prever_mensagens(textos_do_cliente)
        por_indice = dict(zip(indices_do_cliente, probabilidades))

        # Mesma regra das probabilidades de satisfacao: so a fala do CLIENTE.
        # As tres cabecas foram fine-tunadas em texto de cliente, e rodar
        # qualquer uma na fala do bot devolveria numero sem lastro.
        emocoes = self._emocao_de(textos_do_cliente, emocao)
        ironias = (
            [float(p[IRONICO]) for p in todas["ironia"]]
            if todas
            else self._ironia_de(textos_do_cliente)
        )
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
                    # Estilo e deterministico e nao depende de classificador:
                    # sai para TODA mensagem, inclusive as do bot, e a tela
                    # decide o que mostrar. As features do fusor continuam
                    # lendo so o cliente -- `features_estilo` nao mudou.
                    "estilo": estilo_da_mensagem(mensagem.texto),
                }
            )

        contribuicoes = features = None
        if conversa.tem_sinal_cliente:
            # A MESMA curadoria que pontua: se a atribuicao usasse outro lexico
            # que o score, a tela explicaria a nota com evidencia que nao a
            # produziu -- pior que nao explicar.
            # `texto`/`emocao` ja tem o lote da fala do cliente: montar o vetor
            # nao roda os modelos de novo.
            features = montar_features(conversa, texto, emocao, curadoria)
            contribuicoes = self._fusor.contribuicoes(features)

        return {
            "mensagens": mensagens,
            "importancias": self._fusor.importancias(),
            "contribuicoes": contribuicoes,
            # Ate 20/08/2026 esta lista trazia ["emocao", "prob_ironia"]: os dois
            # vinham na resposta mas nao entravam no score. Desde o contrato de
            # 35 features (21/08/2026) ate 03/09/2026 as duas cabecas ENTRAVAM
            # em `contribuicoes` e no score, entao a lista esvaziou. Em
            # 04/09/2026 a ironia SAIU do vetor de novo -- o corpus de treino
            # fez a cabeca funcionar como detector de sentimento positivo, nao
            # de ironia (ver o comentario de `NOMES_FEATURES` em `fusor.py`) --
            # entao a lista volta a ter conteudo. O campo continua existindo
            # mesmo quando vazio: "sinais que vieram mas nao entram no score" e
            # uma pergunta valida independente da resposta do momento, e a
            # interface ja consome o contrato de tipo (`dashboard/lib/api.ts`);
            # sumir com o campo trocaria "nao ha nenhum" por "campo ausente",
            # que e outra coisa.
            "sinais_fora_do_score": ["prob_ironia"],
        }, features

    def deriva_da_amostra(self, conversas, curadoria=None) -> dict | None:
        """Quais features desta amostra sairam da faixa de treino do fusor.

        DIAGNOSTICO, nunca predicao: nada aqui muda score, nota ou categoria de
        conversa nenhuma. Existe porque a guarda da invariante 10 roda no
        notebook, sobre o CORPUS, e o corpus do sinal de tempo nunca passou de
        minutos -- ele nao tem o que dizer sobre a conversa de tres horas que
        aparece em producao e faz o relogio assumir a nota.

        CUSTA UMA PASSAGEM DE MODELO POR CONVERSA, porque as features so
        existem depois do BERTimbau. Por isso quem chama corta a amostra: esta
        rota e um exame pedido, nao um agregado de tela.

        Conversa sem fala do cliente fica de fora -- ela nao tem features, e
        contar como "dentro da faixa" seria inventar uma medida tranquilizadora
        a partir de ausencia de dado.
        """
        zs = [
            self._fusor.z_das_features(
                montar_features(conversa, self._classificador, self._emocao, curadoria)
            )
            for conversa in conversas
            if conversa.tem_sinal_cliente
        ]
        return resumo_de_deriva(zs, self._fusor.distribuicao_de_treino())

    def regua(self) -> str | None:
        """Com qual regua este motor pontua: os pesos do fusor MAIS a regra da cortesia.

        A curadoria tem regua propria (`lexico_versao`); esta cobre o resto do
        que muda nota sem reimportar -- um retreino do fusor, ou a lista de
        `fraus/cortesia.py` (que tira a nota de uma conversa sem mexer em peso
        nenhum). O banco grava a regua com cada conversa, e o aviso de regua
        misturada conta quem ficou para tras.
        """
        assinatura = getattr(self._fusor, "assinatura", None)
        pesos = assinatura() if callable(assinatura) else None
        if pesos is None:
            return None
        from fraus import cortesia

        regra = hashlib.sha256("\n".join(sorted(cortesia.FORMULAS_DE_CORTESIA)).encode())
        return f"{pesos}-{regra.hexdigest()[:8]}"

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
        atribuicao, features = self._atribuir(conversa, curadoria)
        for mensagem in atribuicao["mensagens"]:
            mensagem["palavras"] = (
                pesos_das_palavras(mensagem["texto"], self._classificador)
                if mensagem["autor"] == "cliente"
                else None
            )

        # O vetor da atribuicao e o mesmo que `pontuar_conversa` montaria:
        # mesma conversa, mesma curadoria, mesmo lote. Repontuar era a terceira
        # passada dos modelos pelo mesmo texto.
        score = self._fusor.pontuar(features) if features is not None else None
        return {
            **atribuicao,
            "score": score,
            "vocabulario": vocabulario(conversa, referencia),
        }

    def simular_texto(self, texto: str) -> dict:
        """Roda o classificador de texto sobre uma mensagem avulsa, fora do banco.

        Usado por `/modelo/simular` para deixar o operador testar frases sem
        importar CSV. So mexe no classificador de texto (nao ha conversa, entao
        nao ha as outras 34 features do vetor -- tempo, emoji, emocao, lexico
        e estilo -- que so existem agregadas na conversa) -- o classificador
        e o fusor continuam sem vazar para a rota.
        """
        todas = self._prever_todas([texto])
        probabilidades = (
            todas["satisfacao"][0]
            if todas
            else self._classificador.prever_mensagens([texto])[0]
        )
        emojis = [
            {"emoji": emoji, "score": score_do_emoji(emoji), "posicao_relativa": posicao}
            for emoji, posicao in emojis_com_posicao(texto)
        ]
        emocoes = self._emocao_de(
            [texto], _Precalculado(todas["emocao"]) if todas else None
        )
        ironias = (
            [float(todas["ironia"][0][IRONICO])]
            if todas
            else self._ironia_de([texto])
        )
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
            "estilo": estilo_da_mensagem(texto),
        }
