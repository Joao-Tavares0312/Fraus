import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Sinalizadores } from "./Sinalizadores";
import type { Sinalizador } from "@/lib/api";

const loop: Sinalizador = {
  regra: "loop_do_bot",
  evidencia: [1, 3],
  detalhe: "2 respostas do bot quase idênticas, com fala do cliente entre elas (Jaccard ≥ 0,85; limiar sem procedência)",
};

const html = (s: Sinalizador[] | null | undefined) =>
  renderToStaticMarkup(<Sinalizadores sinalizadores={s} />);

describe("Sinalizadores", () => {
  it("null é não avaliado, não 'nada disparou'", () => {
    const m = html(null);
    expect(m).toContain("não avaliados");
    expect(m).toContain("sem fala do cliente");
    expect(m).not.toContain("Nenhum sinalizador");
  });

  it("lista vazia diz que nada disparou", () => {
    expect(html([])).toContain("Nenhum sinalizador disparou");
  });

  it("achado mostra o rótulo, o detalhe do servidor e as mensagens", () => {
    const m = html([loop]);
    expect(m).toContain("Loop do bot");
    expect(m).toContain(loop.detalhe);
    expect(m).toContain("mensagens 2 e 4");
    expect(m).toContain("não avalia o atendente");
  });

  it("undefined é API antiga: nem 'não avaliado' nem 'nada disparou'", () => {
    const m = html(undefined);
    expect(m).toContain("indisponíveis nesta versão da API");
    expect(m).not.toContain("sem fala do cliente");
    expect(m).not.toContain("Nenhum sinalizador");
  });

  it("regra desconhecida mostra o nome cru, não 'undefined'", () => {
    const m = html([{ ...loop, regra: "regra_nova" as never }]);
    expect(m).toContain("regra_nova");
    expect(m).not.toContain("undefined");
  });
});
