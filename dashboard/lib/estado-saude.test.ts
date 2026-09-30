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

import { intervaloDeSaudeMs, suavizarSaude } from "./estado-saude";

describe("suavizarSaude", () => {
  it("nao rebaixa no-ar por causa de uma instancia fria", () => {
    expect(suavizarSaude("no-ar", "frio")).toBe("no-ar");
    expect(suavizarSaude("no-ar", "aquecendo")).toBe("no-ar");
  });
  it("rebaixa quando e de verdade pior", () => {
    expect(suavizarSaude("no-ar", "erro-motor")).toBe("erro-motor");
    expect(suavizarSaude("no-ar", "fora-do-ar")).toBe("fora-do-ar");
    expect(suavizarSaude("no-ar", "duble")).toBe("duble");
  });
  it("sobe normalmente de frio para aquecendo e no-ar", () => {
    expect(suavizarSaude("verificando", "frio")).toBe("frio");
    expect(suavizarSaude("frio", "aquecendo")).toBe("aquecendo");
    expect(suavizarSaude("aquecendo", "no-ar")).toBe("no-ar");
  });
});

describe("intervaloDeSaudeMs", () => {
  it("consulta rapido enquanto nao esta pronto e devagar depois", () => {
    expect(intervaloDeSaudeMs("frio")).toBeLessThan(intervaloDeSaudeMs("no-ar"));
    expect(intervaloDeSaudeMs("aquecendo")).toBe(intervaloDeSaudeMs("frio"));
  });
});
