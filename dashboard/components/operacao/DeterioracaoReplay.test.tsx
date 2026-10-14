import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { DeterioracaoReplay } from "./DeterioracaoReplay";
import type { Deterioracao } from "@/lib/operacao";
import { formatarSegundos } from "@/lib/formato";

const base: Deterioracao = { indice_virada: 2, falas_ate_o_fim: 4, segundos_ate_o_fim: 600, motivo: null, criterio: "primeira mensagem a partir da qual…", rotulo: "retrospectivo: lead time hipotético, não alerta" };
const html = (d: Deterioracao | undefined) => renderToStaticMarkup(<DeterioracaoReplay deterioracao={d} />);

describe("DeterioracaoReplay", () => {
  it("início da deterioração: índice, falas e tempo antes do fim, com o rótulo", () => {
    const m = html(base);
    expect(m).toContain("Início da deterioração no índice 2: a estimativa ficou detratora e não voltou");
    expect(m).not.toMatch(/virada/i);
    expect(m).toContain("4 mensagens");
    expect(m).toContain("retrospectivo");
  });
  it("sem início mostra o motivo", () => {
    expect(html({ ...base, indice_virada: null, falas_ate_o_fim: null, segundos_ate_o_fim: null, motivo: "não terminou detratora" })).toContain("Sem início de deterioração: não terminou detratora.");
  });
  it("API antiga não renderiza nada", () => {
    expect(html(undefined)).toBe("");
  });
  it("mostra o tempo formatado", () => {
    expect(html(base)).toContain(formatarSegundos(600));
  });
  it("início na última mensagem: só no fim da conversa", () => {
    expect(html({ ...base, falas_ate_o_fim: 0, segundos_ate_o_fim: 0 })).toContain("só no fim da conversa");
  });
  it("uma mensagem no singular", () => {
    const m = html({ ...base, falas_ate_o_fim: 1, segundos_ate_o_fim: 60 });
    expect(m).toContain("1 mensagem ");
    expect(m).not.toContain("1 mensagens");
  });
  it("início sem lead time não afirma o fim", () => {
    const m = html({ ...base, falas_ate_o_fim: null, segundos_ate_o_fim: null });
    expect(m).toContain("Início da deterioração no índice 2: a estimativa ficou detratora e não voltou; tempo até o fim indisponível.");
    expect(m).not.toContain("só no fim");
  });
});
