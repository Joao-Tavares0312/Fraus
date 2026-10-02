/**
 * Derivacoes feitas no cliente da API a partir do que os endpoints DAO.
 *
 * A API do Fraus expoe indicadores agregados, a lista de conversas, a
 * transcricao, a atribuicao por sentenca e a SERIE TEMPORAL diaria. Ela nao
 * expoe lexico por classe nem latencia agregada fora da serie. O que este
 * arquivo ainda calcula sai
 * dos timestamps e do texto que a transcricao ja entrega -- nada aqui inventa
 * numero. O que nao da para derivar honestamente nao esta aqui: esta como
 * estado vazio na interface, nomeando o endpoint que resolveria.
 *
 * A atribuicao por sentenca NAO e derivada aqui: ela vem pronta de
 * `GET /conversas/{id}/atribuicao`. As funcoes desta secao so dao FORMA ao
 * que o servidor mandou (classe dominante, saldo, agregacao por sinal).
 *
 * A regra de latencia e a MESMA de `fraus/sinais/tempo.py`: o intervalo de
 * cada mensagem do cliente ate a proxima resposta (bot ou humano).
 */

import { diaDoProduto } from "./fuso";
import lexicoEmoji from "./lexicoEmoji.json";
import type {
  Categoria,
  DetalheConversa,
  IntervaloNps,
  Mensagem,
  MensagemAtribuida,
  PontoSerieApi,
  ResumoConversa,
} from "./api";

const RESPONDENTES = new Set(["bot", "humano"]);
const POLARIDADE: Record<string, number> = lexicoEmoji;

// ---------------------------------------------------------------------------
// Faixas de NPS (0-6 detrator, 7-8 neutro, 9-10 promotor)
// ---------------------------------------------------------------------------

export const FAIXAS_NPS = [
  { categoria: "detrator" as Categoria, de: 0, ate: 6, rotulo: "0–6 detrator" },
  { categoria: "neutro" as Categoria, de: 7, ate: 8, rotulo: "7–8 neutro" },
  { categoria: "promotor" as Categoria, de: 9, ate: 10, rotulo: "9–10 promotor" },
];

/**
 * Nota a partir da qual o atendimento conta como satisfeito no CSAT. E a mesma
 * constante do servidor (`fraus.indicadores.NOTA_MINIMA_SATISFEITO`) e NAO
 * depende da faixa de NPS configurada -- `calcular_csat` conta nota >= 7
 * qualquer que seja o corte de detrator.
 */
export const NOTA_MINIMA_SATISFEITO = 7;

/** Faixa saudavel de referencia do CSAT, em pontos percentuais. */
export const CSAT_SAUDAVEL = { de: 75, ate: 85 };

/*
 * NAO existe aqui uma funcao `notaDeScore`. A nota 0-10 e derivada NO SERVIDOR
 * (`fraus/indicadores.py::nota_0_10`) e vem pronta em `/conversas` e em
 * `/conversas/{id}`. Recalcular no cliente ja custou uma divergencia real:
 * `round` do Python e bancario (`round(6.5) == 6`) e `Math.round` arredonda
 * meio para cima (`Math.round(6.5) == 7`), entao score 65 exibia nota 7 na
 * mesma linha em que a categoria dizia "Detrator". Uma fonte so.
 */

/**
 * Categoria de uma nota SEGUNDO AS FAIXAS VIGENTES.
 *
 * As faixas chegam por parametro, exatamente como no servidor: a invariante 4
 * diz que a faixa vigente e passada para `categoria_nps`/`calcular_nps`, nunca
 * lida de estado global nem digitada de novo em outro lugar. Ate 03/09/2026
 * esta funcao tinha `nota <= 6` e `nota <= 8` escritos no corpo, e isso valia
 * no caminho FELIZ -- entao um operador que movesse as faixas em Configuracoes
 * fazia a mesma tela dar dois vereditos para o mesmo atendimento: a etiqueta da
 * linha vinha do servidor, com as faixas novas, e a cor da barra vinha daqui,
 * com as antigas.
 *
 * `FAIXAS_NPS` continua existindo como PADRAO DE FABRICA, e e o que sobra
 * quando `GET /configuracoes` falha -- e o mesmo padrao do resto da tela:
 * degradar para o de fabrica declarado, nunca para um numero inventado.
 */
export function categoriaDaNota(
  nota: number,
  faixas?: Record<string, [number, number]>,
): Categoria {
  if (faixas) {
    for (const [categoria, [de, ate]] of Object.entries(faixas)) {
      if (nota >= de && nota <= ate) return categoria as Categoria;
    }
  }
  const fabrica = FAIXAS_NPS.find(({ de, ate }) => nota >= de && nota <= ate);
  return fabrica?.categoria ?? "detrator";
}

/**
 * A legenda das tres faixas, escrita a partir das FAIXAS VIGENTES.
 *
 * A legenda da distribuicao era uma constante local "0–6 detrator · 7–8 neutro
 * · 9–10 promotor" embaixo de barras coloridas pelas faixas vigentes: bastava
 * o operador mover um corte em Configuracoes para o grafico pintar a nota 7 de
 * detrator e a legenda logo abaixo dizer que 7 e neutro. Invariante 4: a faixa
 * nunca e digitada de novo.
 *
 * Sem faixas (`GET /configuracoes` falhou) sobra o padrao de fabrica DECLARADO
 * -- o mesmo criterio de `categoriaDaNota`, que e quem pinta as barras, entao
 * legenda e cor continuam dizendo a mesma coisa tambem na falha. Categoria que
 * a resposta nao trouxe fica sem numero: escrever o corte de fabrica ali seria
 * inventar uma faixa que ninguem confirmou.
 */
export function legendaDasFaixas(
  faixas?: Record<string, [number, number]>,
): { categoria: Categoria; rotulo: string }[] {
  if (!faixas) {
    return FAIXAS_NPS.map(({ categoria, rotulo }) => ({ categoria, rotulo }));
  }
  return FAIXAS_NPS.map(({ categoria }) => {
    const faixa = faixas[categoria];
    if (!faixa) return { categoria, rotulo: categoria };
    const [de, ate] = faixa;
    return {
      categoria,
      rotulo: `${de === ate ? de : `${de}–${ate}`} ${categoria}`,
    };
  });
}

export function npsDeCategorias(categorias: Categoria[]): number | null {
  if (categorias.length === 0) return null;
  const promotores = categorias.filter((c) => c === "promotor").length;
  const detratores = categorias.filter((c) => c === "detrator").length;
  return (100 * (promotores - detratores)) / categorias.length;
}

// ---------------------------------------------------------------------------
// Estatistica minima
// ---------------------------------------------------------------------------

export function mediana(valores: number[]): number | null {
  if (valores.length === 0) return null;
  const ordenados = [...valores].sort((a, b) => a - b);
  const meio = Math.floor(ordenados.length / 2);
  return ordenados.length % 2 === 1
    ? ordenados[meio]
    : (ordenados[meio - 1] + ordenados[meio]) / 2;
}

// ---------------------------------------------------------------------------
// Latencia por mensagem
// ---------------------------------------------------------------------------

export type LatenciaAnotada = {
  /** Indice da mensagem RESPONDENTE dentro de `mensagens`. */
  indice: number;
  segundos: number;
};

export function latenciasAnotadas(mensagens: Mensagem[]): LatenciaAnotada[] {
  const anotadas: LatenciaAnotada[] = [];
  for (let i = 0; i < mensagens.length; i += 1) {
    if (mensagens[i].autor !== "cliente") continue;
    for (let j = i + 1; j < mensagens.length; j += 1) {
      if (!RESPONDENTES.has(mensagens[j].autor)) continue;
      const segundos =
        (new Date(mensagens[j].enviada_em).getTime() -
          new Date(mensagens[i].enviada_em).getTime()) /
        1000;
      anotadas.push({ indice: j, segundos });
      break;
    }
  }
  return anotadas;
}

export function latenciaMediana(mensagens: Mensagem[]): number | null {
  return mediana(latenciasAnotadas(mensagens).map((l) => l.segundos));
}

/**
 * Limiares de latencia, em segundos, calibrados pela literatura de live chat
 * que a propria tela cita.
 *
 * ELES VEM DA API (`GET /configuracoes` -> `limiares_latencia_s`), nao de
 * constante do front: a tela de Configuracoes deixa mexer neles, e um controle
 * que nao chega a lugar nenhum e exatamente o que este projeto nao aceita. O
 * objeto abaixo e so o PADRAO DE FABRICA, o mesmo de
 * `fraus/configuracao.py::LIMIARES_LATENCIA_PADRAO`, usado quando a leitura da
 * configuracao falha -- caso em que a propria tela ja mostra a API fora do ar.
 */
export type LimiaresLatencia = {
  /** Ate aqui a satisfacao esta no pico observado (~84,7% de CSAT). */
  pico: number;
  /** Ate aqui a espera ainda e saudavel. */
  saudavel: number;
  /** Ate aqui a satisfacao degrada: -2 a -3 pontos de CSAT por minuto extra. */
  degradando: number;
};

export const LIMIARES_LATENCIA_PADRAO: LimiaresLatencia = {
  pico: 10,
  saudavel: 60,
  degradando: 180,
};

/**
 * Converte `limiares_latencia_s` (a lista de tres da API) nos tres nomes que a
 * interface usa. Lista de tamanho errado nao existe -- o servidor recusa antes
 * de gravar -- mas a leitura cai no padrao em vez de estourar em runtime.
 */
export function limiaresDe(
  limiares: number[] | undefined | null,
): LimiaresLatencia {
  if (!limiares || limiares.length !== 3) return LIMIARES_LATENCIA_PADRAO;
  const [pico, saudavel, degradando] = limiares;
  return { pico, saudavel, degradando };
}

/** Minutos com no maximo uma casa: 180 s vira "3", 90 s vira "1,5". */
export function emMinutos(segundos: number): string {
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(
    segundos / 60,
  );
}

/**
 * Faixa de severidade da espera.
 *
 * "critica" comeca em 3 MINUTOS, nao em 1: a fonte de live chat atribui o
 * abandono (57% dos clientes) a espera acima de tres minutos, e a perda por
 * minuto extra e de 2 a 3 pontos de CSAT. Atribuir 1 minuto ao abandono seria
 * erro factual numa tela que cita a fonte.
 */
export type SeveridadeLatencia = "pico" | "saudavel" | "degradando" | "abandono";

export function severidadeLatencia(
  segundos: number,
  limiares: LimiaresLatencia,
): SeveridadeLatencia {
  if (segundos <= limiares.pico) return "pico";
  if (segundos <= limiares.saudavel) return "saudavel";
  if (segundos <= limiares.degradando) return "degradando";
  return "abandono";
}

/**
 * Rotulo e justificativa de cada faixa, montados a partir dos limiares
 * VIGENTES. Uma fonte so: se o operador mudar o corte, o texto que cita o
 * numero muda junto -- rotulo e limiar nao podem divergir.
 *
 * As porcentagens citadas (84,7% de CSAT no pico, 57% de abandono) sao da
 * literatura e ficam ancoradas ao limiar DE FABRICA. Quando os cortes saem do
 * padrao, a tela para de atribuir a medida da literatura ao corte novo.
 */
export function rotulosLatencia(
  limiares: LimiaresLatencia,
): Record<SeveridadeLatencia, { titulo: string; detalhe: string }> {
  const padrao =
    limiares.pico === LIMIARES_LATENCIA_PADRAO.pico &&
    limiares.saudavel === LIMIARES_LATENCIA_PADRAO.saudavel &&
    limiares.degradando === LIMIARES_LATENCIA_PADRAO.degradando;

  return {
    pico: {
      titulo: "Resposta imediata",
      detalhe: padrao
        ? `até ${limiares.pico} s — pico de satisfação na literatura de live chat (CSAT ~84,7%)`
        : `até ${limiares.pico} s — corte configurado em Configurações`,
    },
    saudavel: {
      titulo: "Espera saudável",
      detalhe: `entre ${limiares.pico} s e ${limiares.saudavel} s — fora do pico, ainda dentro do saudável`,
    },
    degradando: {
      titulo: "Espera longa",
      detalhe: padrao
        ? `entre ${limiares.saudavel} s e ${emMinutos(limiares.degradando)} min — a satisfação degrada de 2 a 3 pontos de CSAT por minuto extra`
        : `entre ${limiares.saudavel} s e ${emMinutos(limiares.degradando)} min — corte configurado em Configurações`,
    },
    abandono: {
      titulo: "Espera crítica",
      detalhe: padrao
        ? `acima de ${emMinutos(limiares.degradando)} min — faixa de abandono: 57% dos clientes desistem`
        : `acima de ${emMinutos(limiares.degradando)} min — corte configurado em Configurações`,
    },
  };
}

// ---------------------------------------------------------------------------
// Serie temporal diaria (NPS inferido x latencia mediana)
// ---------------------------------------------------------------------------

export type PontoSerie = {
  dia: string; // AAAA-MM-DD
  rotulo: string; // DD/MM
  nps: number | null;
  latenciaMediana: number | null;
  atendimentos: number;
  comScore: number;
};

/**
 * Da forma de grafico ao que `GET /serie-temporal` ja agregou.
 *
 * NAO recalcula nada: o NPS e a latencia vem do servidor, pelas mesmas
 * funcoes Python que gravam a categoria. Aqui so entra o rotulo DD/MM, que e
 * apresentacao e nao pertence a API.
 */
export function serieDoServidor(pontos: PontoSerieApi[]): PontoSerie[] {
  return pontos.map((ponto) => {
    const [, mes, numero] = ponto.dia.split("-");
    return {
      dia: ponto.dia,
      rotulo: `${numero}/${mes}`,
      nps: ponto.nps,
      latenciaMediana: ponto.latencia_mediana_s,
      atendimentos: ponto.atendimentos,
      comScore: ponto.com_score,
    };
  });
}

/**
 * Mesma serie, derivada das transcricoes.
 *
 * Sobrevive como PLANO B de `serieDoServidor`: se `/serie-temporal` falhar, o
 * grafico continua de pe com o que a pagina ja baixou, em vez de sumir.
 */
export function serieDiaria(detalhes: DetalheConversa[]): PontoSerie[] {
  const porDia = new Map<
    string,
    { categorias: Categoria[]; latencias: number[]; atendimentos: number }
  >();

  for (const conversa of detalhes) {
    const dia = diaDoProduto(conversa.iniciada_em);
    const balde =
      porDia.get(dia) ?? { categorias: [], latencias: [], atendimentos: 0 };
    balde.atendimentos += 1;
    if (conversa.categoria) balde.categorias.push(conversa.categoria);
    const latencia = latenciaMediana(conversa.mensagens);
    if (latencia !== null) balde.latencias.push(latencia);
    porDia.set(dia, balde);
  }

  return [...porDia.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([dia, balde]): PontoSerie => {
      const [, mes, numero] = dia.split("-");
      return {
        dia,
        rotulo: `${numero}/${mes}`,
        nps: npsDeCategorias(balde.categorias),
        latenciaMediana: mediana(balde.latencias),
        atendimentos: balde.atendimentos,
        comScore: balde.categorias.length,
      };
    });
}

// ---------------------------------------------------------------------------
// Distribuicao de notas
// ---------------------------------------------------------------------------

export type BarraDistribuicao = {
  nota: number;
  rotulo: string;
  categoria: Categoria;
  quantidade: number;
};

export function distribuicaoDeNotas(
  resumos: ResumoConversa[],
  faixas?: Record<string, [number, number]>,
): {
  barras: BarraDistribuicao[];
  semSinal: number;
} {
  const contagem = new Array(11).fill(0) as number[];
  let semSinal = 0;

  for (const resumo of resumos) {
    if (resumo.nota === null) {
      semSinal += 1;
      continue;
    }
    contagem[Math.min(10, Math.max(0, resumo.nota))] += 1;
  }

  return {
    barras: contagem.map((quantidade, nota) => ({
      nota,
      rotulo: String(nota),
      categoria: categoriaDaNota(nota, faixas),
      quantidade,
    })),
    semSinal,
  };
}

// ---------------------------------------------------------------------------
// Lexico por classe: palavras e emojis
// ---------------------------------------------------------------------------

const PARADAS = new Set([
  "que", "para", "com", "uma", "por", "mais", "isso", "mas", "voce", "voces",
  "nao", "sim", "dos", "das", "aos", "sem", "sou", "esta", "estou", "meu",
  "minha", "seu", "sua", "ele", "ela", "eles", "elas", "como", "quando",
  "onde", "aqui", "ali", "esse", "essa", "este", "esta", "aquele", "aquela",
  "tem", "ter", "foi", "sao", "era", "vai", "vou", "ja", "ate", "pra", "pro",
  "the", "and", "num", "numa", "nos", "nas", "lhe", "ser", "fica", "faz",
  "muito", "todo", "toda", "todos", "todas", "outro", "outra", "entao",
  "porque", "pois", "quero", "queria", "preciso", "sobre", "depois", "antes",
]);

function normalizar(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

function palavras(texto: string): string[] {
  return normalizar(texto)
    .split(/[^a-z0-9]+/)
    .filter((palavra) => palavra.length >= 3 && !PARADAS.has(palavra));
}

const REGEX_EMOJI = /\p{Extended_Pictographic}/u;
const SEGMENTADOR = new Intl.Segmenter("pt-BR", { granularity: "grapheme" });

/**
 * Extrai emojis do texto recortando por CLUSTER DE GRAFEMA, nao por codepoint.
 *
 * E o mesmo recorte de `emoji.emoji_list` em `fraus/sinais/emoji.py`: 👍🏽
 * (com modificador de tom de pele) e 👨‍👩‍👧 (sequencia ZWJ) contam como UM
 * emoji, e nao como os 2-3 codepoints pictograficos que os compoem. Sem isso
 * a contagem de "top emojis" e a evidencia marcada divergiam do motor.
 */
export function emojisDoTexto(texto: string): string[] {
  const achados: string[] = [];
  for (const { segment } of SEGMENTADOR.segment(texto)) {
    if (REGEX_EMOJI.test(segment)) achados.push(segment);
  }
  return achados;
}

/**
 * Polaridade do emoji no Emoji Sentiment Ranking, a MESMA tabela que
 * `fraus/sinais/emoji.py` usa (exportada por `scripts/gerar_lexico_emoji.py`).
 *
 * Isto e exibicao de uma tabela publicada, nao atribuicao: quem diz o que
 * puxou a nota de um atendimento e `GET /conversas/{id}/atribuicao`.
 *
 * `null` quando o emoji NAO ESTA na tabela -- e ela e de 2015, entao isso e
 * comum (todo emoji mais novo que ela). Ate 02/10/2026 a falta virava 0, e a
 * tela escrevia "polaridade 0.00 no Emoji Sentiment Ranking": afirmava uma
 * neutralidade medida para um emoji que o ranking nunca viu. Ausencia nao e
 * zero (invariante 2); o zero de verdade existe na tabela e continua zero.
 */
export function polaridadeDoEmoji(emoji: string): number | null {
  return Object.hasOwn(POLARIDADE, emoji) ? POLARIDADE[emoji] : null;
}

export type TermoDaClasse = {
  termo: string;
  ocorrencias: number;
  /** Quanto o termo e mais frequente NESTA classe do que no resto, em [-1, 1]. */
  distincao: number;
};

export type LexicoDaClasse = {
  categoria: Categoria;
  atendimentos: number;
  palavras: TermoDaClasse[];
  emojis: TermoDaClasse[];
};

function ranquear(
  porClasse: Map<Categoria, Map<string, number>>,
  categoria: Categoria,
  limite: number,
): TermoDaClasse[] {
  const daClasse = porClasse.get(categoria) ?? new Map<string, number>();
  const totalDaClasse = [...daClasse.values()].reduce((a, b) => a + b, 0);
  if (totalDaClasse === 0) return [];

  const outras = new Map<string, number>();
  let totalOutras = 0;
  for (const [outraCategoria, tabela] of porClasse) {
    if (outraCategoria === categoria) continue;
    for (const [termo, quantidade] of tabela) {
      outras.set(termo, (outras.get(termo) ?? 0) + quantidade);
      totalOutras += quantidade;
    }
  }

  return [...daClasse.entries()]
    .map(([termo, ocorrencias]) => {
      const pClasse = ocorrencias / totalDaClasse;
      const pOutras = totalOutras === 0 ? 0 : (outras.get(termo) ?? 0) / totalOutras;
      return { termo, ocorrencias, distincao: pClasse - pOutras };
    })
    .sort((a, b) => b.distincao - a.distincao || b.ocorrencias - a.ocorrencias)
    .slice(0, limite);
}

/**
 * Conta palavras e emojis das falas DO CLIENTE, agrupadas pela categoria que o
 * servidor atribuiu ao atendimento. Conversa sem score nao entra em classe
 * nenhuma -- ausencia de dado nao e uma quarta classe.
 */
export function lexicoPorClasse(detalhes: DetalheConversa[]): LexicoDaClasse[] {
  const palavrasPorClasse = new Map<Categoria, Map<string, number>>();
  const emojisPorClasse = new Map<Categoria, Map<string, number>>();
  const atendimentos = new Map<Categoria, number>();

  for (const conversa of detalhes) {
    const categoria = conversa.categoria;
    if (!categoria) continue;
    atendimentos.set(categoria, (atendimentos.get(categoria) ?? 0) + 1);

    const tabelaPalavras =
      palavrasPorClasse.get(categoria) ?? new Map<string, number>();
    const tabelaEmojis = emojisPorClasse.get(categoria) ?? new Map<string, number>();

    for (const mensagem of conversa.mensagens) {
      if (mensagem.autor !== "cliente") continue;
      for (const palavra of palavras(mensagem.texto)) {
        tabelaPalavras.set(palavra, (tabelaPalavras.get(palavra) ?? 0) + 1);
      }
      for (const emoji of emojisDoTexto(mensagem.texto)) {
        tabelaEmojis.set(emoji, (tabelaEmojis.get(emoji) ?? 0) + 1);
      }
    }

    palavrasPorClasse.set(categoria, tabelaPalavras);
    emojisPorClasse.set(categoria, tabelaEmojis);
  }

  return FAIXAS_NPS.map(({ categoria }) => ({
    categoria,
    atendimentos: atendimentos.get(categoria) ?? 0,
    palavras: ranquear(palavrasPorClasse, categoria, 6),
    emojis: ranquear(emojisPorClasse, categoria, 6),
  }));
}

// ---------------------------------------------------------------------------
// Atribuicao por sentenca (vem do servidor, nao e derivada aqui)
// ---------------------------------------------------------------------------

export type SentidoAtribuicao =
  | "puxou_para_baixo"
  | "puxou_para_cima"
  | "sem_inclinacao";

export type MarcaAtribuicao = {
  /** Indice da mensagem dentro de `conversa.mensagens`. */
  indice: number;
  sentido: SentidoAtribuicao;
  /** Classe mais provavel segundo o classificador. */
  classe: "insatisfeito" | "neutro" | "satisfeito";
  /** Probabilidade da classe mais provavel, em [0, 1]. */
  probabilidade: number;
  /** P(satisfeito) - P(insatisfeito): positivo puxa a nota para cima. */
  saldo: number;
  probInsatisfeito: number;
  probNeutro: number;
  probSatisfeito: number;
};

/**
 * A partir de qual saldo a fala e apresentada como tendo puxado a nota.
 *
 * Abaixo disso o classificador esta praticamente indiferente entre as duas
 * pontas, e chamar a frase de "a que derrubou a nota" seria ler ruido como
 * causa.
 */
export const LIMIAR_SALDO = 0.15;

const CLASSES = ["insatisfeito", "neutro", "satisfeito"] as const;

/**
 * Converte `GET /conversas/{id}/atribuicao` nas marcas da transcricao.
 *
 * NADA aqui e heuristica local: as probabilidades sao as do BERTimbau, uma por
 * mensagem, calculadas no servidor. A versao anterior desta tela marcava os
 * trechos por polaridade de emoji e tempo de espera porque o endpoint nao
 * existia; agora existe, e manter as duas seria manter duas fontes de verdade
 * para a mesma pergunta ("o que puxou a nota"). A anotacao de latencia
 * continua onde estava -- ela responde outra pergunta ("quanto o cliente
 * esperou") e sai dos timestamps, nao do classificador.
 *
 * Mensagem de bot/humano vem com probabilidade nula do servidor e nao vira
 * marca: ausencia de dado nao e inclinacao nenhuma.
 */
export function marcasDaAtribuicao(
  mensagens: MensagemAtribuida[],
): Map<number, MarcaAtribuicao> {
  const marcas = new Map<number, MarcaAtribuicao>();

  for (const mensagem of mensagens) {
    const { prob_insatisfeito, prob_neutro, prob_satisfeito } = mensagem;
    if (
      prob_insatisfeito === null ||
      prob_neutro === null ||
      prob_satisfeito === null
    ) {
      continue;
    }

    const probabilidades = [prob_insatisfeito, prob_neutro, prob_satisfeito];
    let melhor = 0;
    probabilidades.forEach((valor, indice) => {
      if (valor > probabilidades[melhor]) melhor = indice;
    });

    const saldo = prob_satisfeito - prob_insatisfeito;
    marcas.set(mensagem.indice, {
      indice: mensagem.indice,
      sentido:
        saldo <= -LIMIAR_SALDO
          ? "puxou_para_baixo"
          : saldo >= LIMIAR_SALDO
            ? "puxou_para_cima"
            : "sem_inclinacao",
      classe: CLASSES[melhor],
      probabilidade: probabilidades[melhor],
      saldo,
      probInsatisfeito: prob_insatisfeito,
      probNeutro: prob_neutro,
      probSatisfeito: prob_satisfeito,
    });
  }

  return marcas;
}

/** As falas que de fato inclinaram a nota, da mais decisiva para a menos. */
export function falasDecisivas(
  marcas: Map<number, MarcaAtribuicao>,
): MarcaAtribuicao[] {
  return [...marcas.values()]
    .filter((marca) => marca.sentido !== "sem_inclinacao")
    .sort((a, b) => Math.abs(b.saldo) - Math.abs(a.saldo));
}

// ---------------------------------------------------------------------------
// Importancia das features do fusor
// ---------------------------------------------------------------------------

export type SinalDaFeature =
  | "texto"
  | "emoji"
  | "tempo"
  | "emocao"
  | "lexico"
  | "ironia"
  | "estilo"
  | "incongruencia"
  | "outros";

// Tempo NAO tem prefixo unico -- `latencia_`, `duracao_`, `qtd_`, `escalou` e
// `abandonou` sao os cinco prefixos da familia (ver
// tests/test_fusor.py::test_contrato_cobre_todos_os_prefixos_esperados no
// backend). As outras seis familias tem prefixo unico, listadas primeiro.
const SINAL_POR_PREFIXO: [string, SinalDaFeature][] = [
  ["texto_", "texto"],
  ["emoji_", "emoji"],
  ["emocao_", "emocao"],
  ["lexico_", "lexico"],
  ["ironia_", "ironia"],
  ["estilo_", "estilo"],
  ["incongruencia_", "incongruencia"],
  ["latencia_", "tempo"],
  ["duracao_", "tempo"],
  ["qtd_", "tempo"],
  ["escalou", "tempo"],
  ["abandonou", "tempo"],
];

/**
 * A qual das sete familias a feature pertence.
 *
 * Prefixo desconhecido vira "outros", NUNCA cai por fallback numa familia
 * real -- foi exatamente esse bug (tudo que nao fosse texto/emoji caia em
 * "tempo") que fez as 19 features novas de emocao/lexico/ironia/estilo se
 * misturarem no balde de tempo no grafico de pesos. Ver `ROTULO_SINAL.outros`.
 */
export function sinalDaFeature(nome: string): SinalDaFeature {
  for (const [prefixo, sinal] of SINAL_POR_PREFIXO) {
    if (nome.startsWith(prefixo)) return sinal;
  }
  return "outros";
}

export const ROTULO_SINAL: Record<SinalDaFeature, string> = {
  texto: "Texto",
  emoji: "Emoji",
  tempo: "Tempo",
  emocao: "Emoção",
  lexico: "Léxico",
  ironia: "Ironia",
  estilo: "Estilo",
  incongruencia: "Incongruência",
  outros: "Outros",
};

/** Ordem de exibicao das familias -- mesma ordem de `NOMES_FEATURES` no backend. */
export const ORDEM_SINAIS: SinalDaFeature[] = [
  "texto",
  "emoji",
  "tempo",
  "emocao",
  "lexico",
  "ironia",
  "estilo",
  "incongruencia",
  "outros",
];

export type PesoDoSinal = {
  sinal: SinalDaFeature;
  /** Soma dos pesos absolutos das features do sinal, normalizada em [0, 1]. */
  fracao: number;
};

/**
 * Agrega as 35 importancias do fusor nas SETE familias do trabalho.
 *
 * O peso e o coeficiente absoluto medio da regressao logistica -- e por isso
 * que o fusor e linear: a pergunta "qual sinal pesou mais" tem resposta.
 *
 * "outros" so aparece se `sinalDaFeature` devolver um prefixo desconhecido --
 * nao esperado num fusor treinado sobre `NOMES_FEATURES`, mas visivel em vez
 * de mudo se o contrato do backend mudar de novo sem o front acompanhar.
 *
 * FAMILIA SEM NENHUMA FEATURE NO VETOR E OMITIDA, nao listada com 0. A ironia
 * saiu do vetor em 04/09/2026 e a legenda continuou dizendo "Ironia · 0% do
 * peso total": zero e uma medida, e ela nao foi medida -- nao esta la. O
 * criterio e PRESENCA, nao soma: a familia que esta no vetor e cujos
 * coeficientes deram zero continua na legenda com 0%, porque esse zero o
 * modelo de fato aprendeu.
 */
export function pesoPorSinal(
  importancias: Record<string, number>,
): PesoDoSinal[] {
  // A chave so existe no mapa se a familia tem feature no vetor: e o `has`
  // dele que separa "pesou zero" de "nao esta la".
  const soma = new Map<SinalDaFeature, number>();
  let total = 0;

  for (const [nome, peso] of Object.entries(importancias)) {
    const sinal = sinalDaFeature(nome);
    const absoluto = Math.abs(peso);
    soma.set(sinal, (soma.get(sinal) ?? 0) + absoluto);
    total += absoluto;
  }

  return ORDEM_SINAIS.filter((sinal) => soma.has(sinal)).map((sinal) => ({
    sinal,
    fracao: total === 0 ? 0 : (soma.get(sinal) ?? 0) / total,
  }));
}

// ---------------------------------------------------------------------------
// Tempo mediano de resposta do conjunto
// ---------------------------------------------------------------------------

export function tempoMedianoDeResposta(detalhes: DetalheConversa[]): number | null {
  const todas = detalhes.flatMap((conversa) =>
    latenciasAnotadas(conversa.mensagens).map((l) => l.segundos),
  );
  return mediana(todas);
}

// ---------------------------------------------------------------------------
// Agregados do PERIODO
// ---------------------------------------------------------------------------

/**
 * Os quatro indicadores recortados por periodo.
 *
 * Existe porque a API nao aceita filtro de data em `/indicadores`: com um
 * periodo ativo, o numero do servidor responde a outra pergunta (o banco
 * inteiro) e exibi-lo ao lado de uma tabela recortada seria mentira.
 *
 * NADA aqui recalcula score, nota ou categoria -- invariante 3. O que se
 * agrega e a CATEGORIA que o servidor ja gravou:
 *   NPS  = %promotores - %detratores            (identico a calcular_nps)
 *   CSAT = %(nota >= 7)                          (identico a calcular_csat)
 *
 * O CSAT sai da NOTA, nao da categoria, e isso passou a importar quando as
 * faixas viraram configuraveis: `calcular_csat` no servidor conta nota >= 7 e
 * ignora a faixa vigente, entao contar "quem nao e detrator" divergiria do
 * numero do servidor no instante em que alguem movesse o corte de detrator.
 * A contencao sai de `escalou_para_humano`, que tambem vem do servidor.
 *
 * Sem nenhuma conversa no recorte, TODOS os campos vem null: agregado sem dado
 * e estado vazio, nunca zero. `containment` inclusive -- o servidor devolve
 * 0.0 para lista vazia, e propagar esse zero seria afirmar "nenhum atendimento
 * foi contido" onde nao houve atendimento nenhum.
 */
export type IndicadoresDoPeriodo = {
  nps: number | null;
  /**
   * Intervalo de confianca do NPS, quando o SERVIDOR o calcula. O plano B
   * deixa null de proposito: derivar intervalo no cliente duplicaria a regra
   * de N_MINIMO_NPS em TypeScript, que e exatamente a divergencia que a
   * invariante 3 existe para impedir.
   */
  npsIntervalo?: IntervaloNps | null;
  csat: number | null;
  containment: number | null;
  /**
   * Percentual dos atendimentos CONTIDOS que sairam detratores -- o sucesso
   * falso. null quando nenhum contido tem sinal: 0 se leria como "nenhum
   * contido saiu insatisfeito", que ninguem mediu.
   */
  falsoContainment: number | null;
  /** O denominador da fracao acima, para a tela poder dizer "3 de 12". */
  contidosComSinal: number;
  total: number;
  semSinal: number;
  /** Quantas conversas entraram nos calculos de NPS/CSAT (as com categoria). */
  comSinal: number;
};

export function indicadoresDoPeriodo(
  resumos: ResumoConversa[],
  detalhes: DetalheConversa[],
): IndicadoresDoPeriodo {
  const categorias = resumos
    .map((resumo) => resumo.categoria)
    .filter((categoria): categoria is Categoria => categoria !== null);

  const total = resumos.length;
  const semSinal = total - categorias.length;

  const notas = resumos
    .map((resumo) => resumo.nota)
    .filter((nota): nota is number => nota !== null);

  const csat =
    notas.length === 0
      ? null
      : (100 * notas.filter((nota) => nota >= NOTA_MINIMA_SATISFEITO).length) /
        notas.length;

  const containment =
    detalhes.length === 0
      ? null
      : (100 * detalhes.filter((d) => !d.escalou_para_humano).length) /
        detalhes.length;

  // Contido E com sinal: quem escalou nao foi contido, e quem nao tem
  // categoria nao e nem sucesso nem fracasso.
  const contidosComSinal = detalhes.filter(
    (d) => !d.escalou_para_humano && d.categoria !== null,
  );
  const falsoContainment =
    contidosComSinal.length === 0
      ? null
      : (100 *
          contidosComSinal.filter((d) => d.categoria === "detrator").length) /
        contidosComSinal.length;

  return {
    nps: npsDeCategorias(categorias),
    npsIntervalo: null,
    csat,
    containment,
    falsoContainment,
    contidosComSinal: contidosComSinal.length,
    total,
    semSinal,
    comSinal: categorias.length,
  };
}

/**
 * Os atendimentos que mais precisam de atencao no periodo.
 *
 * Conversa sem nota NAO entra: ordenar "os piores" jogando os mudos no topo
 * seria exatamente o `?? 0` que o produto combate. Elas aparecem contadas a
 * parte, como "sem sinal".
 */
export function pioresAtendimentos(
  resumos: ResumoConversa[],
  limite: number,
): ResumoConversa[] {
  return resumos
    .filter((resumo) => resumo.nota !== null)
    .sort((a, b) => (a.nota as number) - (b.nota as number))
    .slice(0, limite);
}

// ---------------------------------------------------------------------------
// Features do fusor: importancia GLOBAL x contribuicao DAQUELE atendimento
// ---------------------------------------------------------------------------

export type PesoDaFeature = {
  nome: string;
  rotulo: string;
  sinal: SinalDaFeature;
  valor: number;
  /** |valor| dividido pelo maior |valor| da lista -- largura da barra. */
  fracao: number;
};

/** Nome tecnico da feature -> rotulo legivel, sem inventar semantica nova. */
export const ROTULO_FEATURE: Record<string, string> = {
  texto_prob_insatisfeito_media: "P(insatisfeito) média",
  texto_prob_satisfeito_media: "P(satisfeito) média",
  texto_prob_insatisfeito_max: "P(insatisfeito) máxima",
  texto_prob_satisfeito_ultima: "P(satisfeito) na última fala",
  emoji_score_medio: "Score médio dos emojis",
  emoji_frac_positivos: "Fração de emojis positivos",
  emoji_frac_negativos: "Fração de emojis negativos",
  emoji_contagem: "Quantidade de emojis",
  emoji_posicao_relativa_media: "Posição relativa média do emoji",
  latencia_mediana_s: "Latência mediana (s)",
  latencia_p90_s: "Latência p90 (s)",
  latencia_primeira_resposta_s: "Latência da 1ª resposta (s)",
  duracao_total_s: "Duração total (s)",
  qtd_turnos_cliente: "Turnos do cliente",
  escalou: "Escalou para humano",
  abandonou: "Abandonou",
  emocao_alegria_media: "Alegria média",
  emocao_tristeza_media: "Tristeza média",
  emocao_raiva_media: "Raiva média",
  emocao_medo_media: "Medo médio",
  emocao_nojo_media: "Nojo médio",
  emocao_surpresa_media: "Surpresa média",
  emocao_neutro_media: "Neutro médio",
  emocao_desprezo_derivado: "Desprezo (derivado de raiva + nojo)",
  lexico_polaridade_media: "Polaridade média (SentiLex)",
  lexico_cobertura: "Cobertura do léxico",
  lexico_frac_negados: "Fração de termos negados",
  ironia_prob_media: "P(ironia) média",
  ironia_prob_max: "P(ironia) máxima",
  estilo_frac_caixa_alta: "Fração em caixa alta",
  estilo_pontuacao_enfatica: "Pontuação enfática",
  estilo_frac_alongamento: "Fração com alongamento",
  estilo_palavrao_intensidade: "Intensidade de palavrão",
  estilo_palavrao_dirigido: "Palavrão dirigido a pessoa",
  estilo_frac_censurado: "Fração censurada",
  incongruencia_polaridade: "Incongruência de polaridade",
  incongruencia_emoji_texto: "Incongruência emoji x texto",
  incongruencia_marcador_contraste: "Marcador de contraste",
  incongruencia_hiperbole: "Hipérbole",
  incongruencia_aspas_ironicas: "Aspas irônicas",
  incongruencia_situacao_negativa: "Elogio com situação negativa",
};

export function rotuloDaFeature(nome: string): string {
  return ROTULO_FEATURE[nome] ?? nome;
}

/**
 * Ordena um mapa de pesos por MAGNITUDE e normaliza a largura da barra.
 *
 * Serve tanto para `importancias` (peso global, sempre positivo) quanto para
 * `contribuicoes` (o que pesou naquele atendimento, COM SINAL). A funcao e a
 * mesma; o que nunca se mistura e a exibicao -- sao perguntas diferentes, e a
 * interface precisa dizer qual esta respondendo.
 */
export function ordenarPorMagnitude(
  pesos: Record<string, number>,
): PesoDaFeature[] {
  const entradas = Object.entries(pesos);
  const maior = Math.max(0, ...entradas.map(([, valor]) => Math.abs(valor)));

  return entradas
    .map(([nome, valor]) => ({
      nome,
      rotulo: rotuloDaFeature(nome),
      sinal: sinalDaFeature(nome),
      valor,
      fracao: maior === 0 ? 0 : Math.abs(valor) / maior,
    }))
    .sort((a, b) => Math.abs(b.valor) - Math.abs(a.valor));
}

/** As mesmas features, agrupadas pelas sete familias do trabalho. */
export function agruparPorSinal(
  pesos: Record<string, number>,
): { sinal: SinalDaFeature; features: PesoDaFeature[] }[] {
  const ordenadas = ordenarPorMagnitude(pesos);
  return ORDEM_SINAIS.map((sinal) => ({
    sinal,
    features: ordenadas.filter((feature) => feature.sinal === sinal),
  }));
}
