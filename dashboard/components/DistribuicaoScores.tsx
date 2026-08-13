"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { BarraDistribuicao } from "@/lib/derivacoes";
import { FAIXAS_NPS } from "@/lib/derivacoes";
import { ROTULO_CATEGORIA } from "@/lib/formato";
import { EstadoVazio } from "./EstadoVazio";

const COR_DA_CATEGORIA: Record<string, string> = {
  detrator: "var(--detrator)",
  neutro: "var(--neutro)",
  promotor: "var(--promotor)",
};

/**
 * Distribuicao das notas 0-10 inferidas, com as tres faixas de NPS marcadas.
 *
 * "sem sinal" fica FORA do eixo, num bloco proprio a direita. Colocar essas
 * conversas na barra do zero seria dizer que o cliente ficou insatisfeito
 * quando ele simplesmente nao falou -- exatamente o erro que o produto existe
 * para evitar.
 */
export function DistribuicaoScores({
  barras,
  semSinal,
}: {
  barras: BarraDistribuicao[];
  semSinal: number;
}) {
  const total = barras.reduce((soma, barra) => soma + barra.quantidade, 0);

  if (total === 0 && semSinal === 0) {
    return (
      <EstadoVazio
        titulo="Nenhum atendimento na janela"
        explicacao="A distribuição é montada a partir da lista de conversas; a API não devolveu nenhuma."
      />
    );
  }

  return (
    <div className="flex flex-col gap-0 lg:flex-row">
      <div className="min-w-0 flex-1 px-2 pt-4 pb-1">
        {total === 0 ? (
          <EstadoVazio
            titulo="Nenhum atendimento pontuado"
            explicacao="Todos os atendimentos da janela estão sem sinal do cliente, então não há nota inferida para distribuir."
          />
        ) : (
          <ResponsiveContainer width="100%" height={228}>
            <BarChart data={barras} margin={{ top: 4, right: 8, bottom: 20, left: 0 }}>
              <XAxis
                dataKey="rotulo"
                tick={{ fill: "var(--tinta-3)", fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: "var(--regua)" }}
                label={{
                  value: "nota inferida (0–10)",
                  position: "insideBottom",
                  offset: -12,
                  style: { fill: "var(--tinta-3)", fontSize: 11 },
                }}
              />
              <YAxis
                width={36}
                allowDecimals={false}
                tick={{ fill: "var(--tinta-3)", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip cursor={{ fill: "var(--superficie-2)" }} content={<Dica />} />
              <Bar dataKey="quantidade" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                {barras.map((barra) => (
                  <Cell key={barra.nota} fill={COR_DA_CATEGORIA[barra.categoria]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}

        <ul className="flex flex-wrap gap-x-5 gap-y-1.5 px-3 pt-2">
          {FAIXAS_NPS.map((faixa) => (
            <li
              key={faixa.categoria}
              className="flex items-center gap-2 text-[0.75rem] text-[var(--tinta-2)]"
            >
              <span
                aria-hidden
                className="h-[7px] w-[7px] rounded-full"
                style={{ background: COR_DA_CATEGORIA[faixa.categoria] }}
              />
              {faixa.rotulo}
            </li>
          ))}
        </ul>
      </div>

      <aside className="flex shrink-0 flex-col justify-center gap-1.5 border-t border-[var(--filete)] px-5 py-4 lg:w-56 lg:border-t-0 lg:border-l">
        <p className="text-[0.8125rem] font-medium text-[var(--tinta-2)]">
          Fora da escala
        </p>
        <p className="flex items-baseline gap-2">
          <span className="text-[1.75rem] leading-none font-semibold text-[var(--tinta-3)]">
            {semSinal}
          </span>
          <span className="text-[0.8125rem] text-[var(--tinta-3)]">sem sinal</span>
        </p>
        <p className="text-[0.75rem] leading-[1.5] text-[var(--tinta-3)]">
          Atendimentos sem fala do cliente. Não têm nota e não entram como zero:
          ausência de dado não é insatisfação.
        </p>
      </aside>
    </div>
  );
}

type DicaProps = {
  active?: boolean;
  payload?: { payload: BarraDistribuicao }[];
};

function Dica({ active, payload }: DicaProps) {
  if (!active || !payload?.length) return null;
  const barra = payload[0].payload;
  return (
    <div className="border border-[var(--regua)] bg-[var(--superficie)] px-3 py-2 shadow-[0_2px_8px_rgba(0,0,0,0.12)]">
      <p className="text-[0.75rem] font-semibold text-[var(--tinta)]">
        Nota {barra.rotulo} · {ROTULO_CATEGORIA[barra.categoria]}
      </p>
      <p className="mt-0.5 text-[0.75rem] tabular-nums text-[var(--tinta-2)]">
        {barra.quantidade}{" "}
        {barra.quantidade === 1 ? "atendimento" : "atendimentos"}
      </p>
    </div>
  );
}
