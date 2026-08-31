/**
 * Logout: apaga o cookie de sessão. O token não é revogável no servidor por
 * decisão (12h de validade, sem lista de revogação) — sair é esquecer.
 */

import { cookies } from "next/headers";
import { pedidoDeOutroSite, recusaDeOutroSite } from "@/lib/mesma-origem";
import { COOKIE_SESSAO } from "@/lib/sessao";

export async function POST(requisicao: Request): Promise<Response> {
  if (pedidoDeOutroSite(requisicao)) return recusaDeOutroSite();
  const jarra = await cookies();
  jarra.delete(COOKIE_SESSAO);
  return Response.json({ ok: true });
}
