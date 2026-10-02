import { describe, expect, it } from "vitest";
import { lerListaDaResposta } from "./resposta";

/**
 * API fora do ar ou 401 virava "Nenhum termo curado" / "Nenhuma chave de
 * acesso emitida": o proxy devolve `{detail}` em erro, que nao e array, e o
 * `Array.isArray(corpo) ? corpo : []` transformava a falha em lista vazia.
 * Afirmar ausencia sem ter lido e a invariante 2 pelo outro lado.
 */
describe("lerListaDaResposta", () => {
  it("lista de verdade vem como lista", async () => {
    const leitura = await lerListaDaResposta<number>(Response.json([1, 2]));
    expect(leitura).toEqual({ ok: true, itens: [1, 2] });
  });

  it("lista vazia de verdade continua sendo lista vazia", async () => {
    const leitura = await lerListaDaResposta(Response.json([]));
    expect(leitura).toEqual({ ok: true, itens: [] });
  });

  it("erro com `detail` e erro, com a frase da API", async () => {
    const leitura = await lerListaDaResposta(
      Response.json({ detail: "credencial ausente" }, { status: 401 }),
    );
    expect(leitura).toEqual({ ok: false, erro: "credencial ausente" });
  });

  it("erro sem corpo legivel diz o status", async () => {
    const leitura = await lerListaDaResposta(
      new Response("<html>bad gateway</html>", { status: 502 }),
    );
    expect(leitura).toEqual({ ok: false, erro: "a API respondeu 502" });
  });

  it("`detail` que nao e texto nao vira objeto na tela", async () => {
    const leitura = await lerListaDaResposta(
      Response.json({ detail: [{ msg: "x" }] }, { status: 422 }),
    );
    expect(leitura).toEqual({ ok: false, erro: "a API respondeu 422" });
  });

  it("200 que nao e lista e resposta fora do contrato, nao lista vazia", async () => {
    const leitura = await lerListaDaResposta(Response.json({ itens: [] }));
    expect(leitura.ok).toBe(false);
  });
});
