/**
 * Proxy da API do Fraus. Existe para a chave de acesso viver SO no servidor
 * Next (env sem NEXT_PUBLIC_) e nunca tocar o navegador -- variavel publica
 * vai para o bundle JS, e segredo no bundle e segredo publicado.
 *
 * Repassa metodo, corpo (inclusive multipart de /analisar), query e status.
 * O Authorization vindo do navegador e DESCARTADO: a credencial do deploy e a
 * do servidor, nao a que o cliente mandar.
 */

import { autorizacaoDoServidor } from "@/lib/credencial-do-servidor";
import { pedidoDeOutroSite, recusaDeOutroSite } from "@/lib/mesma-origem";

const API = process.env.FRAUS_API_URL ?? "http://localhost:8000";

async function repassar(
  requisicao: Request,
  contexto: { params: Promise<{ caminho: string[] }> },
): Promise<Response> {
  // Antes de qualquer coisa: este proxy escreve na API com a credencial do
  // DEPLOY, então um POST vindo de outro site seria uma escrita autenticada
  // que o dono nunca pediu. Leitura (GET) não passa por aqui — ela já é
  // barrada pelo CORS na hora de ler a resposta.
  if (pedidoDeOutroSite(requisicao)) return recusaDeOutroSite();

  const { caminho } = await contexto.params;
  const busca = new URL(requisicao.url).search;
  const destino = `${API}/${caminho.join("/")}${busca}`;

  const cabecalhos = new Headers(requisicao.headers);
  cabecalhos.delete("host");
  cabecalhos.delete("authorization");
  // O cookie da dashboard nao tem nada a fazer numa requisicao para a API: o
  // que ele carrega e a credencial, e ela sai no Authorization abaixo.
  cabecalhos.delete("cookie");

  const autorizacao = await autorizacaoDoServidor(requisicao);
  if (autorizacao) cabecalhos.set("authorization", autorizacao);

  let resposta: Response;
  try {
    resposta = await fetch(destino, {
      method: requisicao.method,
      headers: cabecalhos,
      body: requisicao.body,
      // meio-duplex e exigido pelo fetch do Node ao repassar um corpo em stream
      // @ts-expect-error duplex ainda nao esta no tipo RequestInit
      duplex: "half",
      cache: "no-store",
      // Sem teto, uma API que aceita a conexao e nunca responde deixa a aba
      // girando para sempre. 60s porque /analisar roda os BERTimbau em CPU e
      // leva segundos por conversa -- um limite "generoso" de 10s cortaria a
      // rota mais lenta do produto no meio do trabalho.
      signal: AbortSignal.timeout(60_000),
    });
  } catch {
    // API fora do ar, DNS errado ou estouro do teto acima. O 502 nomeia o que
    // houve sem repetir `destino` no corpo: a URL interna da API (e a porta em
    // que ela escuta) nao precisa chegar ao navegador de quem abre a dashboard
    // publicada. Quem opera le o motivo exato no log do servidor Next.
    return Response.json({ detail: "API não respondeu" }, { status: 502 });
  }

  const cabecalhosResposta = new Headers(resposta.headers);
  // o fetch do Node ja descomprime o corpo -- repassar content-encoding/
  // content-length/transfer-encoding faria o navegador tentar decodificar
  // (ou truncar) um corpo que ja chegou decodificado.
  cabecalhosResposta.delete("content-encoding");
  cabecalhosResposta.delete("content-length");
  cabecalhosResposta.delete("transfer-encoding");

  return new Response(resposta.body, {
    status: resposta.status,
    headers: cabecalhosResposta,
  });
}

export {
  repassar as GET,
  repassar as POST,
  repassar as PUT,
  repassar as PATCH,
  repassar as DELETE,
};
