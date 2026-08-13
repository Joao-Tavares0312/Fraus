import { CartaoIndicador, type Trilho } from "./CartaoIndicador";
import {
  CSAT_SAUDAVEL,
  LIMIARES_LATENCIA,
  type IndicadoresDoPeriodo,
} from "@/lib/derivacoes";
import {
  formatarNps,
  formatarNumero,
  formatarSegundos,
} from "@/lib/formato";

/**
 * Os quatro indicadores do periodo.
 *
 * NPS e CSAT levam a etiqueta "estimativa" e o sublinhado de proveniencia: os
 * dois sao INFERIDOS do texto, nao perguntados ao cliente. Contencao e latencia
 * sao OBSERVADAS -- saem de `escalou_para_humano` e dos timestamps -- e por
 * isso nao levam nem etiqueta nem sublinhado. A diferenca entre as duas
 * origens e o produto inteiro.
 *
 * Cada cartao falha sozinho: `erro` pinta so o proprio cartao.
 */

const TRILHO_NPS: Trilho = {
  minimo: -100,
  maximo: 100,
  // O NPS nao tem "faixa saudavel" universal publicada que caiba aqui sem
  // inventar limiar, entao o trilho marca apenas o ZERO -- a fronteira entre
  // mais detratores e mais promotores, que e definicao, nao benchmark.
  faixas: [],
  marcas: [{ valor: 0, rotulo: "zero: tantos promotores quanto detratores" }],
};

const TRILHO_CSAT: Trilho = {
  minimo: 0,
  maximo: 100,
  faixas: [
    {
      de: CSAT_SAUDAVEL.de,
      ate: CSAT_SAUDAVEL.ate,
      rotulo: `banda saudável ${CSAT_SAUDAVEL.de}–${CSAT_SAUDAVEL.ate}%`,
      cor: "bg-medido-fraco",
    },
  ],
};

const TRILHO_LATENCIA: Trilho = {
  minimo: 0,
  maximo: LIMIARES_LATENCIA.degradando,
  faixas: [
    {
      de: 0,
      ate: LIMIARES_LATENCIA.pico,
      rotulo: `até ${LIMIARES_LATENCIA.pico}s pico de CSAT (~84,7%)`,
      cor: "bg-promotor",
    },
    {
      de: LIMIARES_LATENCIA.pico,
      ate: LIMIARES_LATENCIA.saudavel,
      rotulo: `até ${LIMIARES_LATENCIA.saudavel}s saudável`,
      cor: "bg-neutro",
    },
    {
      de: LIMIARES_LATENCIA.saudavel,
      ate: LIMIARES_LATENCIA.degradando,
      rotulo: `até ${LIMIARES_LATENCIA.degradando / 60}min degradando`,
      cor: "bg-detrator",
    },
  ],
};

export function FaixaIndicadores({
  indicadores,
  tempoMediano,
  erro,
  rotuloDoPeriodo,
}: {
  indicadores: IndicadoresDoPeriodo;
  tempoMediano: number | null;
  /** Falha da listagem: todos os quatro dependem dela. */
  erro?: string;
  rotuloDoPeriodo: string;
}) {
  const semSinalTexto =
    indicadores.semSinal > 0
      ? `${indicadores.semSinal} de ${indicadores.total} sem fala do cliente — fora do cálculo, nunca como zero.`
      : undefined;

  return (
    <section
      aria-label={`Indicadores de ${rotuloDoPeriodo}`}
      className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4"
    >
      <CartaoIndicador
        rotulo="NPS inferido"
        qualificacao="estimativa"
        estimativa
        erro={erro}
        valor={indicadores.nps}
        formatado={
          indicadores.nps === null ? undefined : formatarNps(indicadores.nps)
        }
        trilho={TRILHO_NPS}
        explicacaoVazio={
          indicadores.total === 0
            ? "Nenhum atendimento no período selecionado."
            : "Nenhum atendimento do período tem fala do cliente, então não há categoria para agregar."
        }
        rodape={
          indicadores.nps === null
            ? undefined
            : `Sobre ${indicadores.comSinal} atendimento(s) com sinal. ${semSinalTexto ?? ""}`
        }
      />

      <CartaoIndicador
        rotulo="CSAT inferido"
        qualificacao="estimativa"
        estimativa
        unidade="%"
        erro={erro}
        valor={indicadores.csat}
        formatado={
          indicadores.csat === null
            ? undefined
            : formatarNumero(indicadores.csat)
        }
        trilho={TRILHO_CSAT}
        explicacaoVazio="Sem atendimento pontuado no período, não há proporção de satisfeitos a calcular."
        rodape={`Proporção de atendimentos com nota ≥ 7, a mesma regra do servidor.`}
      />

      <CartaoIndicador
        rotulo="Taxa de contenção"
        qualificacao="observado"
        unidade="%"
        erro={erro}
        valor={indicadores.containment}
        formatado={
          indicadores.containment === null
            ? undefined
            : formatarNumero(indicadores.containment)
        }
        trilho={{ minimo: 0, maximo: 100, faixas: [] }}
        explicacaoVazio="Nenhuma transcrição carregada no período — a contenção sai de escalou_para_humano, que vem com a conversa."
        rodape="Atendimentos resolvidos sem passar para um humano. Não depende de score."
      />

      <CartaoIndicador
        rotulo="Latência mediana"
        qualificacao="observado"
        erro={erro}
        valor={tempoMediano}
        formatado={
          tempoMediano === null ? undefined : formatarSegundos(tempoMediano)
        }
        trilho={TRILHO_LATENCIA}
        explicacaoVazio="Nenhum par pergunta → resposta no período: sem duas mensagens seguidas não há espera a medir."
        rodape="Mediana do intervalo entre a fala do cliente e a resposta seguinte, derivada dos timestamps."
      />
    </section>
  );
}
