"""Converte o SentiLex-PT02 flexionado no CSV compacto que o sinal lexico le.

Fonte: SentiLex-PT02, Silva, Carvalho e Sarmento (PROPOR 2012), CC-BY.
82.346 formas flexionadas com polaridade e alvo de predicacao.

O arquivo original tem 6,9 MB de campos que o Fraus nao usa (lema, PoS, flexao,
tipo de anotacao). Aqui ele vira `forma,polaridade` -- mesma escolha ja feita
para o lexicon de emoji, que tambem mora derivado em fraus/dados/.

Uso:
    python scripts/preparar_sentilex.py caminho/para/SentiLex-flex-PT02.txt

O relatorio no fim NAO e enfeite: a fonte tem linhas malformadas, e o que foi
normalizado ou descartado precisa aparecer em vez de sumir no silencio.
"""

import csv
import re
import sys
from collections import Counter
from pathlib import Path

DESTINO = Path(__file__).parent.parent / "fraus" / "dados" / "sentilex_pt02.csv"

# POL:N0 e a polaridade quando o alvo humano e o SUJEITO; POL:N1, quando e o
# complemento. O Fraus quer a polaridade do que o cliente disse, entao N0 vem
# primeiro e N1 e o reserva -- 315 idiomas ("e culpa de") so tem N1.
PADRAO_N0 = re.compile(r"POL:N0=(-?\d+)")
PADRAO_N1 = re.compile(r"POL:N1=(-?\d+)")


def polaridade_da_linha(linha: str) -> tuple[str, int] | None:
    """Devolve (forma, polaridade em -1/0/1) ou None se a linha nao serve."""
    forma, _, resto = linha.partition(",")
    forma = forma.strip().lower()
    if not forma or not resto:
        return None

    achado = PADRAO_N0.search(resto) or PADRAO_N1.search(resto)
    if not achado:
        return None

    bruto = int(achado.group(1))
    # A escala do SentiLex e -1/0/1. Nove entradas marcadas REV:POL (revisao
    # pendente) trazem 2..8 e -2/-3, com o contador vazado no campo. A direcao
    # continua inequivoca -- "intrepido" e positivo, "ponto fraco" e negativo --
    # entao normaliza pelo SINAL em vez de descartar palavra legitima.
    if bruto > 1:
        return forma, 1
    if bruto < -1:
        return forma, -1
    return forma, bruto


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    origem = Path(sys.argv[1])
    if not origem.is_file():
        print(f"arquivo nao encontrado: {origem}")
        return 1

    tabela: dict[str, int] = {}
    contagem = Counter()
    for linha in origem.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        contagem["linhas"] += 1
        resultado = polaridade_da_linha(linha)
        if resultado is None:
            contagem["descartadas"] += 1
            continue
        forma, polaridade = resultado
        if "POL:N0=" not in linha:
            contagem["polaridade_do_complemento_n1"] += 1
        if re.search(r"POL:N[01]=-?(?:[2-9]|\d{2,})", linha):
            contagem["sinal_normalizado"] += 1
        if forma in tabela and tabela[forma] != polaridade:
            # Mesma forma com polaridades diferentes (homografo, ou entrada em
            # revisao). Neutraliza em vez de deixar a ordem do arquivo decidir.
            tabela[forma] = 0
            contagem["conflito_neutralizado"] += 1
            continue
        tabela[forma] = polaridade

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    with DESTINO.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["forma", "polaridade"])
        for forma in sorted(tabela):
            escritor.writerow([forma, tabela[forma]])

    distribuicao = Counter(tabela.values())
    print(f"lidas               {contagem['linhas']}")
    print(f"descartadas         {contagem['descartadas']} (sem POL:N0 nem POL:N1)")
    print(f"polaridade via N1   {contagem['polaridade_do_complemento_n1']}")
    print(f"sinal normalizado   {contagem['sinal_normalizado']} (REV:POL na fonte)")
    print(f"conflito zerado     {contagem['conflito_neutralizado']}")
    print(f"gravadas            {len(tabela)} formas -> {DESTINO}")
    print(f"  positivas {distribuicao[1]}  negativas {distribuicao[-1]}  neutras {distribuicao[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
