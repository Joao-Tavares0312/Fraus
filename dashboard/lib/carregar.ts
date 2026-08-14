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
 * Carrega e recorta por periodo tudo que as telas de atendimento consomem.
 *
 * A lista inteira e baixada UMA vez mesmo com filtro: a extensao do conjunto
 * (que ancora os atalhos do filtro) precisa do todo, e a listagem e barata --
 * o que custava caro era a transcricao. O corte dos resumos continua no
 * cliente por isso; `GET /conversas?de=&ate=` existe para quem nao precisa
 * da extensao.
 *
 * As TRANSCRICOES sao o N+1 real, e `comDetalhes: false` as pula: a visao
 * geral nao precisa mais delas -- serie, lexico e tempo mediano vem agregados
 * do servidor (`/serie-temporal`, `/lexico`, `/indicadores`).
 */
export async function carregarRecorte(
  parametros: Record<string, string | string[] | undefined>,
  { comDetalhes = true }: { comDetalhes?: boolean } = {},
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
  const { detalhes, falhas } = comDetalhes
    ? await obterDetalhes(resumos.map((resumo) => resumo.id))
    : { detalhes: [], falhas: 0 };

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
