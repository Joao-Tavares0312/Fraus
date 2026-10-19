import type { PreviaLeitura } from "@/lib/api";

/**
 * O que a tela Analisar faz com uma prévia — regra pura, testada à parte.
 *
 * "Arrastar e pronto" (19/10/2026): leitura confiável vai direto para o
 * modelo; duvidosa para na conferência de colunas. Quem decide o que é
 * confiável é o SERVIDOR (`leitura_confiavel`), nunca uma segunda regra aqui.
 */
export function proximoPasso(previa: Pick<PreviaLeitura, "confiavel">): "analisar" | "conferir" {
  return previa.confiavel ? "analisar" : "conferir";
}

/**
 * Sempre salvar, exceto quando não há horário: sem horário não há nota, e o
 * servidor recusa gravar (422). Aí a leitura é avulsa e a tela diz por quê.
 */
export function deveSalvar(previa: Pick<PreviaLeitura, "tem_tempo">): boolean {
  return previa.tem_tempo;
}
