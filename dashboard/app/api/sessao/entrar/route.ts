/**
 * Login: troca e-mail e senha pelo cookie de sessão.
 *
 * O token que a API devolve NUNCA chega ao navegador — vira cookie httpOnly
 * aqui e morre no `sair`. O corpo da resposta leva só a ficha do usuário.
 */

import { cookies } from "next/headers";
import { pedidoDeOutroSite, recusaDeOutroSite } from "@/lib/mesma-origem";
import { COOKIE_SESSAO } from "@/lib/sessao";

const API = process.env.FRAUS_API_URL ?? "http://localhost:8000";

// 12h, o mesmo prazo do token (fraus/token_acesso.py). Cookie mais longo que
// o token só guardaria um token morto.
const DURACAO_S = 12 * 60 * 60;

export async function POST(requisicao: Request): Promise<Response> {
  // Escrita autenticada disparada de outro site é exatamente o que o cookie
  // SameSite defende — mas o login é ANTES do cookie existir, então a defesa
  // é a mesma do proxy: origem.
  if (pedidoDeOutroSite(requisicao)) return recusaDeOutroSite();

  let resposta: Response;
  try {
    resposta = await fetch(`${API}/auth/entrar`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: await requisicao.text(),
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    return Response.json({ detail: "API não respondeu" }, { status: 502 });
  }

  if (!resposta.ok) {
    // Repassa a recusa da API como ela veio — inclusive a mensagem uniforme
    // de credencial, que não pode ganhar variações daqui.
    return new Response(resposta.body, {
      status: resposta.status,
      headers: { "content-type": "application/json" },
    });
  }

  const corpo = (await resposta.json()) as { token: string; usuario: unknown };
  const jarra = await cookies();
  jarra.set(COOKIE_SESSAO, corpo.token, {
    httpOnly: true,
    sameSite: "lax",
    // `secure` só fora do desenvolvimento: em http://localhost um cookie
    // secure simplesmente não é gravado e o login "funciona" sem logar.
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: DURACAO_S,
  });

  return Response.json({ usuario: corpo.usuario });
}
