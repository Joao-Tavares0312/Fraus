import { listarConversas, type ResumoConversa } from "./api";
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
 * NENHUMA TRANSCRICAO passa por aqui. Elas eram o N+1 real -- uma chamada a
 * `/conversas/{id}` por linha do recorte -- e nao ha mais tela que precise
 * delas no caminho feliz: serie, lexico, indicadores e tempo mediano vem
 * agregados do servidor. Quem ainda quiser transcricao (a Visao geral, so
 * quando um agregado FALHA) chama `obterDetalhes` explicitamente, e paga o
 * custo a vista em vez de recebe-lo embutido num carregador de lista.
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
      erro: conversas.erro,
    };
  }

  const extensao = extensaoDosDados(conversas.dado);

  return {
    periodo,
    extensao,
    rotulo: rotuloPeriodo(periodo, extensao),
    sufixo,
    resumos: filtrarPorPeriodo(conversas.dado, periodo),
  };
}
