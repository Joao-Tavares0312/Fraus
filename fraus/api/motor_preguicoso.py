"""Provedor thread-safe que tira os modelos do caminho das rotas leves.

O provedor se comporta como o motor depois do primeiro acesso a um atributo.
Antes disso, seu estado pode ser consultado sem construir classificadores nem
abrir sessoes ONNX. Uma falha e memorizada e sempre volta a subir: nunca existe
fallback para motor sintetico ou parcialmente carregado.
"""

from collections.abc import Callable
from threading import Condition, Thread
from typing import Literal

from fraus.api.observabilidade import medir
from fraus.motor import Motor

EstadoDoMotor = Literal["frio", "carregando", "pronto", "erro"]


class ProvedorDeMotor:
    """Constroi exatamente um ``Motor``, inclusive com chamadas concorrentes."""

    def __init__(
        self,
        construir: Callable[[], Motor],
        regua: Callable[[], str | None] | None = None,
    ) -> None:
        self._construir = construir
        self._regua_barata = regua
        self._regua_lida: tuple[str | None] | None = None
        self._motor: Motor | None = None
        self._erro: Exception | None = None
        self._estado: EstadoDoMotor = "frio"
        self._condicao = Condition()

    @property
    def estado(self) -> EstadoDoMotor:
        """Retrato instantaneo; consultar nunca inicia a carga."""
        with self._condicao:
            return self._estado

    def aquecer(self) -> bool:
        """Comeca a carga em segundo plano e volta na hora.

        Idempotente: so dispara quando o estado e ``frio``. Existe porque o
        motor so carregava na primeira PREDICAO, entao cada instancia serverless
        nova mostrava ``frio`` ate alguem pagar a carga dentro da requisicao.
        Uma falha fica memorizada no estado (``erro``) como sempre, sem
        fallback; a thread nunca propaga excecao para quem chamou.

        Devolve se esta chamada iniciou a carga.
        """
        with self._condicao:
            if self._estado != "frio":
                return False
        Thread(target=self._carregar_calado, name="aquecer-motor", daemon=True).start()
        return True

    def _carregar_calado(self) -> None:
        try:
            self.carregar()
        except Exception:  # noqa: BLE001 - o erro ja ficou memorizado no estado
            pass

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
            motor = medir("carga_modelo", self._construir)
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

    def regua(self) -> str | None:
        """A regua vigente, sem carregar os modelos quando ha como.

        Rota de LEITURA pergunta a regua: `/indicadores` conta quem ficou na
        regua antiga a cada abertura da Visao geral. Pelo `__getattr__` a
        pergunta esperava as tres sessoes ONNX -- 10 a 12 s numa instancia nova
        (producao, 02/10/2026), a dashboard desistia e caia no agregado de
        reserva. A regua so depende do fusor, que e um arquivo pequeno.

        Sem o atalho (provedor montado so com `construir`), vale o de sempre.
        """
        with self._condicao:
            if self._estado == "pronto":
                assert self._motor is not None
                return self._motor.regua()
            if self._regua_lida is not None:
                return self._regua_lida[0]
        if self._regua_barata is None:
            return self.carregar().regua()
        lida = self._regua_barata()
        with self._condicao:
            self._regua_lida = (lida,)
        return lida

    def __getattr__(self, nome: str):
        """Mantem o contrato existente das rotas sem esconder a carga."""
        atributo = getattr(self.carregar(), nome)
        if not callable(atributo) or nome not in {
            "pontuar_conversa",
            "atribuir_conversa",
            "analisar_conversa",
            "simular_texto",
            "deriva_da_amostra",
            "eixo_global",
        }:
            return atributo

        def cronometrado(*args, **kwargs):
            return medir("inferencia", lambda: atributo(*args, **kwargs))

        return cronometrado


def motor_e_real(motor: object) -> bool:
    """Distingue motor real (carregado ou prometido) de dublê."""
    return isinstance(motor, (Motor, ProvedorDeMotor))


def estado_do_motor(motor: object) -> EstadoDoMotor:
    """Estado uniforme para motor injetado e para o provedor tardio."""
    if isinstance(motor, ProvedorDeMotor):
        return motor.estado
    return "pronto"
