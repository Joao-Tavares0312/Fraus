import { describe, expect, it } from "vitest";
import { MARCOS, faseDominante, pesosDasFases, progressoDaRolagem } from "./fases";

const soma = (p: ReturnType<typeof pesosDasFases>) =>
  p.frase + p.disperso + p.mascara + p.nos + p.orbe + p.leitura;

describe("pesosDasFases", () => {
  it("no topo da pagina, as particulas sao a frase", () => {
    expect(pesosDasFases(0).frase).toBe(1);
  });

  it("os pesos de posicao sempre somam 1: a particula nunca fica sem destino", () => {
    for (let p = 0; p <= 1.0001; p += 0.01) expect(soma(pesosDasFases(p))).toBeCloseTo(1, 6);
  });

  it("cada marco da historia e dominado pela sua fase", () => {
    expect(pesosDasFases(MARCOS.disperso).disperso).toBe(1);
    expect(pesosDasFases(MARCOS.mascara).mascara).toBe(1);
    expect(pesosDasFases(MARCOS.nos).nos).toBe(1);
    expect(pesosDasFases(MARCOS.orbe).orbe).toBe(1);
    expect(pesosDasFases(MARCOS.leitura).leitura).toBe(1);
  });

  it("a constelacao da vitrine antiga vem antes do fusor: mascara, depois nos, depois orbe", () => {
    expect(MARCOS.mascara).toBeLessThan(MARCOS.nos);
    expect(MARCOS.nos).toBeLessThan(MARCOS.orbe);
  });

  it("os marcos estao em ordem: a historia nao anda para tras", () => {
    const m = Object.values(MARCOS);
    expect([...m].sort((a, b) => a - b)).toEqual(m);
  });

  it("no fecho as particulas voltam ao orbe e respiram", () => {
    const fim = pesosDasFases(1);
    expect(fim.orbe).toBe(1);
    expect(fim.respira).toBe(1);
  });

  it("na secao do analista o campo recua para nao competir com o dado", () => {
    expect(pesosDasFases(MARCOS.recuo).brilho).toBeLessThan(0.4);
    expect(pesosDasFases(MARCOS.nos).brilho).toBe(1);
  });

  it("grampeia progresso fora de [0, 1]", () => {
    expect(pesosDasFases(-3)).toEqual(pesosDasFases(0));
    expect(pesosDasFases(7)).toEqual(pesosDasFases(1));
  });
});

describe("progressoDaRolagem", () => {
  const ancoras = [
    { y: 0, p: 0 },
    { y: 1000, p: 0.14 },
    { y: 3000, p: 0.5 },
    { y: 5000, p: 1 },
  ];
  it("no ponto da ancora, devolve o marco dela", () => {
    expect(progressoDaRolagem(1000, ancoras)).toBeCloseTo(0.14);
    expect(progressoDaRolagem(3000, ancoras)).toBeCloseTo(0.5);
  });
  it("entre ancoras, interpola linearmente", () => {
    expect(progressoDaRolagem(2000, ancoras)).toBeCloseTo(0.32);
  });
  it("antes da primeira e depois da ultima, grampeia", () => {
    expect(progressoDaRolagem(-50, ancoras)).toBe(0);
    expect(progressoDaRolagem(9999, ancoras)).toBe(1);
  });
  it("ancoras fora de ordem sao ordenadas por y", () => {
    expect(progressoDaRolagem(2000, [...ancoras].reverse())).toBeCloseTo(0.32);
  });
  it("sem ancoras, o progresso fica no topo", () => {
    expect(progressoDaRolagem(500, [])).toBe(0);
  });
});

describe("faseDominante", () => {
  it("nomeia o momento que mais pesa", () => {
    expect(faseDominante(MARCOS.mascara)).toBe("mascara");
    expect(faseDominante(MARCOS.nos)).toBe("nos");
    expect(faseDominante(MARCOS.orbe)).toBe("orbe");
    expect(faseDominante(0)).toBe("frase");
  });
});
