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
import { Button } from "@/components/ui/button";
import type { PontoSerie } from "@/lib/derivacoes";
import { formatarNps, formatarSegundos } from "@/lib/formato";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EstadoVazio } from "./EstadoVazio";

/**
 * O grafico que carrega a tese do trabalho: NPS inferido e latencia mediana
 * SOBREPOSTOS, com eixos Y distintos.
 *
 * Sobrepor duas escalas e, em geral, antipadrao reconhecido -- o alinhamento
 * entre as curvas e arbitrario e sugere correlacao que o dado nao tem. Aqui a
 * sobreposicao e requisito de produto: otimizar um KPI isolado quebra outro
 * (empurrar deflexao derruba CSAT), e cartoes separados escondem exatamente o
 * trade-off que o produto existe para mostrar. As TRES mitigacoes obrigatorias:
 *
 *   1. dominio FIXO em cada eixo -- NPS em [-100, +100], que e o dominio real
 *      do indicador, e latencia a partir de zero. Nenhum dos dois se ajusta ao
 *      dado, que e de onde vem o alinhamento arbitrario;
 *   2. cada eixo rotulado e colorido com a sua serie, e a latencia SEMPRE
 *      tracejada -- cor nao e o unico canal;
 *   3. visao de tabela no mesmo painel: quem precisa do numero exato nao
 *      depende da leitura cruzada.
 *
 * Cor: azul (`--medido`) e o que foi medido/inferido pela maquina; magenta
 * (`--tempo`) e latencia. O ambar (`--dito`) nao aparece aqui -- nao ha fala
 * neste painel -- e o lime da marca nunca entra em dado.
 */
export function GraficoNpsLatencia({ serie }: { serie: PontoSerie[] }) {
  const [verTabela, setVerTabela] = useState(false);
  const idTabela = useId();

  if (serie.length === 0) {
    return (
      <EstadoVazio
        className="m-5"
        titulo="Sem série temporal para desenhar"
        explicacao="Nenhum atendimento no período selecionado, então não há dias para agregar. A série é montada no cliente, agrupando as conversas por data de início."
        endpoint="GET /serie-temporal?de=&ate="
      />
    );
  }

  // Domínio da latência: fixo a partir de zero e arredondado para o próximo
  // múltiplo de 30 s. Amarrar o topo ao maior valor exato do recorte faria o
  // eixo mudar a cada filtro, e a mesma curva pareceria outra.
  // Dia sem latencia e FILTRADO, nao convertido em zero: um `?? 0` aqui seria
  // inofensivo por causa do piso de 30 s, mas o produto nao mantem excecoes
  // convenientes para a propria regra.
  const maiorLatencia = Math.max(
    30,
    ...serie
      .map((ponto) => ponto.latenciaMediana)
      .filter((valor): valor is number => valor !== null),
  );
  const topoLatencia = Math.ceil(maiorLatencia / 30) * 30;

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
        <Legenda />
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => setVerTabela((antes) => !antes)}
          aria-expanded={verTabela}
          aria-controls={idTabela}
          className="sem-impressao"
        >
          {verTabela ? "Ver gráfico" : "Ver tabela"}
        </Button>
      </div>

      {verTabela ? (
        <TabelaDaSerie id={idTabela} serie={serie} />
      ) : (
        // Altura FIXA por breakpoint: gráfico que muda de altura ao trocar de
        // dado causa salto de layout.
        <div className="h-[300px] px-2 pb-2 sm:h-[340px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={serie}
              margin={{ top: 8, right: 18, bottom: 22, left: 6 }}
            >
              <CartesianGrid
                stroke="var(--border)"
                strokeWidth={1}
                vertical={false}
              />
              <XAxis
                dataKey="rotulo"
                tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: "var(--border)" }}
                minTickGap={16}
                label={{
                  value: "Dia de início do atendimento",
                  position: "insideBottom",
                  offset: -14,
                  style: {
                    fill: "var(--muted-foreground)",
                    fontSize: 11,
                    textAnchor: "middle",
                  },
                }}
              />
              <YAxis
                yAxisId="nps"
                domain={[-100, 100]}
                ticks={[-100, -50, 0, 50, 100]}
                width={52}
                tick={{ fill: "var(--medido-texto)", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                label={{
                  value: "NPS inferido (−100 a +100)",
                  angle: -90,
                  position: "insideLeft",
                  offset: 14,
                  style: {
                    fill: "var(--medido-texto)",
                    fontSize: 11,
                    textAnchor: "middle",
                  },
                }}
              />
              <YAxis
                yAxisId="latencia"
                orientation="right"
                domain={[0, topoLatencia]}
                width={58}
                tick={{ fill: "var(--tempo-texto)", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(valor: number) => `${Math.round(valor)}s`}
                label={{
                  value: "Latência mediana (a partir de 0 s)",
                  angle: 90,
                  position: "insideRight",
                  offset: 14,
                  style: {
                    fill: "var(--tempo-texto)",
                    fontSize: 11,
                    textAnchor: "middle",
                  },
                }}
              />
              <ReferenceLine
                yAxisId="nps"
                y={0}
                stroke="var(--border)"
                strokeWidth={1}
              />
              <Tooltip
                cursor={{ stroke: "var(--muted-foreground)", strokeWidth: 1 }}
                content={<Dica />}
              />
              <Line
                yAxisId="nps"
                type="monotone"
                dataKey="nps"
                name="NPS inferido"
                stroke="var(--medido)"
                strokeWidth={2}
                dot={{ r: 3, fill: "var(--card)", strokeWidth: 2 }}
                activeDot={{ r: 5, strokeWidth: 2, stroke: "var(--card)" }}
                connectNulls={false}
                isAnimationActive={false}
              />
              <Line
                yAxisId="latencia"
                type="monotone"
                dataKey="latenciaMediana"
                name="Latência mediana"
                stroke="var(--tempo)"
                strokeWidth={2}
                strokeDasharray="5 3"
                dot={{ r: 3, fill: "var(--card)", strokeWidth: 2 }}
                activeDot={{ r: 5, strokeWidth: 2, stroke: "var(--card)" }}
                connectNulls={false}
                isAnimationActive={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

function Legenda() {
  return (
    <ul className="flex flex-wrap items-center gap-x-5 gap-y-1.5">
      <li className="flex items-center gap-2 text-xs text-muted-foreground">
        <svg width="22" height="8" aria-hidden>
          <line
            x1="0"
            y1="4"
            x2="22"
            y2="4"
            stroke="var(--medido)"
            strokeWidth="2"
          />
        </svg>
        <span className="text-medido-texto">NPS inferido</span>
        <span>(estimativa, linha contínua)</span>
      </li>
      <li className="flex items-center gap-2 text-xs text-muted-foreground">
        <svg width="22" height="8" aria-hidden>
          <line
            x1="0"
            y1="4"
            x2="22"
            y2="4"
            stroke="var(--tempo)"
            strokeWidth="2"
            strokeDasharray="5 3"
          />
        </svg>
        <span className="text-tempo-texto">Latência mediana</span>
        <span>(observada, tracejada)</span>
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
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-popover-foreground">
      <p className="text-xs font-semibold">{ponto.rotulo}</p>
      <dl className="mt-1.5 grid grid-cols-[auto_auto] gap-x-3 gap-y-1 text-xs">
        <dt className="text-medido-texto">NPS inferido</dt>
        <dd className="num text-right font-medium">
          {ponto.nps === null ? (
            <span className="text-muted-foreground">sem sinal</span>
          ) : (
            formatarNps(ponto.nps)
          )}
        </dd>
        <dt className="text-tempo-texto">Latência mediana</dt>
        <dd className="num text-right font-medium">
          {ponto.latenciaMediana === null
            ? "—"
            : formatarSegundos(ponto.latenciaMediana)}
        </dd>
        <dt className="text-muted-foreground">Atendimentos</dt>
        <dd className="num text-right font-medium">
          {ponto.atendimentos}
          {ponto.comScore < ponto.atendimentos
            ? ` (${ponto.atendimentos - ponto.comScore} sem sinal)`
            : ""}
        </dd>
      </dl>
    </div>
  );
}

/** Mitigacao 3: o mesmo dado sem geometria nenhuma entre as duas grandezas. */
function TabelaDaSerie({ id, serie }: { id: string; serie: PontoSerie[] }) {
  return (
    <div id={id} className="max-h-[340px] overflow-auto">
      <Table className="text-xs">
        <TableHeader className="sticky top-0 z-10 bg-muted">
          <TableRow>
            <TableHead>Dia</TableHead>
            <TableHead className="text-right">NPS inferido</TableHead>
            <TableHead className="text-right">Latência mediana</TableHead>
            <TableHead className="text-right">Atendimentos</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {serie.map((ponto) => (
            <TableRow key={ponto.dia}>
              <TableCell className="num">{ponto.rotulo}</TableCell>
              <TableCell className="num text-right">
                {ponto.nps === null ? (
                  <span className="text-muted-foreground">sem sinal</span>
                ) : (
                  formatarNps(ponto.nps)
                )}
              </TableCell>
              <TableCell className="num text-right">
                {ponto.latenciaMediana === null
                  ? "—"
                  : formatarSegundos(ponto.latenciaMediana)}
              </TableCell>
              <TableCell className="num text-right text-muted-foreground">
                {ponto.atendimentos}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
