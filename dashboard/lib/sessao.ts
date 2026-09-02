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

/**
 * Quanto tempo esperar a API responder sobre a sessão.
 *
 * ERA 5 SEGUNDOS, e era o teto mais apertado do sistema inteiro no ponto mais
 * quente: `/auth/eu` roda em TODA renderização de TODA tela da dashboard. Isso
 * era razoável quando a API morava em `localhost`. Com ela publicada por túnel
 * — a requisição sai da Vercel, atravessa a internet até uma máquina doméstica
 * e volta — 5s viraram um limite que a rede estoura sozinha.
 */
const ESPERA_SESSAO_MS = 15_000;

/**
 * A sessão tem TRÊS estados, não dois -- e reduzi-los a dois era o bug.
 *
 * `ausente` é uma RESPOSTA: não há cookie, ou a API olhou o token e recusou.
 * `indeterminada` é a falta de resposta: a pergunta não chegou ou não voltou a
 * tempo. As duas viravam `null`, e quem lia `null` concluía "não está logado"
 * -- então uma lentidão de rede EXPULSAVA para a tela de entrar quem estava
 * logado com o cookie válido na mão. A pessoa logava de novo e nada explicava
 * o que tinha acontecido.
 *
 * É a mesma distinção que a invariante 2 faz no dado: ausência de medida não é
 * medida zero. Aqui, ausência de resposta não é ausência de sessão.
 */
export type Sessao =
  | { estado: "logada"; usuario: Usuario }
  | { estado: "ausente" }
  | { estado: "indeterminada" };

export async function tokenDaSessao(): Promise<string | undefined> {
  try {
    return (await cookies()).get(COOKIE_SESSAO)?.value;
  } catch {
    // Fora do escopo de uma requisição `cookies()` lança — sem requisição,
    // sem sessão.
    return undefined;
  }
}

/** A sessão com os três estados. Quem precisa decidir redirecionar usa esta. */
export async function sessaoAtual(): Promise<Sessao> {
  const token = await tokenDaSessao();
  // Sem cookie não há o que perguntar: isto é resposta, não silêncio.
  if (!token) return { estado: "ausente" };
  let resposta: Response;
  try {
    resposta = await fetch(`${API}/auth/eu`, {
      headers: { authorization: `Bearer ${token}` },
      cache: "no-store",
      signal: AbortSignal.timeout(ESPERA_SESSAO_MS),
    });
  } catch {
    // Tempo esgotado ou API fora do ar. NÃO se sabe se a sessão vale.
    return { estado: "indeterminada" };
  }
  // A API respondeu e recusou: token expirado, adulterado ou conta desativada.
  // Isso é veredito, e vale como "ausente".
  if (resposta.status === 401 || resposta.status === 403) {
    return { estado: "ausente" };
  }
  if (!resposta.ok) return { estado: "indeterminada" };
  try {
    return { estado: "logada", usuario: (await resposta.json()) as Usuario };
  } catch {
    return { estado: "indeterminada" };
  }
}

/**
 * Quem está logado, ou null. Atalho para quem NÃO precisa distinguir
 * "não está logado" de "não deu para perguntar" -- as telas que apenas
 * escolhem um rótulo, ou que mandam quem já entrou para a dashboard.
 *
 * Quem decide EXPULSAR alguém precisa da distinção e usa `sessaoAtual`.
 */
export async function usuarioDaSessao(): Promise<Usuario | null> {
  const sessao = await sessaoAtual();
  return sessao.estado === "logada" ? sessao.usuario : null;
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
      signal: AbortSignal.timeout(ESPERA_SESSAO_MS),
    });
    if (!resposta.ok) return false;
    const corpo = (await resposta.json()) as { disponivel: boolean };
    return corpo.disponivel === true;
  } catch {
    return false;
  }
}
