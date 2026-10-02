/**
 * Lista e emite chaves de ACESSO -- as duas operacoes que exigem a MESTRA.
 *
 * Existe fora do proxy geral por uma razao de contrato, nao de conveniencia. O
 * proxy DESCARTA o `Authorization` que vem do navegador de proposito: a
 * credencial da API e a do deploy, e um cliente que pudesse escolher o proprio
 * header transformaria o proxy num oraculo para testar chaves. So que a chave
 * que o proxy anexa e a de ACESSO, e gerenciar chave e privilegio exclusivo da
 * mestra -- pelo proxy, `GET /acesso/chaves` responderia 403 para sempre.
 *
 * Entao esta rota repassa o `Authorization` do cliente, exatamente como
 * `ligar-autenticacao` ja fazia pela mesma razao (e o unico lugar onde o Joao
 * digita a mestra). O oraculo nao volta: a API valida a chave de qualquer
 * forma, e quem erra recebe o mesmo 403 que receberia falando com ela direto.
 *
 * Com a API ABERTA nao ha o que apresentar, e `exigir_mestra` deixa passar --
 * o painel funciona sem credencial nenhuma, coerente com o resto do modo local.
 */

import { autorizacaoParaLigar } from "@/lib/credencial-do-servidor";
import { pedidoDeOutroSite, recusaDeOutroSite } from "@/lib/mesma-origem";

const API = process.env.FRAUS_API_URL ?? "http://localhost:8000";

async function repassar(
  requisicao: Request,
  metodo: "GET" | "POST",
  corpo?: string,
): Promise<Response> {
  const autorizacao = await autorizacaoParaLigar(requisicao);

  let resposta: Response;
  try {
    resposta = await fetch(`${API}/acesso/chaves`, {
      method: metodo,
      headers: {
        ...(autorizacao ? { authorization: autorizacao } : {}),
        ...(corpo ? { "content-type": "application/json" } : {}),
      },
      body: corpo,
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
  } catch {
    // Mesma regra do proxy: o 502 nao repete a URL interna da API.
    return Response.json({ detail: "API não respondeu" }, { status: 502 });
  }

  const dado = await resposta.json().catch(() => null);
  return Response.json(dado ?? { detail: "resposta inesperada da API" }, {
    status: resposta.status,
  });
}

export async function GET(requisicao: Request): Promise<Response> {
  return repassar(requisicao, "GET");
}

export async function POST(requisicao: Request): Promise<Response> {
  if (pedidoDeOutroSite(requisicao)) return recusaDeOutroSite();

  const pedido = await requisicao.json().catch(() => null);
  const nome = typeof pedido?.nome === "string" ? pedido.nome.trim() : "";
  if (!nome) {
    // Barrado aqui para a tela nao gastar uma ida a API com o que ela ja sabe
    // que esta errado. A API valida de novo -- esta checagem e cortesia, nunca
    // a defesa.
    return Response.json({ detail: "informe um nome para a chave" }, { status: 400 });
  }

  return repassar(requisicao, "POST", JSON.stringify({ nome }));
}
