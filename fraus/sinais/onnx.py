"""Inferencia por ONNX Runtime -- o mesmo modelo, sem os 497 MB do torch.

POR QUE ELE EXISTE. Os tres BERTimbau em fp32 somam 1,25 GB e o `torch` que os
executa pesa mais 497 MB: ~1,75 GB de imagem para multiplicar matrizes de 110M
de parametros em CPU. Com o grafo exportado e quantizado (int8) e o
`onnxruntime` no lugar do torch, a mesma predicao cabe numa fracao disso.

O QUE ELE NAO E. Nao e um segundo modelo, nem uma aproximacao "boa o
suficiente": e o MESMO checkpoint, exportado e com os pesos guardados em menor
precisao. `scripts/encolher_modelos.py` so promove a conversao se o convertido
responder o mesmo que o original dentro de um teto declarado -- e recusa se a
classe vencedora mudar em qualquer sonda.

A ORDEM DAS CLASSES E A INVARIANTE 8, e ela atravessa este arquivo sem
transformacao nenhuma: a saida vem na mesma ordem do eixo de logits do
checkpoint (0 insatisfeito, 1 neutro, 2 satisfeito). Nao ha reordenacao aqui,
e nao pode haver -- inverter a ordem nao levanta erro, faz o sistema pontuar ao
contrario em silencio.

O softmax e feito a mao porque o grafo exportado termina nos LOGITS, e nao
porque alguem quis reimplementar numpy: o `AutoModelForSequenceClassification`
tambem devolve logits, e o softmax sempre morou do lado de fora.
"""

import os
from pathlib import Path

import numpy as np

TAMANHO_MAXIMO = 192


class ModeloOnnxAusenteError(RuntimeError):
    """Grafo ONNX nao encontrado ou ilegivel. Falha alta, como a do torch.

    Invariante 7: servir predicao sem modelo carregado e pior que estar fora do
    ar. Trocar o backend nao afrouxa isso -- so muda qual arquivo falta.
    """


def _softmax(logits: np.ndarray) -> np.ndarray:
    """Softmax estavel por linha -- o maximo sai antes de exponenciar.

    Sem subtrair o maximo, um logit grande estoura o `exp` em `inf` e a linha
    inteira vira `nan`. Com int8 os logits chegam com magnitude ligeiramente
    diferente da do fp32, entao a estabilidade aqui deixa de ser preciosismo.
    """
    deslocado = logits - logits.max(axis=-1, keepdims=True)
    exponenciais = np.exp(deslocado)
    return exponenciais / exponenciais.sum(axis=-1, keepdims=True)


class SessaoOnnx:
    """Um grafo ONNX quantizado mais o tokenizador dele.

    Expoe `prever`, com a MESMA forma de `ClassificadorTexto.prever_mensagens`:
    lista de textos entra, lista de listas de probabilidade sai. E o que
    permite trocar o backend sem que o `Motor`, os sinais ou o fusor saibam
    que a troca aconteceu.
    """

    def __init__(self, diretorio: Path) -> None:
        diretorio = Path(diretorio)
        grafo = diretorio / "model.onnx"
        if not grafo.is_file():
            raise ModeloOnnxAusenteError(
                f"grafo ONNX nao encontrado em {grafo}. "
                "Rode `uv run python scripts/encolher_modelos.py` sobre os "
                "checkpoints de modelos/. Ver docs/treinamento.md."
            )
        try:
            import onnxruntime
            from transformers import AutoTokenizer

            self._tokenizador = AutoTokenizer.from_pretrained(str(diretorio))
            # Threads por passada. Ja nao precisa ser 1 por previsibilidade: o
            # `Motor` deixa entrar no modelo uma passada por vez (semaforo
            # `FRAUS_INFERENCIAS_SIMULTANEAS`), entao a passada que entra pode
            # usar os nucleos. 0 = o runtime escolhe (nucleos fisicos).
            opcoes = onnxruntime.SessionOptions()
            opcoes.intra_op_num_threads = int(os.environ.get("FRAUS_ONNX_THREADS", "0"))
            # Sem arena: o alocador de CPU do runtime reserva blocos e nao os
            # devolve. Medido em 15/09/2026 com o app montado e 30 conversas:
            # pico 1.445 MB -> 1.347 MB, mesmos scores, sem perder velocidade
            # (180 conversas em 33 s contra 35 s).
            opcoes.enable_cpu_mem_arena = False
            opcoes.graph_optimization_level = (
                onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
            )
            self._sessao = onnxruntime.InferenceSession(
                str(grafo), opcoes, providers=["CPUExecutionProvider"]
            )
        except ModeloOnnxAusenteError:
            raise
        except Exception as erro:
            raise ModeloOnnxAusenteError(
                f"grafo ONNX em {diretorio} ilegivel: {erro}"
            ) from erro

        # O grafo exportado declara quais entradas aceita, e isso varia com a
        # versao do exportador -- alguns trazem `token_type_ids`, outros nao.
        # Perguntar ao grafo em vez de assumir evita o erro mais chato do
        # ONNX Runtime, que e recusar uma entrada a mais sem dizer qual.
        self._entradas = {entrada.name for entrada in self._sessao.get_inputs()}

    def prever(self, textos: list[str]) -> list[list[float]]:
        """Probabilidades por texto, na ORDEM DE CLASSES do checkpoint."""
        if not textos:
            return []
        codificado = self._tokenizador(
            textos,
            truncation=True,
            max_length=TAMANHO_MAXIMO,
            padding=True,
            return_tensors="np",
        )
        entradas = {
            nome: valor.astype(np.int64)
            for nome, valor in codificado.items()
            if nome in self._entradas
        }
        (logits,) = self._sessao.run(None, entradas)
        return _softmax(np.asarray(logits, dtype=np.float32)).tolist()


class SessaoMultitarefaOnnx(SessaoOnnx):
    """Um unico encoder BERTimbau com tres cabecas de classificacao.

    Os nomes das saidas fazem parte do artefato: depender da ordem retornada
    pelo exportador permitiria trocar emocao por satisfacao sem erro visivel.
    """

    SAIDAS = {
        "satisfacao": "satisfacao_logits",
        "emocao": "emocao_logits",
        "ironia": "ironia_logits",
    }

    def __init__(self, diretorio: Path) -> None:
        super().__init__(diretorio)
        encontradas = {saida.name for saida in self._sessao.get_outputs()}
        ausentes = set(self.SAIDAS.values()) - encontradas
        if ausentes:
            raise ModeloOnnxAusenteError(
                "grafo multitarefa sem as saidas obrigatorias: "
                + ", ".join(sorted(ausentes))
            )

    def prever_cabecas(self, textos: list[str]) -> dict[str, list[list[float]]]:
        if not textos:
            return {nome: [] for nome in self.SAIDAS}
        codificado = self._tokenizador(
            textos,
            truncation=True,
            max_length=TAMANHO_MAXIMO,
            padding=True,
            return_tensors="np",
        )
        entradas = {
            nome: valor.astype(np.int64)
            for nome, valor in codificado.items()
            if nome in self._entradas
        }
        nomes = list(self.SAIDAS.values())
        logits = self._sessao.run(nomes, entradas)
        return {
            cabeca: _softmax(np.asarray(saida, dtype=np.float32)).tolist()
            for cabeca, saida in zip(self.SAIDAS, logits)
        }


class ClassificadorCabecaOnnx:
    """Vista de uma cabeca; as tres vistas apontam para a mesma sessao."""

    def __init__(self, multitarefa: SessaoMultitarefaOnnx, nome: str) -> None:
        if nome not in multitarefa.SAIDAS:
            raise ValueError(f"cabeca multitarefa desconhecida: {nome}")
        self.multitarefa = multitarefa
        self.nome = nome

    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        return self.multitarefa.prever_cabecas(textos)[self.nome]


def classificadores_multitarefa(caminho_modelo):
    """Tres interfaces legadas sobre UMA sessao e UM conjunto de pesos."""
    sessao = SessaoMultitarefaOnnx(caminho_modelo)
    return tuple(
        ClassificadorCabecaOnnx(sessao, nome)
        for nome in ("satisfacao", "emocao", "ironia")
    )


class ClassificadorOnnx:
    """Adaptador: um `SessaoOnnx` com a MESMA interface dos tres do torch.

    Os tres classificadores (`ClassificadorTexto`, `ClassificadorEmocao`,
    `ClassificadorIronia`) expoem exatamente um metodo para quem consome --
    `prever_mensagens(textos) -> list[list[float]]` -- e nada no `Motor`, nos
    sinais ou no fusor sabe qual biblioteca esta por baixo. Por isso trocar o
    backend nao exige tocar em nenhum deles: exige um objeto com este metodo.

    O que ele NAO faz: interpretar o significado das colunas. A ordem das
    classes e a do checkpoint, e cada sinal ja sabe ler a sua (invariante 8).
    Um adaptador que "arrumasse" a ordem seria o jeito mais rapido de inverter
    a pontuacao em silencio.
    """

    def __init__(self, caminho_modelo) -> None:
        self._sessao = SessaoOnnx(caminho_modelo)

    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        return self._sessao.prever(textos)
