/**
 * Cliente da API do Fraus.
 *
 * Toda leitura e `no-store`: a dashboard e um instrumento de leitura de um
 * banco que muda a cada importacao, e um numero em cache seria um numero
 * errado apresentado com confianca.
 *
 * Nenhuma funcao daqui lanca para o chamador de pagina: elas devolvem
 * `Resultado<T>`, para que a falha de UM bloco nao derrube os outros -- regra
 * de produto 5 (se um indicador falha, so o card dele mostra falha).
 */

/**
 * O caminho do proxy no servidor Next. E o destino das chamadas feitas PELO
 * NAVEGADOR: o proxy anexa a chave de acesso (FRAUS_CHAVE_ACESSO, env
 * server-side) e repassa para FRAUS_API_URL, de modo que a chave nunca chega
 * ao bundle.
 */
const PROXY = "/api/fraus";

/**
 * Destino de UMA chamada, escolhido pelo lado em que este codigo roda.
 *
 * No SERVIDOR (Server Components, que sao a maioria das telas) a URL precisa
 * ser absoluta: o `fetch` do Node recusa caminho relativo -- nao existe
 * "origem da pagina" ali. Passar `/api/fraus` derrubava TODA tela renderizada
 * no servidor com um TypeError que `proteger` engolia e virava estado de erro.
 * E dar a volta pelo proxy seria absurdo de qualquer modo: o processo falaria
 * consigo mesmo para chegar na API que ele ja alcanca direto.
 *
 * No NAVEGADOR o destino e o proxy, justamente para a chave nao sair do
 * servidor.
 */
function noServidor(): boolean {
  return typeof window === "undefined";
}

export function urlDaApi(rota: string): string {
  if (!noServidor()) return `${PROXY}${rota}`;
  return `${process.env.FRAUS_API_URL ?? "http://localhost:8000"}${rota}`;
}

/**
 * Cabecalhos da chamada, incluindo a autorizacao quando falamos direto com a
 * API (server-side). No navegador nao ha o que anexar: quem autentica e o
 * proxy.
 *
 * `FRAUS_CHAVE_ACESSO` nao tem o prefixo NEXT_PUBLIC_, entao o Next NAO a
 * inlina no bundle do cliente -- do lado do navegador ela vale `undefined`, e
 * o ramo acima nem a consulta. A chave nao vaza por este arquivo.
 */
export function cabecalhosDaApi(extras?: Record<string, string>): Record<string, string> {
  const cabecalhos: Record<string, string> = { ...(extras ?? {}) };
  if (noServidor() && process.env.FRAUS_CHAVE_ACESSO) {
    cabecalhos["Authorization"] = `Bearer ${process.env.FRAUS_CHAVE_ACESSO}`;
  }
  return cabecalhos;
}

/**
 * SO o endereco exibido no exemplo de `curl` da tela de integracoes/ingestao
 * -- nunca destino de fetch. Quem le esse exemplo e um integrador externo,
 * que fala com a API direto (nao com o proxy, que so existe para o navegador
 * desta dashboard).
 */
export const BASE_DA_API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Categoria = "detrator" | "neutro" | "promotor";

export type Indicadores = {
  /** null quando nenhum atendimento tem score: ausencia de dado nao e zero. */
  nps: number | null;
  /** null quando nenhum atendimento tem score. */
  csat: number | null;
  /** Contencao NAO depende de score, entao sempre e um numero. */
  containment_rate: number;
  total_conversas: number;
  sem_sinal: number;
  /**
   * Mediana das esperas cliente -> resposta do recorte, derivada dos
   * timestamps na leitura. null sem nenhum par -- nunca zero.
   */
  tempo_mediano_resposta_s: number | null;
};

export type ResumoConversa = {
  id: string;
  canal: string;
  iniciada_em: string;
  score: number | null;
  categoria: Categoria | null;
  /**
   * Nota 0-10 DERIVADA NO SERVIDOR a partir do score. A dashboard nunca
   * recalcula: o arredondamento do Python (bancario) e o do JavaScript
   * (meio para cima) divergem nas fronteiras 6/7 e 8/9, e a fonte da verdade
   * e o servidor -- ele e quem grava a categoria.
   */
  nota: number | null;

  /**
   * Ficha operacional derivada pelo servidor em `fraus.resumo`.
   *
   * Os tempos vem `null` -- nunca `0` -- quando a espera nao existiu. Zero
   * numa coluna de tempo de resposta se le como "respondeu na hora", e uma
   * conversa que nunca teve atendente humano apareceria como a mais agil da
   * operacao. Toda exibicao daqui precisa tratar o nulo como "não houve".
   */
  qtd_mensagens: number;
  qtd_cliente: number;
  qtd_bot: number;
  qtd_humano: number;
  latencia_primeira_resposta_s: number | null;
  latencia_mediana_s: number | null;
  latencia_mediana_bot_s: number | null;
  latencia_mediana_humano_s: number | null;
  duracao_s: number;
  escalou_para_humano: boolean;
  encerrada_em: string | null;
  desfecho: Desfecho;
};

/**
 * Como o atendimento terminou. Conjunto FECHADO e cada um verificavel no dado
 * -- nao existe "resolvida", porque resolucao e julgamento sobre o problema do
 * cliente e nada no dado a sustenta. A precedencia esta em `fraus.resumo`.
 */
export type Desfecho =
  | "sem_sinal"
  | "escalada"
  | "sem_resposta"
  | "encerrada"
  | "em_aberto";

export type Autor = "cliente" | "bot" | "humano";

export type Mensagem = {
  autor: Autor;
  texto: string;
  enviada_em: string;
};

export type DetalheConversa = ResumoConversa & {
  mensagens: Mensagem[];
};

/**
 * Uma mensagem da transcricao com a probabilidade que o classificador de
 * texto deu a ela.
 *
 * Os tres campos vem `null` para bot e humano: o classificador foi treinado
 * em fala de CLIENTE, e o servidor recusa pontuar o resto. O `indice` e a
 * posicao na mesma lista de `/conversas/{id}`, para alinhar sem recontar.
 */
export type MensagemAtribuida = {
  indice: number;
  autor: Autor;
  texto: string;
  prob_insatisfeito: number | null;
  prob_neutro: number | null;
  prob_satisfeito: number | null;

  /**
   * As duas cabecas de LEITURA. Elas descrevem a fala e NAO entram no score:
   * o fusor tem dezesseis features e nenhuma vem daqui. A resposta marca isso
   * em `sinais_fora_do_score`, e a interface tem que manter os dois numeros
   * visualmente separados da nota -- "ironia 0,99" encostado num score baixo
   * convida a conclusao de que uma causou a outra.
   *
   * `null` quando o servidor subiu sem a cabeca correspondente.
   *
   * RESSALVA MEDIDA sobre `prob_ironia`: o modelo acerta o caso de manual
   * ("que atendimento maravilhoso, so esperei 3 horas") e marca 6 em 10 falas
   * sinceras de atendimento como ironicas. Exibir como indicio, nunca como
   * veredito. Ver tests/test_ironia_dominio.py.
   */
  emocao: Record<string, number> | null;
  prob_ironia: number | null;
};

/** Resposta de `GET /conversas/{id}/atribuicao`. */
export type Atribuicao = {
  conversa_id: string;
  /** Os mesmos score/nota/categoria de `/conversas/{id}`: gravados na importacao. */
  score: number | null;
  nota: number | null;
  categoria: Categoria | null;
  mensagens: MensagemAtribuida[];
  /** Peso absoluto GLOBAL de cada uma das 16 features do fusor -- aprendido
   * no treino, nao especifico desta conversa. */
  importancias: Record<string, number>;
  /** Quanto cada feature pesou NESTA conversa: positivo empurrou para
   * satisfeito, negativo para insatisfeito. `null` quando nao ha fala do
   * cliente -- sem score, sem contribuicao. */
  contribuicoes: Record<string, number> | null;
};

/** Metricas do treino, exportadas pelo notebook 01. `null` ate o treino rodar. */
export type MetricasTreino = {
  acuracia?: number;
  f1_macro?: number;
  [chave: string]: unknown;
};

/**
 * Uma das tres cabecas BERTimbau, com o que o treino dela mediu.
 *
 * As metricas tem FORMATOS DIFERENTES de proposito -- cada notebook exporta o
 * que faz sentido para a sua tarefa, e uniformizar apagaria justamente os
 * campos que carregam a ressalva (o F1 em corpus independente da emocao, a
 * limitacao declarada da ironia). A tela le os campos conhecidos e mostra o
 * resto como veio.
 */
export type CabecaDeModelo = {
  nome: string;
  classes: string[];
  /** `null` antes do notebook exportar. Nunca zero. */
  metricas: MetricasTreino | null;
  /** Se ela entra no fusor. Hoje so a satisfacao. */
  pontua: boolean;
};

/** Resposta de `GET /modelo` -- a ficha do modelo. */
export type FichaModelo = {
  /** Peso GLOBAL de cada uma das 16 features. Nao e especifico de conversa. */
  importancias: Record<string, number>;
  /** `null` enquanto o notebook 01 nao exportou metricas.json. NUNCA zero. */
  metricas: MetricasTreino | null;
  classes: string[];
  /**
   * As tres cabecas fine-tunadas, cada uma com a metrica que ELA mediu.
   *
   * `pontua` separa quem decide a nota de quem so descreve: hoje so a
   * satisfacao entra no fusor. Sem esse campo a tela mostraria tres cartoes
   * iguais e o leitor concluiria que os tres pesam na nota.
   */
  cabecas: CabecaDeModelo[];
  /** Faixas de NPS lidas do SERVIDOR (fonte unica), nao digitadas no front. */
  faixas_nps: Record<string, [number, number]>;
  total_emojis_lexicon: number;
};

export type ItemLexicon = {
  emoji: string;
  score: number;
  negativo: number;
  neutro: number;
  positivo: number;
};

export type PaginaLexicon = {
  total: number;
  itens: ItemLexicon[];
};

export type EmojiDetectado = {
  emoji: string;
  score: number;
  /** Posicao do emoji no texto, em [0, 1]: 1 = no fim da frase. */
  posicao_relativa: number;
};

/** Resposta de `POST /modelo/simular`. */
export type Simulacao = {
  texto: string;
  prob_insatisfeito: number;
  prob_neutro: number;
  prob_satisfeito: number;
  emojis: EmojiDetectado[];
  /**
   * As oito emocoes: as sete treinadas (Ekman + neutro) mais o `desprezo`,
   * DERIVADO da diade raiva+nojo por media geometrica (Plutchik 1980) porque
   * nenhum corpus PT-BR o anota. `null` se a API subiu sem essa cabeca.
   */
  emocao: Record<string, number> | null;
  /** Ver a ressalva medida em `MensagemAtribuida.prob_ironia`. */
  prob_ironia: number | null;
};

/**
 * Configuracao vigente e a de FABRICA, como `GET /configuracoes` devolve.
 *
 * As duas vem juntas de proposito: sem a de fabrica, "voltar ao padrao" seria
 * um botao preenchido com numeros digitados de novo na interface -- e faixa
 * duplicada em dois lugares ja foi defeito deste projeto uma vez.
 */
export type ValoresConfiguracao = {
  /** categoria -> [nota minima, nota maxima], inclusive nas duas pontas. */
  faixas_nps: Record<string, [number, number]>;
  /** [pico, saudavel, degradando] em segundos, estritamente crescentes. */
  limiares_latencia_s: number[];
};

export type Configuracoes = {
  vigente: ValoresConfiguracao;
  fabrica: ValoresConfiguracao;
};

/** Fonte de integracao. `variavel_segredo` e o NOME de uma variavel de ambiente. */
export type FonteIntegracao = {
  id: number;
  nome: string;
  canal: string;
  tipo: string;
  /** NOME da variavel de ambiente que carrega a credencial -- nunca o valor. */
  variavel_segredo: string | null;
  ativa: boolean;
  criada_em: string;
  /**
   * Os quatro ultimos caracteres da chave em uso, ou `null` se a fonte ainda
   * nao tem chave. Serve para o operador reconhecer QUAL chave esta valendo
   * ("termina em 3f9a") sem que o pedaco exibido ajude a adivinhar o resto.
   * O hash da chave nunca sai da API.
   */
  chave_dica: string | null;
  chave_criada_em: string | null;
  /**
   * Se a variavel nomeada acima EXISTE no ambiente da API, verificado na
   * leitura. `false` nao diz que o segredo esta errado: diz que a variavel
   * nao esta definida onde a API roda.
   */
  configurada: boolean;
};

export type MotivoRejeicao = {
  numero_linha: number;
  motivo: string;
};

/** Uma linha do historico de `GET /integracoes/importacoes`. */
export type Importacao = {
  id: number;
  ocorrida_em: string;
  arquivo: string;
  aceitas: number;
  rejeitadas: number;
  /** Ate 20 motivos por importacao — a API trunca; o resto fica no CSV. */
  motivos: MotivoRejeicao[];
};

export type Resultado<T> =
  | { ok: true; dado: T }
  | { ok: false; erro: string };

async function buscar<T>(rota: string): Promise<T> {
  const resposta = await fetch(urlDaApi(rota), {
    cache: "no-store",
    headers: cabecalhosDaApi(),
  });
  if (!resposta.ok) throw new Error(`${rota} respondeu ${resposta.status}`);
  return (await resposta.json()) as T;
}

/**
 * Escrita na API, preservando a MENSAGEM do servidor.
 *
 * O `400` do Fraus nomeia o problema ("buraco entre detrator e neutro: nenhuma
 * faixa cobre a nota 6"). Trocar isso por "erro ao salvar" jogaria fora a
 * unica frase da tela que diz o que consertar -- entao o `detail` sobe inteiro.
 */
async function escrever<T>(
  rota: string,
  metodo: "POST" | "PUT" | "PATCH" | "DELETE",
  corpo?: unknown,
): Promise<T> {
  const resposta = await fetch(urlDaApi(rota), {
    method: metodo,
    headers: cabecalhosDaApi(
      corpo === undefined ? undefined : { "Content-Type": "application/json" },
    ),
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
    cache: "no-store",
  });

  if (!resposta.ok) {
    const dado = (await resposta.json().catch(() => null)) as
      | { detail?: unknown }
      | null;
    const detalhe = dado?.detail;
    throw new Error(
      typeof detalhe === "string"
        ? detalhe
        : detalhe
          ? JSON.stringify(detalhe)
          : `${metodo} ${rota} respondeu ${resposta.status}`,
    );
  }

  if (resposta.status === 204) return undefined as T;
  return (await resposta.json()) as T;
}

function mensagemDeErro(erro: unknown): string {
  if (erro instanceof Error) {
    // `fetch` recusado dá "fetch failed" — inútil para quem está na banca.
    if (/fetch failed|ECONNREFUSED/i.test(erro.message)) {
      return `API não respondeu em ${urlDaApi("")}`;
    }
    return erro.message;
  }
  return "falha desconhecida ao consultar a API";
}

async function proteger<T>(promessa: Promise<T>): Promise<Resultado<T>> {
  try {
    return { ok: true, dado: await promessa };
  } catch (erro) {
    return { ok: false, erro: mensagemDeErro(erro) };
  }
}

/**
 * `?de=&ate=` (AAAA-MM-DD, pontas inclusivas) para as rotas que recortam no
 * servidor. Ponta ausente fica fora da query -- a API trata ausencia como
 * "sem corte", e mandar string vazia viraria 400.
 */
function queryDePeriodo(de?: string | null, ate?: string | null): string {
  const consulta = new URLSearchParams();
  if (de) consulta.set("de", de);
  if (ate) consulta.set("ate", ate);
  const texto = consulta.toString();
  return texto ? `?${texto}` : "";
}

export const obterIndicadores = (de?: string | null, ate?: string | null) =>
  proteger(buscar<Indicadores>(`/indicadores${queryDePeriodo(de, ate)}`));

export const listarConversas = (de?: string | null, ate?: string | null) =>
  proteger(buscar<ResumoConversa[]>(`/conversas${queryDePeriodo(de, ate)}`));

export type TermoDoLexico = {
  termo: string;
  ocorrencias: number;
  /** Quanto o termo e mais frequente nesta classe do que nas outras, em [-1, 1]. */
  distincao: number;
};

export type ClasseDoLexico = {
  categoria: Categoria;
  atendimentos: number;
  palavras: TermoDoLexico[];
  emojis: TermoDoLexico[];
};

export const obterLexico = (de?: string | null, ate?: string | null) =>
  proteger(
    buscar<{ classes: ClasseDoLexico[] }>(`/lexico${queryDePeriodo(de, ate)}`),
  );

export const obterConversa = (id: string) =>
  proteger(buscar<DetalheConversa>(`/conversas/${encodeURIComponent(id)}`));

export const obterAtribuicao = (id: string) =>
  proteger(
    buscar<Atribuicao>(`/conversas/${encodeURIComponent(id)}/atribuicao`),
  );

export const obterModelo = () => proteger(buscar<FichaModelo>("/modelo"));

/** Uma pagina do lexicon de emoji. `busca` casa o emoji exato, como a API faz. */
export const obterLexicon = (
  { busca, limite, deslocamento }: {
    busca?: string;
    limite: number;
    deslocamento: number;
  },
) => {
  const parametros = new URLSearchParams({
    limite: String(limite),
    deslocamento: String(deslocamento),
  });
  if (busca) parametros.set("busca", busca);
  return proteger(buscar<PaginaLexicon>(`/modelo/lexicon?${parametros}`));
};

/**
 * Roda o classificador numa frase avulsa. Nao persiste nada.
 *
 * Ao contrario das leituras, esta e uma chamada do NAVEGADOR (o simulador e
 * interativo): `urlDaApi` a manda para o proxy, que anexa a chave no servidor.
 */
export async function simularTexto(texto: string): Promise<Resultado<Simulacao>> {
  return proteger(
    (async () => {
      const resposta = await fetch(urlDaApi("/modelo/simular"), {
        method: "POST",
        headers: cabecalhosDaApi({ "Content-Type": "application/json" }),
        body: JSON.stringify({ texto }),
        cache: "no-store",
      });
      if (!resposta.ok) {
        // A API responde 400 com `{detail}` -- mostrar o motivo real vale mais
        // que "erro 400" para quem esta demonstrando o produto.
        const corpo = (await resposta.json().catch(() => null)) as
          | { detail?: string }
          | null;
        throw new Error(
          corpo?.detail ?? `/modelo/simular respondeu ${resposta.status}`,
        );
      }
      return (await resposta.json()) as Simulacao;
    })(),
  );
}

/**
 * Configuracao vigente + de fabrica.
 *
 * Chamada tambem pelas telas de leitura: os limiares de latencia que qualificam
 * "rapido/aceitavel/lento" saem daqui, nao de constante no front.
 */
export const obterConfiguracoes = () =>
  proteger(buscar<Configuracoes>("/configuracoes"));

/**
 * Grava as chaves enviadas. Manda so o que mudou -- o `PUT` valida chave a
 * chave, entao enviar o bloco inteiro faria um erro de latencia recusar
 * tambem uma faixa de NPS correta.
 */
export const salvarConfiguracoes = (valores: Partial<ValoresConfiguracao>) =>
  proteger(escrever<Configuracoes>("/configuracoes", "PUT", valores));

export const listarFontes = () =>
  proteger(buscar<FonteIntegracao[]>("/integracoes/fontes"));

export const criarFonte = (fonte: {
  nome: string;
  canal: string;
  tipo: string;
  /** NOME da variavel de ambiente. A credencial nunca passa por aqui. */
  variavel_segredo?: string | null;
}) => proteger(escrever<FonteIntegracao>("/integracoes/fontes", "POST", fonte));

export const ajustarFonte = (
  id: number,
  mudanca: { nome?: string; ativa?: boolean },
) =>
  proteger(
    escrever<FonteIntegracao>(`/integracoes/fontes/${id}`, "PATCH", mudanca),
  );

/** Remove o CADASTRO da fonte. Nenhum atendimento e apagado junto. */
export const apagarFonte = (id: number) =>
  proteger(escrever<void>(`/integracoes/fontes/${id}`, "DELETE"));

export type ChaveGerada = {
  fonte: FonteIntegracao;
  /**
   * A chave EM CLARO. Este e o unico lugar em toda a API onde ela existe, e
   * so nesta resposta: o servidor guarda apenas o hash e nao ha rota para
   * reler. A tela precisa mostra-la agora ou ela se perde.
   *
   * NUNCA guardar isto em localStorage, sessionStorage ou URL -- ela morre
   * junto com o estado do componente, de proposito.
   */
  chave: string;
  aviso: string;
};

/**
 * Gera a chave de API da fonte, SUBSTITUINDO a anterior.
 *
 * Duas chaves validas ao mesmo tempo pareceriam rotacao sem risco, mas a
 * antiga seguiria aceita sem ninguem saber quem ainda a usa.
 */
export const gerarChave = (id: number) =>
  proteger(escrever<ChaveGerada>(`/integracoes/fontes/${id}/chave`, "POST"));

/** Invalida a chave. A fonte e os atendimentos dela continuam. */
export const revogarChave = (id: number) =>
  proteger(escrever<void>(`/integracoes/fontes/${id}/chave`, "DELETE"));

export type TipoDeFonte = { valor: string; rotulo: string; ajuda: string };

/**
 * Os tipos que a ingestao sabe tratar.
 *
 * Lidos da API de proposito: a tela mantinha a propria copia da lista, e copia
 * so fica errada no dia em que um tipo novo entra no servidor -- o formulario
 * seguiria oferecendo os antigos, sem erro nenhum, so sumindo da vista.
 */
export const listarTiposDeFonte = () =>
  proteger(buscar<TipoDeFonte[]>("/integracoes/tipos"));

export type ArquivoImportavel = { caminho: string; bytes: number };

/** Os CSV disponiveis na raiz de importacao, com caminho relativo a ela. */
export const listarArquivosImportaveis = () =>
  proteger(
    buscar<{ raiz: string; arquivos: ArquivoImportavel[] }>(
      "/integracoes/arquivos",
    ),
  );

export type ResultadoImportacao = {
  importadas: number;
  rejeitadas: number;
  motivos: { linha: number; motivo: string }[];
};

/**
 * Importa um CSV da raiz. O `caminho` e o que a listagem devolveu, sem ajuste.
 *
 * O servidor recusa qualquer caminho que escape da raiz; a interface nunca
 * monta caminho a mao nem oferece campo livre para isso.
 */
export const importarArquivo = (caminho: string) =>
  proteger(
    escrever<ResultadoImportacao>("/conversas/importar", "POST", { caminho }),
  );

export const listarImportacoes = () =>
  proteger(buscar<Importacao[]>("/integracoes/importacoes"));

/**
 * Peso de UMA palavra na leitura que o modelo fez da mensagem.
 *
 * Medido por oclusao: apaga-se a palavra e pergunta-se de novo. Positivo
 * empurrou para satisfeito, negativo para insatisfeito.
 *
 * `peso: null` NAO e o mesmo que `0`. Zero e medicao ("apagar esta palavra nao
 * mudou nada"); nulo e ausencia de medicao -- a mensagem passou do teto de
 * palavras que o servidor mede. A tela precisa distinguir os dois.
 *
 * `inicio`/`fim` sao indices no texto original, para grifar sem re-tokenizar:
 * uma segunda tokenizacao no cliente acabaria grifando trecho diferente do que
 * o servidor mediu.
 */
export type PesoDePalavra = {
  palavra: string;
  inicio: number;
  fim: number;
  peso: number | null;
};

/** Palavra mais usada pelo cliente, comparada ao restante do banco. */
export type ItemVocabulario = {
  palavra: string;
  vezes: number;
  /**
   * Quantas vezes a palavra e mais frequente aqui do que na referencia --
   * `3.0` e "o triplo do normal nesta operacao". `null` quando a palavra nao
   * aparece na referencia: nao ha com o que comparar, e `1.0` afirmaria
   * "igual a media" sem ter medido media nenhuma.
   */
  destaque: number | null;
};

export type MensagemAnalisada = MensagemAtribuida & {
  /** `null` para bot e humano: so a fala do cliente recebe peso de palavra. */
  palavras: PesoDePalavra[] | null;
};

export type ConversaAnalisada = {
  conversa: DetalheConversa;
  score: number | null;
  nota: number | null;
  categoria: Categoria | null;
  mensagens: MensagemAnalisada[];
  contribuicoes: Record<string, number> | null;
  importancias: Record<string, number>;
  sinais_fora_do_score: string[];
  vocabulario: ItemVocabulario[];
  qtd_mensagens: number;
  qtd_cliente: number;
  qtd_bot: number;
  qtd_humano: number;
  latencia_primeira_resposta_s: number | null;
  latencia_mediana_s: number | null;
  latencia_mediana_bot_s: number | null;
  latencia_mediana_humano_s: number | null;
  duracao_s: number;
  desfecho: Desfecho;
};

export type ResultadoAnalise = {
  analises: ConversaAnalisada[];
  conversas_no_arquivo: number;
  conversas_analisadas: number;
  rejeitadas: { numero_linha: number; motivo: string }[];
  total_rejeitadas: number;
  /** Quantas conversas do banco serviram de referencia para o `destaque`. */
  referencia_conversas: number;
  /** Como o arquivo foi entendido: "export da Totalk", "transcrição em pdf"… */
  formato: string;
  /**
   * Falso quando o arquivo nao traz horario (tipico de .docx e .pdf).
   *
   * Sem horario nao ha latencia, e latencia e uma das dezesseis features do
   * fusor -- entao a conversa NAO recebe nota. Nao e falha: e a resposta
   * honesta. Zerar o tempo faria o modelo ler como se toda resposta tivesse
   * sido instantanea e a nota sairia melhor que a verdade.
   */
  tem_tempo: boolean;
  /** O que a leitura teve que inferir. Exibir sempre, não só quando dá errado. */
  avisos: string[];
};

/**
 * Analisa um arquivo de conversa SEM gravar nada.
 *
 * O conteudo vai no corpo e e interpretado em memoria: nada entra no banco,
 * nada toca o disco. E o que separa esta chamada da importacao -- aqui se
 * pergunta "o que o modelo acha disto?", nao "passe a contar isto no NPS".
 */
export const analisarArquivo = (csv: string) =>
  proteger(escrever<ResultadoAnalise>("/analisar", "POST", { csv }));

/**
 * Analisa um arquivo binario -- csv, xlsx, docx ou pdf.
 *
 * Vai como multipart e nao como JSON porque planilha e PDF nao sao texto:
 * codificar em base64 para caber num campo de string inflaria o corpo em um
 * terco sem ganhar nada. Continua sem gravar coisa alguma no servidor.
 */
export async function analisarUpload(
  arquivo: File,
): Promise<Resultado<ResultadoAnalise>> {
  return proteger(
    (async () => {
      const corpo = new FormData();
      corpo.append("arquivo", arquivo);
      // Sem Content-Type a mao: o `fetch` precisa gerar o boundary do
      // multipart, e fixa-lo aqui quebraria o parse do lado da API.
      const resposta = await fetch(urlDaApi("/analisar/arquivo"), {
        method: "POST",
        headers: cabecalhosDaApi(),
        body: corpo,
      });
      if (!resposta.ok) {
        // O `detail` do FastAPI e a mensagem que NOMEIA o que se esperava --
        // ela e o produto principal de uma recusa, e perde-la deixaria o
        // operador com "erro 400" e nada para consertar.
        const erro = await resposta.json().catch(() => null);
        throw new Error(erro?.detail ?? `A API respondeu ${resposta.status}.`);
      }
      return (await resposta.json()) as ResultadoAnalise;
    })(),
  );
}

export type PontoSerieApi = {
  dia: string; // AAAA-MM-DD
  nps: number | null;
  latencia_mediana_s: number | null;
  atendimentos: number;
  com_score: number;
};

/**
 * Serie diaria de NPS x latencia, ja agregada pelo servidor.
 *
 * O recorte vai como `?de=&ate=` e as duas pontas sao INCLUSIVAS. Data
 * malformada devolve 400 em vez de ser ignorada -- filtro descartado em
 * silencio faria o grafico mostrar a serie inteira parecendo o recorte.
 */
export const obterSerieTemporal = (de?: string | null, ate?: string | null) => {
  const query = new URLSearchParams();
  if (de) query.set("de", de);
  if (ate) query.set("ate", ate);
  const sufixo = query.toString();
  return proteger(
    buscar<{ de: string | null; ate: string | null; pontos: PontoSerieApi[] }>(
      `/serie-temporal${sufixo ? `?${sufixo}` : ""}`,
    ),
  );
};

/** Estado de saude da API -- alimenta o indicador do app shell. */
export const obterSaude = () =>
  proteger(buscar<{ status: string }>("/saude"));

const LOTE_DETALHES = 8;

/**
 * Busca as transcricoes de varias conversas.
 *
 * A serie temporal SAIU daqui: ela vem agregada de `GET /serie-temporal`. O
 * N+1 sobrevive para o que ainda nao tem agregado no servidor -- o lexico por
 * classe e o tempo mediano de resposta da faixa de indicadores, que continuam
 * precisando do texto e dos timestamps de cada transcricao. Eliminar o resto
 * exige `GET /indicadores?de=&ate=` e um agregado de lexico.
 *
 * Conversas que falharem individualmente sao descartadas em vez de derrubar a
 * pagina inteira.
 */
export async function obterDetalhes(
  ids: string[],
): Promise<{ detalhes: DetalheConversa[]; falhas: number }> {
  const detalhes: DetalheConversa[] = [];
  let falhas = 0;

  for (let inicio = 0; inicio < ids.length; inicio += LOTE_DETALHES) {
    const lote = ids.slice(inicio, inicio + LOTE_DETALHES);
    const resultados = await Promise.all(lote.map((id) => obterConversa(id)));
    for (const resultado of resultados) {
      if (resultado.ok) detalhes.push(resultado.dado);
      else falhas += 1;
    }
  }

  return { detalhes, falhas };
}

/**
 * O endereco que a interface EXIBE como destino das chamadas do navegador
 * (tooltip do indicador de saude). E o proxy, porque e para la que o navegador
 * fala -- mostrar a URL interna da API confundiria e ainda a divulgaria.
 */
export const ENDERECO_API = PROXY;
