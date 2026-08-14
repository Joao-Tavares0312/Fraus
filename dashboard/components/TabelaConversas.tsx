"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ChevronsUpDown, Download } from "lucide-react";
import { flexRender } from "@tanstack/react-table";
import {
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  legacyCreateColumnHelper,
  useLegacyTable,
  type LegacyColumnDef,
  type LegacyRow,
} from "@tanstack/react-table/legacy";
import type { Categoria, Desfecho } from "@/lib/api";
import {
  EXPLICACAO_DESFECHO,
  ROTULO_CATEGORIA,
  ROTULO_DESFECHO,
  ROTULO_SEM_SINAL,
  formatarEsperaOuTraco,
} from "@/lib/formato";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EtiquetaCategoria } from "./EtiquetaCategoria";
import { EstadoVazio } from "./EstadoVazio";

export type LinhaConversa = {
  id: string;
  canal: string;
  /** Ja formatado no servidor: evita divergencia de fuso entre render e hidratacao. */
  data: string;
  /** Ordenacao usa o ISO, nao o texto. */
  ordenacao: string;
  nota: number | null;
  categoria: Categoria | null;
  qtd_mensagens: number;
  qtd_cliente: number;
  qtd_bot: number;
  qtd_humano: number;
  latencia_primeira_resposta_s: number | null;
  latencia_mediana_bot_s: number | null;
  latencia_mediana_humano_s: number | null;
  desfecho: Desfecho;
};

const colunas = legacyCreateColumnHelper<LinhaConversa>();

/** Caracteres que fazem o Excel/Sheets tratar a celula como FORMULA. */
const GATILHOS_DE_FORMULA = ["=", "+", "-", "@"];

/**
 * Escapa um campo para CSV.
 *
 * Alem das aspas, neutraliza injecao de formula: `id` e `canal` vem do CSV
 * ingerido, entao um campo como `=HYPERLINK(...)` viraria formula executavel
 * ao abrir a planilha.
 */
function escaparCampo(campo: string): string {
  const seguro = GATILHOS_DE_FORMULA.some((gatilho) => campo.startsWith(gatilho))
    ? `'${campo}`
    : campo;
  return `"${seguro.replaceAll('"', '""')}"`;
}

/**
 * Ordenacao que manda AUSENCIA para o fim nos dois sentidos.
 *
 * Vale para nota e para tempo de espera, pelo mesmo motivo: ordenar por espera
 * crescente nao pode fazer a conversa que nunca teve resposta humana aparecer
 * como a mais rapida da operacao, do mesmo jeito que ordenar por nota nao pode
 * fazer o atendimento mudo aparecer como o pior.
 */
function ausenciaPorUltimo(a: number | null, b: number | null): number {
  if (a === null && b === null) return 0;
  if (a === null) return 1;
  if (b === null) return -1;
  return a - b;
}

/** Uma medida pequena com rotulo, para as celulas de duas linhas. */
function Miudo({ children }: { children: React.ReactNode }) {
  return (
    <span className="block text-xs leading-tight text-muted-foreground">
      {children}
    </span>
  );
}

const CLASSE_DESFECHO: Record<Desfecho, string> = {
  // Os dois desfechos que exigem acao ficam legiveis a distancia; o resto
  // desce para o cinza. Uma tabela em que tudo grita nao destaca nada.
  sem_resposta: "text-destructive",
  escalada: "text-foreground",
  sem_sinal: "text-muted-foreground",
  encerrada: "text-muted-foreground",
  em_aberto: "text-muted-foreground",
};

/**
 * Tabela de atendimentos.
 *
 * A versao anterior tinha cinco colunas -- id, inicio, canal, nota, categoria --
 * e nenhuma delas respondia "o que aconteceu neste atendimento?". A correcao
 * nao foi acrescentar cinco colunas soltas, que teria deixado a tela mais
 * confusa em vez de menos: cada coluna aqui responde UMA pergunta, e os fatos
 * que so fazem sentido juntos moram na mesma celula. Canal e data acompanham o
 * id porque identificam o mesmo atendimento; nota e categoria sao o mesmo fato
 * em duas escalas; as tres esperas so significam alguma coisa comparadas entre
 * si.
 *
 * Tres regras de honestidade moram aqui:
 *
 *   1. nota e espera vazias aparecem como "sem sinal" e "—", e ORDENAM POR
 *      ULTIMO NOS DOIS SENTIDOS;
 *   2. o CSV escreve "sem sinal" na coluna de nota e deixa a de tempo vazia.
 *      Escrever 0 ali propagaria para a planilha exatamente a mentira que o
 *      produto combate;
 *   3. o desfecho nunca afirma resolucao -- "encerrada" diz que a conversa
 *      fechou, que e o unico fato que o dado sustenta.
 *
 * As linhas ja chegam recortadas pelo periodo, entao o que se exporta e
 * SEMPRE o que esta em tela.
 */
export function TabelaConversas({
  linhas,
  sufixoDeQuery,
  nomeCsv,
  rotuloDoPeriodo,
}: {
  linhas: LinhaConversa[];
  sufixoDeQuery: string;
  nomeCsv: string;
  rotuloDoPeriodo: string;
}) {
  const [filtro, setFiltro] = useState("");
  const [categoria, setCategoria] = useState<string>("todas");
  const [desfecho, setDesfecho] = useState<string>("todos");
  const [ordenacao, setOrdenacao] = useState([{ id: "data", desc: true }]);

  const definicoes = useMemo(
    () =>
      [
        colunas.accessor("ordenacao", {
          id: "data",
          header: "Atendimento",
          cell: (contexto) => {
            const linha = contexto.row.original;
            return (
              <div className="min-w-0">
                <Link
                  href={`/atendimentos/${encodeURIComponent(linha.id)}${sufixoDeQuery}`}
                  className="num rounded-sm text-foreground underline decoration-border underline-offset-4 outline-none transition-colors duration-150 hover:decoration-primary focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {linha.id}
                </Link>
                <Miudo>
                  {linha.canal} · <span className="num">{linha.data}</span>
                </Miudo>
              </div>
            );
          },
        }),
        colunas.accessor("qtd_mensagens", {
          header: "Mensagens",
          cell: (contexto) => {
            const linha = contexto.row.original;
            return (
              <div className="min-w-0">
                <span className="num text-foreground">{linha.qtd_mensagens}</span>
                <Miudo>
                  <span className="num">{linha.qtd_cliente}</span> cliente ·{" "}
                  <span className="num">{linha.qtd_bot}</span> bot
                  {linha.qtd_humano > 0 ? (
                    <>
                      {" "}
                      · <span className="num">{linha.qtd_humano}</span> humano
                    </>
                  ) : null}
                </Miudo>
              </div>
            );
          },
        }),
        colunas.accessor("latencia_primeira_resposta_s", {
          id: "espera",
          header: "Espera",
          sortFn: (a: LegacyRow<LinhaConversa>, b: LegacyRow<LinhaConversa>) =>
            ausenciaPorUltimo(
              a.original.latencia_primeira_resposta_s,
              b.original.latencia_primeira_resposta_s,
            ),
          cell: (contexto) => {
            const linha = contexto.row.original;
            return (
              <div className="min-w-0 whitespace-nowrap">
                {/* O "1ª" e obrigatorio: sem ele o numero grande e so um tempo
                    solto, e o leitor nao tem como saber que ele mede a
                    PRIMEIRA resposta enquanto os dois de baixo sao medianas. */}
                <span className="text-xs text-muted-foreground">1ª </span>
                <span className="num text-foreground">
                  {formatarEsperaOuTraco(linha.latencia_primeira_resposta_s)}
                </span>
                <Miudo>
                  bot{" "}
                  <span className="num">
                    {formatarEsperaOuTraco(linha.latencia_mediana_bot_s)}
                  </span>{" "}
                  · humano{" "}
                  <span className="num">
                    {formatarEsperaOuTraco(linha.latencia_mediana_humano_s)}
                  </span>
                </Miudo>
              </div>
            );
          },
        }),
        colunas.accessor("desfecho", {
          header: "Desfecho",
          cell: (contexto) => {
            const valor = contexto.getValue();
            return (
              <span
                className={`whitespace-nowrap text-sm ${CLASSE_DESFECHO[valor]}`}
                title={EXPLICACAO_DESFECHO[valor]}
              >
                {ROTULO_DESFECHO[valor]}
              </span>
            );
          },
        }),
        colunas.accessor("nota", {
          header: "Nota inferida",
          sortFn: (a: LegacyRow<LinhaConversa>, b: LegacyRow<LinhaConversa>) =>
            ausenciaPorUltimo(a.original.nota, b.original.nota),
          cell: (contexto) => {
            const nota = contexto.getValue();
            const linha = contexto.row.original;
            return nota === null ? (
              <span className="text-muted-foreground">{ROTULO_SEM_SINAL}</span>
            ) : (
              <div className="flex min-w-0 flex-col items-start gap-1">
                <span className="num estimado text-foreground">{nota}</span>
                <EtiquetaCategoria categoria={linha.categoria} />
              </div>
            );
          },
        }),
      ] as LegacyColumnDef<LinhaConversa>[],
    [sufixoDeQuery],
  );

  // Os recortes acontecem antes da tabela para que o contador, a paginacao e o
  // EXPORT falem todos do mesmo conjunto.
  const visiveisPorRecorte = useMemo(() => {
    let restantes = linhas;
    if (categoria === "sem-sinal") {
      restantes = restantes.filter((linha) => linha.categoria === null);
    } else if (categoria !== "todas") {
      restantes = restantes.filter((linha) => linha.categoria === categoria);
    }
    if (desfecho !== "todos") {
      restantes = restantes.filter((linha) => linha.desfecho === desfecho);
    }
    return restantes;
  }, [linhas, categoria, desfecho]);

  const tabela = useLegacyTable<LinhaConversa>({
    data: visiveisPorRecorte,
    columns: definicoes,
    state: { sorting: ordenacao, globalFilter: filtro },
    onSortingChange: setOrdenacao,
    onGlobalFilterChange: setFiltro,
    globalFilterFn: (linha, _coluna, valor: string) => {
      const alvo = String(valor).toLowerCase();
      const original = linha.original;
      return (
        original.id.toLowerCase().includes(alvo) ||
        original.canal.toLowerCase().includes(alvo) ||
        original.data.toLowerCase().includes(alvo) ||
        ROTULO_DESFECHO[original.desfecho].toLowerCase().includes(alvo) ||
        (original.categoria
          ? ROTULO_CATEGORIA[original.categoria].toLowerCase().includes(alvo)
          : ROTULO_SEM_SINAL.includes(alvo))
      );
    },
    initialState: { pagination: { pageIndex: 0, pageSize: 12 } },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  const filtradas = tabela
    .getFilteredRowModel()
    .rows.map((linha) => linha.original);

  const baixarCsv = () => {
    if (filtradas.length === 0) return;
    const cabecalho = [
      "id",
      "inicio",
      "canal",
      "mensagens",
      "msg_cliente",
      "msg_bot",
      "msg_humano",
      "primeira_resposta_s",
      "resposta_bot_mediana_s",
      "resposta_humano_mediana_s",
      "desfecho",
      "nota_inferida",
      "categoria",
    ];
    // Celula VAZIA para tempo que nao existiu -- nunca 0. Numa planilha, o
    // zero entraria em media e faria a operacao parecer mais rapida do que foi.
    const tempo = (valor: number | null) =>
      valor === null ? "" : String(Math.round(valor));

    const corpo = filtradas.map((linha) => [
      linha.id,
      linha.ordenacao,
      linha.canal,
      String(linha.qtd_mensagens),
      String(linha.qtd_cliente),
      String(linha.qtd_bot),
      String(linha.qtd_humano),
      tempo(linha.latencia_primeira_resposta_s),
      tempo(linha.latencia_mediana_bot_s),
      tempo(linha.latencia_mediana_humano_s),
      ROTULO_DESFECHO[linha.desfecho],
      linha.nota === null ? ROTULO_SEM_SINAL : String(linha.nota),
      linha.categoria ? ROTULO_CATEGORIA[linha.categoria] : ROTULO_SEM_SINAL,
    ]);

    const texto = [
      [`# Fraus — atendimentos de ${rotuloDoPeriodo}`],
      ["# nota_inferida é estimativa a partir do texto, não NPS declarado"],
      ["# tempo em branco = essa espera não existiu; não é zero"],
      cabecalho,
      ...corpo,
    ]
      .map((campos) => campos.map(escaparCampo).join(","))
      .join("\r\n");

    // BOM para o Excel em pt-BR abrir os acentos corretamente.
    const blob = new Blob([`﻿${texto}`], {
      type: "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const ancora = document.createElement("a");
    ancora.href = url;
    ancora.download = `${nomeCsv}.csv`;
    ancora.click();
    URL.revokeObjectURL(url);
  };

  if (linhas.length === 0) {
    return (
      <EstadoVazio
        className="m-5"
        titulo="Nenhum atendimento no período"
        explicacao="Ou o recorte de período não cobre nenhum atendimento, ou a API respondeu com uma lista vazia. Importe um CSV pela tela de Integrações ou suba o servidor de demonstração para popular o banco."
      />
    );
  }

  const visiveis = tabela.getRowModel().rows;

  return (
    <div className="min-w-0">
      <div className="sem-impressao flex flex-wrap items-end gap-3 border-b border-border px-5 py-3">
        <div className="flex flex-col gap-1">
          <Label
            htmlFor="filtro-atendimentos"
            className="text-xs font-normal text-muted-foreground"
          >
            Buscar
          </Label>
          <Input
            id="filtro-atendimentos"
            type="search"
            value={filtro}
            onChange={(evento) => setFiltro(evento.target.value)}
            placeholder="id, canal, desfecho ou categoria"
            className="h-9 w-56"
          />
        </div>

        <div className="flex flex-col gap-1">
          <Label
            htmlFor="filtro-categoria"
            className="text-xs font-normal text-muted-foreground"
          >
            Categoria
          </Label>
          {/* O Select do chassi permite limpar a selecao (valor `null`);
              aqui isso significa "todas", nao "nenhuma categoria". */}
          <Select
            value={categoria}
            onValueChange={(valor) => setCategoria(valor ?? "todas")}
          >
            <SelectTrigger id="filtro-categoria" className="h-9 w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="todas">Todas</SelectItem>
              <SelectItem value="detrator">Detrator</SelectItem>
              <SelectItem value="neutro">Neutro</SelectItem>
              <SelectItem value="promotor">Promotor</SelectItem>
              <SelectItem value="sem-sinal">Sem sinal</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-1">
          <Label
            htmlFor="filtro-desfecho"
            className="text-xs font-normal text-muted-foreground"
          >
            Desfecho
          </Label>
          <Select
            value={desfecho}
            onValueChange={(valor) => setDesfecho(valor ?? "todos")}
          >
            <SelectTrigger id="filtro-desfecho" className="h-9 w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="todos">Todos</SelectItem>
              {Object.entries(ROTULO_DESFECHO).map(([chave, rotulo]) => (
                <SelectItem key={chave} value={chave}>
                  {rotulo}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <p className="num mb-2 text-xs text-muted-foreground">
          {filtradas.length} de {linhas.length} atendimentos
        </p>

        <Button
          type="button"
          size="sm"
          variant="outline"
          className="mb-1.5 ml-auto"
          onClick={baixarCsv}
          disabled={filtradas.length === 0}
        >
          <Download aria-hidden />
          Exportar CSV
        </Button>
      </div>

      {/* Rolagem horizontal PROPRIA: o `body` nunca rola na horizontal. */}
      <div className="w-full overflow-x-auto">
        <Table className="min-w-[860px] text-sm">
          <TableHeader className="sticky top-0 z-10 bg-muted">
            {tabela.getHeaderGroups().map((grupo) => (
              <TableRow key={grupo.id}>
                {grupo.headers.map((cabecalho) => {
                  const ordenavel = cabecalho.column.getCanSort();
                  const direcao = cabecalho.column.getIsSorted();
                  const Icone =
                    direcao === "asc"
                      ? ArrowUp
                      : direcao === "desc"
                        ? ArrowDown
                        : ChevronsUpDown;
                  return (
                    <TableHead key={cabecalho.id} scope="col">
                      {ordenavel ? (
                        <button
                          type="button"
                          onClick={cabecalho.column.getToggleSortingHandler()}
                          aria-label={`Ordenar por ${String(cabecalho.column.columnDef.header)}`}
                          className="flex items-center gap-1.5 rounded-sm outline-none transition-colors duration-150 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          {flexRender(
                            cabecalho.column.columnDef.header,
                            cabecalho.getContext(),
                          )}
                          <Icone aria-hidden className="size-3" />
                        </button>
                      ) : (
                        flexRender(
                          cabecalho.column.columnDef.header,
                          cabecalho.getContext(),
                        )
                      )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {visiveis.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="py-8 text-muted-foreground">
                  Nenhum atendimento corresponde ao filtro atual.
                </TableCell>
              </TableRow>
            ) : (
              visiveis.map((linha) => (
                <TableRow
                  key={linha.id}
                  className="transition-colors duration-150 ease-fluid hover:bg-muted"
                >
                  {linha.getVisibleCells().map((celula) => (
                    <TableCell key={celula.id} className="align-top">
                      {flexRender(
                        celula.column.columnDef.cell,
                        celula.getContext(),
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <nav
        aria-label="Paginação dos atendimentos"
        className="sem-impressao flex items-center justify-between gap-3 border-t border-border px-5 py-3"
      >
        <span className="num text-xs text-muted-foreground">
          Página {tabela.getState().pagination.pageIndex + 1} de{" "}
          {Math.max(1, tabela.getPageCount())}
        </span>
        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => tabela.previousPage()}
            disabled={!tabela.getCanPreviousPage()}
          >
            Anterior
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => tabela.nextPage()}
            disabled={!tabela.getCanNextPage()}
          >
            Próxima
          </Button>
        </div>
      </nav>
    </div>
  );
}
