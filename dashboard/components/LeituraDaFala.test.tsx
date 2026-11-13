import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { LeituraDaFala } from "./LeituraDaFala";

const classes = { insatisfeito: 0.52, neutro: 0.41, satisfeito: 0.07 };
const emocao = {
  alegria: 0.05, surpresa: 0.06, neutro: 0.19, tristeza: 0.21,
  medo: 0.02, raiva: 0.38, nojo: 0.09, desprezo: 0.18,
};
const html = (p: Partial<Parameters<typeof LeituraDaFala>[0]> = {}) =>
  renderToStaticMarkup(
    <LeituraDaFala classes={classes} emocao={emocao} ironia={0.64} recolher={false} {...p} />,
  );
const posicao = (m: string, trecho: string) => {
  const i = m.indexOf(trecho);
  expect(i, `faltou "${trecho}"`).toBeGreaterThan(-1);
  return i;
};

describe("LeituraDaFala", () => {
  it("sem nenhuma leitura nao desenha nada", () => {
    expect(html({ classes: null, emocao: null, ironia: null })).toBe("");
  });

  it("sao tres graficos, um por pergunta, cada um com o seu grupo", () => {
    const m = html();
    expect(m).toContain('aria-label="satisfação desta fala"');
    expect(m).toContain('aria-label="emoção desta fala"');
    expect(m).toContain('aria-label="ironia desta fala"');
  });

  it("so desenha o grafico da leitura que veio: ausencia nao vira zero", () => {
    const m = html({ classes: null, ironia: null });
    expect(m).not.toContain("satisfação desta fala");
    expect(m).not.toContain("ironia desta fala");
    expect(m).toContain("emoção desta fala");
  });

  it("satisfacao: veredito, as tres classes na ordem fixa e a disputa como distancia", () => {
    const m = html();
    expect(posicao(m, ">insatisfeito<")).toBeLessThan(posicao(m, ">neutro<"));
    expect(m).toContain("em disputa com neutro");
    expect(m).toContain("Δ ,11");
    expect(m).not.toContain("confiança");
    expect(m).toContain(",52");
    expect(m).toContain(",41");
    expect(m).toContain(",07");
  });

  it("satisfacao sem disputa diz a folga sobre a segunda", () => {
    const m = html({ classes: { insatisfeito: 0.04, neutro: 0.09, satisfeito: 0.87 } });
    expect(m).not.toContain("em disputa");
    expect(m).toContain("folga de");
    expect(m).toContain(",78");
  });

  it("emocao: da maior para a menor, dominante no topo, desprezo por ultimo e derivado", () => {
    const m = html();
    const ordem = ["raiva", "tristeza", "neutro", "nojo", "surpresa", "alegria", "medo", "desprezo"].map(
      (nome) => posicao(m, `data-emocao="${nome}"`),
    );
    expect([...ordem].sort((a, b) => a - b)).toEqual(ordem);
    expect(m).toContain("derivado de raiva + nojo");
  });

  it("emocao recolhida: so as maiores a vista, o resto e o desprezo atras do ver mais", () => {
    const m = html({ recolher: true });
    const corte = posicao(m, "<details");
    expect(posicao(m, 'data-emocao="tristeza"')).toBeLessThan(corte);
    expect(posicao(m, 'data-emocao="neutro"')).toBeGreaterThan(corte);
    expect(posicao(m, 'data-emocao="desprezo"')).toBeGreaterThan(corte);
    expect(m).toContain("mais 5 emoções e o desprezo");
  });

  it("ironia: medidor tracejado, marca do meio e o aviso de cabeca pouco confiavel", () => {
    const m = html();
    expect(m).toContain("indício de ironia");
    expect(m).toContain("cabeça pouco confiável");
    expect(m).toContain("border-dashed");
    expect(m).toContain(",64");
  });

  it("ironia abaixo do meio nao afirma ausencia de ironia: diz que nao ha indicio", () => {
    const m = html({ ironia: 0.12 });
    expect(m).toContain("sem indício de ironia");
    expect(m).toContain("cabeça pouco confiável");
  });

  it("zero observado continua zero escrito", () => {
    const m = html({ ironia: 0, classes: null, emocao: null });
    expect(m).toContain(",00");
  });
});
