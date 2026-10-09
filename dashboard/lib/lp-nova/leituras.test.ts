import { describe, expect, it } from "vitest";
import { IDS_LEITURAS, concordaComRoteiro, dataDaGravacao, validarLeituras } from "./leituras";

function leitura(id: string, score: number | null) {
  return {
    id,
    score,
    nota: score === null ? null : Math.round(score / 10),
    categoria: score === null ? null : "detrator",
    motivo_sem_sinal: score === null ? "sem_fala_do_cliente" : null,
    mensagens: [],
    contribuicoes: [],
    conversa: { id: `lp-${id}`, mensagens: [] },
    sha256: "ab".repeat(32),
  };
}

function conjunto() {
  return {
    procedencia: { gravado_em: "2026-10-09T13:00:00+00:00", api: "https://exemplo.invalid", modelo: "fusor:abc123def456" },
    leituras: IDS_LEITURAS.map((id) => leitura(id, id === "sem-sinal" ? null : 30)),
  };
}

describe("validarLeituras", () => {
  it("sem arquivo gravado, nomeia o que falta para o VISITANTE, sem instrucao de desenvolvedor", () => {
    const r = validarLeituras(null);
    expect("falta" in r && r.falta).toMatch(/ainda não foram gravadas/);
    expect("falta" in r && r.falta).not.toMatch(/scripts\/|\.py/);
  });

  it("aceita o conjunto completo, na ordem da pagina", () => {
    const r = validarLeituras(conjunto());
    expect("leituras" in r && r.leituras.map((l) => l.id)).toEqual([...IDS_LEITURAS]);
  });

  it("recusa quando falta uma das cinco", () => {
    const c = conjunto();
    c.leituras = c.leituras.filter((l) => l.id !== "ironia");
    expect(validarLeituras(c)).toEqual({ falta: expect.stringMatching(/ironia/) });
  });

  it("recusa sem-sinal com nota: ausencia de dado nunca vira numero", () => {
    const c = conjunto();
    c.leituras[4] = leitura("sem-sinal", 0);
    expect(validarLeituras(c)).toEqual({ falta: expect.stringMatching(/sem-sinal/) });
  });

  it("recusa leitura com cliente que veio sem nota", () => {
    const c = conjunto();
    c.leituras[2] = leitura("espera", null);
    expect(validarLeituras(c)).toEqual({ falta: expect.stringMatching(/espera/) });
  });

  it("recusa procedencia incompleta: etiqueta sem lastro", () => {
    const c = conjunto();
    c.procedencia.modelo = "";
    expect(validarLeituras(c)).toEqual({ falta: expect.stringMatching(/procedência/) });
  });
});

describe("dataDaGravacao", () => {
  it("usa o fuso do produto: 01:30 UTC do dia 10 ainda e dia 9 em Brasilia", () => {
    expect(dataDaGravacao("2026-10-10T01:30:00+00:00")).toBe("09/10/2026");
  });
});

describe("concordaComRoteiro", () => {
  it("o roteiro do obrigado e de detrator", () => {
    expect(concordaComRoteiro({ id: "obrigado", categoria: "detrator" })).toBe(true);
    expect(concordaComRoteiro({ id: "obrigado", categoria: "neutro" })).toBe(false);
  });
  it("sem-sinal concorda quando nao ha categoria", () => {
    expect(concordaComRoteiro({ id: "sem-sinal", categoria: null })).toBe(true);
  });
  it("o promotor concorda so com promotor", () => {
    expect(concordaComRoteiro({ id: "promotor", categoria: "promotor" })).toBe(true);
    expect(concordaComRoteiro({ id: "promotor", categoria: "neutro" })).toBe(false);
  });
});
