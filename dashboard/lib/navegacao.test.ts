import { describe, expect, it } from "vitest";
import { consultaDoPeriodo, gruposDoPapel, telaEstaAtiva, telasDaConta } from "./navegacao";

const destinosDoUsuario = [
  "/dashboard", "/dashboard/atendimentos", "/dashboard/analisar", "/dashboard/grafo",
];

describe("navegação por tarefa e papel", () => {

  it("usuario não recebe destinos administrativos nem grupo vazio", () => {
    const grupos = gruposDoPapel("usuario");
    expect(grupos.map((grupo) => grupo.rotulo)).toEqual(["Acompanhar", "Investigar"]);
    expect(grupos.flatMap((grupo) => grupo.telas.map((tela) => tela.href))).toEqual(destinosDoUsuario);
  });

  it("a lateral do dev ganha só o Modelo; o resto mora no menu da conta", () => {
    const destinos = gruposDoPapel("dev").flatMap((grupo) => grupo.telas.map((tela) => tela.href));
    expect(destinos).toEqual([...destinosDoUsuario, "/dashboard/modelo"]);
  });

  it("o menu da conta respeita o papel", () => {
    expect(telasDaConta("usuario").map((tela) => tela.href)).toEqual(["/dashboard/operacao"]);
    expect(telasDaConta("dev").map((tela) => tela.href)).toEqual([
      "/dashboard/operacao", "/dashboard/integracoes", "/dashboard/configuracoes",
    ]);
  });
});

describe("contexto de navegação", () => {
  it("distingue a visão geral da seção de um atendimento", () => {
    expect(telaEstaAtiva("/dashboard", "/dashboard")).toBe(true);
    expect(telaEstaAtiva("/dashboard/atendimentos/caso-42", "/dashboard")).toBe(false);
    expect(telaEstaAtiva("/dashboard/atendimentos/caso-42", "/dashboard/atendimentos")).toBe(true);
    expect(telaEstaAtiva("/dashboard/atendimentos-extra", "/dashboard/atendimentos")).toBe(false);
    expect(telaEstaAtiva("/dashboard/modelo/comparacao", "/dashboard/modelo")).toBe(true);
  });

  it("carrega somente de/ate, descartando filtros locais e credenciais", () => {
    expect(consultaDoPeriodo(new URLSearchParams("de=2026-08-01&ate=2026-08-22&busca=cliente&pagina=4&token=segredo")))
      .toBe("?de=2026-08-01&ate=2026-08-22");
    expect(consultaDoPeriodo(new URLSearchParams("de=2026-08-01&de=2020-01-01"))).toBe("?de=2026-08-01");
    expect(consultaDoPeriodo(new URLSearchParams("de=&busca=texto"))).toBe("");
    expect(consultaDoPeriodo(new URLSearchParams("ate=2026-08-22"))).toBe("?ate=2026-08-22");
  });
});
