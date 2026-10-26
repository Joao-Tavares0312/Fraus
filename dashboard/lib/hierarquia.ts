/** Um painel dominante por tela; os apoios se agrupam por espaço e divisória. */

export type Nivel = "dominante" | "apoio";

const CLASSES: Record<Nivel, string> = {
  dominante: "superficie fio p-4 sm:p-6",
  apoio: "painel-apoio p-4 sm:p-5",
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
  // O explorador mostra o processamento; os vereditos permanecem como apoio.
  "/dashboard/modelo": "explorador-do-modelo",
  "/dashboard/grafo": "canvas-do-grafo",
  "/dashboard/integracoes": "fontes",
  "/dashboard/configuracoes": "faixas-de-nps",
};

/** Devolve o identificador estavel do dominante da rota, ou null se a rota
 * nao for tela da ferramenta. */
export function dominanteDaTela(rota: string): string | null {
  return DOMINANTE_POR_TELA[rota] ?? null;
}
