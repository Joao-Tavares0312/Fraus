// dashboard/lib/camadas.test.ts
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const CAMADAS = "app/camadas.css";

function arquivos(pasta: string): string[] {
  return readdirSync(pasta).flatMap((nome) => {
    const caminho = join(pasta, nome);
    return statSync(caminho).isDirectory() ? arquivos(caminho) : [caminho];
  });
}

function bloco(css: string, seletor: RegExp): string {
  const inicio = css.search(seletor);
  if (inicio < 0) return "";
  const abre = css.indexOf("{", inicio);
  return css.slice(abre + 1, css.indexOf("}", abre));
}

describe("primitivas de camadas", () => {
  it("camadas.css existe e define todas as primitivas", () => {
    expect(existsSync(CAMADAS)).toBe(true);
    const css = readFileSync(CAMADAS, "utf8");
    for (const classe of ["chanfro", "placas", "placas-so-hover", "fio", "fio-hover", "pincel", "fenda"]) {
      expect(css, classe).toMatch(new RegExp(`\\.${classe}(?![\\w-])`));
    }
  });

  it("globals.css importa camadas.css", () => {
    const globals = readFileSync("app/globals.css", "utf8");
    expect(globals).toMatch(/@import\s+["']\.\/camadas\.css["'];/);
  });

  it("o poligono do canto e as cores das placas moram so em camadas.css", () => {
    // Fonte unica: copiar o poligono ou o hexadecimal em outro arquivo faz
    // o canto e a placa divergirem na primeira mudanca de valor.
    const proibidos = ["calc(100% - var(--chanfro", "#a8904f", "#6f5f36"];
    const suspeitos = [...arquivos("app"), ...arquivos("components")]
      .filter((caminho) => /\.(css|tsx?|jsx?)$/.test(caminho))
      .filter((caminho) => !caminho.endsWith("camadas.css"));
    for (const caminho of suspeitos) {
      const fonte = readFileSync(caminho, "utf8").toLowerCase();
      for (const trecho of proibidos) expect(fonte.includes(trecho), `${caminho}: ${trecho}`).toBe(false);
    }
  });

  it("placas anulam borda e anel do proprio elemento", () => {
    // Sem clip-path no elemento, borda e box-shadow (Button, .superficie)
    // desenhariam um retangulo em volta das placas, duplicado pela sombra.
    const css = readFileSync(CAMADAS, "utf8");
    const regra = bloco(css, /^\s*\.placas,\s*\.placas-so-hover\s*\{[^}]*isolation:/m);
    expect(regra).toMatch(/isolation:\s*isolate/);
    expect(regra).toMatch(/border-color:\s*transparent/);
    expect(regra).toMatch(/box-shadow:\s*none/);
  });

  it("os dois temas definem as placas", () => {
    // Os tokens moram em camadas.css: a guarda acima proibe o hex fora dele.
    const css = readFileSync(CAMADAS, "utf8");
    const escuro = bloco(css, /^\s*:root\s*,\s*\.dark\s*\{/m);
    for (const token of ["--placa-2", "--placa-3", "--placa-card-2", "--placa-card-3"]) {
      expect(escuro, token).toMatch(new RegExp(`${token}:`));
    }
    const claro = bloco(css, /^\s*\.light\s*\{/m);
    expect(claro).toMatch(/--placa-2:/);
    expect(claro).toMatch(/--placa-3:/);
    expect(claro).toMatch(/color-mix\(in oklch/);
  });
  it("a regiao .superficie ganha o canto pela primitiva, nao pelo raio", () => {
    const globals = readFileSync("app/globals.css", "utf8");
    const regra = bloco(globals, /^\s*\.superficie\s*\{/m);
    expect(regra).not.toMatch(/border-radius/);
    // background-color: o atalho `background` apagaria as camadas de fundo
    expect(regra).not.toMatch(/background\s*:/);
    expect(regra).toMatch(/background-color:\s*var\(--card\)/);
    const css = readFileSync(CAMADAS, "utf8");
    const cabeca = css.slice(css.indexOf("clip-path: polygon") - 400, css.indexOf("clip-path: polygon"));
    expect(cabeca).toMatch(/\.superficie(?![\w-])/);
    expect(css).toMatch(/\.superficie(?![\w-])[^{]*\{\s*--camada-fio: none/);
  });

  it("a sobreposicao .superficie-flutuante continua arredondada", () => {
    const globals = readFileSync("app/globals.css", "utf8");
    expect(bloco(globals, /^\s*\.superficie-flutuante\s*\{/m)).toMatch(/border-radius:\s*12px/);
    expect(bloco(globals, /^\s*\.painel-apoio\s*\{/m)).toMatch(/border-radius:\s*0/);
  });

  it("campos, gatilho e abas deixam o foco e o raio para a primitiva", () => {
    const fontes: Record<string, string> = {
      input: readFileSync("components/ui/input.tsx", "utf8"),
      textarea: readFileSync("components/ui/textarea.tsx", "utf8"),
      select: readFileSync("components/ui/select.tsx", "utf8"),
      tabs: readFileSync("components/ui/tabs.tsx", "utf8"),
    };
    const gatilho = fontes.select.slice(fontes.select.indexOf("function SelectTrigger"), fontes.select.indexOf("SelectPrimitive.Icon"));
    const trigger = fontes.tabs.slice(fontes.tabs.indexOf("function TabsTrigger"), fontes.tabs.indexOf("function TabsContent"));
    const alvos: Record<string, string> = { input: fontes.input, textarea: fontes.textarea, gatilho, trigger };
    for (const [nome, fonte] of Object.entries(alvos)) {
      expect(fonte, nome).not.toMatch(/rounded-md/);
      expect(fonte, nome).not.toMatch(/focus-visible:ring-2/);
      expect(fonte, nome).toMatch(/chanfro|superficie/);
    }
    // erro continua visivel por dentro do recorte
    for (const nome of ["input", "textarea", "gatilho"]) {
      expect(alvos[nome], nome).toMatch(/aria-invalid:\[--cor-borda-chanfro:var\(--destructive\)\]/);
    }
  });

  it("o alerta guarda a borda esquerda colorida e o traco do canto na mesma cor", () => {
    const alerta = readFileSync("components/ui/alert.tsx", "utf8");
    expect(alerta).toMatch(/border-l-primary/);
    expect(alerta).toMatch(/border-l-destructive/);
    expect(alerta).toMatch(/\[--cor-borda-chanfro:var\(--primary\)\]/);
    expect(alerta).toMatch(/\[--cor-borda-chanfro:var\(--destructive\)\]/);
    expect(alerta).not.toMatch(/rounded-lg/);
  });

  it("sobreposicoes nao recebem .superficie (a gaveta mobile continua arredondada)", () => {
    const sidebar = readFileSync("components/ui/sidebar.tsx", "utf8");
    const gaveta = sidebar.slice(sidebar.indexOf("<SheetContent"), sidebar.indexOf("showCloseButton"));
    expect(gaveta).toMatch(/className=/);
    expect(gaveta).not.toMatch(/(^|[\s"'`])superficie(?![\w-])/);
    const sheet = readFileSync("components/ui/sheet.tsx", "utf8");
    expect(sheet).toMatch(/superficie-flutuante/);
    expect(sheet).not.toMatch(/(^|[\s"'`])superficie(?![\w-])/);
  });
});
