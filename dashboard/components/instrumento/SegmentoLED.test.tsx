import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { celulaDe, celulasDoValor, totalDeAcesos } from "../../lib/segmentos";

/** Segmentos acesos de um digito; qualquer outra celula nao tem nenhum. */
const acesosDe = (caractere: string) => {
  const c = celulaDe(caractere);
  return c.tipo === "digito" ? c.acesos : [];
};
import { SegmentoLED } from "./SegmentoLED";

/**
 * O SegmentoLED e onde a invariante 2 do CLAUDE.md vira desenho: ausencia nao
 * e zero. Estes testes prendem as tres coisas que nao podem regredir --
 * o numero certo acende os segmentos certos, `null` nao acende NADA, e o
 * rotulo acessivel sempre existe.
 */

const html = (props: Parameters<typeof SegmentoLED>[0]) =>
  renderToStaticMarkup(<SegmentoLED {...props} />);

/** Quantos poligonos ACESOS (marcados com data-aceso) o markup tem. */
const acesos = (markup: string) => (markup.match(/data-aceso=/g) ?? []).length;

describe("celulaDe", () => {
  it("acende os segmentos certos de cada digito", () => {
    expect(celulaDe("1")).toEqual({ tipo: "digito", acesos: ["b", "c"] });
    expect(celulaDe("7")).toEqual({ tipo: "digito", acesos: ["a", "b", "c"] });
    expect(celulaDe("8")).toMatchObject({ tipo: "digito" });
    expect(acesosDe("8")).toHaveLength(7);
    expect(acesosDe("0")).not.toContain("g");
  });

  it("o hifen e so o segmento do meio", () => {
    expect(celulaDe("-")).toEqual({ tipo: "digito", acesos: ["g"] });
  });

  it("o menos tipografico e o hifen sao o mesmo sinal", () => {
    expect(celulaDe("−")).toEqual(celulaDe("-"));
  });

  it("o mais do NPS positivo e uma celula propria, nao texto cru", () => {
    expect(celulaDe("+")).toEqual({ tipo: "mais" });
  });

  it("separadores sao celulas estreitas", () => {
    expect(celulaDe(",")).toEqual({ tipo: "virgula" });
    // O ponto NAO e a virgula: em pt-BR `66.1` e `66,1` sao numeros diferentes.
    expect(celulaDe(".")).toEqual({ tipo: "ponto" });
    expect(celulaDe(":")).toEqual({ tipo: "doispontos" });
    expect(celulaDe(" ")).toEqual({ tipo: "espaco" });
  });

  it("caractere fora do alfabeto nao some: vira texto cru", () => {
    expect(celulaDe("%")).toEqual({ tipo: "cru", texto: "%" });
    expect(celulaDe("s")).toEqual({ tipo: "cru", texto: "s" });
  });
});

describe("celulasDoValor", () => {
  it("valor null vira celulas apagadas, nunca zero", () => {
    const c = celulasDoValor(null, 3);
    expect(c).toHaveLength(3);
    expect(totalDeAcesos(c)).toBe(0);
  });

  it("respeita o numero de celulas pedido e nunca devolve menos de uma", () => {
    expect(celulasDoValor(null, 5)).toHaveLength(5);
    expect(celulasDoValor(null, 0)).toHaveLength(1);
  });

  it("o zero aceso e diferente do apagado", () => {
    expect(totalDeAcesos(celulasDoValor("0", 3))).toBe(6);
    expect(totalDeAcesos(celulasDoValor(null, 1))).toBe(0);
  });
});

describe("SegmentoLED", () => {
  it("digitos: 39 acende 5 + 6 segmentos", () => {
    // 3 = a b c d g (5)   9 = a b c d f g (6)
    expect(acesos(html({ valor: "39", rotulo: "features" }))).toBe(11);
  });

  it("negativo: -18 acende g + (b c) + (7 segmentos)", () => {
    expect(acesos(html({ valor: "-18", rotulo: "NPS" }))).toBe(1 + 2 + 7);
  });

  it("decimal: 2,9 tem duas celulas largas e uma virgula", () => {
    const m = html({ valor: "2,9", rotulo: "nota" });
    expect(m.match(/data-celula="digito"/g)).toHaveLength(2);
    expect(m.match(/data-celula="virgula"/g)).toHaveLength(1);
    // A virgula tem CAUDA (`data-cauda`); o ponto nao.
    expect(m).toContain("data-cauda");
    expect(acesos(m)).toBe(5 + 6);
  });

  it("ponto: 2.9 desenha o ponto, sem cauda", () => {
    const m = html({ valor: "2.9", rotulo: "nota" });
    expect(m.match(/data-celula="ponto"/g)).toHaveLength(1);
    expect(m).not.toContain("data-cauda");
  });

  it("hora: 4:12 tem tres digitos e dois-pontos", () => {
    const m = html({ valor: "4:12", rotulo: "latência" });
    expect(m.match(/data-celula="digito"/g)).toHaveLength(3);
    expect(m.match(/data-celula="doispontos"/g)).toHaveLength(1);
  });

  it("null: nenhum segmento aceso, marcado como apagado", () => {
    const m = html({ valor: null, rotulo: "nota estimada" });
    expect(acesos(m)).toBe(0);
    expect(m).toContain('data-apagado="true"');
    expect(m.match(/data-celula="digito"/g)).toHaveLength(3);
  });

  it("null: o aria-label diz sem sinal e nunca inventa um numero", () => {
    const m = html({ valor: null, rotulo: "nota estimada" });
    expect(m).toContain('aria-label="nota estimada: sem sinal"');
    expect(m).not.toMatch(/aria-label="[^"]*\b0\b/);
  });

  it("NPS positivo: +12 desenha o mais e nao vira texto", () => {
    const m = html({ valor: "+12", rotulo: "NPS" });
    expect(m).toContain('data-celula="mais"');
    expect(m).not.toContain('data-celula="cru"');
  });

  it("caractere invalido vira texto cru e nao quebra", () => {
    const m = html({ valor: "38%", rotulo: "contenção" });
    expect(m).toContain('data-celula="cru"');
    expect(m).toContain(">%<");
    expect(acesos(m)).toBe(5 + 7);
  });

  it("o aria-label junta o rotulo e o valor por extenso", () => {
    expect(html({ valor: "2,9", rotulo: "nota estimada" })).toContain(
      'aria-label="nota estimada 2,9"',
    );
  });

  it("as celulas internas ficam escondidas do leitor de tela", () => {
    const m = html({ valor: "12", rotulo: "x" });
    expect(m).toContain('role="img"');
    expect(m.match(/aria-hidden="true"/g)!.length).toBeGreaterThanOrEqual(2);
  });

  it("o traco fino (vitrine) apaga o brilho mas continua desenhando o apagado", () => {
    const fino = html({ valor: "2,9", rotulo: "nota", traco: "fino" });
    expect(fino).not.toContain("drop-shadow");
    expect(fino).toContain('data-traco="fino"');
    // 2 acende 5, 9 acende 6: os mesmos segmentos do traco cheio
    expect(acesos(fino)).toBe(11);
    const vazio = html({ valor: null, rotulo: "nota", traco: "fino" });
    expect(acesos(vazio)).toBe(0);
    expect(vazio).toContain("sem sinal");
    expect(vazio.match(/<polygon/g)!.length).toBe(21);
  });

  it("a cor vem de token, nunca de literal", () => {
    expect(html({ valor: "1", rotulo: "x" })).toContain("var(--medido)");
    expect(html({ valor: "1", rotulo: "x", cor: "marca" })).toContain("var(--primary)");
    expect(html({ valor: "1", rotulo: "x", cor: "tinta" })).toContain("var(--foreground)");
    expect(html({ valor: "1", rotulo: "x", cor: "erro" })).toContain("var(--destructive)");
  });
});
