/**
 * Rotas de `app/api` que guardam a sessao e o modo local (auditoria de
 * 13/10/2026). Ficam em `lib/` porque o vitest so inclui `lib/**` e
 * `components/**`; o alias `@` da config e o que deixa importar o `route.ts`.
 */
import { afterEach, describe, expect, it, vi } from "vitest";

const apagados: string[] = [];

vi.mock("next/headers", () => ({
  cookies: async () => ({
    delete: (nome: string) => {
      apagados.push(nome);
    },
  }),
}));

afterEach(() => {
  apagados.length = 0;
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("POST /api/sessao/sair", () => {
  it("esquece tambem o cookie da chave tecnica, nao so o da sessao", async () => {
    // `fraus_acesso` e gravado por /api/fraus/ligar-autenticacao e o proxy o
    // usa mesmo com login ligado: sobrando depois de "Sair", quem usa o mesmo
    // navegador continua lendo a API com a chave tecnica.
    const { POST } = await import("../app/api/sessao/sair/route");
    const { NOME_DO_COOKIE } = await import("./credencial-do-servidor");
    const { COOKIE_SESSAO } = await import("./sessao");

    const resposta = await POST(new Request("http://localhost:3000/api/sessao/sair", { method: "POST" }));

    expect(resposta.status).toBe(200);
    expect(apagados).toEqual(expect.arrayContaining([COOKIE_SESSAO, NOME_DO_COOKIE]));
  });
});

describe("GET /api/fraus/iniciar", () => {
  it("responde 404 com o modo local desligado, sem revelar comando nem caminho", async () => {
    // A trava 1 promete 404 "para quem nao deveria saber que ela existe";
    // o POST cumpria, o GET devolvia 200 com o argv e o caminho do log.
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("FRAUS_MODO_LOCAL", "");
    const { GET } = await import("../app/api/fraus/iniciar/route");

    const resposta = await GET();

    expect(resposta.status).toBe(404);
    const corpo = JSON.stringify(await resposta.json());
    expect(corpo).not.toContain("uvicorn");
    expect(corpo).not.toContain(".fraus-api.log");
  });
});

describe("npm run dev", () => {
  it("escuta so em loopback, porque sem login o proxy empresta a chave tecnica", async () => {
    // Auditoria de 13/10/2026: `next dev` sem -H escuta em todas as
    // interfaces, e no modo sem login `credencialDoServidor` anexa a chave
    // tecnica a QUALQUER requisicao -- inclusive de outra maquina da rede.
    const { readFileSync } = await import("node:fs");
    const pacote = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf-8"));
    expect(pacote.scripts.dev).toMatch(/-H 127\.0\.0\.1\b/);
  });
});
