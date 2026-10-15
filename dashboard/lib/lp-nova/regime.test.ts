import { describe, expect, it } from "vitest";
import { PARTICULAS, SaudeDeQuadros, rebaixar, regimeInicial } from "./regime";

const base = { temWebGpu: true, movimentoReduzido: false, falhouInit: false };

describe("regimeInicial", () => {
  it("comeca vivo e alto quando ha WebGPU", () => {
    expect(regimeInicial(base)).toEqual({ regime: "vivo-alto", motivo: "inicial" });
  });
  it("cai no poster sem WebGPU", () => {
    expect(regimeInicial({ ...base, temWebGpu: false })).toEqual({ regime: "poster", motivo: "sem-webgpu" });
  });
  it("cai no poster quando o init falhou, mesmo com navigator.gpu presente", () => {
    expect(regimeInicial({ ...base, falhouInit: true })).toEqual({ regime: "poster", motivo: "falha-gpu" });
  });
  it("movimento reduzido vence tudo: congela, nao desacelera", () => {
    expect(regimeInicial({ temWebGpu: false, movimentoReduzido: true, falhouInit: true })).toEqual({
      regime: "poster",
      motivo: "movimento-reduzido",
    });
  });
});

describe("rebaixar", () => {
  it("desce de alto para baixo com o motivo", () => {
    expect(rebaixar("vivo-alto", "quadros")).toEqual({ regime: "vivo-baixo", motivo: "quadros" });
  });
  it("nao desce de novo nem oscila: baixo continua baixo", () => {
    expect(rebaixar("vivo-baixo", "bateria").regime).toBe("vivo-baixo");
  });
  it("nunca tira o poster do lugar", () => {
    expect(rebaixar("poster", "quadros").regime).toBe("poster");
  });
});

describe("orcamento", () => {
  it("o regime baixo sempre gasta menos que o alto", () => {
    expect(PARTICULAS["vivo-baixo"].desktop).toBeLessThan(PARTICULAS["vivo-alto"].desktop);
    expect(PARTICULAS["vivo-baixo"].celular).toBeLessThan(PARTICULAS["vivo-alto"].celular);
  });
});

describe("SaudeDeQuadros", () => {
  it("quadros acima do orcamento por mais de 2 s pedem a descida", () => {
    const s = new SaudeDeQuadros();
    let desceu = false;
    for (let t = 0; t < 8000; t += 30) desceu = s.registrar(30, t) || desceu;
    expect(desceu).toBe(true);
  });
  it("a volta de uma aba oculta (um 'quadro' de um minuto) nao conta como lentidao", () => {
    const s = new SaudeDeQuadros();
    let desceu = s.registrar(60_000, 0);
    for (let t = 16; t < 4000; t += 20) desceu = s.registrar(20, t) || desceu;
    expect(desceu).toBe(false);
  });
  it("quadros dentro do orcamento nunca descem", () => {
    const s = new SaudeDeQuadros();
    let desceu = false;
    for (let t = 0; t < 6000; t += 16) desceu = s.registrar(16, t) || desceu;
    expect(desceu).toBe(false);
  });
  it.each([8, 16, 20, 24])("cadencia de %i ms permanece alta", (ms) => {
    const s = new SaudeDeQuadros();
    let desceu = false;
    for (let t = 0; t < 12_000; t += ms) desceu = s.registrar(ms, t) || desceu;
    expect(desceu).toBe(false);
  });
  it.each([25, 30, 60])("cadencia de %i ms sustentada pede descida", (ms) => {
    const s = new SaudeDeQuadros();
    let desceu = false;
    for (let t = 0; t < 16_000; t += ms) desceu = s.registrar(ms, t) || desceu;
    expect(desceu).toBe(true);
  });
  it("pausa voluntaria separa janelas de lentidao sem acumular os segundos oculta", () => {
    const s = new SaudeDeQuadros();
    for (let t = 0; t < 4800; t += 30) expect(s.registrar(30, t)).toBe(false);
    s.reiniciar();
    for (let t = 60_000; t < 64_800; t += 30) expect(s.registrar(30, t)).toBe(false);
    let desceu = false;
    for (let t = 64_800; t < 68_000; t += 30) desceu = s.registrar(30, t) || desceu;
    expect(desceu).toBe(true);
  });
});
