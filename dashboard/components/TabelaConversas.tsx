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
import type { Categoria } from "@/lib/api";
import { ROTULO_CATEGORIA, ROTULO_SEM_SINAL } from "@/lib/formato";
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
 * Tabela de atendimentos. TanStack Table entra headless -- ordenacao, filtro e
 * paginacao sem impor visual nenhum -- sobre a `Table` do chassi.
 *
 * Duas regras de honestidade moram aqui:
 *
 *   1. nota vazia aparece como "sem sinal" e ORDENA POR ULTIMO NOS DOIS
 *      SENTIDOS. Ordenar por nota crescente nao pode fazer os atendimentos
 *      mudos aparecerem como os piores;
 *   2. o CSV escreve "sem sinal" na coluna de nota. Escrever 0 ali propagaria
 *      para a planilha exatamente a mentira que o produto combate.
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
  const [ordenacao, setOrdenacao] = useState([{ id: "data", desc: true }]);

  const definicoes = useMemo(
    () =>
      [
        colunas.accessor("id", {
          header: "Atendimento",
          cell: (contexto) => (
            <Link
              href={`/atendimentos/${encodeURIComponent(contexto.getValue())}${sufixoDeQuery}`}
              className="num rounded-sm text-foreground underline decoration-border underline-offset-4 outline-none transition-colors duration-150 hover:decoration-primary focus-visible:ring-2 focus-visible:ring-ring"
            >
              {contexto.getValue()}
            </Link>
          ),
        }),
        colunas.accessor("ordenacao", {
          id: "data",
          header: "Início",
          cell: (contexto) => (
            <span className="num whitespace-nowrap text-muted-foreground">
              {contexto.row.original.data}
            </span>
          ),
        }),
        colunas.accessor("canal", {
          header: "Canal",
          cell: (contexto) => (
            <span className="text-muted-foreground">{contexto.getValue()}</span>
          ),
        }),
        colunas.accessor("nota", {
          header: "Nota inferida",
          sortFn: (a: LegacyRow<LinhaConversa>, b: LegacyRow<LinhaConversa>) => {
            const na = a.original.nota;
            const nb = b.original.nota;
            if (na === null && nb === null) return 0;
            if (na === null) return 1; // sem sinal sempre depois
            if (nb === null) return -1;
            return na - nb;
          },
          cell: (contexto) => {
            const nota = contexto.getValue();
            return nota === null ? (
              <span className="text-muted-foreground">{ROTULO_SEM_SINAL}</span>
            ) : (
              <span className="num estimado text-foreground">{nota}</span>
            );
          },
        }),
        colunas.accessor("categoria", {
          header: "Categoria",
          cell: (contexto) => (
            <EtiquetaCategoria categoria={contexto.getValue()} />
          ),
        }),
      ] as LegacyColumnDef<LinhaConversa>[],
    [sufixoDeQuery],
  );

  // O recorte por categoria acontece antes da tabela para que o contador, a
  // paginacao e o EXPORT falem todos do mesmo conjunto.
  const visiveisPorCategoria = useMemo(() => {
    if (categoria === "todas") return linhas;
    if (categoria === "sem-sinal")
      return linhas.filter((linha) => linha.categoria === null);
    return linhas.filter((linha) => linha.categoria === categoria);
  }, [linhas, categoria]);

  const tabela = useLegacyTable<LinhaConversa>({
    data: visiveisPorCategoria,
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
    const cabecalho = ["id", "inicio", "canal", "nota_inferida", "categoria"];
    const corpo = filtradas.map((linha) => [
      linha.id,
      linha.ordenacao,
      linha.canal,
      linha.nota === null ? ROTULO_SEM_SINAL : String(linha.nota),
      linha.categoria ? ROTULO_CATEGORIA[linha.categoria] : ROTULO_SEM_SINAL,
    ]);

    const texto = [
      [`# Fraus — atendimentos de ${rotuloDoPeriodo}`],
      ["# nota_inferida é estimativa a partir do texto, não NPS declarado"],
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
        explicacao="Ou o recorte de período não cobre nenhum atendimento, ou a API respondeu com uma lista vazia. Importe um CSV pelo endpoint de importação ou suba o servidor de demonstração para popular o banco."
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
            placeholder="id, canal ou categoria"
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
            <SelectTrigger id="filtro-categoria" className="h-9 w-44">
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
        <Table className="min-w-[720px] text-sm">
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
                    <TableCell key={celula.id}>
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
