import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { FormularioAuth } from "./FormularioAuth";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const token = "a".repeat(43);

describe("admissão no formulário de cadastro", () => {
  it.each([true, false])("recolhe o código sem perder a exigência de admissão: restrito=%s", (restrito) => {
    const html = renderToStaticMarkup(<FormularioAuth modo="cadastrar" cadastroExigeCodigo={restrito} />);
    const divulgacao = html.match(/<details\b[^>]*>[\s\S]*?<\/details>/)?.[0];
    expect(divulgacao).toBeDefined();
    expect(divulgacao?.match(/^<details[^>]*>/)?.[0]).not.toMatch(/\bopen(?:=|\s|>)/);
    const codigo = divulgacao?.match(/<input[^>]*name="codigo_dev"[^>]*>/)?.[0];
    expect(codigo).toBeDefined();
    if (restrito) {
      expect(codigo).toContain('required=""');
    } else {
      expect(codigo).not.toContain("required");
    }
  });

  it("convite de equipe dispensa código mesmo quando o cadastro é restrito", () => {
    const html = renderToStaticMarkup(<FormularioAuth modo="cadastrar" cadastroExigeCodigo convite={token} />);
    expect(html).not.toContain('name="codigo_dev"');
    expect(html).toContain(`href="/entrar?convite=${token}"`);
  });

  it("login não pede código nem nome e mantém o retorno para o convite", () => {
    const html = renderToStaticMarkup(<FormularioAuth modo="entrar" convite={token} />);
    expect(html).not.toContain('name="codigo_dev"');
    expect(html).not.toContain('name="nome"');
    expect(html).toContain(`href="/cadastrar?convite=${token}"`);
  });
});
