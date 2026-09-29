"""Adaptador do Laya multilíngue para o contrato binário de ironia do Fraus.

O Laya continua opcional: importar o Fraus ou usar BERTimbau/ONNX não pode
arrastar torch nem baixar pesos. A dependência e o checkpoint só são tocados
quando ``FRAUS_IRONIA_BACKEND=laya`` é declarado.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
import json
import os
from pathlib import Path
import sys
import types
from typing import Any


REVISAO_LAYA_PADRAO = "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851"

PERGUNTA_IRONIA = {
    "ironia": {
        "type": "choice",
        "instructions": (
            "A fala do cliente é irônica? Considere incongruência entre o "
            "sentido literal e a situação descrita."
        ),
        # Chaves neutras evitam o viés documentado dos rótulos true/false.
        "criteria": {
            "A": "há ironia ou incongruência entre elogio literal e situação negativa",
            "B": "a fala é literal e não irônica",
        },
    }
}

INSTRUCAO_PADRAO = PERGUNTA_IRONIA["ironia"]["instructions"]
CRITERIO_IRONICO_PADRAO = PERGUNTA_IRONIA["ironia"]["criteria"]["A"]
CRITERIO_LITERAL_PADRAO = PERGUNTA_IRONIA["ironia"]["criteria"]["B"]


class DependenciaLayaAusenteError(RuntimeError):
    pass


class RespostaLayaInvalidaError(RuntimeError):
    pass


def revisao_laya_declarada() -> str:
    return os.environ.get("FRAUS_LAYA_REVISAO") or REVISAO_LAYA_PADRAO


class ClassificadorIroniaLaya:
    """Expõe ``prever_mensagens`` no mesmo formato das cabeças existentes."""

    def __init__(
        self,
        *,
        router: Any | None = None,
        revisao: str = REVISAO_LAYA_PADRAO,
        modelo: str = "multilingual",
    ) -> None:
        if router is None:
            try:
                from laya import Router
            except ImportError as erro:
                raise DependenciaLayaAusenteError(
                    "O backend de ironia Laya exige `uv sync --extra laya`."
                ) from erro
            router = Router(revision=revisao, max_loaded=1)
        self._router = router
        self._modelo = modelo

    @staticmethod
    def _probabilidade_ironia(resultado: dict[str, Any]) -> float:
        try:
            probabilidades = resultado["answers"]["ironia"]["probabilities"]
            probabilidade = float(probabilidades["A"])
        except (KeyError, TypeError, ValueError) as erro:
            raise RespostaLayaInvalidaError(
                "Laya não devolveu answers.ironia.probabilities.A"
            ) from erro
        if not 0.0 <= probabilidade <= 1.0:
            raise RespostaLayaInvalidaError("probabilidade de ironia fora de 0..1")
        return probabilidade

    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        if not textos:
            return []
        requisicoes = [
            {
                "state": texto,
                "questions": PERGUNTA_IRONIA,
                "model": self._modelo,
                "lang": "pt",
            }
            for texto in textos
        ]
        resultados: Sequence[dict[str, Any]] = self._router.predict_batch(
            requisicoes, sort_by_length=True
        )
        if len(resultados) != len(textos):
            raise RespostaLayaInvalidaError("Laya devolveu quantidade inesperada de respostas")
        probabilidades = [self._probabilidade_ironia(resultado) for resultado in resultados]
        return [[1.0 - probabilidade, probabilidade] for probabilidade in probabilidades]

    def prever_configurado(
        self,
        texto: str,
        *,
        contexto: str = "",
        instrucao: str = INSTRUCAO_PADRAO,
        criterio_ironico: str = CRITERIO_IRONICO_PADRAO,
        criterio_literal: str = CRITERIO_LITERAL_PADRAO,
    ) -> float:
        """Avalia uma fala com esquema editável, sem mudar o perfil global."""
        estado: str | dict[str, str] = texto
        if contexto.strip():
            estado = {"contexto_anterior": contexto.strip(), "fala_do_cliente": texto}
        perguntas = {
            "ironia": {
                "type": "choice",
                "instructions": instrucao,
                "criteria": {"A": criterio_ironico, "B": criterio_literal},
            }
        }
        resultado = self._router.predict(
            estado, perguntas, model=self._modelo, lang="pt"
        )
        return self._probabilidade_ironia(resultado)


def _corrigir_config_tokenizador(caminho: str) -> None:
    """Compatibilidade do ONNXAgent sem importar ``laya.agent`` (e torch).

    O Laya 0.3.21 reutiliza esta funcao do runtime PyTorch no construtor ONNX.
    Em producao instalamos o pacote sem dependencias para manter torch fora da
    Large Function; o pequeno ajuste abaixo e equivalente ao upstream para os
    dois campos que podem impedir o AutoTokenizer de abrir o checkpoint.
    """
    arquivo = Path(caminho) / "tokenizer" / "tokenizer_config.json"
    if not arquivo.is_file():
        return
    configuracao = json.loads(arquivo.read_text(encoding="utf-8"))
    mudou = False
    if configuracao.get("tokenizer_class") in (None, "TokenizersBackend"):
        configuracao["tokenizer_class"] = "PreTrainedTokenizerFast"
        configuracao.pop("backend", None)
        configuracao.pop("is_local", None)
        mudou = True
    extras = configuracao.get("extra_special_tokens")
    if isinstance(extras, list):
        configuracao["extra_special_tokens"] = {
            f"extra_{indice}": token for indice, token in enumerate(extras)
        }
        mudou = True
    if mudou:
        arquivo.write_text(json.dumps(configuracao, indent=2) + "\n", encoding="utf-8")


def _carregar_classe_onnx_agent():
    """Carrega o runtime oficial ONNX sem acionar o modulo PyTorch do Laya."""
    try:
        from laya.onnx_agent import ONNXAgent
    except ImportError as erro:
        raise DependenciaLayaAusenteError(
            "O backend Laya ONNX exige laya==0.3.21 instalado sem dependencias."
        ) from erro

    # ONNXAgent importa laya.agent apenas no construtor para obter a funcao
    # acima. Esse modulo importa torch no topo. O shim preserva o runtime ONNX
    # puro e fica deliberadamente limitado a versao pinada no deploy.
    if "laya.agent" not in sys.modules:
        compatibilidade = types.ModuleType("laya.agent")
        compatibilidade._fix_tokenizer_config = _corrigir_config_tokenizador
        sys.modules["laya.agent"] = compatibilidade
    return ONNXAgent


class ClassificadorIroniaLayaOnnx(ClassificadorIroniaLaya):
    """Laya multilíngue exportado para ONNX/INT8, sem Router nem PyTorch."""

    def __init__(self, *, agente: Any | None = None, diretorio: Path | None = None) -> None:
        if agente is None:
            from fraus.api.caminhos import CAMINHO_ONNX_LAYA

            diretorio = diretorio or CAMINHO_ONNX_LAYA
            classe = _carregar_classe_onnx_agent()
            agente = classe(
                str(diretorio),
                onnx_path=str(diretorio / "laya.int8.onnx"),
            )
        self._agente = agente

    def prever_mensagens(self, textos: list[str]) -> list[list[float]]:
        if not textos:
            return []
        resultados = self._agente.predict_batch(
            textos, PERGUNTA_IRONIA, lang="pt", sort_by_length=True
        )
        probabilidades = [self._probabilidade_ironia(resultado) for resultado in resultados]
        return [[1.0 - probabilidade, probabilidade] for probabilidade in probabilidades]

    def prever_configurado(
        self,
        texto: str,
        *,
        contexto: str = "",
        instrucao: str = INSTRUCAO_PADRAO,
        criterio_ironico: str = CRITERIO_IRONICO_PADRAO,
        criterio_literal: str = CRITERIO_LITERAL_PADRAO,
    ) -> float:
        estado: str | dict[str, str] = texto
        if contexto.strip():
            estado = {"contexto_anterior": contexto.strip(), "fala_do_cliente": texto}
        perguntas = {
            "ironia": {
                "type": "choice",
                "instructions": instrucao,
                "criteria": {"A": criterio_ironico, "B": criterio_literal},
            }
        }
        resultado = self._agente.system_one(estado, perguntas, lang="pt")
        return self._probabilidade_ironia(resultado)


@lru_cache(maxsize=1)
def obter_classificador_ironia_laya() -> ClassificadorIroniaLaya:
    """Uma instância por processo, compartilhada pela API e pelo Motor."""
    return ClassificadorIroniaLaya(revisao=revisao_laya_declarada())


@lru_cache(maxsize=1)
def obter_classificador_ironia_laya_onnx() -> ClassificadorIroniaLayaOnnx:
    return ClassificadorIroniaLayaOnnx()


def obter_classificador_ironia_laya_declarado():
    from fraus.api.caminhos import backend_ironia_declarado

    if backend_ironia_declarado() == "laya-onnx":
        return obter_classificador_ironia_laya_onnx()
    return obter_classificador_ironia_laya()
