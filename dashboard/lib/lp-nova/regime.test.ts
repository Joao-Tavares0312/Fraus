import { describe, expect, it } from "vitest";
import { PARTICULAS, rebaixar, regimeInicial, rotuloDoRegime } from "./regime";

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

describe("orcamento e rotulo", () => {
  it("o regime baixo sempre gasta menos que o alto", () => {
    expect(PARTICULAS["vivo-baixo"].desktop).toBeLessThan(PARTICULAS["vivo-alto"].desktop);
    expect(PARTICULAS["vivo-baixo"].celular).toBeLessThan(PARTICULAS["vivo-alto"].celular);
    expect(PARTICULAS["vivo-alto"].celular).toBe(16000);
    expect(PARTICULAS["vivo-baixo"].celular).toBe(4000);
  });
  it("nomeia o que falta em vez de esconder", () => {
    expect(rotuloDoRegime("vivo-alto", "inicial")).toBe("GPU · alto");
    expect(rotuloDoRegime("vivo-baixo", "quadros")).toBe("GPU · baixo · quadros lentos");
    expect(rotuloDoRegime("poster", "sem-webgpu")).toBe("pôster · sem WebGPU");
    expect(rotuloDoRegime("poster", "movimento-reduzido")).toBe("pôster · movimento reduzido");
  });
});
