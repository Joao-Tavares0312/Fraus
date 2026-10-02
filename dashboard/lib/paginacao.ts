/**
 * A pagina que de fato existe, dado quantas paginas ha.
 *
 * A tabela de atendimentos deixou de voltar sozinha a pagina 1 quando a lista
 * e relida (a sincronizacao por foco troca a identidade das linhas a cada
 * volta a aba). Sem esse reset, alguem precisa garantir que a pagina atual
 * continua existindo quando a lista ENCOLHE -- senao a tela mostra "Página 5
 * de 2" sobre uma tabela vazia.
 */
export function limitarPagina(pagina: number, totalDePaginas: number): number {
  const ultima = Math.max(0, totalDePaginas - 1);
  return Math.min(Math.max(0, pagina), ultima);
}
