// dashboard/lib/hierarquia.test.ts
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  DOMINANTE_POR_TELA,
  classesDoNivel,
  dominanteDaTela,
} from "./hierarquia";

describe("classesDoNivel", () => {
  it("da ao dominante uma superficie mais densa que a do apoio", () => {
    expect(classesDoNivel("dominante")).toContain("vidro");
    expect(classesDoNivel("dominante")).not.toContain("vidro-fino");
    expect(classesDoNivel("apoio")).toContain("vidro-fino");
  });

  it("nao devolve a mesma coisa para os dois niveis", () => {
    expect(classesDoNivel("dominante")).not.toBe(classesDoNivel("apoio"));
  });
});

describe("dominanteDaTela", () => {
  it("nomeia um dominante para cada tela da ferramenta", () => {
    const rotas = [
      "/dashboard",
      "/dashboard/atendimentos",
      "/dashboard/modelo",
      "/dashboard/grafo",
      "/dashboard/integracoes",
      "/dashboard/configuracoes",
    ];
    for (const rota of rotas) {
      const id = dominanteDaTela(rota);
      expect(id, rota).toBeTruthy();
      // Identificador estavel: sem espaco e sem maiuscula. E o que impede
      // alguem de reintroduzir titulo de exibicao aqui sem perceber.
      expect(id, rota).toMatch(/^[a-z0-9-]+$/);
    }
  });

  it("da UM dominante por tela, nunca dois", () => {
    // A tese da hierarquia: um sistema por tela responde a pergunta que
    // levou o analista ali. Dois dominantes e nenhum.
    const valores = Object.values(DOMINANTE_POR_TELA);
    expect(new Set(valores).size).toBe(valores.length);
  });

  it("devolve null para rota que nao e tela da ferramenta", () => {
    expect(dominanteDaTela("/")).toBeNull();
  });
});

describe("Painel", () => {
  it("consome o vocabulario em vez de digitar a superficie de novo", () => {
    // Guarda de duplicacao: se alguem cravar `vidro-fino` no Painel, a regra
    // passa a existir em dois lugares e diverge no dia em que um dos dois for
    // corrigido -- que e exatamente como o Aparato nasceu (ver o cabecalho
    // dele).
    const fonte = readFileSync("components/Painel.tsx", "utf8");
    expect(fonte).toContain("classesDoNivel");
    expect(fonte).not.toMatch(/"[^"]*\bvidro(-fino)?\b[^"]*"/);
  });
});

describe("aparato", () => {
  it("o Painel nao hospeda mais um Aparato proprio", () => {
    // Seis aparatos identicos por tela viram ruido: a honestidade fica com
    // forma de repeticao, e nao de rigor. A prosa se consolida num so, no pe
    // da tela; os rotulos curtos continuam colados ao numero.
    const fonte = readFileSync("components/Painel.tsx", "utf8");
    expect(fonte).not.toContain("<Aparato");
    expect(fonte).toContain("RessalvaDaTela");
  });

  it("o layout monta o provedor e o aparato da tela para todas as paginas", () => {
    // Quem monta o rodape e o layout, nao cada pagina: e o que garante que
    // toda tela ganhe o aparato sem repetir a montagem.
    const fonte = readFileSync("app/dashboard/layout.tsx", "utf8");
    expect(fonte).toContain("AparatoDaTela");
    expect(fonte).toContain("ProvedorDeAparato");
  });
});

describe("regua", () => {
  it("o Painel sabe montar a regua com os dois lados", () => {
    const fonte = readFileSync("components/Painel.tsx", "utf8");
    expect(fonte).toContain("regua");
    expect(fonte).toContain("border-linha");
  });

  it("o grafico de NPS x latencia NAO usa regua", () => {
    // As duas series sao MEDIDAS. Regua ali seria notacao decorativa.
    const fonte = readFileSync("components/GraficoNpsLatencia.tsx", "utf8");
    expect(fonte).not.toContain("regua=");
  });
});
