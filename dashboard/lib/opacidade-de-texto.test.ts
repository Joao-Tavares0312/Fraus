import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * `npm run contraste` le TOKENS, e opacidade aplicada por classe nao e token:
 * `text-muted-foreground/70` passa verde no gate e sai com 3,4:1 sobre o vidro
 * dos paineis (medido em 14/09/2026, composicao em sRGB com gama, os dois
 * temas; a 60% cai para 2,8:1). O texto atenuado era justamente ressalva --
 * "(pouco confiavel)", "exemplo ilustrativo". Hierarquia se faz por tamanho e
 * peso (DESIGN.md §4), nao apagando o texto.
 *
 * Proibe o atalho no tom que ja e o mais apagado da paleta. `foreground/60` e
 * `sidebar-foreground/70` ficam fora: medidos, passam de 4,9:1 no pior vidro.
 */
function arquivos(pasta: string): string[] {
  return readdirSync(pasta).flatMap((nome) => {
    const caminho = join(pasta, nome);
    if (statSync(caminho).isDirectory()) return arquivos(caminho);
    return /\.tsx$/.test(nome) && !/\.test\./.test(nome) ? [caminho] : [];
  });
}

describe("texto atenuado por opacidade", () => {
  it("muted-foreground nunca leva opacidade", () => {
    const raiz = join(__dirname, "..");
    const achados = [join(raiz, "app"), join(raiz, "components")]
      .flatMap(arquivos)
      .flatMap((caminho) =>
        [...readFileSync(caminho, "utf8").matchAll(/(?<![:\w-])text-muted-foreground\/\d+/g)].map(
          (m) => `${caminho.slice(raiz.length + 1)}: ${m[0]}`,
        ),
      );
    expect(achados).toEqual([]);
  });
});
