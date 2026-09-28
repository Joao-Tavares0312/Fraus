import { describe, expect, it } from "vitest";

import { classificarSaude } from "./estado-saude";

describe("classificarSaude", () => {
  it.each([
    ["frio", "frio"],
    ["carregando", "aquecendo"],
    ["pronto", "no-ar"],
    ["erro", "erro-motor"],
  ] as const)("traduz o estado %s do motor para %s", (estadoMotor, esperado) => {
    expect(
      classificarSaude({
        ok: true,
        dado: { status: "ok", motor: "real", estado_motor: estadoMotor },
      }),
    ).toBe(esperado);
  });

  it("preserva compatibilidade com API real anterior ao estado explicito", () => {
    expect(classificarSaude({ ok: true, dado: { status: "ok", motor: "real" } })).toBe(
      "no-ar",
    );
  });

  it("nunca anuncia motor desconhecido como real", () => {
    expect(classificarSaude({ ok: true, dado: { status: "ok" } })).toBe("duble");
    expect(classificarSaude({ ok: false, erro: "sem resposta" })).toBe("fora-do-ar");
  });
});
