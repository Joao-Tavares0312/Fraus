import { describe, expect, it } from "vitest";
import { escolherEtapa } from "./narrativa";

describe("etapa visivel da narrativa", () => {
  it("escolhe a maior porcao visivel, nao a ultima entrada do observador", () => {
    expect(escolherEtapa([
      { etapa: 0, top: -400, bottom: 200 },
      { etapa: 1, top: 200, bottom: 900 },
      { etapa: 2, top: 900, bottom: 1600 },
    ], 800)).toBe(1);
  });

  it("desempata pela proximidade do centro da viewport", () => {
    expect(escolherEtapa([
      { etapa: 0, top: -1000, bottom: 400 },
      { etapa: 1, top: 400, bottom: 800 },
    ], 800)).toBe(1);
  });

  it("nao inventa etapa se a narrativa saiu da viewport", () => {
    expect(escolherEtapa([{ etapa: 3, top: -900, bottom: -100 }], 800)).toBeNull();
    expect(escolherEtapa([], 800)).toBeNull();
  });

});
