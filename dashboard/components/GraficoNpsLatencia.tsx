"use client";

import { useId, useState } from "react";
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PontoSerie } from "@/lib/derivacoes";
import { formatarNps, formatarSegundos } from "@/lib/formato";
import { EstadoVazio } from "./EstadoVazio";

/**
 * O grafico que carrega a tese do trabalho: NPS inferido e latencia mediana
 * SOBREPOSTOS, com eixos Y distintos.
 *
 * Sobrepor duas escalas e, em geral, um erro de dataviz -- o alinhamento entre
 * elas e arbitrario e sugere correlacao que o dado nao tem. Aqui a sobreposicao
 * e requisito de produto e existe justamente para expor o trade-off que cards
 * isolados escondem (empurrar deflexao derruba CSAT). As tres mitigacoes:
 *
 *   1. o eixo do NPS e fixo em [-100, +100], o dominio REAL do indicador --
 *      nao um intervalo ajustado ao dado, que seria a origem do alinhamento
 *      arbitrario; o eixo de latencia comeca em zero;
 *   2. cada eixo leva o nome e a cor da sua serie, e a legenda de rodape diz em
 *      voz alta que as escalas sao independentes;
 *   3. existe a visao de tabela, onde os dois numeros aparecem sem geometria
 *      nenhuma entre eles.
 *
 * Cores: azul = grandeza inferida, laranja = grandeza observada. E a mesma
 * convencao da faixa de indicadores e do detalhe do atendimento.
 */
export function GraficoNpsLatencia({ serie }: { serie: PontoSerie[] }) {
  const [verTabela, setVerTabela] = useState(false);
  const idTabela = useId();

  if (serie.length === 0) {
    return (
      <EstadoVazio
        titulo="Sem série temporal para desenhar"
        explicacao="Nenhum atendimento foi devolvido pela API, então não há dias para agregar. A série é montada no cliente, agrupando as conversas por data de início."
        endpoint="GET /serie-temporal"
      />
    );
  }

  const maiorLatencia = Math.max(
    10,
    ...serie.map((ponto) => ponto.latenciaMediana ?? 0),
  );

  return (
    <div>
      <div className="flex items-center justify-between gap-4 px-5 pt-4">
        <Legenda />
        <button
          type="button"
          onClick={() => setVerTabela((antes) => !antes)}
          aria-expanded={verTabela}
          aria-controls={idTabela}
          className="sem-impressao shrink-0 rounded-[2px] border border-[var(--filete)] px-2.5 py-1 text-[0.75rem] text-[var(--tinta-2)] transition-colors duration-150 hover:border-[var(--regua)] hover:text-[var(--tinta)]"
        >
          {verTabela ? "Ver gráfico" : "Ver tabela"}
        </button>
      </div>

      {verTabela ? (
        <TabelaDaSerie id={idTabela} serie={serie} />
      ) : (
        <div className="px-2 pt-3 pb-1">
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={serie} margin={{ top: 8, right: 16, bottom: 28, left: 4 }}>
              <CartesianGrid
                stroke="var(--filete)"
                strokeWidth={1}
                vertical={false}
              />
              <XAxis
                dataKey="rotulo"
                tick={{ fill: "var(--tinta-3)", fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: "var(--regua)" }}
                minTickGap={16}
              />
              <YAxis
                yAxisId="nps"
                domain={[-100, 100]}
                ticks={[-100, -50, 0, 50, 100]}
                width={44}
                tick={{ fill: "var(--serie-nps)", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                label={{
                  value: "NPS inferido",
                  angle: -90,
                  position: "insideLeft",
                  offset: 12,
                  style: { fill: "var(--serie-nps)", fontSize: 11, textAnchor: "middle" },
                }}
              />
              <YAxis
                yAxisId="latencia"
                orientation="right"
                domain={[0, Math.ceil(maiorLatencia * 1.15)]}
                width={52}
                tick={{ fill: "var(--serie-latencia)", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(valor: number) => `${Math.round(valor)}s`}
                label={{
                  value: "Latência mediana",
                  angle: 90,
                  position: "insideRight",
                  offset: 12,
                  style: {
                    fill: "var(--serie-latencia)",
                    fontSize: 11,
                    textAnchor: "middle",
                  },
                }}
              />
              <ReferenceLine
                yAxisId="nps"
                y={0}
                stroke="var(--regua)"
                strokeWidth={1}
              />
              <Tooltip
                cursor={{ stroke: "var(--regua)", strokeWidth: 1 }}
                content={<Dica />}
              />
              <Line
                yAxisId="nps"
                type="monotone"
                dataKey="nps"
                name="NPS inferido"
                stroke="var(--serie-nps)"
                strokeWidth={2}
                dot={{ r: 3, fill: "var(--superficie)", strokeWidth: 2 }}
                activeDot={{ r: 5, strokeWidth: 2, stroke: "var(--superficie)" }}
                connectNulls={false}
                isAnimationActive={false}
              />
              <Line
                yAxisId="latencia"
                type="monotone"
                dataKey="latenciaMediana"
                name="Latência mediana"
                stroke="var(--serie-latencia)"
                strokeWidth={2}
                strokeDasharray="5 3"
                dot={{ r: 3, fill: "var(--superficie)", strokeWidth: 2 }}
                activeDot={{ r: 5, strokeWidth: 2, stroke: "var(--superficie)" }}
                connectNulls={false}
                isAnimationActive={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      <p className="border-t border-[var(--filete)] px-5 py-3 text-[0.75rem] leading-[1.5] text-[var(--tinta-3)]">
        As duas escalas são independentes: a altura de uma curva em relação à
        outra não significa nada, só o formato de cada uma ao longo do tempo. O
        eixo do NPS é o domínio inteiro do indicador (−100 a +100) e o da
        latência começa em zero, para que o alinhamento não seja escolhido.
        Dias sem nenhum atendimento pontuado ficam com a linha do NPS
        interrompida — nunca em zero.
      </p>
    </div>
  );
}

function Legenda() {
  return (
    <ul className="flex flex-wrap items-center gap-x-5 gap-y-1.5">
      <li className="flex items-center gap-2 text-[0.8125rem] text-[var(--tinta-2)]">
        <svg width="20" height="8" aria-hidden>
          <line
            x1="0"
            y1="4"
            x2="20"
            y2="4"
            stroke="var(--serie-nps)"
            strokeWidth="2"
          />
        </svg>
        NPS inferido <span className="text-[var(--tinta-3)]">(estimativa)</span>
      </li>
      <li className="flex items-center gap-2 text-[0.8125rem] text-[var(--tinta-2)]">
        <svg width="20" height="8" aria-hidden>
          <line
            x1="0"
            y1="4"
            x2="20"
            y2="4"
            stroke="var(--serie-latencia)"
            strokeWidth="2"
            strokeDasharray="5 3"
          />
        </svg>
        Latência mediana <span className="text-[var(--tinta-3)]">(observada)</span>
      </li>
    </ul>
  );
}

type DicaProps = {
  active?: boolean;
  payload?: { payload: PontoSerie }[];
};

function Dica({ active, payload }: DicaProps) {
  if (!active || !payload?.length) return null;
  const ponto = payload[0].payload;

  return (
    <div className="border border-[var(--regua)] bg-[var(--superficie)] px-3 py-2 shadow-[0_2px_8px_rgba(0,0,0,0.12)]">
      <p className="text-[0.75rem] font-semibold text-[var(--tinta)]">
        {ponto.rotulo}
      </p>
      <dl className="mt-1.5 grid grid-cols-[auto_auto] gap-x-3 gap-y-1 text-[0.75rem]">
        <dt className="text-[var(--tinta-2)]">NPS inferido</dt>
        <dd className="text-right font-medium tabular-nums text-[var(--tinta)]">
          {ponto.nps === null ? "sem sinal" : formatarNps(ponto.nps)}
        </dd>
        <dt className="text-[var(--tinta-2)]">Latência mediana</dt>
        <dd className="text-right font-medium tabular-nums text-[var(--tinta)]">
          {ponto.latenciaMediana === null
            ? "—"
            : formatarSegundos(ponto.latenciaMediana)}
        </dd>
        <dt className="text-[var(--tinta-2)]">Atendimentos</dt>
        <dd className="text-right font-medium tabular-nums text-[var(--tinta)]">
          {ponto.atendimentos}
          {ponto.comScore < ponto.atendimentos
            ? ` (${ponto.atendimentos - ponto.comScore} sem sinal)`
            : ""}
        </dd>
      </dl>
    </div>
  );
}

function TabelaDaSerie({ id, serie }: { id: string; serie: PontoSerie[] }) {
  return (
    <div id={id} className="max-h-[352px] overflow-auto">
      <table className="w-full border-collapse text-[0.8125rem]">
        <thead className="sticky top-0 bg-[var(--superficie-2)]">
          <tr className="text-left text-[0.75rem] text-[var(--tinta-2)]">
            <th scope="col" className="px-5 py-2 font-medium">Dia</th>
            <th scope="col" className="px-5 py-2 text-right font-medium">NPS inferido</th>
            <th scope="col" className="px-5 py-2 text-right font-medium">Latência mediana</th>
            <th scope="col" className="px-5 py-2 text-right font-medium">Atendimentos</th>
          </tr>
        </thead>
        <tbody>
          {serie.map((ponto) => (
            <tr key={ponto.dia} className="border-t border-[var(--filete)]">
              <td className="px-5 py-2 tabular-nums text-[var(--tinta)]">{ponto.rotulo}</td>
              <td className="px-5 py-2 text-right tabular-nums text-[var(--tinta)]">
                {ponto.nps === null ? (
                  <span className="text-[var(--tinta-3)]">sem sinal</span>
                ) : (
                  formatarNps(ponto.nps)
                )}
              </td>
              <td className="px-5 py-2 text-right tabular-nums text-[var(--tinta)]">
                {ponto.latenciaMediana === null
                  ? "—"
                  : formatarSegundos(ponto.latenciaMediana)}
              </td>
              <td className="px-5 py-2 text-right tabular-nums text-[var(--tinta-2)]">
                {ponto.atendimentos}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
