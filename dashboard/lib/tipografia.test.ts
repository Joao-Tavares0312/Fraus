import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * O DESIGN.md §4 proíbe fonte de display em rótulo e dado, e a vitrine é a
 * única excecao nomeada. Este teste le o globals.css de verdade: se alguem
 * ligar a Bricolage Grotesque no corpo, num rotulo ou num dado, ele cai.
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
  it("define --fonte-bricolage", () => {
    expect(CSS).toContain("--fonte-bricolage");
  });

  it("governa .display-vitrine e .titulo-vitrine", () => {
    for (const alvo of [".display-vitrine", ".titulo-vitrine"]) {
      const regra = regras().find((r) => r.seletor === alvo);
      expect(regra, `regra ${alvo} nao existe`).toBeDefined();
      expect(regra!.corpo).toContain("var(--fonte-display)");
    }
  });

  it("nao vaza para nenhuma outra regra", () => {
    // `:root` fica de fora do alvo: e la que `--fonte-display` e DEFINIDA em
    // termos de `--fonte-bricolage`, e isso e a declaracao do token, nao um
    // vazamento para uma regra de estilo.
    const vazamentos = regras()
      .filter((r) => !r.seletor.includes(":root"))
      .filter(
        (r) =>
          r.corpo.includes("var(--fonte-display)") ||
          r.corpo.includes("var(--fonte-bricolage)"),
      )
      .map((r) => r.seletor)
      .filter((s) => s !== ".display-vitrine" && s !== ".titulo-vitrine");
    expect(vazamentos).toEqual([]);
  });

  it("nao troca a sans nem a mono do resto do produto", () => {
    expect(CSS).toContain("--fonte-sans: var(--fonte-inter)");
    expect(CSS).toContain("--fonte-mono: var(--fonte-martian)");
  });
});

/**
 * O PISO DE 11px. A banca le esta interface num projetor, e o levantamento de
 * 14/09/2026 achou texto em 9 e 10px -- dois deles eram a etiqueta
 * "estimativa", justamente o rotulo que a honestidade metodologica manda
 * manter colado ao numero e sempre visivel. Rotulo ilegivel e rotulo ausente.
 *
 * Varre o TSX por tamanho arbitrario do Tailwind (`text-[10px]`,
 * `text-[0.625rem]`) e o CSS por `font-size` literal. Nao ve `fontSize` de
 * grafico nem `ctx.font` do canvas -- esses ficam de conferencia manual.
 */
describe("o piso de 11px", () => {
  const PISO_PX = 11;

  function arquivos(pasta: string): string[] {
    return readdirSync(pasta).flatMap((nome: string) => {
      const caminho = join(pasta, nome);
      if (statSync(caminho).isDirectory()) return arquivos(caminho);
      return /\.tsx$/.test(nome) && !/\.test\./.test(nome) ? [caminho] : [];
    });
  }

  const emPx = (valor: string, unidade: string) =>
    unidade === "px" ? Number(valor) : Number(valor) * 16;

  it("nenhum tamanho arbitrario de texto abaixo do piso no TSX", () => {
    const raiz = join(__dirname, "..");
    const abaixo = [join(raiz, "app"), join(raiz, "components")]
      .flatMap(arquivos)
      .flatMap((caminho) =>
        [...readFileSync(caminho, "utf8").matchAll(/text-\[(\d*\.?\d+)(px|rem)\]/g)]
          .filter((m) => emPx(m[1], m[2]) < PISO_PX)
          .map((m) => `${caminho.slice(raiz.length + 1)}: ${m[0]}`),
      );
    expect(abaixo).toEqual([]);
  });

  it("nenhum font-size literal abaixo do piso no globals.css", () => {
    const abaixo = [...CSS_SEM_COMENTARIOS.matchAll(/font-size:\s*(\d*\.?\d+)(px|rem)/g)]
      .filter((m) => emPx(m[1], m[2]) < PISO_PX)
      .map((m) => m[0]);
    expect(abaixo).toEqual([]);
  });
});
