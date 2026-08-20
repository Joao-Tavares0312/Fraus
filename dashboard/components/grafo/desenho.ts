/**
 * =============================================================================
 * A NOTACAO DO CANVAS — cor, raio e traco de um no do grafo
 *
 * Modulo PURO: nenhum React, nenhum estado. Ele so sabe transformar um no em
 * pixel. Quem decide QUAIS nos estao acesos e o `GrafoDaMemoria`; aqui mora a
 * gramatica visual, que e a aplicacao do `DESIGN.md` ao bitmap.
 * =============================================================================
 */

import type { NoDoGrafo, TipoDeNo } from "@/lib/api";

/**
 * O no COM as coordenadas que a simulacao escreve nele.
 *
 * `NoDoGrafo` e o contrato da API, e a API nao manda posicao -- quem cria `x`
 * e `y` e o force-graph, mutando o objeto durante a simulacao. Declarar isso
 * aqui, e nao no tipo da API, mantem honesto o que o servidor de fato devolve.
 */
export type NoPosicionado = NoDoGrafo & { x?: number; y?: number };

/**
 * Acima da linha o que foi DITO, abaixo o que foi MEDIDO (DESIGN.md secao 1).
 *
 * Num grafo nao ha "acima" e "abaixo" geometricos -- a simulacao coloca o no
 * onde a fisica manda. Entao a regra que aqui sobrevive e a CROMATICA. Ela
 * deixou de ser "ambar contra azul" e passou a ser QUENTE contra FRIO: a
 * familia continua dizendo dito/medido a distancia, e o matiz dentro da
 * familia diz o TIPO. Duas cores nao davam conta de nove tipos -- `categoria`,
 * `canal`, `fonte` e `feature` saiam todas do mesmo azul, e a tela nao
 * distinguia o eixo aprendido pelo fusor de um canal de atendimento.
 *
 * Esta lista sobrevive porque a FICHA e a lista ainda falam em dito/medido, e
 * porque a familia precisa de uma definicao unica -- deduzi-la do matiz seria
 * espalhar a regra por dois lugares.
 */
const DITO: TipoDeNo[] = ["conversa", "termo", "emoji"];

/**
 * O token de cor de cada tipo de no.
 *
 * `Record` completo, e nao um mapa com padrao: se um tipo novo nascer na API,
 * o TypeScript para o build aqui em vez de deixar o no aparecer cinza na tela
 * sem ninguem perceber. Cor faltando e um tipo que ninguem decidiu como ler.
 */
const TOKEN_DO_TIPO: Record<TipoDeNo, string> = {
  conversa: "--no-conversa",
  termo: "--no-termo",
  emoji: "--no-emoji",
  feature: "--no-feature",
  categoria: "--no-categoria",
  canal: "--no-canal",
  desfecho: "--no-desfecho",
  fonte: "--no-fonte",
  importacao: "--no-importacao",
};

/** Os tipos na ordem em que a legenda os apresenta: dito primeiro, medido depois. */
export const TIPOS_NA_LEGENDA: TipoDeNo[] = [
  "conversa",
  "termo",
  "emoji",
  "feature",
  "categoria",
  "canal",
  "desfecho",
  "fonte",
  "importacao",
];

/**
 * Os tokens do `globals.css` resolvidos em string que o canvas entende.
 *
 * O canvas nao expande `var(--dito)`: ele recebe uma cor literal. Ler o token
 * computado no `:root` em vez de copiar o valor para ca e o que impede a
 * paleta de envelhecer separada do design system -- trocar o ambar no CSS
 * troca o ambar do grafo, sem ninguem lembrar deste arquivo.
 */
export type Paleta = {
  dito: string;
  medido: string;
  /** A cor resolvida de CADA tipo de no -- e daqui que o canvas pinta. */
  porTipo: Record<TipoDeNo, string>;
  linha: string;
  rotulo: string;
  fundo: string;
  selecao: string;
};

/** Paleta neutra do SSR, onde nao existe `document`. Nunca chega a pintar. */
const PALETA_VAZIA: Paleta = {
  dito: "transparent",
  medido: "transparent",
  porTipo: Object.fromEntries(
    TIPOS_NA_LEGENDA.map((tipo) => [tipo, "transparent"]),
  ) as Record<TipoDeNo, string>,
  linha: "transparent",
  rotulo: "transparent",
  fundo: "transparent",
  selecao: "transparent",
};

let paletaEmCache: Paleta | null = null;

/**
 * A paleta, lida do CSS na primeira chamada e guardada dali em diante.
 *
 * Cache no modulo, e nao estado do React, porque o tema e escuro UNICO: os
 * tokens nao mudam durante a vida da pagina. Assim quem pinta um quadro
 * apenas chama isto -- sem `getComputedStyle` por no por quadro (refluxo
 * forcado sessenta vezes por segundo) e sem um `useEffect` que exista so
 * para copiar CSS para dentro do React.
 */
export function paletaAtual(): Paleta {
  if (typeof document === "undefined") return PALETA_VAZIA;
  paletaEmCache ??= lerPaleta();
  return paletaEmCache;
}

function lerPaleta(): Paleta {
  const raiz = getComputedStyle(document.documentElement);
  const token = (nome: string) => raiz.getPropertyValue(nome).trim();
  return {
    dito: token("--dito"),
    medido: token("--medido"),
    porTipo: Object.fromEntries(
      TIPOS_NA_LEGENDA.map((tipo) => [tipo, token(TOKEN_DO_TIPO[tipo])]),
    ) as Record<TipoDeNo, string>,
    // A aresta e ESTRUTURA, nao dado: ela usa a regua do sistema e nao gasta
    // um canal de cor proprio. Duas vozes na tela ja sao as duas que existem.
    linha: token("--linha"),
    // `--muted-foreground` e o piso de cor de texto (DESIGN.md 3.1): rotulo de
    // no e legenda, e legenda nao pode competir com o dado que ela nomeia.
    rotulo: token("--muted-foreground"),
    fundo: token("--background"),
    // O anel de selecao e a UNICA aparicao de `--primary` aqui, e ela e legal
    // porque nao codifica valor nenhum: e o cursor de leitura do grafo, a
    // excecao nomeada em DESIGN.md 3.3. Nenhuma serie usa dourado.
    selecao: token("--primary"),
  };
}

/**
 * A cor de um no: uma por TIPO, dentro da familia quente/fria do dito/medido.
 *
 * O esboco do brief pedia um `temaClaro: boolean` -- ele nao entrou porque o
 * tema e escuro UNICO (DESIGN.md), e parametro que so aceita um valor e
 * mentira sobre a variacao que existe. O que de fato varia e a paleta, e ela
 * entra explicita.
 *
 * O fallback para dito/medido nao e defensivo a toa: `paletaAtual()` devolve a
 * paleta VAZIA no SSR, e um tipo que a API inventar depois de um deploy
 * chegaria aqui sem token. Cair na familia certa e melhor que pintar de
 * `undefined` -- que no canvas e silenciosamente preto sobre fundo preto.
 */
export function corDoNo(no: NoDoGrafo, paleta: Paleta): string {
  return (
    paleta.porTipo[no.tipo] ||
    (DITO.includes(no.tipo) ? paleta.dito : paleta.medido)
  );
}

/** Se o tipo pertence a familia do que foi DITO. A legenda agrupa por isto. */
export function eDito(tipo: TipoDeNo): boolean {
  return DITO.includes(tipo);
}

/**
 * Raio pelo GRAU, nunca pelo score.
 *
 * Mapear score -> tamanho faria o no "sem sinal" encolher ate sumir, que e
 * violar por via visual a invariante que a cabeca vazada existe para honrar.
 * Tamanho e conectividade; o veredito mora no preenchimento.
 *
 * A raiz quadrada porque o grau tem cauda longa -- um `canal` com mil arestas
 * ao lado de um `termo` com tres viraria um disco cobrindo a vizinhanca. O
 * teto em 5 fecha a cauda; abaixo dele a diferenca continua legivel.
 */
export function raioDoNo(no: NoDoGrafo): number {
  return 3 + Math.min(Math.sqrt(no.grau), 5);
}

/**
 * O navegador entende `color-mix` no canvas? Testado uma vez, no modulo.
 *
 * O parser de cor do canvas e o mesmo do CSS, entao a checagem vale para a
 * pagina inteira -- e ela e barata o suficiente para ser feita na importacao
 * e cara demais para ser feita por aresta por quadro.
 */
const SUPORTA_COLOR_MIX = (() => {
  if (typeof document === "undefined") return false;
  const ctx = document.createElement("canvas").getContext("2d");
  if (!ctx) return false;
  ctx.fillStyle = "#000000";
  ctx.fillStyle = "color-mix(in oklch, white 50%, transparent)";
  return ctx.fillStyle !== "#000000";
})();

/**
 * Modula a opacidade de uma cor ja resolvida.
 *
 * `color-mix` porque os tokens sao OKLCH e alguns ja carregam alfa proprio
 * (`--linha` e branco a 24%): reescrever isso na mao exigiria parsear cor, e
 * o navegador ja sabe fazer. Se ele nao souber, devolve a cor intacta -- uma
 * aresta opaca demais e pior que nada, mas invisivel e pior ainda.
 */
export function comOpacidade(cor: string, opacidade: number): string {
  if (!SUPORTA_COLOR_MIX) return cor;
  const porcento = Math.round(Math.max(0, Math.min(1, opacidade)) * 100);
  return `color-mix(in oklch, ${cor} ${porcento}%, transparent)`;
}

/** O rotulo so aparece a partir deste zoom. Ver `desenharNo`. */
const ZOOM_DO_ROTULO = 1.5;

/** Rotulo comprido vira faixa de texto atravessando o grafo. */
function encurtar(rotulo: string): string {
  return rotulo.length > 22 ? `${rotulo.slice(0, 21)}…` : rotulo;
}

/**
 * Desenha um no. Conversa SEM SINAL sai vazada -- so o contorno.
 *
 * E a mesma forma que a linha do tempo usa: a regra "ausencia de dado nao e
 * insatisfacao" deixa de ser nota de rodape e vira notacao. O marcador
 * existe, ocupa a posicao, e e oco.
 *
 * O contorno mantem a cor do tipo (ambar, porque conversa e fala) em vez de
 * virar cinza: neste canvas a cor codifica dito/medido, e so isso. Trocar o
 * matiz aqui faria o vazio parecer uma terceira voz, quando o que ele diz e
 * exatamente "esta voz nao foi medida".
 */
export function desenharNo(
  no: NoPosicionado,
  ctx: CanvasRenderingContext2D,
  escala: number,
  opacidade: number,
  selecionado: boolean,
  paleta: Paleta,
): void {
  const x = no.x ?? 0;
  const y = no.y ?? 0;
  const raio = raioDoNo(no);
  const cor = corDoNo(no, paleta);

  ctx.globalAlpha = opacidade;

  // O anel de selecao vem ANTES do no, por fora dele: assim ele nao engorda o
  // marcador (o raio e informacao) nem tapa o miolo vazado do "sem sinal".
  if (selecionado) {
    ctx.beginPath();
    ctx.arc(x, y, raio + 3, 0, 2 * Math.PI);
    ctx.strokeStyle = paleta.selecao;
    ctx.lineWidth = 1.5 / escala;
    ctx.stroke();
  }

  ctx.beginPath();
  ctx.arc(x, y, raio, 0, 2 * Math.PI);

  if (no.sem_sinal) {
    // O contorno e mais grosso que o do anel para o oco nao parecer defeito de
    // renderizacao a zoom baixo -- vazio de proposito precisa parecer proposito.
    ctx.strokeStyle = cor;
    ctx.lineWidth = 1.6 / escala;
    ctx.stroke();
  } else {
    ctx.fillStyle = cor;
    ctx.fill();
  }

  // Label so com zoom: em milhares de nos, texto sempre visivel e mancha.
  if (escala > ZOOM_DO_ROTULO) {
    // Tamanho em coordenadas do MUNDO dividido pela escala = tamanho constante
    // na tela. Sem isso o rotulo cresce junto com o zoom e vira cartaz.
    // A pilha literal, e nao `var(--fonte-sans)`: `ctx.font` nao expande
    // custom property e uma string invalida e descartada em silencio, deixando
    // o rotulo na fonte serifada padrao do canvas. Mesma familia do CSS.
    const corpo = 10 / escala;
    ctx.font = `${corpo}px ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    const texto = encurtar(no.rotulo);
    const base = y + raio + 3 / escala;
    // Halo na cor do papel: sem ele o rotulo cai por cima das arestas e fica
    // ilegivel justamente na regiao densa, que e onde alguem deu zoom.
    ctx.lineWidth = 3 / escala;
    ctx.strokeStyle = paleta.fundo;
    ctx.lineJoin = "round";
    ctx.strokeText(texto, x, base);
    ctx.fillStyle = selecionado ? cor : paleta.rotulo;
    ctx.fillText(texto, x, base);
  }

  ctx.globalAlpha = 1;
}

/**
 * A area clicavel do no, pintada no canvas invisivel de hit-test.
 *
 * Ela e maior que o desenho de proposito: acertar um disco de 3px com o mouse
 * e trabalho, e o no "sem sinal" e oco -- sem esta area o vazado teria buraco
 * tambem no alvo, e o marcador que existe para ser notado seria o unico
 * impossivel de clicar.
 */
export function pintarAreaDoNo(
  no: NoPosicionado,
  cor: string,
  ctx: CanvasRenderingContext2D,
): void {
  ctx.fillStyle = cor;
  ctx.beginPath();
  ctx.arc(no.x ?? 0, no.y ?? 0, raioDoNo(no) + 3, 0, 2 * Math.PI);
  ctx.fill();
}

/**
 * A espessura da aresta pelo peso, com teto baixo.
 *
 * Aresta e sintaxe, nao dado: ela diz que existe ligacao, e o peso so
 * sussurra quanto. Passando de ~1.5px o traco compete com o no e o grafo vira
 * emaranhado de fios em vez de nuvem de pontos.
 */
export function espessuraDaAresta(peso: number): number {
  return Math.min(0.4 + peso * 0.2, 1.6);
}
