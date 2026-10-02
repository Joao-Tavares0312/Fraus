import { describe, expect, it } from "vitest";

import { diaDoProduto, noFusoDoProduto } from "./fuso";
import { formatarData, formatarDataHora, formatarHora } from "./formato";
import { dentroDoPeriodo, diaLocal } from "./periodo";

// 01:30 UTC do dia 13 ainda e 22:30 do dia 12 em Brasilia. A API agrupa por
// esse dia (`fraus/fuso.py`); a tela tem de escrever o mesmo.
const VIRADA = "2026-09-13T01:30:00Z";

describe("fuso do produto", () => {
  it("o dia de uma conversa e o dia de Brasilia, nao o do navegador", () => {
    expect(diaDoProduto(VIRADA)).toBe("2026-09-12");
    expect(diaDoProduto("2026-09-13T03:00:00Z")).toBe("2026-09-13");
    expect(diaDoProduto("2026-09-12T23:59:59-03:00")).toBe("2026-09-12");
  });

  it("nao muda com o offset em que o instante foi escrito", () => {
    expect(diaDoProduto("2026-09-13T10:30:00+09:00")).toBe("2026-09-12");
  });

  it("ano e mes viram junto com o dia", () => {
    expect(diaDoProduto("2027-01-01T02:00:00Z")).toBe("2026-12-31");
  });

  it("devolve as partes do relogio de Brasilia", () => {
    const partes = noFusoDoProduto(VIRADA);
    expect([partes.getUTCHours(), partes.getUTCMinutes()]).toEqual([22, 30]);
  });

  it("o filtro de periodo e a formatacao usam o mesmo dia", () => {
    expect(diaLocal(VIRADA)).toBe("2026-09-12");
    expect(dentroDoPeriodo(VIRADA, { de: "2026-09-12", ate: "2026-09-12" })).toBe(true);
    expect(dentroDoPeriodo(VIRADA, { de: "2026-09-13", ate: null })).toBe(false);
    expect(formatarData(VIRADA)).toBe("12/09/2026");
    expect(formatarDataHora(VIRADA)).toMatch(/^12\/09\/2026,? 22:30$/);
    expect(formatarHora(VIRADA)).toBe("22:30:00");
  });
});
