"""Servidor de DEMONSTRACAO do Dolos -- APENAS para desenvolver a interface.

=============================================================================
NUNCA USE ISTO EM PRODUCAO. Este servidor NAO carrega o BERTimbau nem o fusor:
ele substitui o Motor real por um dublê deterministico que pontua a conversa a
partir de contagem de palavras e emojis do proprio texto. O numero que sai daqui
NAO e uma predicao do modelo -- e um valor sintetico, estavel, cuja unica funcao
e dar a dashboard dados com a forma certa (faixas, nulos, datas) enquanto o
modelo da Task 6 ainda nao foi treinado no Colab.

O `app` real vive em `dolos.api.main` e falha alto sem `modelos/` -- e isso e
por design. Este arquivo existe porque a Task 10 precisa de uma API no ar antes
disso, nao porque o comportamento real seja opcional.

Como rodar:
    uv run python scripts/api_demo.py
    # -> http://localhost:8000  (banco temporario, recriado a cada boot)
=============================================================================
"""

from __future__ import annotations

import sys
import tempfile
from datetime import timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import uvicorn  # noqa: E402

from dolos.api.main import criar_app  # noqa: E402
from dolos.db import Banco  # noqa: E402
from dolos.fusor import NOMES_FEATURES  # noqa: E402
from dolos.indicadores import categoria_nps  # noqa: E402
from dolos.ingest.simulador import INICIO, gerar_lote  # noqa: E402
from dolos.modelos import Conversa, Mensagem  # noqa: E402
from dolos.sinais.tempo import features_tempo  # noqa: E402

# Frases rotuladas: 0 = insatisfeito, 1 = neutro, 2 = satisfeito.
FRASES_POR_ROTULO: dict[int, list[str]] = {
    0: [
        "ja e a terceira vez que eu explico a mesma coisa e ninguem resolve 😡",
        "isso nao me ajudou em nada, quero falar com um atendente de verdade",
        "cancela minha assinatura, perdi a paciencia com esse atendimento",
        "voces cobraram duas vezes no meu cartao e ninguem me da retorno 😤",
        "pessimo, fiquei quase uma hora esperando por uma resposta automatica",
        "nao foi isso que eu perguntei, voce esta lendo o que eu escrevo?",
    ],
    1: [
        "ok, obrigado 🙂",
        "entendi, vou verificar aqui e retorno depois",
        "ta bom entao",
        "certo, e quanto tempo costuma demorar?",
        "so isso mesmo, valeu",
        "hmm, acho que da pra tentar assim",
    ],
    2: [
        "perfeito, resolveu na hora, muito obrigado! 😄",
        "atendimento excelente, voces sao rapidos demais 👏",
        "era exatamente isso que eu precisava, gratidao ❤️",
        "otimo, ja consegui acompanhar meu pedido, valeu mesmo",
        "nossa, que rapidez, adorei o suporte de voces 😍",
        "resolvido! obrigado pela atencao e paciencia",
    ],
}

TERMOS_NEGATIVOS = (
    "pessimo", "nao resolve", "cancela", "terceira vez", "paciencia", "cobraram",
    "esperando", "nao me ajudou", "ninguem", "nao foi isso", "demora", "😡", "😤",
)
TERMOS_POSITIVOS = (
    "perfeito", "excelente", "obrigado", "otimo", "resolveu", "resolvido",
    "rapidez", "rapidos", "adorei", "gratidao", "valeu", "😄", "👏", "❤️", "😍", "🙂",
)


class MotorDuble:
    """Dublê deterministico do Motor real. NAO usa modelo nenhum.

    Score 0-100 derivado do texto do cliente (termos e emojis) e penalizado pela
    latencia mediana das respostas -- so o suficiente para a dashboard exercitar
    as tres faixas de NPS e o trade-off NPS x latencia.
    """

    @staticmethod
    def _probabilidades(texto: str) -> list[float]:
        """[insatisfeito, neutro, satisfeito] a partir da contagem de termos.

        Deterministico e sem modelo -- mesma logica do score do dublê, so que
        por mensagem, para a dashboard exercitar a atribuicao por sentenca.
        """
        minusculo = texto.lower()
        positivos = sum(minusculo.count(t) for t in TERMOS_POSITIVOS)
        negativos = sum(minusculo.count(t) for t in TERMOS_NEGATIVOS)
        bruto = [1.0 + 3.0 * negativos, 1.0, 1.0 + 3.0 * positivos]
        total = sum(bruto)
        return [valor / total for valor in bruto]

    def atribuir_conversa(self, conversa: Conversa) -> dict:
        mensagens = []
        for indice, mensagem in enumerate(conversa.mensagens):
            do_cliente = mensagem.autor == "cliente"
            p = self._probabilidades(mensagem.texto) if do_cliente else [None] * 3
            mensagens.append(
                {
                    "indice": indice,
                    "autor": mensagem.autor,
                    "texto": mensagem.texto,
                    "prob_insatisfeito": p[0],
                    "prob_neutro": p[1],
                    "prob_satisfeito": p[2],
                }
            )
        # Pesos ficticios, so para a interface ter as 16 chaves com forma certa.
        importancias = {
            nome: round(0.2 + 0.05 * (indice % 7), 3)
            for indice, nome in enumerate(NOMES_FEATURES)
        }
        # Contribuicoes ficticias da CONVERSA -- deterministicas, com sinal,
        # so para a interface exercitar o "empurrou pra cima/baixo". Sem
        # fala do cliente nao ha score, entao tambem nao ha contribuicao.
        contribuicoes = (
            {
                nome: round(0.3 * ((indice % 5) - 2), 3)
                for indice, nome in enumerate(NOMES_FEATURES)
            }
            if conversa.tem_sinal_cliente
            else None
        )
        return {
            "mensagens": mensagens,
            "importancias": importancias,
            "contribuicoes": contribuicoes,
        }

    def pontuar_conversa(self, conversa: Conversa) -> float | None:
        if not conversa.tem_sinal_cliente:
            return None  # ausencia de dado nao e insatisfacao

        texto = " ".join(m.texto.lower() for m in conversa.mensagens_cliente)
        positivos = sum(texto.count(t) for t in TERMOS_POSITIVOS)
        negativos = sum(texto.count(t) for t in TERMOS_NEGATIVOS)

        score = 55.0 + 14.0 * positivos - 16.0 * negativos

        latencia = float(features_tempo(conversa).get("latencia_mediana_s", 0.0))
        score -= min(25.0, latencia / 12.0)
        if conversa.escalou_para_humano:
            score -= 8.0

        return max(0.0, min(100.0, round(score, 2)))


def conversa_sem_fala_do_cliente() -> Conversa:
    """Conversa so com o bot: exercita o estado 'sem sinal' na interface."""
    inicio = INICIO + timedelta(days=7, hours=3)
    return Conversa(
        id="demo-sem-sinal-001",
        canal="webchat",
        iniciada_em=inicio,
        encerrada_em=inicio + timedelta(seconds=95),
        escalou_para_humano=False,
        mensagens=[
            Mensagem(
                autor="bot",
                texto="Ola! Sou o assistente virtual. Como posso ajudar?",
                enviada_em=inicio,
            ),
            Mensagem(
                autor="bot",
                texto="Continuo por aqui caso precise de alguma coisa.",
                enviada_em=inicio + timedelta(seconds=45),
            ),
            Mensagem(
                autor="bot",
                texto="Vou encerrar o atendimento por inatividade. Ate logo!",
                enviada_em=inicio + timedelta(seconds=95),
            ),
        ],
    )


def conversa_muda_no_canal_telefone() -> Conversa:
    """Segunda conversa sem sinal, em outro canal -- o estado nao pode parecer bug."""
    inicio = INICIO + timedelta(days=13, hours=11)
    return Conversa(
        id="demo-sem-sinal-002",
        canal="whatsapp",
        iniciada_em=inicio,
        encerrada_em=inicio + timedelta(seconds=30),
        escalou_para_humano=True,
        mensagens=[
            Mensagem(
                autor="bot",
                texto="Transferindo voce para um atendente humano.",
                enviada_em=inicio,
            ),
            Mensagem(
                autor="humano",
                texto="Oi, aqui e a Marina. Esta me ouvindo?",
                enviada_em=inicio + timedelta(seconds=30),
            ),
        ],
    )


CANAIS = ("webchat", "whatsapp", "instagram", "telegram")


def semear(banco: Banco, motor: MotorDuble, quantidade: int = 60) -> int:
    conversas: list[Conversa] = []
    for indice, (conversa, _rotulo) in enumerate(
        gerar_lote(FRASES_POR_ROTULO, quantidade=quantidade, semente=20260813)
    ):
        # canal variado: o simulador marca tudo como "simulado"
        conversas.append(conversa.model_copy(update={"canal": CANAIS[indice % len(CANAIS)]}))

    conversas.append(conversa_sem_fala_do_cliente())
    conversas.append(conversa_muda_no_canal_telefone())

    for conversa in conversas:
        score = motor.pontuar_conversa(conversa)
        banco.salvar(conversa, score, categoria_nps(score) if score is not None else None)
    return len(conversas)


def montar_app():
    caminho = Path(tempfile.gettempdir()) / "dolos-demo.db"
    caminho.unlink(missing_ok=True)
    banco = Banco(caminho)
    banco.migrar()
    motor = MotorDuble()
    total = semear(banco, motor)
    print(f"[api_demo] banco de demonstracao em {caminho} com {total} conversas")
    print("[api_demo] ATENCAO: motor dublê, sem modelo. Nao use em producao.")
    return criar_app(banco=banco, motor=motor)


app = montar_app()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
