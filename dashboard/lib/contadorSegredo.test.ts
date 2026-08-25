import { describe, expect, it } from "vitest";
import {
  CLIQUES_PARA_ABRIR,
  CONTADOR_ZERADO,
  JANELA_MS,
  abriu,
  registrarClique,
} from "./contadorSegredo";

/** Aplica uma sequencia de instantes (ms) sobre o contador zerado. */
function sequencia(instantes: number[]) {
  return instantes.reduce(registrarClique, CONTADOR_ZERADO);
}

describe("contadorSegredo", () => {
  it("o primeiro clique conta um", () => {
    expect(registrarClique(CONTADOR_ZERADO, 1000).cliques).toBe(1);
  });

  it("cinco cliques dentro da janela abrem", () => {
    const estado = sequencia([0, 300, 600, 900, 1200]);
    expect(estado.cliques).toBe(CLIQUES_PARA_ABRIR);
    expect(abriu(estado)).toBe(true);
  });

  it("quatro cliques nao abrem", () => {
    expect(abriu(sequencia([0, 300, 600, 900]))).toBe(false);
  });

  it("silencio maior que a janela zera: o quinto clique vira o primeiro", () => {
    const estado = sequencia([0, 300, 600, 900, 900 + JANELA_MS + 500]);
    expect(estado.cliques).toBe(1);
    expect(abriu(estado)).toBe(false);
  });

  it("a janela conta do ULTIMO clique, nao do primeiro", () => {
    // Cinco cliques espacados de 1,5s: o total (6s) passa da janela, mas
    // nenhum intervalo passa. Tem que abrir.
    const estado = sequencia([0, 1500, 3000, 4500, 6000]);
    expect(abriu(estado)).toBe(true);
  });

  it("depois de abrir, o proximo clique recomeca do um", () => {
    const aberto = sequencia([0, 300, 600, 900, 1200]);
    expect(registrarClique(aberto, 1400).cliques).toBe(1);
  });
});
