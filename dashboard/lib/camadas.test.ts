// dashboard/lib/camadas.test.ts
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const CAMADAS = "app/camadas.css";

function arquivos(pasta: string): string[] {
  return readdirSync(pasta).flatMap((nome) => {
    const caminho = join(pasta, nome);
    return statSync(caminho).isDirectory() ? arquivos(caminho) : [caminho];
  });
}

function bloco(css: string, seletor: RegExp): string {
  const inicio = css.search(seletor);
  if (inicio < 0) return "";
  const abre = css.indexOf("{", inicio);
  return css.slice(abre + 1, css.indexOf("}", abre));
}

describe("primitivas de camadas", () => {
  it("camadas.css existe e define todas as primitivas", () => {
    expect(existsSync(CAMADAS)).toBe(true);
    const css = readFileSync(CAMADAS, "utf8");
    for (const classe of ["chanfro", "placas", "placas-so-hover", "fio", "fio-hover", "pincel", "fenda"]) {
      expect(css, classe).toMatch(new RegExp(`\\.${classe}(?![\\w-])`));
    }
  });

  it("globals.css importa camadas.css", () => {
    const globals = readFileSync("app/globals.css", "utf8");
    expect(globals).toMatch(/@import\s+["']\.\/camadas\.css["'];/);
  });

  it("o poligono do canto e as cores das placas moram so em camadas.css", () => {
    // Fonte unica: copiar o poligono ou o hexadecimal em outro arquivo faz
    // o canto e a placa divergirem na primeira mudanca de valor.
    const proibidos = ["calc(100% - var(--chanfro", "#a8904f", "#6f5f36"];
    const suspeitos = [...arquivos("app"), ...arquivos("components")]
      .filter((caminho) => /\.(css|tsx?|jsx?)$/.test(caminho))
      .filter((caminho) => !caminho.endsWith("camadas.css"));
    for (const caminho of suspeitos) {
      const fonte = readFileSync(caminho, "utf8").toLowerCase();
      for (const trecho of proibidos) expect(fonte.includes(trecho), `${caminho}: ${trecho}`).toBe(false);
    }
  });

  it("os dois temas definem as placas", () => {
    // Os tokens moram em camadas.css: a guarda acima proibe o hex fora dele.
    const css = readFileSync(CAMADAS, "utf8");
    const escuro = bloco(css, /^\s*:root\s*,\s*\.dark\s*\{/m);
    for (const token of ["--placa-2", "--placa-3", "--placa-card-2", "--placa-card-3"]) {
      expect(escuro, token).toMatch(new RegExp(`${token}:`));
    }
    const claro = bloco(css, /^\s*\.light\s*\{/m);
    expect(claro).toMatch(/--placa-2:/);
    expect(claro).toMatch(/--placa-3:/);
    expect(claro).toMatch(/color-mix\(in oklch/);
  });
});
