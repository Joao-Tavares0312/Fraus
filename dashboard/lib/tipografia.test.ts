import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const CSS = readFileSync(join(__dirname, "..", "app", "globals.css"), "utf8");

const CSS_SEM_COMENTARIOS = CSS.replace(/\/\*[\s\S]*?\*\//g, "");


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
