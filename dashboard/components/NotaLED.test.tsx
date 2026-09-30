import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { NotaLED } from "./NotaLED";

/**
 * A nota no LED carrega a invariante 2 (ausencia nao e zero) para TODOS os
 * lugares que a mostram. Estes testes prendem a unica coisa que importa: nota
 * nula NAO acende segmento algum, e nota 0 (que e nota, e detrator) acende.
 */
const html = (nota: number | null) =>
  renderToStaticMarkup(<NotaLED nota={nota} />);
const acesos = (markup: string) => (markup.match(/data-aceso=/g) ?? []).length;

describe("NotaLED", () => {
  it("nota nula: nenhum segmento aceso e o rotulo diz sem sinal", () => {
    const markup = html(null);
    expect(acesos(markup)).toBe(0);
    expect(markup).toContain("sem sinal");
    expect(markup).toContain('data-apagado="true"');
  });

  it("nota ZERO e uma nota (detrator), nao ausencia: acende os segmentos do 0", () => {
    const markup = html(0);
    expect(acesos(markup)).toBe(6);
    expect(markup).not.toContain("data-apagado");
    expect(markup).toContain("nota inferida, estimativa 0");
  });

  it("nota 10 ocupa duas celulas", () => {
    // "1" acende b,c (2) e "0" acende 6.
    expect(acesos(html(10))).toBe(8);
  });
});
