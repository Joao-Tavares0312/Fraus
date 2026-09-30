/**
 * A NUMERACAO DAS TELAS.
 *
 * O Instrumento numera a navegacao (`01_VISAO GERAL`) e repete a numeracao na
 * faixa de telemetria do topo. As duas pontas leem DAQUI: numero digitado em
 * dois lugares e numero que diverge na primeira tela nova -- a mesma disciplina
 * que manda cor para token e faixa de NPS para um lugar so.
 *
 * A ORDEM E A DA TELA, nao a do papel: um `usuario` so ve as duas primeiras, e
 * elas continuam sendo 01 e 02. Numero que muda conforme quem olha faria a
 * mesma tela ter dois nomes.
 *
 * As tres de olhar (visao geral, atendimentos, analisar, modelo, grafo) vem
 * antes das duas de mexer (configuracoes, integracoes), como o menu ja separa.
 */

export const TELAS = [
  { href: "/dashboard", rotulo: "Visão geral" },
  { href: "/dashboard/atendimentos", rotulo: "Atendimentos" },
  { href: "/dashboard/analisar", rotulo: "Analisar" },
  { href: "/dashboard/modelo", rotulo: "Modelo" },
  { href: "/dashboard/grafo", rotulo: "Grafo" },
  { href: "/dashboard/configuracoes", rotulo: "Configurações" },
  { href: "/dashboard/integracoes", rotulo: "Integrações" },
] as const;

export type Tela = (typeof TELAS)[number];

/** `01`, `02`... -- dois digitos, para o cursor do menu nao dancar de 9 para 10. */
export function numeroDaRota(href: string): string | null {
  const indice = TELAS.findIndex((t) => t.href === href);
  return indice === -1 ? null : String(indice + 1).padStart(2, "0");
}

/**
 * A tela a que um caminho pertence, por PREFIXO MAIS LONGO.
 *
 * `/dashboard/atendimentos/abc-123` e a tela de Atendimentos, e `/dashboard`
 * sozinho so casa consigo mesmo -- senao TODA rota casaria com a Visao geral.
 * Caminho fora da ferramenta devolve `null`, e quem chama decide o que mostrar.
 */
export function telaDoCaminho(caminho: string): Tela | null {
  let melhor: Tela | null = null;
  for (const tela of TELAS) {
    const casa =
      tela.href === "/dashboard"
        ? caminho === "/dashboard"
        : caminho === tela.href || caminho.startsWith(`${tela.href}/`);
    if (casa && (melhor === null || tela.href.length > melhor.href.length)) {
      melhor = tela;
    }
  }
  return melhor;
}

/** `01_VISÃO GERAL` -- o rotulo numerado, em caixa alta. */
export function rotuloNumerado(tela: Tela): string {
  return `${numeroDaRota(tela.href)}_${tela.rotulo.toLocaleUpperCase("pt-BR")}`;
}
