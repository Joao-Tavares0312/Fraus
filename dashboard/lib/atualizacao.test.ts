import { describe, expect, it } from "vitest";
import { INTERVALO_MINIMO_FOCO_MS, deveAtualizarNoFoco } from "./atualizacao";

describe("deveAtualizarNoFoco", () => {
  it("nao relê antes de 60 s desde a ultima leitura", () => {
    expect(deveAtualizarNoFoco(1_000 + INTERVALO_MINIMO_FOCO_MS - 1, 1_000)).toBe(false);
  });

  it("relê a partir de 60 s", () => {
    expect(deveAtualizarNoFoco(1_000 + INTERVALO_MINIMO_FOCO_MS, 1_000)).toBe(true);
  });
});
