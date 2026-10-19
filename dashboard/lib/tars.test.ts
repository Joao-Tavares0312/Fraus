import { describe, expect, it } from "vitest";
import type { FonteIntegracao } from "./api";
import { fonteDoTars, urlDeIngestao } from "./tars";

const fonte = (id: number, canal: string) => ({ id, canal } as FonteIntegracao);

describe("conexão com o TARS", () => {
  it("acha a fonte pelo canal tars, a mais antiga primeiro", () => {
    expect(fonteDoTars([fonte(3, "whatsapp"), fonte(9, "tars"), fonte(4, "tars")])?.id).toBe(4);
  });

  it("sem fonte do TARS devolve null", () => {
    expect(fonteDoTars([fonte(1, "whatsapp")])).toBeNull();
  });

  it("monta o endereço de ingestão sem barra dobrada", () => {
    expect(urlDeIngestao("https://fraus-api.vercel.app/")).toBe("https://fraus-api.vercel.app/ingestao");
    expect(urlDeIngestao("http://localhost:8000")).toBe("http://localhost:8000/ingestao");
  });
});
