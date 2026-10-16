import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ValorNumerico } from "./ValorNumerico";
import { NotaInferida } from "./NotaInferida";

describe("ValorNumerico", () => {
  it("ausência é nomeada, não convertida em zero", () => {
    const html = renderToStaticMarkup(<ValorNumerico valor={null} rotulo="satisfação" />);
    expect(html).toContain('aria-label="satisfação: Sem sinal"');
    expect(html).toContain(">Sem sinal</span>");
    expect(html).not.toContain(">0</span>");
  });
  it.each(["0", "−18,2", "+39", "1:05", "não disponível"])("preserva integralmente %s sem calcular", (valor) => {
    const html = renderToStaticMarkup(<ValorNumerico valor={valor} rotulo="leitura" />);
    expect(html).toContain(`aria-label="leitura: ${valor}"`);
    expect(html).toContain(`>${valor}</span>`);
  });
  it("permite nomear a ausência de um agregado", () => {
    const html = renderToStaticMarkup(<ValorNumerico valor={null} rotulo="NPS inferido" ausencia="Sem estimativa" />);
    expect(html).toContain('aria-label="NPS inferido: Sem estimativa"');
  });
});

describe("NotaInferida", () => {
  it("zero é uma nota e conserva sua qualificação de estimativa", () => {
    const html = renderToStaticMarkup(<NotaInferida nota={0} />);
    expect(html).toContain('aria-label="nota inferida, estimativa: 0"');
    expect(html).toContain(">0</span>");
  });
  it("nota nula nunca ganha categoria ou valor por apresentação", () => {
    const html = renderToStaticMarkup(<NotaInferida nota={null} />);
    expect(html).toContain('aria-label="nota inferida, estimativa: Sem sinal"');
    expect(html).not.toContain(">0</span>");
  });
});
