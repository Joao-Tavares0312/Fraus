"""Apaga a chave mestra gravada no banco -- a saida de quem perdeu a chave.

POR QUE ISTO E UM SCRIPT, E NAO UM BOTAO. A tela liga a autenticacao, e nao
desliga: um controle que baixa a defesa numa interface sem login nao tem
contrapartida de risco aceitavel, e a rota que o serviria estaria alcancavel
justamente quando a API esta aberta. Desligar exige o disco e a mao de quem
opera a maquina -- que e uma credencial que nao trafega em rede nenhuma.

QUANDO USAR. A mestra sai em claro UMA vez, na criacao. Se ela se perdeu, a API
continua exigindo credencial e nao ha mais como gerenciar chave nenhuma: o
banco guarda so o hash, e hash nao volta a ser chave. Este script devolve a API
ao estado aberto, para que ligar de novo (e receber uma mestra nova) volte a
ser possivel.

A OUTRA SAIDA, que nao apaga nada: `FRAUS_CHAVE_MESTRA` no ambiente VENCE a
gravada. Se voce so precisa entrar agora, definir a variavel resolve sem tocar
no banco -- e este script avisa quando esse e o seu caso.

    uv run python scripts/resetar_mestra.py
    uv run python scripts/resetar_mestra.py --banco outro.db
"""

import argparse
import os
import sys

from fraus.api.caminhos import CAMINHO_BANCO
from fraus.db import Banco

CONFIRMACAO = "DESLIGAR"


def main() -> int:
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument(
        "--banco",
        default=None,
        help=f"caminho do SQLite (padrao: {CAMINHO_BANCO})",
    )
    argumentos.add_argument(
        "--sim",
        action="store_true",
        help="pula a confirmacao interativa. Existe para automacao; no uso "
        "normal, digitar a palavra e a trava que impede o comando errado.",
    )
    opcoes = argumentos.parse_args()

    caminho = opcoes.banco or CAMINHO_BANCO
    if not os.path.exists(caminho):
        print(f"banco nao encontrado: {caminho}", file=sys.stderr)
        return 1

    banco = Banco(caminho)
    registrada = banco.chave_mestra_registrada()

    if registrada is None:
        print(f"Nao ha mestra gravada em {caminho} -- nada a fazer.")
        # A variavel do ambiente NAO passa por esta tabela, e quem esta tomando
        # 401 sem entender precisa saber disso: apagar o banco inteiro nao
        # desligaria uma autenticacao que vem de fora dele.
        if os.environ.get("FRAUS_CHAVE_MESTRA"):
            print(
                "\nATENCAO: FRAUS_CHAVE_MESTRA esta definida no ambiente desta "
                "sessao. Ela vence a gravada e NAO e apagada por este script --"
                "\na API vai continuar exigindo chave. Para desliga-la, remova "
                "a variavel de onde a API sobe."
            )
        return 0

    print("Isto DESLIGA a autenticacao da API.")
    print(f"\n  Banco:  {caminho}")
    print(f"  Mestra: gravada em {registrada['criada_em']} (dica {registrada['dica']})")
    print(
        "\nAs chaves de ACESSO e de FONTE nao sao apagadas: elas continuam no "
        "banco e voltam a valer\nassim que a autenticacao for ligada de novo."
    )
    if os.environ.get("FRAUS_CHAVE_MESTRA"):
        print(
            "\nATENCAO: FRAUS_CHAVE_MESTRA esta definida no ambiente desta "
            "sessao e VENCE a gravada.\nApagar a do banco nao vai abrir a API "
            "enquanto a variavel existir onde ela sobe."
        )

    if not opcoes.sim:
        try:
            resposta = input(f"\nDigite {CONFIRMACAO} para confirmar: ")
        except (EOFError, KeyboardInterrupt):
            print("\ncancelado.")
            return 1
        if resposta.strip() != CONFIRMACAO:
            print("cancelado -- nada foi alterado.")
            return 1

    if banco.apagar_chave_mestra():
        print(
            "\nMestra apagada. A API esta ABERTA a partir da proxima "
            "requisicao -- a decisao e por\nrequisicao, entao nao e preciso "
            "reiniciar. Ligue de novo em Configuracoes -> Autenticacao."
        )
        return 0

    # Corrida com outro processo que apagou entre a leitura e o DELETE.
    print("a mestra ja nao estava mais la -- nada foi alterado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
