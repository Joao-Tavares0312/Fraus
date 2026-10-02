import { describe, expect, it } from "vitest";
import { minutosRestantesDeExportacao } from "./operacao";

const AGORA = Date.parse("2026-10-02T12:00:00Z");

/**
 * `PUT /operacao/acesso/{id}` so aceita `exportar_minutos`, e 0 grava
 * `exporta_ate: None`. O campo nascia em 0 e era sempre enviado: editar so os
 * canais de uma conta encerrava a janela de exportacao dela.
 */
describe("minutosRestantesDeExportacao", () => {
  it("sem janela, zero", () => {
    expect(minutosRestantesDeExportacao(null, AGORA)).toBe(0);
  });

  it("janela vencida, zero", () => {
    expect(minutosRestantesDeExportacao("2026-10-02T11:59:00+00:00", AGORA)).toBe(0);
  });

  it("janela aberta devolve o que resta", () => {
    expect(minutosRestantesDeExportacao("2026-10-02T12:30:00+00:00", AGORA)).toBe(30);
  });

  it("fracao de minuto arredonda para cima: reenviar nunca encurta a janela", () => {
    expect(minutosRestantesDeExportacao("2026-10-02T12:00:20+00:00", AGORA)).toBe(1);
    expect(minutosRestantesDeExportacao("2026-10-02T12:29:30+00:00", AGORA)).toBe(30);
  });

  it("nunca passa do teto que a rota aceita", () => {
    expect(minutosRestantesDeExportacao("2026-10-03T12:00:00+00:00", AGORA)).toBe(480);
  });

  it("data ilegivel nao vira janela", () => {
    expect(minutosRestantesDeExportacao("nao-e-data", AGORA)).toBe(0);
  });
});
