import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * O DESIGN.md §4 proíbe fonte de display em rótulo e dado, e a vitrine é a
 * única excecao nomeada. Este teste le o globals.css de verdade: se alguem
 * ligar a Mona Sans no corpo, num rotulo ou num dado, ele cai.
 */
const CSS = readFileSync(join(__dirname, "..", "app", "globals.css"), "utf8");

/**
 * Sem os comentarios de bloco, o CSS tem fartura deles (todo o raciocinio de
 * design mora ali). Sem remove-los antes do regex de regras, um comentario
 * sem chaves na frente de um seletor gruda no seletor seguinte e a
 * comparacao exata nunca bate.
 */
const CSS_SEM_COMENTARIOS = CSS.replace(/\/\*[\s\S]*?\*\//g, "");

/** Toda regra do arquivo, como par (seletor, corpo). */
function regras(): Array<{ seletor: string; corpo: string }> {
  const encontradas: Array<{ seletor: string; corpo: string }> = [];
  const padrao = /([^{}]+)\{([^{}]*)\}/g;
  let achado: RegExpExecArray | null;
  while ((achado = padrao.exec(CSS_SEM_COMENTARIOS)) !== null) {
    encontradas.push({ seletor: achado[1].trim(), corpo: achado[2] });
  }
  return encontradas;
}

describe("a familia de display", () => {
  it("define --fonte-mona uma vez", () => {
    expect(CSS).toContain("--fonte-mona");
  });

  it("governa .display-vitrine e .titulo-vitrine", () => {
    for (const alvo of [".display-vitrine", ".titulo-vitrine"]) {
      const regra = regras().find((r) => r.seletor === alvo);
      expect(regra, `regra ${alvo} nao existe`).toBeDefined();
      expect(regra!.corpo).toContain("var(--fonte-display)");
    }
  });

  it("nao vaza para nenhuma outra regra", () => {
    const vazamentos = regras()
      .filter((r) => r.corpo.includes("var(--fonte-display)"))
      .map((r) => r.seletor)
      .filter((s) => s !== ".display-vitrine" && s !== ".titulo-vitrine");
    expect(vazamentos).toEqual([]);
  });

  it("nao troca a sans nem a mono do resto do produto", () => {
    expect(CSS).toContain("--fonte-sans: var(--fonte-inter)");
    expect(CSS).toContain("--fonte-mono: var(--fonte-jetbrains)");
  });
});
