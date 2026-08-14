import { listarConversas, obterDetalhes, type DetalheConversa, type ResumoConversa } from "./api";
import {
  extensaoDosDados,
  filtrarPorPeriodo,
  lerPeriodo,
  paraQuery,
  rotuloPeriodo,
  type Extensao,
  type Periodo,
} from "./periodo";

export type Recorte = {
  periodo: Periodo;
  /** Extensao de TODO o conjunto -- os atalhos do filtro se ancoram nela. */
  extensao: Extensao;
  rotulo: string;
  /** `?de=&ate=` para preservar o recorte nos links. */
  sufixo: string;
  /** Conversas dentro do periodo. */
  resumos: ResumoConversa[];
  /** Transcricoes das conversas do periodo. */
  detalhes: DetalheConversa[];
  /** Quantas transcricoes falharam individualmente (falha isolada). */
  falhas: number;
  /** Erro da listagem; quando presente, tudo que depende dela mostra falha. */
  erro?: string;
};

/**
 * Carrega e RECORTA por periodo tudo que as telas de atendimento consomem.
 *
 * O corte acontece aqui, no cliente da API, porque `/conversas` e
 * `/indicadores` ainda nao aceitam filtro de data. Isso tem um custo real:
 * baixa-se a lista inteira e as transcricoes das conversas do recorte para
 * descartar o resto. Um `GET /conversas?de=&ate=` (e o mesmo par em
 * `/indicadores`) tornaria o corte server-side.
 *
 * A serie temporal JA saiu daqui: `GET /serie-temporal?de=&ate=` recorta e
 * agrega no servidor, e a pagina principal nao a deriva mais das transcricoes.
 *
 * As transcricoes so sao buscadas para as conversas que sobraram no periodo --
 * e a unica economia possivel sem mudar a API.
 */
export async function carregarRecorte(
  parametros: Record<string, string | string[] | undefined>,
): Promise<Recorte> {
  const periodo = lerPeriodo(parametros);
  const sufixo = paraQuery(periodo);
  const conversas = await listarConversas();

  if (!conversas.ok) {
    return {
      periodo,
      extensao: null,
      rotulo: rotuloPeriodo(periodo, null),
      sufixo,
      resumos: [],
      detalhes: [],
      falhas: 0,
      erro: conversas.erro,
    };
  }

  const extensao = extensaoDosDados(conversas.dado);
  const resumos = filtrarPorPeriodo(conversas.dado, periodo);
  const { detalhes, falhas } = await obterDetalhes(
    resumos.map((resumo) => resumo.id),
  );

  return {
    periodo,
    extensao,
    rotulo: rotuloPeriodo(periodo, extensao),
    sufixo,
    resumos,
    detalhes,
    falhas,
  };
}
