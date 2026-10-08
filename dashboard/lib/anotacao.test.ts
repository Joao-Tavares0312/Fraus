import { describe, expect, it } from "vitest";
import {
  carregarFila,
  chaveDoGrupo,
  entrarNoGrupo,
  mensagemDoGrupo,
  enviarResposta,
  estadoDaFila,
  faltam,
  fila,
  respostaDaTecla,
  tokenDeAnotador,
  type EstadoDaFila,
  type Frase,
} from "./anotacao";

const frases: Frase[] = [
  { id: "aaaaaaaaaaaa", texto: "um" },
  { id: "bbbbbbbbbbbb", texto: "dois" },
  { id: "cccccccccccc", texto: "tres" },
];
const tecla = (key: string, extra: object = {}) => ({ key, repeat: false, ctrlKey: false, metaKey: false, altKey: false, ...extra });

describe("tokenDeAnotador", () => {
  it("aceita so o formato url-safe de 43 caracteres", () => {
    expect(tokenDeAnotador("a".repeat(43))).toBe("a".repeat(43));
    expect(tokenDeAnotador("a".repeat(42))).toBeNull();
    expect(tokenDeAnotador("a/../" + "a".repeat(38))).toBeNull();
    expect(tokenDeAnotador(undefined)).toBeNull();
  });
});

describe("retomada", () => {
  it("comeca na primeira frase sem resposta", () => {
    const e = estadoDaFila(frases, { aaaaaaaaaaaa: "ironico" });
    expect(e.pos).toBe(1);
    expect(faltam(e)).toBe(2);
  });
  it("comeca na primeira quando nao ha respostas", () => {
    expect(estadoDaFila(frases, {}).pos).toBe(0);
  });
  it("ignora resposta de frase que nao esta na fila", () => {
    const e = estadoDaFila(frases, { zzzzzzzzzzzz: "ironico" });
    expect(faltam(e)).toBe(3);
  });
  it("tudo respondido cai no fim", () => {
    const e = estadoDaFila(frases, { aaaaaaaaaaaa: "ironico", bbbbbbbbbbbb: "contexto", cccccccccccc: "nao_ironico" });
    expect(e.pos).toBe(3);
    expect(fila(e).fim).toBe(true);
  });
});

describe("avanco so depois do 201", () => {
  it("enviar nao avanca; sucesso avanca", () => {
    let e = estadoDaFila(frases, {});
    e = fila(e).enviar();
    expect(e.enviando).toBe(true);
    expect(e.pos).toBe(0);
    e = fila(e).sucesso("aaaaaaaaaaaa", "ironico");
    expect(e.enviando).toBe(false);
    expect(e.pos).toBe(1);
    expect(e.respostas.aaaaaaaaaaaa).toBe("ironico");
  });
  it("erro mantem a frase, nao grava e mostra alerta", () => {
    let e = fila(estadoDaFila(frases, {})).enviar();
    e = fila(e).falha({ tipo: "rede" });
    expect(e.pos).toBe(0);
    expect(e.enviando).toBe(false);
    expect(e.respostas).toEqual({});
    expect(e.erro).toMatch(/não foi registrada/i);
  });
  it("429 pede para aguardar", () => {
    const e = fila(fila(estadoDaFila(frases, {})).enviar()).falha({ tipo: "limite", segundos: 7 });
    expect(e.erro).toMatch(/aguarde/i);
    expect(e.erro).toMatch(/não foi registrada/i);
  });
  it("nova tentativa limpa o alerta", () => {
    let e = fila(fila(estadoDaFila(frases, {})).enviar()).falha({ tipo: "http", status: 500 });
    e = fila(e).enviar();
    expect(e.erro).toBeNull();
  });
  it("nao ha resposta dupla enquanto envia", () => {
    const e1 = fila(estadoDaFila(frases, {})).enviar();
    expect(fila(e1).podeResponder).toBe(false);
    expect(fila(e1).enviar()).toBe(e1);
  });
  it("no fim nao ha o que enviar", () => {
    const e = estadoDaFila(frases, { aaaaaaaaaaaa: "ironico", bbbbbbbbbbbb: "ironico", cccccccccccc: "ironico" });
    expect(fila(e).enviar()).toBe(e);
  });
});

describe("voltar e trocar", () => {
  const feitas = (): EstadoDaFila => estadoDaFila(frases, { aaaaaaaaaaaa: "ironico", bbbbbbbbbbbb: "contexto" });
  it("voltar recua uma frase e nao altera respostas", () => {
    const e = fila(feitas()).voltar();
    expect(e.pos).toBe(1);
    expect(e.respostas).toEqual(feitas().respostas);
  });
  it("na primeira frase voltar nao faz nada e o botao fica indisponivel", () => {
    const e = estadoDaFila(frases, {});
    expect(fila(e).podeVoltar).toBe(false);
    expect(fila(e).voltar()).toBe(e);
  });
  it("nao volta durante o envio", () => {
    const e = fila(feitas()).enviar();
    expect(fila(e).voltar()).toBe(e);
  });
  it("troca a resposta e retoma na primeira sem resposta", () => {
    let e = fila(fila(feitas()).voltar()).voltar();
    expect(e.pos).toBe(0);
    e = fila(fila(e).enviar()).sucesso("aaaaaaaaaaaa", "nao_ironico");
    expect(e.respostas.aaaaaaaaaaaa).toBe("nao_ironico");
    expect(e.pos).toBe(2);
    expect(faltam(e)).toBe(1);
  });
  it("do fim da para voltar a ultima frase", () => {
    const e = estadoDaFila(frases, { aaaaaaaaaaaa: "ironico", bbbbbbbbbbbb: "ironico", cccccccccccc: "ironico" });
    expect(fila(e).voltar().pos).toBe(2);
  });
});

describe("teclado", () => {
  it("1, 2 e 3 mapeiam as respostas", () => {
    expect(respostaDaTecla(tecla("1"))).toBe("ironico");
    expect(respostaDaTecla(tecla("2"))).toBe("nao_ironico");
    expect(respostaDaTecla(tecla("3"))).toBe("contexto");
    expect(respostaDaTecla(tecla("4"))).toBeNull();
  });
  it("tecla repetida e atalhos com modificador sao ignorados", () => {
    expect(respostaDaTecla(tecla("1", { repeat: true }))).toBeNull();
    expect(respostaDaTecla(tecla("1", { ctrlKey: true }))).toBeNull();
    expect(respostaDaTecla(tecla("1", { metaKey: true }))).toBeNull();
    expect(respostaDaTecla(tecla("1", { altKey: true }))).toBeNull();
  });
});

describe("enviarResposta", () => {
  const resp = (status: number, corpo: unknown = {}, cab: Record<string, string> = {}) =>
    async () => new Response(JSON.stringify(corpo), { status, headers: cab });
  it("manda so os dois campos, para o proxy same-origin", async () => {
    let visto: { url: string; init?: RequestInit } | null = null;
    const r = await enviarResposta("tok", "aaaaaaaaaaaa", "ironico", async (url, init) => {
      visto = { url: String(url), init };
      return new Response("{}", { status: 201 });
    });
    expect(r).toEqual({ ok: true });
    expect(visto!.url).toBe("/api/fraus/anotacao/tok/respostas");
    expect(visto!.init?.method).toBe("POST");
    expect(JSON.parse(String(visto!.init?.body))).toEqual({ frase_id: "aaaaaaaaaaaa", resposta: "ironico" });
  });
  it("429 devolve o Retry-After", async () => {
    expect(await enviarResposta("t", "a", "ironico", resp(429, {}, { "Retry-After": "9" }))).toEqual({ ok: false, falha: { tipo: "limite", segundos: 9 } });
  });
  it("outros status viram falha http", async () => {
    expect(await enviarResposta("t", "a", "ironico", resp(422))).toEqual({ ok: false, falha: { tipo: "http", status: 422 } });
    expect(await enviarResposta("t", "a", "ironico", resp(200))).toEqual({ ok: false, falha: { tipo: "http", status: 200 } });
  });
  it("erro de rede vira falha de rede", async () => {
    const r = await enviarResposta("t", "a", "ironico", async () => { throw new TypeError("x"); });
    expect(r).toEqual({ ok: false, falha: { tipo: "rede" } });
  });
});

describe("carregarFila", () => {
  const json = (status: number, corpo: unknown) => async () => new Response(JSON.stringify(corpo), { status });
  it("404 e link invalido", async () => {
    expect(await carregarFila("t", json(404, { detail: "x" }))).toEqual({ tipo: "invalido" });
  });
  it("500 e erro, nao link invalido", async () => {
    expect(await carregarFila("t", json(500, {}))).toEqual({ tipo: "erro" });
  });
  it("rede caida e erro", async () => {
    expect(await carregarFila("t", async () => { throw new TypeError("x"); })).toEqual({ tipo: "erro" });
  });
  it("200 devolve frases na ordem do servidor e as respostas", async () => {
    const c = await carregarFila("t", json(200, { frases, respostas: { aaaaaaaaaaaa: "ironico" } }));
    expect(c).toEqual({ tipo: "ok", frases, respostas: { aaaaaaaaaaaa: "ironico" } });
  });
  it("fila vazia e erro, nao 'fim'", async () => {
    expect(await carregarFila("t", json(200, { frases: [], respostas: {} }))).toEqual({ tipo: "erro" });
  });
});

describe("contrato novo da API", () => {
  it("409 encerra: mostra o erro e nao aceita mais respostas", async () => {
    const r = await enviarResposta("t", "a", "ironico", async () => new Response("{}", { status: 409 }));
    expect(r).toEqual({ ok: false, falha: { tipo: "maximo" } });
    const e = fila(fila(estadoDaFila(frases, {})).enviar()).falha({ tipo: "maximo" });
    expect(e.erro).toMatch(/não foi registrada/i);
    expect(e.pos).toBe(0);
    expect(fila(e).podeResponder).toBe(false);
    expect(fila(e).enviar()).toBe(e);
  });
  it("429 no GET pede para aguardar, sem tratar como link invalido", async () => {
    expect(await carregarFila("t", async () => new Response("{}", { status: 429, headers: { "Retry-After": "5" } }))).toEqual({ tipo: "limite" });
  });
  it("o 429 do POST nao depende do texto", async () => {
    const r = await enviarResposta("t", "a", "ironico", async () => new Response(JSON.stringify({ detail: "qualquer coisa" }), { status: 429 }));
    expect(r).toEqual({ ok: false, falha: { tipo: "limite", segundos: null } });
  });
});

describe("link de grupo", () => {
  const grupo = "g".repeat(43);
  const pessoal = "p".repeat(43);
  const resposta = (status: number, corpo: unknown = {}, headers: Record<string, string> = {}) =>
    new Response(JSON.stringify(corpo), { status, headers });
  const memoria = () => {
    const dados = new Map<string, string>();
    return {
      dados,
      armazenamento: { ler: (k: string) => dados.get(k) ?? null, gravar: (k: string, v: string) => { dados.set(k, v); } },
    };
  };

  it("a chave guarda so os 16 primeiros caracteres do token do grupo", () => {
    expect(chaveDoGrupo(grupo)).toBe(`fraus-anotacao-grupo:${"g".repeat(16)}`);
  });

  it("com link pessoal guardado, nao gasta vaga", async () => {
    const { dados, armazenamento } = memoria();
    dados.set(chaveDoGrupo(grupo), pessoal);
    let chamadas = 0;
    const r = await entrarNoGrupo(grupo, { armazenamento, buscar: async () => { chamadas++; return resposta(201, { token: "x" }); } });
    expect(r).toEqual({ tipo: "pessoal", token: pessoal });
    expect(chamadas).toBe(0);
  });

  it("sem link guardado, entra, guarda e devolve o pessoal", async () => {
    const { dados, armazenamento } = memoria();
    const urls: string[] = [];
    const r = await entrarNoGrupo(grupo, {
      armazenamento,
      buscar: async (u, i) => { urls.push(`${i?.method} ${u}`); return resposta(201, { token: pessoal }); },
    });
    expect(r).toEqual({ tipo: "pessoal", token: pessoal });
    expect(urls).toEqual([`POST /api/fraus/anotacao/grupos/${grupo}/entrar`]);
    expect(dados.get(chaveDoGrupo(grupo))).toBe(pessoal);
  });

  it("valor guardado fora do formato e ignorado", async () => {
    const { dados, armazenamento } = memoria();
    dados.set(chaveDoGrupo(grupo), "../lixo");
    const r = await entrarNoGrupo(grupo, { armazenamento, buscar: async () => resposta(201, { token: pessoal }) });
    expect(r).toEqual({ tipo: "pessoal", token: pessoal });
  });

  it("armazenamento que lanca nao impede a entrada", async () => {
    const quebrado = { ler: () => { throw new Error("bloqueado"); }, gravar: () => { throw new Error("bloqueado"); } };
    const r = await entrarNoGrupo(grupo, { armazenamento: quebrado, buscar: async () => resposta(201, { token: pessoal }) });
    expect(r).toEqual({ tipo: "pessoal", token: pessoal });
  });

  it("dois pedidos ao mesmo tempo gastam UMA vaga", async () => {
    const { armazenamento } = memoria();
    let chamadas = 0;
    const buscar = async () => { chamadas++; return resposta(201, { token: pessoal }); };
    const [a, b] = await Promise.all([entrarNoGrupo(grupo, { armazenamento, buscar }), entrarNoGrupo(grupo, { armazenamento, buscar })]);
    expect(a).toEqual(b);
    expect(chamadas).toBe(1);
  });

  it("traduz 409, 404, 429, resposta sem token e rede", async () => {
    const { armazenamento } = memoria();
    const com = (r: () => Promise<Response>) => entrarNoGrupo(grupo, { armazenamento, buscar: r });
    expect(await com(async () => resposta(409))).toEqual({ tipo: "cheio" });
    expect(await com(async () => resposta(404))).toEqual({ tipo: "invalido" });
    expect(await com(async () => resposta(429, {}, { "Retry-After": "7" }))).toEqual({ tipo: "limite", segundos: 7 });
    expect(await com(async () => resposta(201, { token: "curto" }))).toEqual({ tipo: "erro" });
    expect(await com(async () => { throw new TypeError("rede"); })).toEqual({ tipo: "rede" });
  });

  it("mensagens do grupo", () => {
    expect(mensagemDoGrupo({ tipo: "cheio" })).toBe("Este link já foi usado por todas as pessoas previstas. Peça um link novo a quem organiza.");
    expect(mensagemDoGrupo({ tipo: "invalido" })).toBe("Link inválido ou revogado.");
    expect(mensagemDoGrupo({ tipo: "limite", segundos: 7 })).toContain("7 segundos");
    expect(mensagemDoGrupo({ tipo: "rede" })).toContain("conexão");
  });
});
