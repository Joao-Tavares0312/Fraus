import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Palavras } from "./Palavras";

describe("Palavras", () => {
  it("marca so a palavra em destaque com a pincelada", () => {
    const html = renderToStaticMarkup(<Palavras texto="A análise começa." destaque="análise" />);
    expect(html.match(/class="pincel"/g)).toHaveLength(1);
    expect(html).toContain('<span class="w w-pincel"><span class="pincel">análise</span></span>');
    expect(html.match(/class="w/g)).toHaveLength(3);
  });

  it("sem destaque a saida nao muda", () => {
    const html = renderToStaticMarkup(<Palavras texto="A análise começa." />);
    expect(html).not.toContain("pincel");
    expect(html).toBe(
      '<span class="w"><span>A</span></span> <span class="w"><span>análise</span></span> <span class="w"><span>começa.</span></span>',
    );
  });
});
