"""Traz para `docs/` o Markdown que mora fora dele, ANTES do `mkdocs build`.

O site le so o `docs_dir`. Dois documentos que o site precisa moram em outro
lugar por bons motivos e nao vao se mudar:

- `dashboard/DESIGN.md` mora ao lado do codigo que ele governa, e e onde quem
  escreve interface o procura;
- `CLAUDE.md` mora na raiz porque e o arquivo que a sessao de agente carrega.

A copia acontece NO BUILD, nunca a mao. Copia manual de documento vivo diverge
do original em uma semana, e a versao publicada -- a que estranho le -- e
sempre a que envelhece, porque ninguem que trabalha no projeto olha para ela.

Os arquivos gerados sao ignorados pelo git (ver .gitignore): eles nao sao
fonte, sao saida de build. Rodar duas vezes da o mesmo resultado.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs"

# A MARCA. Ela mora em `dashboard/public/` porque e o produto que a serve; o
# site precisa dela para o cabecalho e o favicon. Copia de build, como o resto.
ATIVOS = {
    RAIZ / "dashboard" / "public" / "fraus-logo.svg": (
        DOCS / "assets" / "fraus-logo.svg"
    ),
}

# origem -> destino dentro de docs/, com o aviso que vai no topo do gerado.
COPIAS = {
    RAIZ / "dashboard" / "DESIGN.md": (
        DOCS / "design.md",
        "dashboard/DESIGN.md",
    ),
}

AVISO = (
    "<!-- GERADO POR scripts/reunir_docs.py A PARTIR DE {origem} -->\n"
    "<!-- Nao edite este arquivo: a edicao se perde no proximo build. -->\n\n"
)


def reunir() -> list[Path]:
    """Copia cada documento externo para dentro de `docs/`, com o aviso no topo."""
    gerados = []
    for origem, (destino, rotulo) in COPIAS.items():
        if not origem.exists():
            raise SystemExit(
                f"documento esperado nao existe: {origem}\n"
                "O site declara esta pagina no nav -- publicar sem ela daria "
                "um link quebrado numa pagina publica."
            )
        destino.write_text(
            AVISO.format(origem=rotulo) + origem.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        gerados.append(destino)

    # Os ativos binarios vao sem aviso no topo, pela razao obvia: um comentario
    # HTML dentro de um SVG usado como favicon nao ajuda ninguem e alguns
    # leitores engasgam.
    for origem, destino in ATIVOS.items():
        if not origem.exists():
            raise SystemExit(f"ativo esperado nao existe: {origem}")
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(origem.read_bytes())
        gerados.append(destino)

    return gerados


if __name__ == "__main__":
    for caminho in reunir():
        print(f"gerado: {caminho.relative_to(RAIZ)}", file=sys.stderr)
