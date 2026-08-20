"""Servidor de DEMONSTRACAO do Fraus -- APENAS para desenvolver a interface.

=============================================================================
NUNCA USE ISTO EM PRODUCAO -- mas nao pelo motivo antigo. O que este arquivo
tem de demonstracao e o DADO, nao o modelo: ele semeia um banco temporario com
conversas do simulador e o joga fora a cada boot. Nao ha aqui atendimento de
gente nenhuma.

O MOTOR, esse, e o real desde que os tres BERTimbau treinaram: `montar_motor`
carrega satisfacao, emocao e ironia do disco e so cai no dublê deterministico
se os pesos nao estiverem la (ou com FRAUS_DEMO_DUBLE=1, para iterar na
interface sem esperar o carregamento). O boot imprime qual dos dois subiu, e a
distincao importa: o dublê pontua por contagem de palavra e emoji, um numero
sintetico com forma de predicao.

O `app` de producao vive em `fraus.api.main` e falha alto sem `modelos/`.

Como rodar:
    uv run python scripts/api_demo.py
    # -> http://localhost:8000  (banco temporario, recriado a cada boot)
=============================================================================
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import uvicorn  # noqa: E402

from fraus.api.main import (CAMINHO_FUSOR, CAMINHO_MODELO_EMOCAO,  # noqa: E402
                            CAMINHO_MODELO_IRONIA, CAMINHO_MODELO_TEXTO,
                            Motor, criar_app)
from fraus.db import Banco  # noqa: E402
from fraus.fusor import NOMES_FEATURES, Fusor  # noqa: E402
from fraus.indicadores import categoria_nps  # noqa: E402
from fraus.ingest.simulador import (FRASES_POR_ROTULO, INICIO,  # noqa: E402
                                    gerar_lote)
from fraus.modelos import Conversa, Mensagem  # noqa: E402
from fraus.sinais.emocao import ClassificadorEmocao  # noqa: E402
from fraus.sinais.emoji import emojis_com_posicao, score_do_emoji  # noqa: E402
from fraus.sinais.ironia import ClassificadorIronia  # noqa: E402
from fraus.sinais.tempo import features_tempo  # noqa: E402
from fraus.sinais.texto import ClassificadorTexto  # noqa: E402


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

    def importancias(self) -> dict:
        # Mesmos pesos ficticios de `atribuir_conversa`, so para a ficha do
        # modelo em `/modelo` ter as 16 chaves com forma certa.
        return {
            nome: round(0.2 + 0.05 * (indice % 7), 3)
            for indice, nome in enumerate(NOMES_FEATURES)
        }

    def simular_texto(self, texto: str) -> dict:
        p = self._probabilidades(texto)
        emojis = [
            {"emoji": emoji, "score": score_do_emoji(emoji), "posicao_relativa": posicao}
            for emoji, posicao in emojis_com_posicao(texto)
        ]
        return {
            "prob_insatisfeito": p[0],
            "prob_neutro": p[1],
            "prob_satisfeito": p[2],
            "emojis": emojis,
        }


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


def dia_inteiro_sem_sinal() -> list[Conversa]:
    """Um DIA em que nenhum atendimento teve fala do cliente.

    As duas conversas mudas anteriores caem em dias que TAMBEM tem atendimento
    pontuado, entao o dia inteiro ainda soa e a interface o desenha cheio. Este
    dia existe para exercitar o caso que o produto precisa saber mostrar: houve
    movimento, e nenhum dele virou medicao.

    E o unico jeito de ver a cabeca vazada da faixa de presenca -- o marcador
    que ocupa o tempo e nao soa. Sem um dia assim, a regra "ausencia de dado
    nao e insatisfacao" fica escrita no codigo e invisivel na tela.
    """
    dia = INICIO + timedelta(days=21, hours=8)
    return [
        Conversa(
            id="demo-dia-mudo-001",
            canal="instagram",
            iniciada_em=dia,
            encerrada_em=dia + timedelta(seconds=60),
            escalou_para_humano=False,
            mensagens=[
                Mensagem(
                    autor="bot",
                    texto="Oi! Vi que voce abriu o chat. Posso ajudar em algo?",
                    enviada_em=dia,
                ),
                Mensagem(
                    autor="bot",
                    texto="Encerrando por inatividade. Volte quando quiser.",
                    enviada_em=dia + timedelta(seconds=60),
                ),
            ],
        ),
        Conversa(
            id="demo-dia-mudo-002",
            canal="telegram",
            iniciada_em=dia + timedelta(hours=6),
            encerrada_em=dia + timedelta(hours=6, seconds=40),
            escalou_para_humano=False,
            mensagens=[
                Mensagem(
                    autor="bot",
                    texto="Bom dia! Este e o atendimento automatico.",
                    enviada_em=dia + timedelta(hours=6),
                ),
                Mensagem(
                    autor="bot",
                    texto="Sem resposta por aqui, vou fechar o chamado.",
                    enviada_em=dia + timedelta(hours=6, seconds=40),
                ),
            ],
        ),
    ]


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
    conversas.extend(dia_inteiro_sem_sinal())

    for conversa in conversas:
        score = motor.pontuar_conversa(conversa)
        banco.salvar(conversa, score, categoria_nps(score) if score is not None else None)
    return len(conversas)


def montar_motor():
    """Motor REAL quando os pesos estao no disco; dublê so quando nao estao.

    A precedencia inverteu de proposito no dia em que os tres BERTimbau
    treinaram. Enquanto o modelo nao existia, o dublê era a unica forma de ter
    a dashboard de pe -- mas manter ele no comando DEPOIS do treino faria a
    tela seguir exibindo contagem de palavra com cara de predicao, que e o
    genero de mentira que ninguem percebe porque os numeros continuam bonitos.

    O que decide e a presenca dos arquivos, nao uma flag: flag desligada por
    engano voltaria ao dublê em silencio. `FRAUS_DEMO_DUBLE=1` forca o dublê
    para quem quiser iterar na interface sem esperar o modelo carregar.
    """
    if os.environ.get("FRAUS_DEMO_DUBLE") == "1":
        print("[api_demo] FRAUS_DEMO_DUBLE=1 -- dublê forcado, numeros SINTETICOS.")
        return MotorDuble()

    if not CAMINHO_MODELO_TEXTO.is_dir() or not CAMINHO_FUSOR.is_file():
        print(
            f"[api_demo] ATENCAO: motor dublê, sem modelo em {CAMINHO_MODELO_TEXTO}/. "
            "Numeros SINTETICOS. Nao use em producao."
        )
        return MotorDuble()

    print("[api_demo] carregando os modelos reais (CPU, leva alguns segundos)...")
    classificador = ClassificadorTexto(CAMINHO_MODELO_TEXTO)
    fusor = Fusor.carregar(CAMINHO_FUSOR)
    emocao = ClassificadorEmocao(CAMINHO_MODELO_EMOCAO) if CAMINHO_MODELO_EMOCAO.is_dir() else None
    ironia = ClassificadorIronia(CAMINHO_MODELO_IRONIA) if CAMINHO_MODELO_IRONIA.is_dir() else None
    carregadas = ["satisfacao"] + [n for n, c in (("emocao", emocao), ("ironia", ironia)) if c]
    print(f"[api_demo] motor REAL. Cabecas carregadas: {', '.join(carregadas)}.")
    return Motor(classificador, fusor, emocao=emocao, ironia=ironia)


def montar_app():
    caminho = Path(tempfile.gettempdir()) / "fraus-demo.db"
    try:
        caminho.unlink(missing_ok=True)
    except PermissionError:
        # No Windows o arquivo continua travado enquanto outra instancia da demo
        # o mantiver aberto. Cair para um nome unico e melhor que recusar o boot:
        # o banco e descartavel e resemeado do zero a cada subida.
        caminho = Path(tempfile.mkdtemp(prefix="fraus-demo-")) / "fraus-demo.db"
    banco = Banco(caminho)
    banco.migrar()
    motor = montar_motor()
    total = semear(banco, motor)
    print(f"[api_demo] banco de demonstracao em {caminho} com {total} conversas")
    # A mesma leitura de `criar_app_padrao`: a doc de hospedagem promete que
    # definir FRAUS_CHAVE_MESTRA protege a API, e quem sobe o tunel pela demo
    # tinha essa promessa quebrada em silencio -- a variavel era ignorada aqui.
    chave_mestra = os.environ.get("FRAUS_CHAVE_MESTRA") or None
    if chave_mestra is None:
        print(
            "[api_demo] AVISO: API sem autenticacao (uso local). "
            "Defina FRAUS_CHAVE_MESTRA para exigir chave em todas as rotas."
        )
    else:
        # A demo NAO passa por `ligar_no_primeiro_uso` -- e nem deveria: com a
        # mestra vindo do ambiente, aquele fluxo tambem nao grava nada na API
        # real, porque a variavel VENCE a gravada e escrever em disco uma chave
        # gerada seria guardar credencial que nao abre nada.
        #
        # A consequencia e que aqui nao existe chave de ACESSO em lugar nenhum:
        # a API sobe fechada e a dashboard toma 401 em toda tela, sem nada na
        # saida dizendo como sair disso. Fechar em silencio e o que transforma
        # uma protecao em parede -- entao a saida ensina o caminho inteiro.
        print(
            "[api_demo] API FECHADA pela FRAUS_CHAVE_MESTRA do ambiente.\n"
            "  Nenhuma chave de acesso existe ainda -- a dashboard levara 401.\n"
            "  Emita uma e entregue a ela:\n"
            "    curl -X POST localhost:8000/acesso/chaves \\\n"
            "      -H \"Authorization: Bearer $FRAUS_CHAVE_MESTRA\" \\\n"
            "      -H 'content-type: application/json' -d '{\"nome\": \"dashboard\"}'\n"
            "    cd dashboard && FRAUS_CHAVE_ACESSO=<a chave fra_...> npm run dev\n"
            "  A chave morre junto com este banco: a demo o recria a cada boot."
        )
    return criar_app(banco=banco, motor=motor, chave_mestra=chave_mestra)


app = montar_app()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
