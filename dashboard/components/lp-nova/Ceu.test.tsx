import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Ceu } from "./Ceu";

describe("Ceu", () => {
  const html = renderToStaticMarkup(<Ceu />);

  it("renderiza igual em duas chamadas", () => {
    expect(renderToStaticMarkup(<Ceu />)).toBe(html);
  });

  it("e decorativo e traz 140 pontos e 26 riscos", () => {
    expect(html).toContain('aria-hidden="true"');
    expect(html.match(/class="lp-ponto/g)).toHaveLength(140);
    expect(html.match(/class="lp-risco/g)).toHaveLength(26);
  });

  it("separa os pontos em tres planos de profundidade", () => {
    expect(html.match(/class="lp-plano"/g)).toHaveLength(3);
  });

  it("traz nevoa e feixe da fenda como camadas de fundo", () => {
    for (const camada of ["lp-nevoa", "lp-feixe"]) expect(html).toContain(`class="${camada}"`);
  });
});
