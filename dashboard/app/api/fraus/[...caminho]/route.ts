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
const CHAVE_DO_AMBIENTE = process.env.FRAUS_CHAVE_ACESSO;
const COOKIE = "fraus_acesso";

function chaveDaRequisicao(requisicao: Request): string | undefined {
  // O ambiente VENCE: e a credencial declarada do deploy. O cookie e o atalho
  // de quem ligou a autenticacao pela tela, e existe porque variavel de
  // ambiente nao muda em processo vivo -- sem ele, o clique que liga a
  // autenticacao derrubaria a propria dashboard.
  if (CHAVE_DO_AMBIENTE) return CHAVE_DO_AMBIENTE;

  const bruto = requisicao.headers.get("cookie");
  if (!bruto) return undefined;
  for (const pedaco of bruto.split(";")) {
    const [nome, ...resto] = pedaco.trim().split("=");
    // `join("=")`: valor de cookie pode conter `=`, e cortar no primeiro
    // truncaria a chave sem erro nenhum aparecer.
    if (nome === COOKIE) return resto.join("=");
  }
  return undefined;
}

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
  // O cookie da dashboard nao tem nada a fazer numa requisicao para a API: o
  // que ele carrega e a credencial, e ela sai no Authorization abaixo.
  cabecalhos.delete("cookie");

  const chave = chaveDaRequisicao(requisicao);
  if (chave) cabecalhos.set("authorization", `Bearer ${chave}`);

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
