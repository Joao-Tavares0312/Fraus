import { describe, expect, it } from "vitest";
import { permiteCena3D, permiteParticulas } from "./capacidade-visual";

const desktop = {
  largura: 1440,
  movimentoReduzido: false,
  economizarDados: false,
  memoriaGb: 8,
  nucleos: 8,
};

describe("politica de aprimoramento visual", () => {
  it("habilita a experiencia completa num desktop capaz", () => {
    expect(permiteCena3D(desktop)).toBe(true);
    expect(permiteParticulas(desktop)).toBe(true);
  });

  it.each([
    { ...desktop, movimentoReduzido: true },
    { ...desktop, economizarDados: true },
  ])("respeita preferencias de acessibilidade e dados", (sinais) => {
    expect(permiteCena3D(sinais)).toBe(false);
    expect(permiteParticulas(sinais)).toBe(false);
  });

  it("mantem a narrativa leve em telas pequenas e aparelhos limitados", () => {
    expect(permiteCena3D({ ...desktop, largura: 390 })).toBe(false);
    expect(permiteCena3D({ ...desktop, memoriaGb: 4 })).toBe(false);
    expect(permiteCena3D({ ...desktop, nucleos: 4 })).toBe(false);
  });
});
