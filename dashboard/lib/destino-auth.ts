/** Retorno limitado ao convite: nunca aceita redirecionamento externo. */
export function tokenDeConvite(valor: unknown): string | null {
  return typeof valor === "string" && /^[A-Za-z0-9_-]{43}$/.test(valor) ? valor : null;
}
export function destinoAuth(convite: unknown): string {
  const token = tokenDeConvite(convite);
  return token ? `/convite/${token}` : "/dashboard";
}
