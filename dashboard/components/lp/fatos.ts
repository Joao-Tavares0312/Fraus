/**
 * OS FATOS DO PRODUTO QUE A VITRINE ANUNCIA, num lugar so.
 *
 * Sao os numeros do CLAUDE.md, e a vitrine promete "nenhum numero inventado".
 * Um literal solto em cada componente era o que deixava o "39" divergir de
 * `NOMES_FEATURES` sem ninguem ver: em 04/09/2026 o contrato caiu de 40 para
 * 38 e a LP seguiu anunciando 35.
 *
 * `tests/test_derivacoes_dashboard.py` le ESTE arquivo como texto e compara
 * `features` com `len(NOMES_FEATURES)`, e varre a vitrine inteira atras de
 * qualquer outro "N features" digitado a mao. Nao formate os numeros de forma
 * que essa busca deixe de achar -- se o formato mudar, atualize o teste, nao
 * apague a guarda.
 */
export const FATOS_DO_MODELO = {
  familias: 7,
  features: 39,
  bertimbau: 3,
  llms: 0,
} as const;

/**
 * AS SETE FAMILIAS DO VETOR, com a contagem REAL de features de cada uma, na
 * ordem de `NOMES_FEATURES`. A constelacao da vitrine desenha um no por
 * feature agrupado por familia, e a lista do Sistema escreve a contagem: se
 * ela fosse desenho, quem contasse os pontos leria numero falso.
 *
 * `tests/test_derivacoes_dashboard.py` le estes pares `chave`/`qtd` como
 * texto e compara com o agrupamento de `NOMES_FEATURES`. A soma bate com
 * `FATOS_DO_MODELO.features` por `lib/vitrine/coreografia.test.ts`.
 */
export const FAMILIAS_DO_VETOR = [
  { chave: "texto", rotulo: "Texto", qtd: 4, leitura: "BERTimbau fine-tunado, probabilidade por mensagem — por isso a nota aponta a fala que a puxou." },
  { chave: "emoji", rotulo: "Emoji", qtd: 5, leitura: "Emoji Sentiment Ranking, com a posição do emoji na mensagem." },
  { chave: "tempo", rotulo: "Tempo", qtd: 7, leitura: "Latência, duração, turnos, escalação e abandono — derivados dos horários, nunca gravados." },
  { chave: "emocao", rotulo: "Emoção", qtd: 8, leitura: "Sete classes, com desprezo derivado da díade raiva + nojo." },
  { chave: "lexico", rotulo: "Léxico", qtd: 3, leitura: "SentiLex-PT02 com escopo de negação: “não está bom” não é “bom”." },
  { chave: "estilo", rotulo: "Estilo", qtd: 6, leitura: "Caixa alta, pontuação, alongamento, palavrão e censura." },
  { chave: "incongruencia", rotulo: "Incongruência", qtd: 6, leitura: "Emoji contra texto, contraste, hipérbole, aspas e elogio contra situação negativa." },
] as const;

/** Em duas casas ("07", "00"), como o LED e a telemetria os mostram. */
export function emDuasCasas(n: number): string {
  return String(n).padStart(2, "0");
}
