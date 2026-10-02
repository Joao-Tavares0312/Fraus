import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  autorizacaoDoServidor,
  autorizacaoParaLigar,
  esquecerEstadoDoLogin,
} from "./credencial-do-servidor";

const CHAVE_DO_DEPLOY = "fra_chave-tecnica-do-deploy";

function pedido(cookie?: string, extras?: Record<string, string>): Request {
  return new Request("https://fraus.exemplo/api/fraus/conversas", {
    headers: { ...(cookie ? { cookie } : {}), ...(extras ?? {}) },
  });
}

function apiResponde(disponivel: boolean) {
  return vi.fn(async () => Response.json({ disponivel, cadastro_exige_codigo: true }));
}

beforeEach(() => {
  esquecerEstadoDoLogin();
  vi.stubEnv("FRAUS_CHAVE_ACESSO", CHAVE_DO_DEPLOY);
  // Producao: o arquivo de chaves do clone local nao entra na conta.
  vi.stubEnv("NODE_ENV", "production");
  vi.stubEnv("FRAUS_MODO_LOCAL", "");
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("credencial que o servidor apresenta à API", () => {
  it("visitante sem sessão NÃO herda a chave do deploy quando há login", async () => {
    vi.stubGlobal("fetch", apiResponde(true));
    expect(await autorizacaoDoServidor(pedido())).toBeUndefined();
  });

  it("cookie de outra coisa não conta como sessão", async () => {
    vi.stubGlobal("fetch", apiResponde(true));
    expect(await autorizacaoDoServidor(pedido("tema=chuva; outro=1"))).toBeUndefined();
  });

  it("sessão de usuário vai como está, sem perguntar nada à API", async () => {
    const api = apiResponde(true);
    vi.stubGlobal("fetch", api);
    expect(await autorizacaoDoServidor(pedido("fraus_sessao=jwt.do.usuario"))).toBe(
      "Bearer jwt.do.usuario",
    );
    expect(api).not.toHaveBeenCalled();
  });

  it("instalação sem login (modo local) segue usando a chave do deploy", async () => {
    vi.stubGlobal("fetch", apiResponde(false));
    expect(await autorizacaoDoServidor(pedido())).toBe(`Bearer ${CHAVE_DO_DEPLOY}`);
  });

  it("sem conseguir perguntar, fecha em vez de abrir", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("API fora do ar"); }));
    expect(await autorizacaoDoServidor(pedido())).toBeUndefined();
    esquecerEstadoDoLogin();
    vi.stubGlobal("fetch", vi.fn(async () => new Response("erro", { status: 500 })));
    expect(await autorizacaoDoServidor(pedido())).toBeUndefined();
  });

  it("a chave que o próprio navegador recebeu ao ligar a autenticação continua valendo", async () => {
    vi.stubGlobal("fetch", apiResponde(true));
    expect(await autorizacaoDoServidor(pedido("fraus_acesso=fra_do-navegador"))).toBe(
      "Bearer fra_do-navegador",
    );
  });

  it("a resposta sobre o login é lembrada por um minuto", async () => {
    const api = apiResponde(true);
    vi.stubGlobal("fetch", api);
    await Promise.all([autorizacaoDoServidor(pedido()), autorizacaoDoServidor(pedido())]);
    await autorizacaoDoServidor(pedido());
    expect(api).toHaveBeenCalledTimes(1);
  });

  it("a dúvida é lembrada só por cinco segundos, para não dobrar o tráfego de uma API lenta", async () => {
    vi.useFakeTimers();
    try {
      const falha = vi.fn(async () => { throw new Error("fora"); });
      vi.stubGlobal("fetch", falha);
      await autorizacaoDoServidor(pedido());
      await autorizacaoDoServidor(pedido());
      expect(falha).toHaveBeenCalledTimes(1);

      // A API voltou, e é o modo local: passados os cinco segundos a chave volta.
      vi.stubGlobal("fetch", apiResponde(false));
      expect(await autorizacaoDoServidor(pedido())).toBeUndefined();
      vi.advanceTimersByTime(5_001);
      expect(await autorizacaoDoServidor(pedido())).toBe(`Bearer ${CHAVE_DO_DEPLOY}`);
    } finally {
      vi.useRealTimers();
    }
  });

  it("rota de mestra: o Authorization digitado vence; sem ele vale a mesma regra", async () => {
    vi.stubGlobal("fetch", apiResponde(true));
    expect(await autorizacaoParaLigar(pedido(undefined, { authorization: "Bearer mestra" }))).toBe(
      "Bearer mestra",
    );
    expect(await autorizacaoParaLigar(pedido())).toBeUndefined();
  });
});
