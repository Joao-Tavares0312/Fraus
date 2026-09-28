"""Provedor thread-safe que tira os modelos do caminho das rotas leves.

O provedor se comporta como o motor depois do primeiro acesso a um atributo.
Antes disso, seu estado pode ser consultado sem construir classificadores nem
abrir sessoes ONNX. Uma falha e memorizada e sempre volta a subir: nunca existe
fallback para motor sintetico ou parcialmente carregado.
"""

from collections.abc import Callable
from threading import Condition
from typing import Literal

from fraus.motor import Motor

EstadoDoMotor = Literal["frio", "carregando", "pronto", "erro"]


class ProvedorDeMotor:
    """Constroi exatamente um ``Motor``, inclusive com chamadas concorrentes."""

    def __init__(self, construir: Callable[[], Motor]) -> None:
        self._construir = construir
        self._motor: Motor | None = None
        self._erro: Exception | None = None
        self._estado: EstadoDoMotor = "frio"
        self._condicao = Condition()

    @property
    def estado(self) -> EstadoDoMotor:
        """Retrato instantaneo; consultar nunca inicia a carga."""
        with self._condicao:
            return self._estado

    def carregar(self) -> Motor:
        """Entrega o motor ou propaga a falha original, sem nova tentativa."""
        with self._condicao:
            while self._estado == "carregando":
                self._condicao.wait()
            if self._estado == "pronto":
                assert self._motor is not None
                return self._motor
            if self._estado == "erro":
                assert self._erro is not None
                raise self._erro
            self._estado = "carregando"

        try:
            motor = self._construir()
        except Exception as erro:
            with self._condicao:
                self._erro = erro
                self._estado = "erro"
                self._condicao.notify_all()
            raise

        with self._condicao:
            self._motor = motor
            self._estado = "pronto"
            self._condicao.notify_all()
            return motor

    def __getattr__(self, nome: str):
        """Mantem o contrato existente das rotas sem esconder a carga."""
        return getattr(self.carregar(), nome)


def motor_e_real(motor: object) -> bool:
    """Distingue motor real (carregado ou prometido) de dublê."""
    return isinstance(motor, (Motor, ProvedorDeMotor))


def estado_do_motor(motor: object) -> EstadoDoMotor:
    """Estado uniforme para motor injetado e para o provedor tardio."""
    if isinstance(motor, ProvedorDeMotor):
        return motor.estado
    return "pronto"
