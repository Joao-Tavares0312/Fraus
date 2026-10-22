import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }) }));
vi.mock("@/lib/api", () => ({ removerConversa: vi.fn() }));
vi.mock("@/lib/atualizacao", () => ({ anunciarAtualizacao: vi.fn() }));
vi.mock("@/lib/utils", async () => import("../../lib/utils"));
vi.mock("@/components/ui/button", async () => import("../ui/button"));
import { RemoverAtendimento } from "./RemoverAtendimento";

describe("remover atendimento", () => {
  it("começa pedindo o primeiro clique, sem remover nada", () => {
    const html = renderToStaticMarkup(<RemoverAtendimento id="x" voltarPara="/dashboard/atendimentos" />);
    expect(html).toContain("Remover atendimento");
    expect(html).not.toContain("Confirmar remoção");
  });
});
