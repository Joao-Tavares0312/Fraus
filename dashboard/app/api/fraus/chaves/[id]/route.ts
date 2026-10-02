/**
 * Revoga uma chave de acesso. Mesma razao de existir da rota irma (`../route.ts`):
 * revogar e privilegio da MESTRA, e o proxy geral anexa a chave de acesso.
 *
 * A revogacao vale na chamada SEGUINTE -- a decisao de credencial acontece por
 * requisicao, entao nao ha janela em que a chave revogada continue passando.
 */

import { autorizacaoParaLigar } from "@/lib/credencial-do-servidor";
import { pedidoDeOutroSite, recusaDeOutroSite } from "@/lib/mesma-origem";

const API = process.env.FRAUS_API_URL ?? "http://localhost:8000";

export async function DELETE(
  requisicao: Request,
  contexto: { params: Promise<{ id: string }> },
): Promise<Response> {
  if (pedidoDeOutroSite(requisicao)) return recusaDeOutroSite();

  const { id } = await contexto.params;
  // O id vai para a URL como NUMERO, nunca como o texto que chegou: a rota da
  // API o declara `int`, e interpolar texto cru num caminho e o comeco de uma
  // classe de bug que nao precisa existir aqui.
  const numero = Number(id);
  if (!Number.isInteger(numero) || numero <= 0) {
    return Response.json({ detail: "identificador inválido" }, { status: 400 });
  }

  const autorizacao = await autorizacaoParaLigar(requisicao);

  let resposta: Response;
  try {
    resposta = await fetch(`${API}/acesso/chaves/${numero}`, {
      method: "DELETE",
      headers: autorizacao ? { authorization: autorizacao } : {},
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
  } catch {
    return Response.json({ detail: "API não respondeu" }, { status: 502 });
  }

  // 204 nao tem corpo para repassar -- devolver `Response.json(null)` faria a
  // tela tentar ler um JSON que nao existe.
  if (resposta.status === 204) return new Response(null, { status: 204 });

  const dado = await resposta.json().catch(() => null);
  return Response.json(dado ?? { detail: "resposta inesperada da API" }, {
    status: resposta.status,
  });
}
