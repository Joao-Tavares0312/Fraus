/**
 * Logout: apaga o cookie de sessão. O token não é revogável no servidor por
 * decisão (12h de validade, sem lista de revogação) — sair é esquecer.
 *
 * Esquece também `fraus_acesso`, a chave técnica gravada por
 * `/api/fraus/ligar-autenticacao`: o proxy a usa mesmo com login ligado, e
 * sobrando depois de "Sair" ela continuava abrindo a API para quem usasse o
 * mesmo navegador (auditoria de 13/10/2026).
 */

import { cookies } from "next/headers";
import { pedidoDeOutroSite, recusaDeOutroSite } from "@/lib/mesma-origem";
import { NOME_DO_COOKIE } from "@/lib/credencial-do-servidor";
import { COOKIE_SESSAO } from "@/lib/sessao";

export async function POST(requisicao: Request): Promise<Response> {
  if (pedidoDeOutroSite(requisicao)) return recusaDeOutroSite();
  const jarra = await cookies();
  jarra.delete(COOKIE_SESSAO);
  jarra.delete(NOME_DO_COOKIE);
  return Response.json({ ok: true });
}
