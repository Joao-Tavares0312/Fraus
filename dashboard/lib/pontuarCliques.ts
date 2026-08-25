/**
 * FRAUS LE QUEM CLICOU.
 *
 * Os cinco cliques que abrem a fenda tem timestamps -- ou seja, sao uma
 * conversa: tem ritmo, tem espera, tem hesitacao. Este modulo aplica a eles a
 * mesma pergunta que o produto faz a um atendimento, e devolve uma leitura.
 *
 * O QUE ISTO NAO E, e o painel diz isso em texto visivel: nao e "o score do
 * Fraus". A leitura sai SO do sinal de tempo -- sem texto, sem emoji, sem
 * modelo. O front nao carrega BERTimbau, e apresentar isto como score do
 * produto seria o projeto mentindo sobre a propria metodologia dentro de uma
 * piada, que e o pior lugar concebivel para faze-lo.
 *
 * NAO EXISTE `nota` NEM `categoria` AQUI, e a ausencia e deliberada. A
 * invariante 3 proibe deriva-las no cliente, e o README registra que duplicar
 * essa regra em TypeScript ja produziu divergencia de arredondamento nas
 * fronteiras 6/7 e 8/9. A leitura 0-100 nao e a escada do NPS e nao vira uma.
 *
 * Funcao PURA, sem relogio proprio: quem chama passa os instantes. E o que
 * torna o ritmo testavel sem esperar de verdade.
 */

/** Abaixo disto o clique e considerado imediato -- nenhuma pena. */
export const PISO_SEM_PENA = 250;

/** Cada tanto de milissegundo acima do piso custa um ponto. */
const MS_POR_PONTO = 25;

/** Teto da pena por lentidao, para a hesitacao ainda ter o que descontar. */
const PENA_MAXIMA_POR_LENTIDAO = 60;

/** Uma latencia acima da mediana vezes isto e hesitacao, nao ritmo. */
export const LIMIAR_DE_HESITACAO = 2.5;

/** Quanto custa ter hesitado uma vez. */
const PENA_POR_HESITAR = 20;

export type LeituraDeCliques = {
  /** Os intervalos entre cliques consecutivos, na ordem em que aconteceram. */
  readonly latenciasMs: number[];
  /** O meio das latencias ordenadas -- resistente ao unico clique perdido. */
  readonly medianaMs: number;
  /** Houve um intervalo destoante o bastante para ser espera, nao ritmo. */
  readonly hesitou: boolean;
  /** Qual intervalo foi a hesitacao, para a tela apontar o dedo. `null` se nao houve. */
  readonly indiceDaHesitacao: number | null;
  /** 0 a 100, so pelo sinal de tempo. NAO e o score do produto. */
  readonly leitura: number;
};

function mediana(valores: number[]): number {
  const ordenados = [...valores].sort((a, b) => a - b);
  const meio = Math.floor(ordenados.length / 2);
  return ordenados.length % 2 === 0
    ? (ordenados[meio - 1] + ordenados[meio]) / 2
    : ordenados[meio];
}

/**
 * Le a sequencia de cliques. `null` quando nao ha o que ler.
 *
 * Menos de dois cliques nao produz latencia nenhuma, e leitura sem latencia
 * seria numero inventado -- exatamente o que a invariante 2 proibe. Ausencia de
 * dado nao vira zero aqui, vira `null`.
 */
export function lerCliques(instantesMs: number[]): LeituraDeCliques | null {
  if (instantesMs.length < 2) return null;

  // ARREDONDADAS na origem, e nao so na exibicao: `performance.now()` devolve
  // fracao de milissegundo, e a tela mostrava "192.0999999642372 ms". Milissegundo
  // inteiro e toda a precisao que este ritmo tem significado, e arredondar aqui
  // faz a mediana e a leitura sairem da MESMA grandeza que o painel exibe --
  // numero mostrado e numero pontuado nao podem divergir.
  const latenciasMs = instantesMs
    .slice(1)
    .map((instante, i) => Math.round(instante - instantesMs[i]));

  const medianaMs = mediana(latenciasMs);

  const maior = Math.max(...latenciasMs);
  const hesitou = maior > medianaMs * LIMIAR_DE_HESITACAO;
  const indiceDaHesitacao = hesitou ? latenciasMs.indexOf(maior) : null;

  const penaPorLentidao = Math.min(
    PENA_MAXIMA_POR_LENTIDAO,
    Math.max(0, (medianaMs - PISO_SEM_PENA) / MS_POR_PONTO),
  );
  const bruto = 100 - penaPorLentidao - (hesitou ? PENA_POR_HESITAR : 0);
  const leitura = Math.round(Math.min(100, Math.max(0, bruto)));

  return { latenciasMs, medianaMs, hesitou, indiceDaHesitacao, leitura };
}

/**
 * O que Fraus diz sobre a leitura -- na voz dele, sem rotulo de categoria.
 *
 * O desfecho do painel e a ACUSACAO, e nao um rotulo de NPS: a graca esta em
 * ele apontar que voce diria outra coisa se perguntassem, que e a tese inteira
 * do produto virada contra quem achou o segredo.
 */
export function vereditoDe(leitura: LeituraDeCliques): string {
  if (leitura.hesitou) {
    return "Você hesitou. Fraus registrou.";
  }
  if (leitura.leitura >= 90) {
    return "Rápido demais. Ninguém decide tão rápido — você já sabia do segredo.";
  }
  if (leitura.leitura >= 60) {
    return "Ritmo de quem estava só conferindo.";
  }
  return "Você demorou. Isso também é um dado.";
}

/**
 * A duracao da sequencia em TIMECODE de fita: `MM:SS:QQ`, quadros de 1/25 s.
 *
 * Nao e fantasia de "tecnico": este produto mede TEMPO, e o numero na cabeca da
 * fita e a duracao real dos cinco cliques. Em vinte e cinco quadros por segundo
 * a resolucao do ultimo par e 40 ms -- fina o bastante para o timecode mudar
 * entre uma sequencia apressada e uma hesitante, que e a unica coisa que ele
 * precisa distinguir.
 */
export function timecodeDe(duracaoMs: number): string {
  const totalDeQuadros = Math.round((duracaoMs / 1000) * 25);
  const doisDigitos = (n: number) => String(n).padStart(2, "0");
  return [
    doisDigitos(Math.floor(totalDeQuadros / (25 * 60))),
    doisDigitos(Math.floor(totalDeQuadros / 25) % 60),
    doisDigitos(totalDeQuadros % 25),
  ].join(":");
}
