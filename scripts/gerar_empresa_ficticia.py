"""Gera a empresa ficticia da banca: a Lumen Telecom, provedor de internet.

156 atendimentos FABRICADOS, todos com id `sintetica-lumen-*`, para a demo de
09/12/2026. Nao e corpus de treino nem de avaliacao: o sinal de tempo foi
treinado em `fraus/ingest/simulador.py`, e reaproveitar aquele gerador aqui
faria a demo medir o modelo na propria distribuicao de treino (circular).

O que o gerador garante, e por que:

- **Deterministico** (`random.Random(20261209)`): rodar de novo da os mesmos
  bytes, e reenviar os mesmos ids SUBSTITUI no Fraus em vez de duplicar.
- **Faixas de espera sobrepostas entre tons** (5-90 s insatisfeito, 3-60 s
  neutro, 3-45 s satisfeito). Faixa disjunta por classe entrega o rotulo pelo
  relogio -- foi o que fez o primeiro fusor marcar 99,3% (invariante 10).
- **Cada fala repete o termo do tema**, para o agrupamento por TF-IDF + DBSCAN
  do Radar ter o que juntar. O tom vem do texto escrito a mao, nao de um
  rotulo gravado: o Fraus continua inferindo a nota sozinho.
- **Nenhum dado pessoal**: sem nome, telefone, CPF ou endereco.

    uv run python scripts/gerar_empresa_ficticia.py   # grava dados_demo/lumen-telecom.csv

Para levar ao Fraus, `scripts/carregar_empresa_ficticia.py`.
"""

import csv
import io
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "dados_demo" / "lumen-telecom.csv"
SEMENTE = 20261209
FUSO = timezone(timedelta(hours=-3))
PRIMEIRO_DIA = datetime(2026, 11, 8, tzinfo=FUSO)
DIAS = 30
POR_DIA = 5
CANAIS = ("webchat", "whatsapp", "instagram")
CABECALHO = ("conversa_id", "canal", "autor", "texto", "enviada_em", "escalou_para_humano")

# Espera do cliente ate a resposta do bot, em segundos, por tom. SOBREPOSTAS.
ESPERA_DO_BOT = {"insatisfeito": (5, 90), "neutro": (3, 60), "satisfeito": (3, 45)}
# Do bot ate a proxima fala do cliente: igual para todos os tons.
ESPERA_DO_CLIENTE = (20, 120)
FRACAO_ESCALADA_INSATISFEITO = 0.2

# (insatisfeito, neutro, satisfeito) por tema, 30 atendimentos cada.
MISTURA = {
    "internet caindo": (18, 7, 5),
    "cobrança indevida": (17, 8, 5),
    "troca de plano": (6, 10, 14),
    "visita do técnico": (10, 10, 10),
    "segunda via do boleto": (3, 7, 20),
}

FALAS = {
    "internet caindo": {
        "insatisfeito": [
            "Minha internet caiu de novo, é a terceira vez esta semana",
            "A internet fica caindo toda hora, assim não dá para trabalhar",
            "Já reiniciei o modem e a internet continua caindo, que descaso",
            "Pago caro e a internet cai todo dia no fim da tarde",
            "Isso não resolve, a internet caiu de novo agora mesmo",
            "Estou sem internet desde ontem e ninguém me dá previsão",
            "Vocês sempre dizem que vão verificar a internet e nada muda",
            "Cansei, se a internet cair de novo eu cancelo",
            "A internet caiu no meio de uma reunião, péssimo",
            "Mais uma vez a internet caindo e o atendimento não ajuda",
        ],
        "neutro": [
            "A internet caiu agora há pouco, queria saber se é na região",
            "Minha internet está caindo às vezes, podem verificar?",
            "Reiniciei o modem como pediram, vou ver se a internet volta",
            "A luz do modem está piscando e a internet caiu",
            "Tem alguma manutenção programada? A internet caiu",
            "Certo, vou acompanhar se a internet cai de novo",
            "A internet voltou, mas caiu duas vezes hoje cedo",
            "Entendi, então aguardo a internet normalizar",
        ],
        "satisfeito": [
            "A internet voltou depois do reinício, muito obrigado",
            "Perfeito, a internet não caiu mais desde a troca do modem",
            "Agora a internet está estável, valeu pela ajuda",
            "Resolvido, a internet parou de cair, ótimo atendimento",
            "Que bom, a internet voltou rapidinho, obrigado",
            "A internet está funcionando de novo, atendimento excelente",
            "Show, a internet está firme agora, agradeço",
            "Deu certo, a internet não caiu mais, muito obrigado mesmo",
        ],
    },
    "cobrança indevida": {
        "insatisfeito": [
            "Veio uma cobrança indevida na minha fatura de novo",
            "Cobrança indevida de um serviço que eu nunca contratei, absurdo",
            "Quero o estorno dessa cobrança indevida agora",
            "Já é o segundo mês com cobrança indevida, estou indignado",
            "Ninguém resolve essa cobrança indevida, só me enrolam",
            "Essa cobrança indevida é um desrespeito com o cliente",
            "Vou reclamar no Procon por causa dessa cobrança indevida",
            "Vocês prometeram cancelar a cobrança indevida e ela voltou",
            "Paguei a cobrança indevida e até agora não devolveram",
        ],
        "neutro": [
            "Apareceu uma cobrança que não reconheço, pode ser indevida?",
            "Queria entender essa cobrança de serviço adicional, parece indevida",
            "A cobrança indevida vai ser estornada na próxima fatura?",
            "Ok, vou aguardar a análise da cobrança indevida",
            "Qual o prazo para revisar a cobrança indevida?",
            "Mandei o comprovante da cobrança indevida por aqui",
            "Certo, então a cobrança indevida entra como crédito",
            "Preciso do protocolo da contestação da cobrança indevida",
        ],
        "satisfeito": [
            "Estornaram a cobrança indevida, muito obrigado",
            "Perfeito, a cobrança indevida já saiu da fatura",
            "Ótimo, cancelaram a cobrança indevida rapidinho",
            "Resolvido, a cobrança indevida virou crédito, valeu",
            "Que bom que corrigiram a cobrança indevida, obrigado",
            "Atendimento excelente, a cobrança indevida foi estornada",
            "Show, recebi o estorno da cobrança indevida",
            "Agradeço, a cobrança indevida foi resolvida sem dor de cabeça",
        ],
    },
    "troca de plano": {
        "insatisfeito": [
            "Pedi a troca de plano faz uma semana e nada",
            "A troca de plano saiu mais cara do que me prometeram",
            "Não consigo fazer a troca de plano pelo aplicativo, que raiva",
            "Fizeram a troca de plano errada, não foi isso que eu pedi",
            "Cobram multa para troca de plano, isso é um absurdo",
            "Ninguém me explica a troca de plano direito",
            "Depois da troca de plano a velocidade piorou",
            "Já pedi três vezes a troca de plano, cansei",
        ],
        "neutro": [
            "Quais são as opções para troca de plano?",
            "Queria saber o valor da troca de plano para 500 megas",
            "A troca de plano muda a data de vencimento?",
            "Tem fidelidade na troca de plano?",
            "Vou pensar sobre a troca de plano e volto depois",
            "A troca de plano vale a partir de quando?",
            "Ok, então a troca de plano entra no próximo ciclo",
            "Preciso de algum documento para a troca de plano?",
        ],
        "satisfeito": [
            "Fiz a troca de plano, ficou ótimo, obrigado",
            "Perfeito, a troca de plano já está valendo",
            "Adorei a troca de plano, a internet ficou bem mais rápida",
            "Troca de plano feita em minutos, atendimento nota dez",
            "Valeu, a troca de plano saiu até mais barata",
            "Que bom, a troca de plano foi bem simples",
            "Obrigado pela ajuda com a troca de plano",
            "Show, a troca de plano resolveu o que eu precisava",
        ],
    },
    "visita do técnico": {
        "insatisfeito": [
            "O técnico não apareceu na visita marcada, fiquei o dia todo esperando",
            "Remarcaram a visita do técnico pela terceira vez",
            "A visita do técnico foi inútil, o problema continua",
            "O técnico chegou atrasado e foi embora sem resolver",
            "Faltei no trabalho para a visita do técnico e ninguém veio",
            "Ninguém confirma o horário da visita do técnico, que descaso",
            "Quero uma visita do técnico hoje, não aguento mais",
            "O técnico disse que voltaria e nunca voltou",
        ],
        "neutro": [
            "Qual o horário previsto para a visita do técnico?",
            "Posso remarcar a visita do técnico para sábado?",
            "O técnico precisa de acesso ao prédio para a visita?",
            "Ok, vou ficar em casa aguardando a visita do técnico",
            "A visita do técnico tem custo?",
            "Recebi a confirmação da visita do técnico",
            "Quanto tempo dura a visita do técnico?",
            "Certo, então a visita do técnico fica para amanhã de manhã",
        ],
        "satisfeito": [
            "O técnico veio na hora certa e resolveu tudo, obrigado",
            "Excelente visita do técnico, muito educado",
            "A visita do técnico foi rápida e a internet voltou",
            "Perfeito, o técnico trocou o cabo e ficou ótimo",
            "Gostei muito da visita do técnico, atendimento nota dez",
            "Valeu, o técnico chegou antes do horário",
            "O técnico explicou tudo direitinho, agradeço",
            "Resolvido na visita do técnico, muito obrigado",
        ],
    },
    "segunda via do boleto": {
        "insatisfeito": [
            "Não consigo tirar a segunda via do boleto no site, que raiva",
            "A segunda via do boleto veio com valor errado",
            "Pedi a segunda via do boleto e não chegou, vou pagar juros por culpa de vocês",
            "O código de barras da segunda via do boleto não funciona",
            "Já tentei três vezes a segunda via do boleto e dá erro",
            "Absurdo não conseguir uma simples segunda via do boleto",
            "A segunda via do boleto venceu antes de chegar",
            "Ninguém me manda a segunda via do boleto",
        ],
        "neutro": [
            "Como faço para pegar a segunda via do boleto?",
            "Pode enviar a segunda via do boleto por e-mail?",
            "A segunda via do boleto já vem com juros?",
            "Ok, vou baixar a segunda via do boleto no aplicativo",
            "Qual o vencimento da segunda via do boleto?",
            "Recebi a segunda via do boleto, vou conferir",
            "A segunda via do boleto pode ser paga por pix?",
            "Preciso da segunda via do boleto do mês passado",
        ],
        "satisfeito": [
            "Recebi a segunda via do boleto, muito obrigado",
            "Perfeito, consegui pagar a segunda via do boleto",
            "Que rápido, a segunda via do boleto chegou na hora",
            "Valeu, a segunda via do boleto veio certinha",
            "Ótimo atendimento, a segunda via do boleto resolveu",
            "Obrigado, a segunda via do boleto pelo pix foi fácil",
            "Show, já paguei a segunda via do boleto",
            "Agradeço, a segunda via do boleto chegou no e-mail",
        ],
    },
}

RESPOSTAS_DO_BOT = {
    "internet caindo": [
        "Vou verificar a conexão da sua internet. Um momento, por favor.",
        "Identifiquei instabilidade na sua região. Pode reiniciar o modem?",
        "Abri um chamado técnico para a sua internet.",
        "Fiz um teste remoto na sua linha de internet.",
        "A equipe está atuando na rede da sua região.",
    ],
    "cobrança indevida": [
        "Vou analisar a cobrança na sua fatura. Um momento.",
        "Encontrei o serviço adicional na fatura. Vou abrir a contestação.",
        "A contestação da cobrança foi registrada.",
        "O valor contestado entra como crédito na próxima fatura.",
        "Pode me enviar o comprovante de pagamento?",
    ],
    "troca de plano": [
        "Temos planos de 300, 500 e 800 megas. Qual prefere?",
        "A troca de plano vale a partir do próximo ciclo.",
        "Não há multa para trocar para um plano maior.",
        "Registrei a solicitação de troca de plano.",
        "Posso confirmar os dados da troca de plano?",
    ],
    "visita do técnico": [
        "Vou consultar a agenda de visitas técnicas.",
        "A visita está marcada para o período da manhã.",
        "Registrei a remarcação da visita técnica.",
        "O técnico entrará em contato antes de chegar.",
        "A visita técnica não tem custo quando o defeito é da rede.",
    ],
    "segunda via do boleto": [
        "Vou gerar a segunda via do seu boleto.",
        "Enviei a segunda via para o e-mail cadastrado.",
        "O boleto também pode ser pago por pix.",
        "A segunda via sai com o valor atualizado.",
        "Pode baixar a segunda via no aplicativo, em Faturas.",
    ],
}

PASSAGEM_PARA_HUMANO = "Aqui é da equipe de atendimento da Lumen. Vou assumir o seu caso a partir de agora."


def _linha(conversa_id, canal, autor, texto, instante, escalou):
    return (conversa_id, canal, autor, texto, instante.isoformat(), "true" if escalou else "false")


def _regulares(rng: random.Random) -> list[tuple]:
    atendimentos = [
        (tema, tom)
        for tema, contagens in MISTURA.items()
        for tom, quantos in zip(("insatisfeito", "neutro", "satisfeito"), contagens)
        for _ in range(quantos)
    ]
    rng.shuffle(atendimentos)
    insatisfeitos = [i for i, (_, tom) in enumerate(atendimentos) if tom == "insatisfeito"]
    escaladas = set(rng.sample(insatisfeitos, round(FRACAO_ESCALADA_INSATISFEITO * len(insatisfeitos))))

    linhas = []
    for indice, (tema, tom) in enumerate(atendimentos):
        conversa_id = f"sintetica-lumen-{indice + 1:04d}"
        canal = CANAIS[indice % len(CANAIS)]
        dia = PRIMEIRO_DIA + timedelta(days=indice // POR_DIA)
        instante = dia + timedelta(hours=8, seconds=rng.randint(0, 11 * 3600))
        escalou = indice in escaladas
        falas = rng.sample(FALAS[tema][tom], rng.randint(2, 5))
        respostas = RESPOSTAS_DO_BOT[tema]
        for numero, fala in enumerate(falas):
            linhas.append(_linha(conversa_id, canal, "cliente", fala, instante, escalou))
            instante += timedelta(seconds=rng.randint(*ESPERA_DO_BOT[tom]))
            ultima = numero == len(falas) - 1
            if escalou and ultima:
                linhas.append(_linha(conversa_id, canal, "humano", PASSAGEM_PARA_HUMANO, instante, escalou))
            else:
                linhas.append(_linha(conversa_id, canal, "bot", respostas[numero % len(respostas)], instante, escalou))
            instante += timedelta(seconds=rng.randint(*ESPERA_DO_CLIENTE))
    return linhas


def _roteiro(conversa_id, inicio, falas, escalou=False):
    """Caso escrito a mao: (autor, texto, segundos desde a fala anterior)."""
    linhas, instante = [], inicio
    for autor, texto, depois in falas:
        instante += timedelta(seconds=depois)
        linhas.append(_linha(conversa_id, "webchat", autor, texto, instante, escalou))
    return linhas


def _casos_fixos() -> list[tuple]:
    dia = datetime(2026, 12, 3, tzinfo=FUSO)
    replay_cliente = [
        "Bom dia! Tudo bem? Queria uma ajuda com a minha internet",
        "Claro, posso esperar, sem problema",
        "Reiniciei o modem como você pediu",
        "Hum, a internet ainda está oscilando um pouco",
        "Certo, faço o teste de novo então",
        "Fiz o teste, a internet continua caindo",
        "Já é a segunda vez que reinicio, sabe?",
        "Vocês têm alguma previsão para a internet voltar?",
        "Isso está demorando mais do que eu esperava",
        "Preciso da internet para trabalhar, isso está complicado",
        "De novo pedindo para reiniciar? Já fiz isso",
        "Estou ficando bem chateado com essa internet caindo",
        "Ninguém resolve nada, que descaso com o cliente",
        "Cansei, quero cancelar essa internet hoje mesmo",
    ]
    replay = []
    for numero, fala in enumerate(replay_cliente):
        replay.append(("cliente", fala, 0 if numero == 0 else 90))
        replay.append(("bot", RESPOSTAS_DO_BOT["internet caindo"][numero % 5], 15 + 3 * numero))

    return [
        # A tese: reclamou da espera, o bot resolveu tarde, fechou com cortesia.
        *_roteiro("sintetica-lumen-tese", dia + timedelta(hours=9), [
            ("cliente", "Estou esperando faz tempo, minha internet caiu e ninguém responde", 0),
            ("bot", "Desculpe a demora. Vou verificar a sua internet.", 380),
            ("cliente", "Já reiniciei o modem duas vezes, continua sem internet", 60),
            ("bot", "Identifiquei falha na sua região. A equipe já atuou e a internet deve voltar.", 610),
            ("cliente", "ok, obrigado 🙂", 240),
        ]),
        # A espera: primeira resposta em 420 s; alvo do contrafactual de 60 s.
        *_roteiro("sintetica-lumen-espera", dia + timedelta(hours=11), [
            ("cliente", "Veio uma cobrança indevida na minha fatura, preciso de ajuda", 0),
            ("bot", "Olá! Vou analisar a cobrança na sua fatura.", 420),
            ("cliente", "Demorou muito para responder, essa cobrança indevida já me irritou", 45),
            ("bot", "A contestação da cobrança foi registrada.", 40),
            ("cliente", "Espero que resolvam essa cobrança indevida logo", 70),
        ]),
        # O replay: 14 falas do cliente, de cordial a irritado.
        *_roteiro("sintetica-lumen-replay", dia + timedelta(hours=14), replay),
        # Cortesia sozinha: sem sinal, nao promotor.
        *_roteiro("sintetica-lumen-cortesia", dia + timedelta(hours=16), [
            ("bot", "Olá! A segunda via do seu boleto foi enviada para o e-mail cadastrado.", 0),
            ("cliente", "ok, obrigado", 30),
        ]),
        # So o bot falou: sem sinal.
        *_roteiro("sintetica-lumen-sem-cliente", dia + timedelta(hours=17), [
            ("bot", "Olá! Sua visita técnica está confirmada para amanhã de manhã.", 0),
            ("bot", "Se precisar remarcar, responda esta mensagem.", 5),
        ]),
        # Caixa alta e palavrao censurado.
        *_roteiro("sintetica-lumen-palavrao", dia + timedelta(hours=18), [
            ("cliente", "A INTERNET CAIU DE NOVO!!! QUE P*RRA É ESSA???", 0),
            ("bot", "Vou verificar a conexão da sua internet. Um momento, por favor.", 25),
            ("cliente", "VOCÊS SÃO UMA M*RDA, TODO DIA A MESMA COISA", 50),
            ("bot", "Abri um chamado técnico para a sua internet.", 20),
        ]),
    ]


def gerar() -> str:
    """O CSV inteiro, no formato de `fraus/ingest/csv_driver.py`."""
    rng = random.Random(SEMENTE)
    saida = io.StringIO()
    escritor = csv.writer(saida, lineterminator="\n")
    escritor.writerow(CABECALHO)
    escritor.writerows(_regulares(rng))
    escritor.writerows(_casos_fixos())
    return saida.getvalue()


def main() -> int:
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(gerar(), encoding="utf-8")
    print(f"gravado {SAIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
