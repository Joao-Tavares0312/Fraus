import { describe, expect, it } from "vitest";
import { FAMILIAS_DO_VETOR, FATOS_DO_MODELO } from "../../components/lp/fatos";
import {
  ESTADOS_DO_ORBE,
  estagioDaConstelacao,
  grampear01,
  misturar,
  monotonizar,
  orbeEntreQuadros,
  type EstadoDoOrbe,
} from "./coreografia";

describe("as familias da constelacao", () => {
  it("somam exatamente as features do fusor", () => {
    const soma = FAMILIAS_DO_VETOR.reduce((total, f) => total + f.qtd, 0);
    expect(soma).toBe(FATOS_DO_MODELO.features);
  });

  it("sao sete, como o vetor", () => {
    expect(FAMILIAS_DO_VETOR).toHaveLength(FATOS_DO_MODELO.familias);
  });
});

describe("grampear01", () => {
  it("prende no intervalo e trata NaN como o extremo seguro", () => {
    expect(grampear01(-2)).toBe(0);
    expect(grampear01(3)).toBe(1);
    expect(grampear01(0.4)).toBe(0.4);
    expect(grampear01(Number.NaN)).toBe(0);
  });
});

describe("estagioDaConstelacao", () => {
  it("abre nas palavras e fecha dentro do fusor", () => {
    expect(estagioDaConstelacao(0)).toBe(1);
    expect(estagioDaConstelacao(1)).toBe(4);
  });

  it("nunca volta atras enquanto a rolagem avanca", () => {
    let anterior = estagioDaConstelacao(0);
    for (let p = 0; p <= 1.0001; p += 0.01) {
      const k = estagioDaConstelacao(p);
      expect(k).toBeGreaterThanOrEqual(anterior - 1e-9);
      anterior = k;
    }
  });

  it("segura cada forma por um trecho, para ela ser lida", () => {
    // mascara inteira e nos inteiros existem em algum platô
    expect(estagioDaConstelacao(0.37)).toBe(2);
    expect(estagioDaConstelacao(0.66)).toBe(3);
  });

  it("grampeia progresso fora da faixa e NaN", () => {
    expect(estagioDaConstelacao(-1)).toBe(1);
    expect(estagioDaConstelacao(7)).toBe(4);
    expect(estagioDaConstelacao(Number.NaN)).toBe(1);
  });
});

describe("misturar", () => {
  const a = ESTADOS_DO_ORBE.largo.hero;
  const b = ESTADOS_DO_ORBE.largo.fecho;

  it("devolve as pontas em 0 e 1", () => {
    expect(misturar(a, b, 0)).toEqual(a);
    expect(misturar(a, b, 1)).toEqual(b);
  });
});

describe("o orbe no sem sinal", () => {
  it("perde a cor e para: ausencia nao e um estado colorido da escala", () => {
    for (const largura of ["largo", "estreito"] as const) {
      const vazio = ESTADOS_DO_ORBE[largura].vazio;
      expect(vazio.sat).toBe(0);
      expect(vazio.vel).toBe(0);
    }
  });
});

describe("a cor do orbe acompanha a secao", () => {
  it("o ambar (dito) domina na entrada da conversa e o azul (medido) no fusor", () => {
    for (const largura of ["largo", "estreito"] as const) {
      const e = ESTADOS_DO_ORBE[largura];
      expect(e.canto.dito).toBeGreaterThan(e.canto.medido);
      expect(e.fusor.medido).toBeGreaterThan(e.fusor.dito);
    }
  });

  it("o fecho devolve o ambar: o cliente mente, o texto nao", () => {
    const e = ESTADOS_DO_ORBE.largo;
    expect(e.fecho.dito).toBeGreaterThan(e.fecho.medido);
  });

  it("interpola a cor junto com a posicao", () => {
    const e = ESTADOS_DO_ORBE.largo;
    const meio = misturar(e.canto, e.fusor, 0.5);
    expect(meio.medido).toBeCloseTo((e.canto.medido + e.fusor.medido) / 2);
  });
});

describe("orbeEntreQuadros", () => {
  const A: EstadoDoOrbe = { ...ESTADOS_DO_ORBE.largo.hero };
  const B: EstadoDoOrbe = { ...ESTADOS_DO_ORBE.largo.canto };
  const quadros = [
    { y: 0, estado: () => A },
    { y: 100, estado: () => B },
  ];

  it("fica no primeiro antes do inicio e no ultimo depois do fim", () => {
    expect(orbeEntreQuadros(quadros, -50)).toEqual(A);
    expect(orbeEntreQuadros(quadros, 500)).toEqual(B);
  });

  it("interpola no meio", () => {
    const meio = orbeEntreQuadros(quadros, 50);
    expect(meio.x).toBeGreaterThan(Math.min(A.x, B.x));
    expect(meio.x).toBeLessThan(Math.max(A.x, B.x));
  });
});

describe("monotonizar", () => {
  it("empurra quadros fora de ordem para depois do anterior", () => {
    expect(monotonizar([0, 50, 40, 200])).toEqual([0, 50, 51, 200]);
  });
});
