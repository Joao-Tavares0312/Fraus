import { renderToStaticMarkup } from "react-dom/server";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";
import { estadoDaFila } from "../../lib/anotacao";

// Resolve os aliases do componente, como em FaixaIndicadores.test.tsx.
vi.mock("@/lib/anotacao", async () => import("../../lib/anotacao"));
vi.mock("@/components/shell/MarcaFraus", () => ({ MarcaFraus: () => null }));
vi.mock("@/components/ui/button", () => ({
  Button: (props: ComponentProps<"button"> & { variant?: string }) => {
    const { variant, ...resto } = props;
    return <button data-variant={variant} {...resto} />;
  },
}));

const { Fila } = await import("./AnotarIronia");

/**
 * Durante um envio o "Voltar" fica inerte por aria-disabled, como os botoes
 * de resposta: `disabled` tiraria o foco do teclado a cada envio.
 */
const frases = [
  { id: "f1", texto: "Primeira" },
  { id: "f2", texto: "Segunda" },
];
const html = (enviando: boolean) =>
  renderToStaticMarkup(
    <Fila
      estado={{ ...estadoDaFila(frases, { f1: "ironico" }), enviando }}
      responder={() => {}}
      voltar={() => {}}
    />,
  );
const botaoVoltar = (markup: string) => markup.match(/<button[^>]*>← Voltar<\/button>/)?.[0] ?? "";

describe("Voltar durante o envio", () => {
  it("fica aria-disabled e nunca disabled", () => {
    const botao = botaoVoltar(html(true));
    expect(botao).toContain('aria-disabled="true"');
    expect(botao).not.toMatch(/\sdisabled=""/);
  });

  it("fora do envio nao e marcado como desabilitado", () => {
    const botao = botaoVoltar(html(false));
    expect(botao).not.toBe("");
    expect(botao).not.toContain('aria-disabled="true"');
  });
});

describe("outro aparelho", () => {
  it("avisa que o endereco da pagina e o que leva a anotacao para outro aparelho", () => {
    expect(html(false)).toContain("Para continuar em outro aparelho, guarde o endereço desta página.");
  });
});
