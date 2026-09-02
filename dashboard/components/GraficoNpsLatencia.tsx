"use client";

import { useId, useState } from "react";
import { useRouter } from "next/navigation";
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
 * neste painel -- e o dourado da marca nunca entra em dado.
 */
export function GraficoNpsLatencia({ serie }: { serie: PontoSerie[] }) {
  const [verTabela, setVerTabela] = useState(false);
  const idTabela = useId();
  const roteador = useRouter();

  /**
   * Drill-down: o dia clicado vira o recorte de /atendimentos. Todo estado
   * apontado no grafico fica a um clique da lista que o explica -- sinalizar
   * um dia ruim sem caminho ate os atendimentos dele seria decoracao.
   */
  const abrirDia = (estado: { activeIndex?: number | string | null }) => {
    const bruto = estado?.activeIndex;
    const indice = typeof bruto === "string" ? Number(bruto) : bruto;
    if (indice == null || Number.isNaN(indice)) return;
    const ponto = serie[indice];
    if (!ponto || ponto.atendimentos === 0) return;
    roteador.push(`/dashboard/atendimentos?de=${ponto.dia}&ate=${ponto.dia}`);
  };

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
        <div className="px-2 pb-2">
          {/* O VISOR: superficie SOLIDA embutida no vidro do Painel. Blur atras
              de uma serie de meio ponto come a serie, e a sobreposicao NPS x
              latencia e compromisso vinculante do PRODUCT.md -- nao pode
              perder legibilidade por causa de um efeito de superficie. */}
          <div className="rounded-md bg-card p-3">
            <div className="h-[300px] sm:h-[340px]">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={serie}
                  margin={{ top: 8, right: 18, bottom: 22, left: 6 }}
                  onClick={abrirDia}
                  className="cursor-pointer"
                >
                  {/* As BARRAS DE COMPASSO: um filete por dia, mais fraco que a
                      regua horizontal. Elas agrupam o tempo sem gastar legenda --
                      quem varre a linha ve onde um dia termina e o outro comeca. */}
                  <CartesianGrid
                    stroke="var(--border)"
                    strokeWidth={1}
                    vertical={false}
                  />
                  <CartesianGrid
                    stroke="var(--compasso)"
                    strokeWidth={1}
                    horizontal={false}
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
                  {/* O CURSOR DE LEITURA. E o unico lugar do sistema onde o
                      dourado da marca toca a area de dado, e ele nao codifica valor
                      nenhum: marca ONDE VOCE ESTA na linha do tempo, como a barra
                      de reproducao de um editor de partitura. Nenhuma serie,
                      categoria ou barra usa esta cor. */}
                  <Tooltip
                    cursor={{ stroke: "var(--primary)", strokeWidth: 1.5 }}
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
          </div>
          <FaixaDePresenca serie={serie} />
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
      {ponto.atendimentos > 0 ? (
        <p className="mt-1.5 text-[0.6875rem] text-muted-foreground">
          Clique para abrir os atendimentos do dia.
        </p>
      ) : null}
    </div>
  );
}

/** Mitigacao 3: o mesmo dado sem geometria nenhuma entre as duas grandezas. */
function TabelaDaSerie({ id, serie }: { id: string; serie: PontoSerie[] }) {
  return (
    <div id={id} className="max-h-[340px] overflow-auto bg-card">
      <Table className="text-xs">
        <TableHeader className="sticky top-0 z-10">
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

/**
 * A FAIXA DE PRESENCA: um marcador por dia, sob a linha do tempo.
 *
 * Aqui mora a peca central da notacao. Numa partitura, a cabeca de nota VAZADA
 * ocupa o tempo e nao soa -- e e exatamente isso que um dia com atendimento e
 * sem nenhuma fala do cliente e. O principio "ausencia de dado nao e
 * insatisfacao" deixa de ser nota de rodape e vira FORMA:
 *
 *   - cheio  = o dia tem atendimento pontuado, e ele esta na linha acima;
 *   - vazado = o dia teve atendimento, mas nenhum com sinal do cliente;
 *   - nada   = nao houve atendimento.
 *
 * O vazado NAO entra na escala de NPS, e por isso vive fora da area de plotagem
 * em vez de virar um ponto em zero -- ponto em zero seria dizer "NPS 0", que e
 * medicao inventada.
 *
 * Os recuos laterais espelham as larguras dos dois eixos Y do grafico para que
 * cada marcador caia sob o seu dia.
 */
function FaixaDePresenca({ serie }: { serie: PontoSerie[] }) {
  if (serie.length === 0) return null;

  const semSinal = serie.filter((p) => p.atendimentos > 0 && p.comScore === 0);

  return (
    <div className="mt-1 pl-[58px] pr-[76px]">
      <div className="flex items-center" role="img"
        aria-label={
          semSinal.length === 0
            ? "Todos os dias com atendimento tem pelo menos um atendimento pontuado."
            : `${semSinal.length} dia(s) com atendimento e nenhum pontuado: ${semSinal.map((p) => p.rotulo).join(", ")}.`
        }
      >
        {serie.map((ponto) => {
          const pontuado = ponto.comScore > 0;
          const vazio = ponto.atendimentos === 0;
          return (
            <span
              key={ponto.dia}
              className="flex flex-1 justify-center"
              title={
                vazio
                  ? `${ponto.rotulo}: nenhum atendimento`
                  : pontuado
                    ? `${ponto.rotulo}: ${ponto.comScore} de ${ponto.atendimentos} atendimento(s) pontuado(s)`
                    : `${ponto.rotulo}: ${ponto.atendimentos} atendimento(s), nenhum com fala do cliente — sem sinal`
              }
            >
              {vazio ? (
                <span aria-hidden className="block size-[7px]" />
              ) : (
                <span
                  aria-hidden
                  className={
                    pontuado
                      ? "block size-[7px] rounded-full bg-medido"
                      : "block size-[7px] rounded-full border border-muted-foreground"
                  }
                />
              )}
            </span>
          );
        })}
      </div>
      <p className="mt-1.5 text-[0.6875rem] leading-tight text-muted-foreground">
        Cada marca é um dia:{" "}
        <span className="inline-block size-[7px] translate-y-px rounded-full bg-medido" />{" "}
        pontuado ·{" "}
        <span className="inline-block size-[7px] translate-y-px rounded-full border border-muted-foreground" />{" "}
        houve atendimento, nenhum com fala do cliente — não entra na escala e
        nunca como zero.
      </p>
    </div>
  );
}
