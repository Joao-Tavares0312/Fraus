/**
 * A sessão de usuário, do lado do servidor Next.
 *
 * O navegador NUNCA vê o token: ele mora no cookie httpOnly `fraus_sessao`,
 * gravado por `app/api/sessao/entrar` — o mesmo desenho que já mantém a chave
 * de acesso fora do navegador. Estes helpers rodam só em Server Component e
 * Route Handler; nenhum deles é importável de código de cliente sem quebrar
 * no build (usam `next/headers`).
 *
 * A ficha vem de `/auth/eu`, que lê o BANCO, não o payload do token: conta
 * desativada para de responder na hora, sem esperar o token expirar.
 */

import { cookies } from "next/headers";

import { COOKIE_SESSAO } from "@/lib/credencial-do-servidor";

export { COOKIE_SESSAO };

const API = process.env.FRAUS_API_URL ?? "http://localhost:8000";

export type Usuario = {
  id: number;
  nome: string;
  email: string;
  papel: "dev" | "usuario";
  ativo: boolean;
  criado_em: string;
};

export async function tokenDaSessao(): Promise<string | undefined> {
  try {
    return (await cookies()).get(COOKIE_SESSAO)?.value;
  } catch {
    // Fora do escopo de uma requisição `cookies()` lança — sem requisição,
    // sem sessão.
    return undefined;
  }
}

/** Quem está logado, ou null — token ausente, expirado ou conta desativada. */
export async function usuarioDaSessao(): Promise<Usuario | null> {
  const token = await tokenDaSessao();
  if (!token) return null;
  try {
    const resposta = await fetch(`${API}/auth/eu`, {
      headers: { authorization: `Bearer ${token}` },
      cache: "no-store",
      signal: AbortSignal.timeout(5_000),
    });
    if (!resposta.ok) return null;
    return (await resposta.json()) as Usuario;
  } catch {
    // API fora do ar: sem como validar, sem sessão. A tela da dashboard já
    // tem o AvisoApiFora para explicar o resto.
    return null;
  }
}

/**
 * Se o login EXISTE nesta instalação (FRAUS_JWT_SEGREDO definida na API).
 *
 * A dashboard só exige login quando há como logar: sem o segredo, mandar o
 * modo aberto para a tela de entrar — que responderia 503 — trancaria a
 * instalação local para fora. Mesma filosofia da API aberta sem mestra.
 *
 * Em caso de dúvida (API fora do ar), a resposta é `false`: a dashboard abre
 * e o AvisoApiFora explica o que falta — melhor que um redirect para um login
 * que também não funcionaria.
 */
export async function loginDisponivel(): Promise<boolean> {
  try {
    const resposta = await fetch(`${API}/auth/estado`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5_000),
    });
    if (!resposta.ok) return false;
    const corpo = (await resposta.json()) as { disponivel: boolean };
    return corpo.disponivel === true;
  } catch {
    return false;
  }
}
