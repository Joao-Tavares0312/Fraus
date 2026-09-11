"""Abre 80 e 443 na Security List da VCN -- o firewall da NUVEM.

A Oracle bloqueia em dois niveis e abrir so um nao da erro nenhum: a conexao
fica pendurada ate expirar, sem recusa e sem pista. O outro nivel e o
`iptables` de dentro da maquina, que `scripts/provisionar_oracle.sh` resolve.

POR QUE ISTO NAO E UM `oci ... --ingress-security-rules '[...]'` NA MAO, e a
razao de o arquivo existir: a API de update **SUBSTITUI** a lista inteira. Quem
passa so as duas regras novas APAGA as que estavam la -- inclusive a da porta
22, e a proxima coisa que acontece e perder o ssh para a propria maquina. Este
script le o que existe, acrescenta o que falta, e reenvia o conjunto.

Uso:
    uv run python scripts/abrir_portas_oracle.py               # descobre a sub-rede publica
    uv run python scripts/abrir_portas_oracle.py --portas 80 443 8000
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

PORTAS_PADRAO = (80, 443)


def _oci(*argumentos: str) -> object:
    """Chama a CLI da Oracle e devolve o campo `data` ja desserializado.

    A CLI escreve avisos de permissao de arquivo no stderr mesmo quando tudo
    deu certo, entao o stderr so e mostrado se o processo REALMENTE falhar.
    """
    processo = subprocess.run(
        ["oci", *argumentos, "--output", "json"],
        capture_output=True,
        text=True,
    )
    if processo.returncode != 0:
        raise SystemExit(f"falhou `oci {' '.join(argumentos)}`:\n{processo.stderr}")
    if not processo.stdout.strip():
        return None
    return json.loads(processo.stdout)["data"]


def _tenancy() -> str:
    """O OCID da tenancy, lido da config -- nunca digitado de novo aqui."""
    import configparser
    import pathlib

    config = configparser.ConfigParser()
    config.read(pathlib.Path.home() / ".oci" / "config")
    return config["DEFAULT"]["tenancy"]


def sub_rede_publica(compartimento: str) -> dict:
    """A sub-rede que aceita IP publico. Se houver mais de uma, e ambiguo."""
    subredes = _oci("network", "subnet", "list", "-c", compartimento) or []
    publicas = [s for s in subredes if not s["prohibit-public-ip-on-vnic"]]
    if not publicas:
        raise SystemExit("nenhuma sub-rede publica na VCN -- rode o VCN Wizard primeiro")
    if len(publicas) > 1:
        nomes = ", ".join(s["display-name"] for s in publicas)
        raise SystemExit(f"mais de uma sub-rede publica ({nomes}) -- passe --subnet")
    return publicas[0]


def regra_de_entrada(porta: int) -> dict:
    """Uma regra TCP vinda de qualquer lugar para uma porta.

    `isStateless: False` de proposito: regra sem estado exigiria a regra de
    saida correspondente, e a falta dela e outro jeito de a conexao pendurar.
    """
    return {
        "source": "0.0.0.0/0",
        "sourceType": "CIDR_BLOCK",
        "protocol": "6",  # TCP
        "isStateless": False,
        "tcpOptions": {"destinationPortRange": {"min": porta, "max": porta}},
    }


def _ja_cobre(regra: dict, porta: int) -> bool:
    """A regra existente ja libera esta porta?

    Compara FAIXA, nao igualdade: uma regra de 1-65535 ja cobre a 443, e
    acrescentar outra seria lixo na lista.
    """
    if str(regra.get("protocol")) != "6" or regra.get("source") != "0.0.0.0/0":
        return False
    opcoes = regra.get("tcp-options") or regra.get("tcpOptions")
    if not opcoes:
        return True  # TCP inteiro liberado
    faixa = opcoes.get("destination-port-range") or opcoes.get("destinationPortRange")
    if not faixa:
        return True
    return faixa["min"] <= porta <= faixa["max"]


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--subnet", help="OCID da sub-rede (padrao: a publica)")
    analisador.add_argument("--portas", nargs="+", type=int, default=list(PORTAS_PADRAO))
    opcoes = analisador.parse_args()

    compartimento = _tenancy()
    if opcoes.subnet:
        subrede = _oci("network", "subnet", "get", "--subnet-id", opcoes.subnet)
    else:
        subrede = sub_rede_publica(compartimento)
    print(f"sub-rede: {subrede['display-name']}")

    for lista_id in subrede["security-list-ids"]:
        lista = _oci("network", "security-list", "get", "--security-list-id", lista_id)
        entrada = lista["ingress-security-rules"]
        faltando = [p for p in opcoes.portas if not any(_ja_cobre(r, p) for r in entrada)]

        if not faltando:
            print(f"  {lista['display-name']}: portas {opcoes.portas} ja liberadas")
            continue

        print(f"  {lista['display-name']}: acrescentando {faltando}")
        # O conjunto INTEIRO, nao so o delta -- ver o cabecalho do arquivo.
        novas = entrada + [regra_de_entrada(p) for p in faltando]
        _oci(
            "network", "security-list", "update",
            "--security-list-id", lista_id,
            "--ingress-security-rules", json.dumps(novas),
            "--force",
        )
        print(f"  {lista['display-name']}: {len(entrada)} -> {len(novas)} regras")

    print("\nFalta o OUTRO firewall: o iptables de dentro da VM.")
    print("Ele entra no passo 1 de scripts/provisionar_oracle.sh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
