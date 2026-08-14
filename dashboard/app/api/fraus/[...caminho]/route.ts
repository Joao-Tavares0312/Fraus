/**
 * Proxy da API do Fraus. Existe para a chave de acesso viver SO no servidor
 * Next (env sem NEXT_PUBLIC_) e nunca tocar o navegador -- variavel publica
 * vai para o bundle JS, e segredo no bundle e segredo publicado.
 *
 * Repassa metodo, corpo (inclusive multipart de /analisar), query e status.
 * O Authorization vindo do navegador e DESCARTADO: a credencial do deploy e a
 * do servidor, nao a que o cliente mandar.
 */

const API = process.env.FRAUS_API_URL ?? "http://localhost:8000";
const CHAVE = process.env.FRAUS_CHAVE_ACESSO;

async function repassar(
  requisicao: Request,
  contexto: { params: Promise<{ caminho: string[] }> },
): Promise<Response> {
  const { caminho } = await contexto.params;
  const busca = new URL(requisicao.url).search;
  const destino = `${API}/${caminho.join("/")}${busca}`;

  const cabecalhos = new Headers(requisicao.headers);
  cabecalhos.delete("host");
  cabecalhos.delete("authorization");
  if (CHAVE) cabecalhos.set("authorization", `Bearer ${CHAVE}`);

  const resposta = await fetch(destino, {
    method: requisicao.method,
    headers: cabecalhos,
    body: requisicao.body,
    // meio-duplex e exigido pelo fetch do Node ao repassar um corpo em stream
    // @ts-expect-error duplex ainda nao esta no tipo RequestInit
    duplex: "half",
    cache: "no-store",
  });

  return new Response(resposta.body, {
    status: resposta.status,
    headers: resposta.headers,
  });
}

export {
  repassar as GET,
  repassar as POST,
  repassar as PUT,
  repassar as DELETE,
};
