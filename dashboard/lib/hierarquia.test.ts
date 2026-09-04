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

describe("as telas declaram nivel", () => {
  const TELAS = [
    ["app/dashboard/page.tsx", "/dashboard"],
    ["app/dashboard/atendimentos/page.tsx", "/dashboard/atendimentos"],
    ["app/dashboard/integracoes/page.tsx", "/dashboard/integracoes"],
    ["app/dashboard/configuracoes/page.tsx", "/dashboard/configuracoes"],
  ] as const;

  it("cada tela marca exatamente um painel como dominante", () => {
    for (const [arquivo] of TELAS) {
      const fonte = readFileSync(arquivo, "utf8");
      const ocorrencias = fonte.match(/nivel="dominante"/g) ?? [];
      expect(ocorrencias.length, arquivo).toBe(1);
    }
  });

  it("toda tela que declara dominante esta no vocabulario", () => {
    // NAO compare titulo: varios paineis montam o titulo em tempo de render
    // (`Atendimentos de ${rotulo}`), e string estatica nunca casa com isso.
    // O vocabulario guarda identificador; quem marca o dominante e a tela.
    for (const [, rota] of TELAS) {
      expect(DOMINANTE_POR_TELA, rota).toHaveProperty(rota);
    }
  });
});

describe("estados do dominante", () => {
  it("o Painel sabe render erro e vazio no lugar do conteudo", () => {
    const fonte = readFileSync("components/Painel.tsx", "utf8");
    expect(fonte).toContain("erro");
    expect(fonte).toContain("vazio");
  });

  // GUARDA DE REGRESSAO, nao teste de TDD: ela passa antes e depois da
  // implementacao. Existe para impedir que alguem introduza o padrao depois,
  // e nao para ficar vermelha agora. Quem implementar nao deve esperar ver
  // esta falhar -- a que tem que falhar primeiro e a de cima.
  it("erro e vazio nao viram string vazia nem zero", () => {
    // Ausencia de dado nao e insatisfacao, e a invariante 2 do CLAUDE.md
    // manda procurar `?? 0` e `|| 0` antes de commitar.
    const fonte = readFileSync("components/Painel.tsx", "utf8");
    expect(fonte).not.toMatch(/\?\?\s*0\b/);
    expect(fonte).not.toMatch(/\|\|\s*0\b/);
  });
});

describe("o aparato avisa quando o sistema nao produziu dado", () => {
  it("o Painel repassa erro/vazio ao RessalvaDaTela como `estado`, erro vencendo vazio", () => {
    // Casa a expressao inteira, nao so a palavra `estado`: garante que a
    // precedencia (erro vence vazio) e a mesma do render acima, e que ela
    // realmente chega ao RessalvaDaTela via a prop nova.
    const fonte = readFileSync("components/Painel.tsx", "utf8");
    expect(fonte).toMatch(
      /estado=\{erro \? "erro" : vazio \? "vazio" : undefined\}/,
    );
  });

  it("RessalvaDaTela declara `estado` como erro ou vazio, e nao so cor", () => {
    const fonte = readFileSync("components/AparatoDaTela.tsx", "utf8");
    expect(fonte).toMatch(/estado\?:\s*"erro"\s*\|\s*"vazio"/);
    // O rotulo tem que ser texto de verdade, nao uma classe de cor sozinha
    // representando o estado -- por isso o teste procura o dicionario de
    // rotulos, nao uma className condicional.
    expect(fonte).toContain("não carregou");
    expect(fonte).toContain("sem dado");
  });
});

describe("regua", () => {
  it("o Painel declara o parametro regua com os dois lados nomeados", () => {
    // `toContain("regua")` sozinho e vacuo: a palavra ja aparecia num
    // comentario pre-existente. Casar `regua` com `dito` e `medido` juntos,
    // na forma de declaracao de tipo, e o que distingue "tem a capacidade"
    // de "menciona a palavra".
    const fonte = readFileSync("components/Painel.tsx", "utf8");
    expect(fonte).toMatch(
      /regua\?:\s*\{\s*dito:\s*ReactNode;\s*medido:\s*ReactNode/,
    );
  });

  it("o corpo ramifica na presenca da regua, e o dito vem antes do medido", () => {
    // A ordem e a tese inteira da §1 (dito ACIMA, medido ABAIXO). Inverter
    // nao quebra nenhum tipo nem gera erro -- so faz a interface afirmar o
    // contrario do que quer dizer. Por isso a ordem e o que este teste
    // guarda, nao so a presenca dos dois lados.
    const fonte = readFileSync("components/Painel.tsx", "utf8");
    const inicioDoRamo = fonte.indexOf("regua ?");
    expect(inicioDoRamo, "esperava um ramo condicional `regua ? ... : ...`").toBeGreaterThan(-1);

    const corpoDoRamo = fonte.slice(inicioDoRamo);
    const idxDito = corpoDoRamo.indexOf("regua.dito");
    const idxLinha = corpoDoRamo.indexOf("border-linha");
    const idxMedido = corpoDoRamo.indexOf("regua.medido");

    expect(idxDito, "regua.dito nao aparece no ramo condicional").toBeGreaterThan(-1);
    expect(idxLinha, "border-linha nao aparece depois do dito").toBeGreaterThan(idxDito);
    expect(idxMedido, "regua.medido nao aparece depois da linha").toBeGreaterThan(idxLinha);
  });

  it("o grafico de NPS x latencia NAO usa regua", () => {
    // As duas series sao MEDIDAS. Regua ali seria notacao decorativa.
    const fonte = readFileSync("components/GraficoNpsLatencia.tsx", "utf8");
    expect(fonte).not.toContain("regua=");
  });
});
