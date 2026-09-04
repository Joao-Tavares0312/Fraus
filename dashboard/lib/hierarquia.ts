// dashboard/lib/hierarquia.ts
/**
 * O VOCABULARIO DE HIERARQUIA.
 *
 * Ate 04/09/2026 todo painel usava a mesma superficie, o mesmo raio e o mesmo
 * espacamento: a pagina era uma pilha de blocos equivalentes, sem primario e
 * secundario legiveis de longe. A §2.2 do DESIGN.md ja pedia ritmo vertical
 * ("um sistema denso ganha o direito de um respiro depois") e a interface nao
 * executava.
 *
 * O peso mora AQUI, e nao na tela, pelo mesmo motivo que cor mora em token:
 * regra digitada de novo em outro lugar diverge. E a mesma disciplina da
 * invariante 4 do CLAUDE.md, que existe porque isso ja aconteceu neste
 * projeto -- duplicar a regra de faixa de NPS no TypeScript causou divergencia
 * de arredondamento nas fronteiras 6/7 e 8/9.
 *
 * NAO decide cor. Nivel e escala, superficie e espaco; cor continua sendo
 * dito/medido e categoria, que sao encoding e nao hierarquia.
 */

export type Nivel = "dominante" | "apoio";

/**
 * As tres espessuras de vidro ja existem desde 21/08/2026 (DESIGN.md §7) e
 * estavam sendo consumidas quase indistintamente. O denso NAO entra aqui: ele
 * existe para o conteudo atras SUMIR num menu suspenso, e usar isso como
 * hierarquia de pagina gastaria a espessura mais cara de CSS em decoracao.
 */
const CLASSES: Record<Nivel, string> = {
  dominante: "vidro p-4 sm:p-6",
  apoio: "vidro-fino p-4 sm:p-5",
};

export function classesDoNivel(nivel: Nivel): string {
  return CLASSES[nivel];
}

/**
 * QUAL sistema responde a pergunta que levou o analista a cada tela.
 *
 * O valor e um IDENTIFICADOR ESTAVEL, nao o titulo exibido. A primeira versao
 * guardava o titulo, e isso era fragil por construcao: varios paineis montam
 * o titulo em tempo de render porque ele carrega periodo ou contagem
 * (`Atendimentos de ${rotulo}`, `${n} nos, ${m} arestas`), e nenhuma string
 * estatica casa com isso. Um consumidor que comparasse titulo falharia em
 * silencio em metade das telas.
 *
 * Quem MARCA o dominante e a propria tela, com `nivel="dominante"` no Painel.
 * Esta tabela documenta a intencao e da a guarda de "um por tela" algo para
 * conferir; ela nao e chave de busca.
 */
export const DOMINANTE_POR_TELA: Record<string, string> = {
  "/dashboard": "nps-x-latencia",
  "/dashboard/atendimentos": "tabela-de-atendimentos",
  // A tela Modelo abria pelo simulador e enterrava no meio o que o avaliador
  // precisa ler primeiro -- ver Task 7.
  "/dashboard/modelo": "veredito-do-modelo",
  "/dashboard/grafo": "canvas-do-grafo",
  "/dashboard/integracoes": "fontes",
  "/dashboard/configuracoes": "faixas-de-nps",
};

/** Devolve o identificador estavel do dominante da rota, ou null se a rota
 * nao for tela da ferramenta. */
export function dominanteDaTela(rota: string): string | null {
  return DOMINANTE_POR_TELA[rota] ?? null;
}
