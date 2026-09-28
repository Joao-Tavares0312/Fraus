"""Regua de transferencia de dominio da cabeca de ironia.

Nao e um corpus humano nem uma estimativa de desempenho no mundo real. E uma
suite de contraexemplos escrita para detectar os dois atalhos conhecidos do
corpus sintetico: confundir marcador conversacional com ironia e exigir um
marcador explicito para reconhecer incongruencia. Por isso seus numeros devem
ser publicados como *taxas na regua de dominio*, nunca como acuracia externa.

As falas moram aqui, e nao em scripts ou notebooks, para que treino, laudo e
teste usem exatamente a mesma regua. Elas nao podem entrar no treino.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass

from fraus.sinais.ironia import IRONICO


SINCERAS_COM_MARCADOR = (
    "nossa, resolveu rapidinho, obrigado",
    "realmente o atendimento foi muito bom",
    "que atendimento bom, parabens pra equipe",
    "nossa, finalmente consegui emitir o boleto, valeu",
    "foi rapido ne, gostei",
    "realmente precisava disso, muito obrigada",
    "que alivio, o pedido chegou certinho",
    "nossa que eficiencia, ja caiu o estorno",
    "ne, bem melhor que da ultima vez, obrigado",
    "realmente, agora funcionou",
)

IRONIAS_SEM_MARCADOR = (
    "excelente, terceira vez que explico a mesma coisa",
    "otimo servico, so levou duas semanas pra responder",
    "adorei ficar uma hora ouvindo musica de espera",
    "parabens, conseguiram perder meu pedido de novo",
    "maravilha, o protocolo nao existe no sistema",
    "show, cobraram duas vezes",
    "perfeito, cancelaram sem avisar",
    "incrivel como ninguem sabe responder nada",
    "amei o robo que nao entende portugues",
    "muito eficiente, fecharam o chamado sem resolver",
)


@dataclass(frozen=True)
class ResultadoReguaIronia:
    """Medidas descritivas da regua; nenhuma e metrica de corpus externo."""

    exemplos_sinceros: int
    exemplos_ironicos: int
    falsos_positivos: int
    falsos_negativos: int
    taxa_falso_positivo: float
    taxa_falso_negativo: float
    maior_confianca_errada: float

    def como_dict(self) -> dict[str, int | float | str]:
        return {
            **asdict(self),
            "tipo_avaliacao": "regua_de_contraexemplos_autoral_nao_independente",
        }


def avaliar_probabilidades(
    probabilidades_sinceras: Sequence[float],
    probabilidades_ironicas: Sequence[float],
    *,
    limiar: float = 0.5,
) -> ResultadoReguaIronia:
    """Calcula erros sem esconder conjunto vazio nem probabilidade invalida."""
    if not probabilidades_sinceras or not probabilidades_ironicas:
        raise ValueError("a regua exige exemplos sinceros e ironicos")
    todas = [*probabilidades_sinceras, *probabilidades_ironicas]
    if any(p < 0.0 or p > 1.0 for p in todas):
        raise ValueError("probabilidade de ironia fora de 0..1")

    erros_sinceros = [p for p in probabilidades_sinceras if p > limiar]
    erros_ironicos = [p for p in probabilidades_ironicas if p <= limiar]
    # Confianca na classe errada: P(ironia) no falso positivo e P(nao-ironia)
    # no falso negativo. Zero significa que nao houve erro nessa regua.
    confiancas_erradas = [*erros_sinceros, *(1.0 - p for p in erros_ironicos)]
    return ResultadoReguaIronia(
        exemplos_sinceros=len(probabilidades_sinceras),
        exemplos_ironicos=len(probabilidades_ironicas),
        falsos_positivos=len(erros_sinceros),
        falsos_negativos=len(erros_ironicos),
        taxa_falso_positivo=len(erros_sinceros) / len(probabilidades_sinceras),
        taxa_falso_negativo=len(erros_ironicos) / len(probabilidades_ironicas),
        maior_confianca_errada=max(confiancas_erradas, default=0.0),
    )


def avaliar_classificador(classificador, *, limiar: float = 0.5) -> ResultadoReguaIronia:
    """Executa a regua em qualquer backend com ``prever_mensagens``."""
    sinceras = [p[IRONICO] for p in classificador.prever_mensagens(list(SINCERAS_COM_MARCADOR))]
    ironicas = [p[IRONICO] for p in classificador.prever_mensagens(list(IRONIAS_SEM_MARCADOR))]
    return avaliar_probabilidades(sinceras, ironicas, limiar=limiar)


def candidato_apto_para_promocao(
    resultado: ResultadoReguaIronia,
    *,
    maximo_falso_positivo: float = 0.30,
    maximo_falso_negativo: float = 0.30,
) -> bool:
    """Portao conservador para artefato candidato, nao alegacao de qualidade."""
    return (
        resultado.taxa_falso_positivo <= maximo_falso_positivo
        and resultado.taxa_falso_negativo <= maximo_falso_negativo
    )
