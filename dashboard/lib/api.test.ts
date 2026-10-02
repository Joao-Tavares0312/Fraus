import { afterEach, describe, expect, it, vi } from "vitest";

import { obterConversa, obterDetalhes, TETO_DETALHES_PLANO_B } from "./api";
import { esquecerEstadoDoLogin } from "./credencial-do-servidor";

/**
 * O PLANO B (`app/dashboard/page.tsx`) baixa transcricao por transcricao
 * quando um agregado do servidor falha, e o periodo pode ser "todos" -- sem
 * teto, uma instalacao com milhares de atendimentos vira uma cadeia de
 * dezenas de lotes SEQUENCIAIS de 8 chamadas cada, presa dentro do render da
 * pagina. Uma API ja DEGRADADA (nao caida, so lenta) fica ainda mais lenta
 * recebendo essa tempestade, e quem espera a tela ve isso como uma trava, nao
 * como "algumas coisas nao carregaram".
 *
 * A regra do projeto e "sem teto silencioso" -- se o plano B corta, ele conta
 * quanto cortou, para a tela poder dizer isso em vez de fingir que o recorte
 * inteiro foi considerado.
 */

const IDS_ALEM_DO_TETO = Array.from(
  { length: TETO_DETALHES_PLANO_B + 37 },
  (_, indice) => `conversa-${indice}`,
);

/**
 * Sem sessao, o servidor pergunta a API se ha login antes de emprestar a
 * propria credencial (`lib/credencial-do-servidor.ts`). Essa pergunta nao e
 * transcricao: os testes daqui a respondem a parte e contam so o resto.
 */
function respostaDoEstadoDoLogin(url: unknown): Response | null {
  return String(url).endsWith("/auth/estado")
    ? Response.json({ disponivel: false, cadastro_exige_codigo: false })
    : null;
}

function mockarFetchQueRespondeQualquerId() {
  const chamadas: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const estado = respostaDoEstadoDoLogin(url);
      if (estado) return estado;
      chamadas.push(url);
      return new Response(JSON.stringify({ id: "x", mensagens: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
  return chamadas;
}

afterEach(() => {
  vi.unstubAllGlobals();
  esquecerEstadoDoLogin();
});

describe("obterDetalhes tem teto para o plano B", () => {
  it("nao busca mais transcricoes do que o teto declarado", async () => {
    const chamadas = mockarFetchQueRespondeQualquerId();

    await obterDetalhes(IDS_ALEM_DO_TETO);

    expect(chamadas.length).toBeLessThanOrEqual(TETO_DETALHES_PLANO_B);
  });

  it("conta quantas foram deixadas de fora, em vez de esconder o corte", async () => {
    mockarFetchQueRespondeQualquerId();

    const resultado = await obterDetalhes(IDS_ALEM_DO_TETO);

    expect(resultado.truncadas).toBe(37);
  });

  it("dentro do teto, nada e cortado", async () => {
    mockarFetchQueRespondeQualquerId();

    const poucos = IDS_ALEM_DO_TETO.slice(0, 10);
    const resultado = await obterDetalhes(poucos);

    expect(resultado.truncadas).toBe(0);
    expect(resultado.detalhes).toHaveLength(10);
  });

  it("falha individual continua descartada, sem contar como truncada", async () => {
    let chamada = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        const estado = respostaDoEstadoDoLogin(url);
        if (estado) return estado;
        chamada += 1;
        if (chamada === 1) return new Response("erro", { status: 500 });
        return new Response(JSON.stringify({ id: "x", mensagens: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );

    const resultado = await obterDetalhes(["a", "b", "c"]);

    expect(resultado.falhas).toBe(1);
    expect(resultado.detalhes).toHaveLength(2);
    expect(resultado.truncadas).toBe(0);
  });
});

/**
 * A tela do atendimento decidia "nao encontrado" com `/404/.test(erro)`, e a
 * mensagem de erro carrega a ROTA -- que carrega o id. Um 500 em
 * `/conversas/c-1404` virava pagina de 404: a tela afirmava que o atendimento
 * nao existe quando o que falhou foi o servidor.
 */
describe("a falha de leitura carrega o STATUS, nao so o texto", () => {
  function mockarStatus(status: number) {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        const estado = respostaDoEstadoDoLogin(url);
        if (estado) return estado;
        return new Response("{}", { status });
      }),
    );
  }

  it("500 num id que contem 404 nao e 404", async () => {
    mockarStatus(500);

    const resultado = await obterConversa("c-1404");

    expect(resultado.ok).toBe(false);
    if (resultado.ok) return;
    expect(resultado.erro).toContain("404"); // o texto engana; por isso o status
    expect(resultado.status).toBe(500);
  });

  it("404 de verdade chega como 404", async () => {
    mockarStatus(404);

    const resultado = await obterConversa("c-1");

    expect(resultado.ok).toBe(false);
    if (resultado.ok) return;
    expect(resultado.status).toBe(404);
  });

  it("falha sem resposta HTTP nao inventa status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        const estado = respostaDoEstadoDoLogin(url);
        if (estado) return estado;
        throw new Error("fetch failed");
      }),
    );

    const resultado = await obterConversa("c-1");

    expect(resultado.ok).toBe(false);
    if (resultado.ok) return;
    expect(resultado.status).toBeUndefined();
  });
});
