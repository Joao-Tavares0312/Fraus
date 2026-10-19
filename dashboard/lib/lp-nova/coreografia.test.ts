import { describe, expect, it } from "vitest";
import {
  FATOS_LP,
  POSE_INICIAL,
  POSES_POR_SECAO,
  SECOES_INDICE,
  criarParticulas,
  formatarContador,
  rotuloIndice,
} from "./coreografia";

describe("fatos da LP", () => {
  it("publica os numeros do contrato do motor", () => {
    expect(FATOS_LP.map(({ valor }) => valor)).toEqual([7, 39, 3, 0]);
  });
});

describe("formatarContador", () => {
  it("preenche com zero e arredonda o quadro intermediario", () => {
    expect(formatarContador(0, 3)).toBe("000");
    expect(formatarContador(38.6, 2)).toBe("39");
    expect(formatarContador(7, 2)).toBe("07");
  });
  it("nunca exibe negativo durante um ease que ultrapassa o alvo", () => {
    expect(formatarContador(-0.4, 2)).toBe("00");
  });
});

describe("indice lateral", () => {
  it("rotula a posicao sobre o total de secoes", () => {
    expect(SECOES_INDICE).toHaveLength(7);
    expect(rotuloIndice(0)).toBe("01 / 07");
    expect(rotuloIndice(6)).toBe("07 / 07");
  });
});

describe("poses do palco", () => {
  it("tem uma pose por transicao entre as secoes e todas completas", () => {
    expect(POSES_POR_SECAO).toHaveLength(SECOES_INDICE.length - 1);
    for (const pose of POSES_POR_SECAO) {
      expect(Object.keys(pose).sort()).toEqual(["gap", "rx", "ry", "rz", "s", "x"]);
    }
  });
  it("comeca sem inversao e sem deslocamento vertical", () => {
    expect(POSE_INICIAL.inv).toBe(0);
    expect(POSE_INICIAL.y).toBe(0);
  });
});

describe("criarParticulas", () => {
  it("e deterministica: o mesmo campo em todo carregamento", () => {
    expect(criarParticulas(50)).toEqual(criarParticulas(50));
  });
  it("distribui num anel atras do FR", () => {
    const pontos = criarParticulas(400);
    expect(pontos).toHaveLength(1200);
    for (let i = 0; i < pontos.length; i += 3) {
      const raio = Math.hypot(pontos[i], pontos[i + 2] + 2);
      expect(raio).toBeGreaterThanOrEqual(4 - 1e-6);
      expect(raio).toBeLessThanOrEqual(11 + 1e-6);
      expect(Math.abs(pontos[i + 1])).toBeLessThanOrEqual(5);
    }
  });
});
