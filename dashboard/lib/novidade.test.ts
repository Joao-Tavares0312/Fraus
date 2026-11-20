import { describe, expect, it } from "vitest";
import { ehNovo } from "./novidade";

describe("ehNovo", () => {
  const VISTO = Date.parse("2026-11-20T12:00:00Z");

  it("marca o que chegou depois da ultima visita", () => {
    expect(ehNovo("2026-11-20T12:00:01+00:00", VISTO)).toBe(true);
  });

  it("nao marca o que ja estava la", () => {
    expect(ehNovo("2026-11-20T11:59:59+00:00", VISTO)).toBe(false);
    expect(ehNovo("2026-11-20T12:00:00+00:00", VISTO)).toBe(false);
  });

  it("hora de chegada desconhecida nao e novidade", () => {
    // Linha anterior a coluna `recebida_em`: ausencia nao vira data.
    expect(ehNovo(null, VISTO)).toBe(false);
    expect(ehNovo(undefined, VISTO)).toBe(false);
    expect(ehNovo("nao e data", VISTO)).toBe(false);
  });

  it("sem marco de visita (servidor, armazenamento bloqueado) nada e novo", () => {
    expect(ehNovo("2026-11-20T12:00:01+00:00", null)).toBe(false);
  });
});
