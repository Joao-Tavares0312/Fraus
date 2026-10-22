import { describe, expect, it } from "vitest";
import { gerarCeu, SEMENTE_CEU } from "./ceu";

describe("gerarCeu", () => {
  const ceu = gerarCeu(SEMENTE_CEU);

  it("tem 140 pontos e 26 riscos", () => {
    expect(ceu.pontos).toHaveLength(140);
    expect(ceu.riscos).toHaveLength(26);
  });

  it("e determinista por semente", () => {
    expect(gerarCeu(SEMENTE_CEU)).toEqual(ceu);
    expect(gerarCeu(SEMENTE_CEU + 1)).not.toEqual(ceu);
  });

  it("mantem os pontos nos intervalos fixados", () => {
    for (const p of ceu.pontos) {
      expect(p.x).toBeGreaterThanOrEqual(0);
      expect(p.x).toBeLessThanOrEqual(100);
      expect(p.y).toBeGreaterThanOrEqual(0);
      expect(p.y).toBeLessThanOrEqual(100);
      expect(p.opacidade).toBeGreaterThanOrEqual(0.35);
      expect(p.opacidade).toBeLessThanOrEqual(1);
      expect(p.tamanho).toBeGreaterThanOrEqual(1.5);
      expect(p.tamanho).toBeLessThanOrEqual(7);
      expect(p.atraso).toBeLessThanOrEqual(0);
      if (p.pisca) {
        expect(p.ciclo).toBeGreaterThanOrEqual(2.5);
        expect(p.ciclo).toBeLessThanOrEqual(7);
      }
    }
  });

  it("faz piscar entre 50% e 70% dos pontos", () => {
    const fracao = ceu.pontos.filter((p) => p.pisca).length / ceu.pontos.length;
    expect(fracao).toBeGreaterThanOrEqual(0.5);
    expect(fracao).toBeLessThanOrEqual(0.7);
  });

  it("mantem os riscos nos intervalos fixados", () => {
    for (const r of ceu.riscos) {
      expect(r.comprimento).toBeGreaterThanOrEqual(180);
      expect(r.comprimento).toBeLessThanOrEqual(520);
      expect(r.alfa).toBeGreaterThanOrEqual(0.04);
      expect(r.alfa).toBeLessThanOrEqual(0.12);
      expect(r.duracao).toBeGreaterThanOrEqual(14);
      expect(r.duracao).toBeLessThanOrEqual(30);
      expect(r.atraso).toBeLessThanOrEqual(0);
    }
  });
});
