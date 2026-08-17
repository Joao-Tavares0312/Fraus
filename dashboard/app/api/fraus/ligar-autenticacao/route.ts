/**
 * Liga a autenticacao da API e GUARDA a chave de acesso que ela emitir.
 *
 * Existe separada do proxy porque o proxy e bobo de proposito: ele repassa
 * bytes e nao interpreta corpo de resposta. Quem sabe que o 201 desta rota
 * especifica carrega uma credencial a guardar e esta rota.
 *
 * A chave vai para um cookie `httpOnly`: o JS do navegador continua sem
 * alcancar credencial nenhuma, que e a mesma promessa da variavel de ambiente
 * server-side. Sem esse cookie, ligar a autenticacao derrubaria a propria
 * dashboard em 401 no clique -- variavel de ambiente nao muda em processo vivo.
 */

const API = process.env.FRAUS_API_URL ?? "http://localhost:8000";
const COOKIE = "fraus_acesso";

export async function POST(requisicao: Request): Promise<Response> {
  // Repassado para a ROTACAO: a API exige a mestra atual para trocar a chave.
  // No primeiro uso nao ha header nenhum, e e assim que deve ser.
  const autorizacao = requisicao.headers.get("authorization");

  let resposta: Response;
  try {
    resposta = await fetch(`${API}/acesso/mestra`, {
      method: "POST",
      headers: autorizacao ? { authorization: autorizacao } : {},
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
  } catch {
    // Mesma regra do proxy: o 502 nao repete a URL interna da API.
    return Response.json({ detail: "API não respondeu" }, { status: 502 });
  }

  const corpo = await resposta.json().catch(() => null);
  if (resposta.status !== 201 || !corpo) {
    // 409 de "já ligada" e 502 chegam aqui e sobem como estão: a frase da API
    // é a instrução útil, e trocá-la por "erro ao ligar" seria perder a única
    // informação que diz o que fazer em seguida.
    return Response.json(corpo ?? { detail: "resposta inesperada da API" }, {
      status: resposta.status,
    });
  }

  const devolvida = Response.json(corpo, { status: 201 });
  if (corpo.chave_acesso) {
    devolvida.headers.append(
      "set-cookie",
      [
        `${COOKIE}=${corpo.chave_acesso}`,
        "Path=/",
        "HttpOnly",
        "SameSite=Lax",
        process.env.NODE_ENV === "production" ? "Secure" : "",
        // Sem Max-Age: cookie de SESSAO. Fechar o navegador exige apresentar a
        // chave de novo, e ela continua no banco -- nada e perdido, só o
        // atalho. Persistir credencial em disco do navegador seria trocar a
        // promessa de "some quando você sai" por conveniência.
      ]
        .filter(Boolean)
        .join("; "),
    );
  }
  return devolvida;
}
