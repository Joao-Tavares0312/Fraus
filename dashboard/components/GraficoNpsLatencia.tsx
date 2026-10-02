"use client";

import { useId, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Bar,
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
import {
  DEFINICAO_SEM_SINAL_AGREGADO,
  formatarNps,
  formatarSegundos,
} from "@/lib/formato";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EstadoVazio } from "./EstadoVazio";
import { IconeDeAcao } from "@/components/IconeDeAcao";

/**
 * O cursor de leitura: um filete dourado TRACEJADO vertical no dia apontado.
 * O `Tooltip` do Recharts entrega, num grafico com barras, a BANDA do dia
 * (x, y, width, height); num so de linhas entrega `points`. As duas formas
 * viram o mesmo filete, para o cursor nao depender de qual serie o grafico
 * desenha.
 */
type CursorProps = {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  points?: { x: number; y: number }[];
};

function CursorDeLeitura({ x, y, width, height, points }: CursorProps) {
  const linha = points && points.length >= 2 ? points : null;
  const posX = linha ? linha[0].x : (x ?? 0) + (width ?? 0) / 2;
  const topo = linha ? Math.min(linha[0].y, linha[1].y) : (y ?? 0);
  const base = linha
    ? Math.max(linha[0].y, linha[1].y)
    : (y ?? 0) + (height ?? 0);
  return (
    <line
      x1={posX}
      x2={posX}
      y1={topo}
      y2={base}
      stroke="var(--primary)"
      strokeWidth={1.5}
      strokeDasharray="3 3"
      pointerEvents="none"
    />
  );
}

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
 *   2. cada eixo rotulado com a sua serie, e a FORMA separa as duas: o NPS e
 *      LINHA, a latencia e BARRA -- cor nao e o unico canal;
 *   3. visao de tabela no mesmo painel: quem precisa do numero exato nao
 *      depende da leitura cruzada.
 *
 * O INSTRUMENTO (30/09/2026) trocou a segunda linha tracejada magenta por
 * BARRAS: uma serie em barra e outra em linha nao se confundem nem em tela de
 * projetor, e a barra e a forma que a latencia tem em todo o produto (espera
 * como intervalo, nao como curva). As duas continuam medidas -- por isso o
 * grafico NAO usa a regua dito/medido (DESIGN.md §1.1: regua so onde o dado de
 * fato se divide).
 *
 * Cor: o NPS inferido e a tinta (`--foreground`), a latencia e o azul do
 * MEDIDO (`--medido`, barra a 30% de opacidade com contorno cheio -- o
 * preenchimento translucido sozinho nao cruza 3:1 contra o visor; o contorno
 * carrega o contraste). O ambar (`--dito`) nao aparece -- nao ha fala neste
 * painel -- e o dourado so aparece como o CURSOR DE LEITURA.
 */
export function GraficoNpsLatencia({ serie }: { serie: PontoSerie[] }) {
  const [verTabela, setVerTabela] = useState(false);
  // Numa tela estreita os dois TITULOS de eixo (rotacionados) comem quase 40% da
  // largura do grafico e sobra um traco de plotagem. Abaixo de 520px o titulo
  // vai para a LEGENDA -- onde o dominio de cada eixo continua escrito -- e o
  // eixo fica so com os numeros. Nada e removido: so muda de lugar.
  const [estreito, setEstreito] = useState(false);
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
        explicacao="Nenhum atendimento no período selecionado, então não há dias para agregar. A série vem agregada do servidor, por data de início do atendimento."
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
        ><IconeDeAcao acao="alternar" />
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
              <ResponsiveContainer
                width="100%"
                height="100%"
                onResize={(largura) => setEstreito(largura < 520)}
              >
                <ComposedChart
                  data={serie}
                  margin={{ top: 8, right: estreito ? 8 : 18, bottom: 22, left: estreito ? 0 : 6 }}
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
                    width={estreito ? 34 : 52}
                    tick={{ fill: "var(--foreground)", fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    label={estreito ? undefined : {
                      value: "NPS inferido (−100 a +100)",
                      angle: -90,
                      position: "insideLeft",
                      offset: 14,
                      style: {
                        fill: "var(--foreground)",
                        fontSize: 11,
                        textAnchor: "middle",
                      },
                    }}
                  />
                  <YAxis
                    yAxisId="latencia"
                    orientation="right"
                    domain={[0, topoLatencia]}
                    width={estreito ? 40 : 58}
                    tick={{ fill: "var(--medido-texto)", fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(valor: number) => `${Math.round(valor)}s`}
                    label={estreito ? undefined : {
                      value: "Latência mediana (a partir de 0 s)",
                      angle: 90,
                      position: "insideRight",
                      offset: 14,
                      style: {
                        fill: "var(--medido-texto)",
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
                  <Tooltip cursor={<CursorDeLeitura />} content={<Dica />} />
                  {/* A LATENCIA: BARRA, desenhada ANTES da linha para ficar
                      atras dela. Preenchimento a 30% mais contorno cheio -- o
                      contorno e o que cruza 3:1 contra o visor. Dia sem
                      latencia (`null`) nao gera barra: nunca uma barra de zero. */}
                  <Bar
                    yAxisId="latencia"
                    dataKey="latenciaMediana"
                    name="Latência mediana"
                    fill="var(--medido)"
                    fillOpacity={0.3}
                    stroke="var(--medido)"
                    strokeWidth={1}
                    maxBarSize={22}
                    isAnimationActive={false}
                  />
                  {/* O NPS: linha continua na tinta, 2px. Interrompida onde o
                      dia nao tem nota (`connectNulls={false}`) -- nunca em zero. */}
                  <Line
                    yAxisId="nps"
                    type="monotone"
                    dataKey="nps"
                    name="NPS inferido"
                    stroke="var(--foreground)"
                    strokeWidth={2}
                    dot={{
                      r: 3,
                      fill: "var(--card)",
                      stroke: "var(--foreground)",
                      strokeWidth: 2,
                    }}
                    activeDot={{
                      r: 5,
                      strokeWidth: 2,
                      stroke: "var(--card)",
                      fill: "var(--foreground)",
                    }}
                    connectNulls={false}
                    isAnimationActive={false}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
          <FaixaDePresenca serie={serie} estreito={estreito} />
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
            stroke="var(--foreground)"
            strokeWidth="2"
          />
        </svg>
        <span className="text-foreground">NPS inferido</span>
        <span>(estimativa, linha contínua, eixo de −100 a +100)</span>
      </li>
      <li className="flex items-center gap-2 text-xs text-muted-foreground">
        <svg width="22" height="10" aria-hidden>
          <rect
            x="1"
            y="1"
            width="20"
            height="8"
            fill="var(--medido)"
            fillOpacity="0.3"
            stroke="var(--medido)"
            strokeWidth="1"
          />
        </svg>
        <span className="text-medido-texto">Latência mediana</span>
        <span>(observada, barras, eixo a partir de 0 s)</span>
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
        <dt className="text-foreground">NPS inferido</dt>
        <dd className="num text-right font-medium">
          {ponto.nps === null ? (
            <span className="text-muted-foreground">sem sinal</span>
          ) : (
            formatarNps(ponto.nps)
          )}
        </dd>
        <dt className="text-medido-texto">Latência mediana</dt>
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
function FaixaDePresenca({
  serie,
  estreito,
}: {
  serie: PontoSerie[];
  estreito: boolean;
}) {
  if (serie.length === 0) return null;

  const semSinal = serie.filter((p) => p.atendimentos > 0 && p.comScore === 0);

  return (
    <div
      className="mt-1"
      // Os recuos espelham a largura dos dois eixos (mais a margem), para cada
      // marcador cair sob o seu dia: 52+6 / 58+18 no largo, 34+0 / 40+8 no estreito.
      style={{
        paddingLeft: estreito ? 34 : 58,
        paddingRight: estreito ? 48 : 76,
      }}
    >
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
                    : `${ponto.rotulo}: ${ponto.atendimentos} atendimento(s), nenhum pontuado (${DEFINICAO_SEM_SINAL_AGREGADO}) — sem sinal`
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
        houve atendimento, nenhum pontuado ({DEFINICAO_SEM_SINAL_AGREGADO}) —
        não entra na escala e nunca como zero.
      </p>
    </div>
  );
}
