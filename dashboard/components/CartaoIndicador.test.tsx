import { createElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/utils", async () => import("../lib/utils"));
vi.mock("@/lib/api", async () => import("../lib/api"));
vi.mock("@/lib/movimento", () => ({ itemDaPilha: {}, TRANSICAO: { amplo: {} } }));
vi.mock("@/components/ui/badge", async () => import("./ui/badge"));
vi.mock("@/components/ValorNumerico", async () => import("./ValorNumerico"));
vi.mock("motion/react", () => ({
  motion: {
    div: ({ children, className }: { children?: ReactNode; className?: string }) =>
      createElement("div", { className }, children),
    span: ({ children, className }: { children?: ReactNode; className?: string }) =>
      createElement("span", { className }, children),
  },
}));

import { CartaoIndicador } from "./CartaoIndicador";

describe("CartaoIndicador", () => {

  it("o erro fica no proprio card, sem virar zero", () => {
    const html = renderToStaticMarkup(
      <CartaoIndicador rotulo="Contenção" valor={null} erro="Falha ao ler a listagem" />,
    );
    expect(html).toContain("Falha ao ler a listagem");
    expect(html).not.toMatch(/>0</);
  });
});
