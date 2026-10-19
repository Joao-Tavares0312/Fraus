import { Activity, ChartNoAxesCombined, FlaskConical, MessagesSquare, Network, Plug, Settings2, Workflow } from "lucide-react";

/** Destinos, agrupamento e visibilidade. A API continua a fronteira de permissão. */
export const GRUPOS_DE_NAVEGACAO = ["Acompanhar", "Investigar"] as const;

export const TELAS = [
  { href: "/dashboard", rotulo: "Visão geral", grupo: "Acompanhar", somenteDev: false, icone: ChartNoAxesCombined },
  { href: "/dashboard/atendimentos", rotulo: "Atendimentos", grupo: "Acompanhar", somenteDev: false, icone: MessagesSquare },
  { href: "/dashboard/analisar", rotulo: "Analisar", grupo: "Investigar", somenteDev: false, icone: FlaskConical },
  { href: "/dashboard/grafo", rotulo: "Grafo", grupo: "Investigar", somenteDev: false, icone: Network },
  { href: "/dashboard/modelo", rotulo: "Modelo", grupo: "Investigar", somenteDev: true, icone: Activity },
  // Gestão e configuração moram no menu da conta (19/10/2026): a lateral fica
  // com as tarefas do dia a dia do cliente final.
  { href: "/dashboard/operacao", rotulo: "Operação", grupo: "Conta", somenteDev: false, icone: Workflow },
  { href: "/dashboard/integracoes", rotulo: "Integrações", grupo: "Conta", somenteDev: true, icone: Plug },
  { href: "/dashboard/configuracoes", rotulo: "Configurações", grupo: "Conta", somenteDev: true, icone: Settings2 },
] as const;

export type Tela = (typeof TELAS)[number];

export function gruposDoPapel(papel: "dev" | "usuario") {
  return GRUPOS_DE_NAVEGACAO.map((rotulo) => ({
    rotulo,
    telas: TELAS.filter((tela) => tela.grupo === rotulo && (!tela.somenteDev || papel === "dev")),
  })).filter((grupo) => grupo.telas.length > 0);
}

/** Os destinos do menu da conta, no rodapé da lateral. */
export function telasDaConta(papel: "dev" | "usuario") {
  return TELAS.filter((tela) => tela.grupo === "Conta" && (!tela.somenteDev || papel === "dev"));
}

/** A visão geral é exata; as demais telas também representam seus descendentes. */
export function telaEstaAtiva(caminho: string, href: Tela["href"]): boolean {
  return caminho === href || (href !== "/dashboard" && caminho.startsWith(`${href}/`));
}

/** Filtros locais da tela anterior nunca vazam para a próxima tarefa. */
export function consultaDoPeriodo(parametros: Pick<URLSearchParams, "get">): string {
  const consulta = new URLSearchParams();
  for (const chave of ["de", "ate"]) {
    const valor = parametros.get(chave);
    if (valor) consulta.set(chave, valor);
  }
  const serializada = consulta.toString();
  return serializada ? `?${serializada}` : "";
}

