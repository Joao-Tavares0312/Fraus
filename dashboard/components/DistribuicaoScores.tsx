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
import { SegmentoLED } from "@/components/instrumento/SegmentoLED";
import { legendaDasFaixas, type BarraDistribuicao } from "@/lib/derivacoes";
import { DEFINICAO_SEM_SINAL_AGREGADO, ROTULO_CATEGORIA } from "@/lib/formato";
import { EstadoVazio } from "./EstadoVazio";
import { CabecaVazada } from "./CabecaVazada";

/**
 * Escala DIVERGENTE do NPS. Os tres tokens sao os do `DESIGN.md`; nenhum deles
 * e o lime da marca, e promotor e teal justamente para ficar longe dele.
 */
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
 * quando ele simplesmente nao falou.
 */
export function DistribuicaoScores({
  barras,
  semSinal,
  faixas,
}: {
  barras: BarraDistribuicao[];
  semSinal: number;
  /**
   * As faixas VIGENTES, as mesmas que coloriram `barras`. `undefined` quando
   * `GET /configuracoes` nao respondeu -- ai a legenda cai no padrao de
   * fabrica, que e tambem o que `categoriaDaNota` usou para pintar. A legenda
   * nunca digita os cortes de novo (invariante 4).
   */
  faixas: Record<string, [number, number]> | undefined;
}) {
  const total = barras.reduce((soma, barra) => soma + barra.quantidade, 0);

  if (total === 0 && semSinal === 0) {
    return (
      <EstadoVazio
        className="m-5"
        titulo="Nenhum atendimento no período"
        explicacao="A distribuição é montada a partir da lista de conversas recortada pelo período; nenhuma sobrou no filtro atual."
      />
    );
  }

  return (
    <div className="flex flex-col lg:flex-row">
      <div className="min-w-0 flex-1 px-2 pt-4 pb-1">
        {total === 0 ? (
          <EstadoVazio
            className="m-3"
            titulo="Nenhum atendimento pontuado"
            explicacao={`Todos os atendimentos do período estão sem sinal — ${DEFINICAO_SEM_SINAL_AGREGADO} —, então não há nota inferida para distribuir.`}
          />
        ) : (
          <div className="h-[228px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={barras}
                margin={{ top: 4, right: 8, bottom: 22, left: 0 }}
              >
                <XAxis
                  dataKey="rotulo"
                  tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                  tickLine={false}
                  axisLine={{ stroke: "var(--border)" }}
                  label={{
                    value: "nota inferida (0–10)",
                    position: "insideBottom",
                    offset: -14,
                    style: { fill: "var(--muted-foreground)", fontSize: 11 },
                  }}
                />
                <YAxis
                  width={40}
                  allowDecimals={false}
                  tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  label={{
                    value: "atendimentos",
                    angle: -90,
                    position: "insideLeft",
                    offset: 14,
                    style: {
                      fill: "var(--muted-foreground)",
                      fontSize: 11,
                      textAnchor: "middle",
                    },
                  }}
                />
                <Tooltip cursor={{ fill: "var(--muted)" }} content={<Dica />} />
                {/* Sem raio: o Instrumento e retangular de ponta a ponta, e uma
                    barra de histograma arredondada le como decoracao. */}
                <Bar dataKey="quantidade" isAnimationActive={false}>
                  {barras.map((barra) => (
                    <Cell
                      key={barra.nota}
                      fill={COR_DA_CATEGORIA[barra.categoria]}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        <ul className="flex flex-wrap gap-x-5 gap-y-1.5 px-3 pt-2">
          {legendaDasFaixas(faixas).map((faixa) => (
            <li
              key={faixa.categoria}
              className="flex items-center gap-2 text-xs text-muted-foreground"
            >
              <span
                aria-hidden
                className="size-2 rounded-full"
                style={{ background: COR_DA_CATEGORIA[faixa.categoria] }}
              />
              {faixa.rotulo}
            </li>
          ))}
        </ul>
      </div>

      <aside className="flex shrink-0 flex-col justify-center gap-1.5 border-t border-border px-5 py-4 lg:w-56 lg:border-t-0 lg:border-l">
        <p className="rotulo-instrumento">Fora da escala</p>
        {/* A CONTAGEM de ausencias e um numero, entao vai no display, mas na
            TINTA (nao no azul do medido): ela conta o que NAO foi medido, e o
            anel oco + a palavra ao lado dizem isso sem depender da cor. */}
        <p className="flex items-end gap-2.5">
          <SegmentoLED
            valor={String(semSinal)}
            rotulo="atendimentos sem sinal, fora da escala"
            altura={30}
            cor="tinta"
          />
          <CabecaVazada className="pb-0.5" />
        </p>
        <p className="text-xs leading-relaxed text-muted-foreground">
          Atendimentos sem sinal: {DEFINICAO_SEM_SINAL_AGREGADO}. Não têm nota e não entram como zero:
          ausência de dado não é insatisfação, e cinza não pertence à escala de
          satisfação de propósito.
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
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-popover-foreground">
      <p className="text-xs font-semibold">
        Nota {barra.rotulo} · {ROTULO_CATEGORIA[barra.categoria]}
      </p>
      <p className="num mt-0.5 text-xs text-muted-foreground">
        {barra.quantidade}{" "}
        {barra.quantidade === 1 ? "atendimento" : "atendimentos"}
      </p>
    </div>
  );
}
