import type { Veredito } from "./api";

/**
 * O que a tela escreve para um veredito de entrega de webhook.
 *
 * Mora em `lib/` (e nao dentro de `Entregas.tsx`, onde nasceu) para ser
 * testavel sem montar o componente: o defeito de 02/10/2026 era justamente
 * comportamento -- um veredito que a tela nao conhecia derrubava o painel.
 */
export type DescricaoDoVeredito = {
  /** Uma entrega, na linha da lista. */
  rotulo: string;
  /** Varias entregas, depois da contagem no cabecalho. */
  plural: string;
  cor: string;
};

/**
 * O rotulo e a cor de cada veredito CONHECIDO.
 *
 * E um `Record<Veredito, ...>` pelo mesmo motivo de o `switch` que ele
 * substitui nao ter `default`: o `Record` exige TODAS as chaves, entao um
 * veredito novo entrando no tipo `Veredito` sem passar por aqui vira erro de
 * tipo no `npx tsc --noEmit`. A exaustividade continua sendo do COMPILADOR; o
 * que mudou e o que acontece em runtime com o valor que o tipo nao previu
 * (ver `descreverVeredito`).
 *
 * SAO DOIS ROTULOS porque sao duas frases diferentes. Na linha da lista o
 * veredito qualifica UMA entrega e o singular esta certo ("assinatura
 * invalida"); no cabecalho ele vem depois de uma contagem, e "18 aceita" e
 * agramatical. Concordar no cabecalho sem estragar a linha exige os dois.
 *
 * A cor segue o DESIGN.md: nada de `--primary` aqui, porque o dourado e acao e
 * foco e NUNCA dado. `sem_segredo` e vermelho porque e defeito da MAQUINA que
 * hospeda -- a variavel de ambiente nao esta la, a rota responde 503, e
 * nenhuma plataforma do outro lado consegue consertar. `erro` (500) leva o
 * mesmo vermelho pelo mesmo motivo: a culpa nao e de quem chamou.
 * `vazao` leva a cor de aviso: nao e defeito de ninguem, e a plataforma
 * mandando mais rapido que o teto, e passa sozinho -- mas explica por que ela
 * comecou a retentar, que e o que o operador veio ver.
 */
const VEREDITOS: Record<Veredito, DescricaoDoVeredito> = {
  aceita: {
    rotulo: "aceita",
    plural: "aceitas",
    cor: "text-promotor-texto",
  },
  assinatura: {
    rotulo: "assinatura inválida",
    plural: "com assinatura inválida",
    cor: "text-muted-foreground",
  },
  fora_da_janela: {
    rotulo: "fora da janela de tempo",
    plural: "fora da janela de tempo",
    cor: "text-muted-foreground",
  },
  duplicada: {
    rotulo: "reentrega",
    plural: "reentregas",
    cor: "text-muted-foreground",
  },
  corpo_invalido: {
    rotulo: "corpo fora do contrato",
    plural: "com corpo fora do contrato",
    cor: "text-muted-foreground",
  },
  fonte_inativa: {
    rotulo: "fonte desativada",
    plural: "recusadas por fonte desativada",
    cor: "text-muted-foreground",
  },
  sem_segredo: {
    rotulo: "segredo ausente no ambiente da API",
    plural: "sem segredo no ambiente da API",
    cor: "text-detrator-texto",
  },
  tipo_incompativel: {
    rotulo: "fonte não é do tipo webhook",
    plural: "recusadas por a fonte não ser do tipo webhook",
    cor: "text-muted-foreground",
  },
  vazao: {
    rotulo: "acima do teto de envios por minuto",
    plural: "recusadas por passar do teto de envios por minuto",
    cor: "text-warning-rich-text",
  },
  erro: {
    rotulo: "falha interna da API",
    plural: "com falha interna da API",
    cor: "text-detrator-texto",
  },
};

/**
 * A ordem canonica dos vereditos, a mesma do tipo `Veredito`.
 *
 * Existe para o cabecalho de contagem NAO dancar: derivada da ordem de
 * aparicao na lista, ela se reorganizava a cada carregamento conforme o que
 * tinha chegado por ultimo. Esta e a tela que o operador fica olhando enquanto
 * depura -- ela nao pode trocar de forma sozinha.
 */
const ORDEM = Object.keys(VEREDITOS);

function conhecido(veredito: string): veredito is Veredito {
  return Object.hasOwn(VEREDITOS, veredito);
}

/**
 * Descreve um veredito, CONHECIDO OU NAO.
 *
 * Recebe `string`, e nao `Veredito`, de proposito: o tipo descreve o que o
 * front sabe, e o valor vem de outro deploy. A dashboard e a API publicam
 * separadas, entao um veredito novo chega aqui antes de o tipo saber dele --
 * foi o caso de `vazao`. O desconhecido aparece com o valor CRU, por extenso:
 * um rotulo em branco ninguem le como bug, e a tela inteira caindo esconde as
 * entregas que o operador veio ler.
 */
export function descreverVeredito(veredito: string): DescricaoDoVeredito {
  if (conhecido(veredito)) return VEREDITOS[veredito];
  return {
    rotulo: `veredito desconhecido: ${veredito}`,
    plural: `com veredito desconhecido (${veredito})`,
    cor: "text-muted-foreground",
  };
}

/** Posicao no cabecalho de contagem; o desconhecido vai para o fim. */
export function ordemDoVeredito(veredito: string): number {
  const posicao = ORDEM.indexOf(veredito);
  return posicao === -1 ? ORDEM.length : posicao;
}
