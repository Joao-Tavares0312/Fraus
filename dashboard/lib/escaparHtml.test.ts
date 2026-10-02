import { describe, expect, it } from "vitest";

import { escaparHtml } from "./escaparHtml";

describe("escaparHtml", () => {
  it("neutraliza a marcação que um id de conversa pode carregar", () => {
    const rotulo = `Atendimento <img src=x onerror="fetch('/api/fraus/conversas')">`;
    const saida = escaparHtml(rotulo);
    expect(saida).not.toMatch(/[<>"]/);
    expect(saida).toBe(
      "Atendimento &lt;img src=x onerror=&quot;fetch(&#39;/api/fraus/conversas&#39;)&quot;&gt;",
    );
  });

  it("escapa o & primeiro, para não escapar duas vezes", () => {
    expect(escaparHtml("a & b < c")).toBe("a &amp; b &lt; c");
    expect(escaparHtml("&lt;")).toBe("&amp;lt;");
  });

  it("devolve texto comum intacto, com acento", () => {
    expect(escaparHtml("Atendimento fonte:3:pedido-91 · ação")).toBe(
      "Atendimento fonte:3:pedido-91 · ação",
    );
  });
});
