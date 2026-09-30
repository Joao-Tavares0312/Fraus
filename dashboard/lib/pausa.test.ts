import { describe, expect, it } from "vitest";
import { LIMIARES_LATENCIA_PADRAO } from "./derivacoes";
import { fracaoDaPausa } from "./pausa";

describe("fracaoDaPausa", () => {
  it("a espera que chega ao limiar de degradacao ocupa a regua inteira", () => {
    expect(fracaoDaPausa(180, LIMIARES_LATENCIA_PADRAO)).toBe(1);
  });

  it("o excesso nao cresce: a regua e o teto", () => {
    expect(fracaoDaPausa(900, LIMIARES_LATENCIA_PADRAO)).toBe(1);
  });

  it("e proporcional entre o piso e o teto", () => {
    expect(fracaoDaPausa(90, LIMIARES_LATENCIA_PADRAO)).toBeCloseTo(0.5, 5);
  });

  it("segue o limiar VIGENTE, nao um numero digitado", () => {
    const limiares = { pico: 5, saudavel: 30, degradando: 60 };
    expect(fracaoDaPausa(30, limiares)).toBeCloseTo(0.5, 5);
    expect(fracaoDaPausa(30, LIMIARES_LATENCIA_PADRAO)).toBeCloseTo(30 / 180, 5);
  });

  it("uma pausa curta continua visivel (piso), sem virar zero", () => {
    expect(fracaoDaPausa(1, LIMIARES_LATENCIA_PADRAO)).toBeGreaterThan(0);
  });

  it("valor invalido nao quebra a regua", () => {
    expect(fracaoDaPausa(Number.NaN, LIMIARES_LATENCIA_PADRAO)).toBeGreaterThan(0);
    expect(fracaoDaPausa(60, { pico: 1, saudavel: 2, degradando: 0 })).toBe(1);
  });
});
