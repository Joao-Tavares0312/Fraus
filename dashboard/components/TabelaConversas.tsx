"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
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

const CLASSE_CABECALHO =
  "px-4 py-2.5 text-left text-[0.75rem] font-medium text-[var(--tinta-2)] whitespace-nowrap";

/**
 * Tabela de atendimentos. TanStack Table entra headless: ordenacao, filtro e
 * paginacao sem impor visual nenhum.
 *
 * A nota vazia aparece como "sem sinal" e ORDENA POR ULTIMO nos dois sentidos,
 * em vez de valer zero -- ordenar por nota crescente nao pode fazer os
 * atendimentos mudos aparecerem como os piores.
 */
export function TabelaConversas({ linhas }: { linhas: LinhaConversa[] }) {
  const router = useRouter();
  const [filtro, setFiltro] = useState("");
  const [ordenacao, setOrdenacao] = useState([{ id: "data", desc: true }]);

  // O helper devolve definicoes com o tipo do acessor preso em cada coluna;
  // a tabela quer a lista homogenea. O `as` aqui e a costura padrao disso.
  const definicoes = useMemo(
    () =>
      [
      colunas.accessor("id", {
        header: "Atendimento",
        cell: (contexto) => (
          <Link
            href={`/conversas/${encodeURIComponent(contexto.getValue())}`}
            className="font-mono text-[0.8125rem] text-[var(--tinta)] underline decoration-[var(--filete)] underline-offset-[3px] transition-colors duration-150 hover:decoration-[var(--foco)]"
          >
            {contexto.getValue()}
          </Link>
        ),
      }),
      colunas.accessor("ordenacao", {
        id: "data",
        header: "Início",
        cell: (contexto) => (
          <span className="tabular-nums whitespace-nowrap text-[var(--tinta-2)]">
            {contexto.row.original.data}
          </span>
        ),
      }),
      colunas.accessor("canal", {
        header: "Canal",
        cell: (contexto) => (
          <span className="text-[var(--tinta-2)]">{contexto.getValue()}</span>
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
            <span className="text-[var(--tinta-3)]">{ROTULO_SEM_SINAL}</span>
          ) : (
            <span className="tabular-nums text-[var(--tinta)]">{nota}</span>
          );
        },
      }),
      colunas.accessor("categoria", {
        header: "Categoria",
        cell: (contexto) => <EtiquetaCategoria categoria={contexto.getValue()} />,
      }),
      ] as LegacyColumnDef<LinhaConversa>[],
    [],
  );

  const tabela = useLegacyTable<LinhaConversa>({
    data: linhas,
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

  if (linhas.length === 0) {
    return (
      <EstadoVazio
        titulo="Nenhum atendimento importado"
        explicacao="A API respondeu com uma lista vazia. Importe um CSV pelo endpoint de importação ou suba o servidor de demonstração para popular o banco."
      />
    );
  }

  const visiveis = tabela.getRowModel().rows;

  return (
    <div>
      <div className="sem-impressao flex flex-wrap items-center gap-3 border-b border-[var(--filete)] px-5 py-3">
        <label className="flex items-center gap-2 text-[0.8125rem] text-[var(--tinta-2)]">
          <span>Filtrar</span>
          <input
            type="search"
            value={filtro}
            onChange={(evento) => setFiltro(evento.target.value)}
            placeholder="id, canal ou categoria"
            className="w-56 border border-[var(--filete)] bg-[var(--plano)] px-2.5 py-1.5 text-[0.8125rem] text-[var(--tinta)] placeholder:text-[var(--tinta-3)] transition-colors duration-150 hover:border-[var(--regua)]"
          />
        </label>
        <span className="text-[0.75rem] tabular-nums text-[var(--tinta-3)]">
          {visiveis.length} de {linhas.length} atendimentos
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] border-collapse text-[0.8125rem]">
          <thead className="bg-[var(--superficie-2)]">
            {tabela.getHeaderGroups().map((grupo) => (
              <tr key={grupo.id}>
                {grupo.headers.map((cabecalho) => {
                  const ordenavel = cabecalho.column.getCanSort();
                  const direcao = cabecalho.column.getIsSorted();
                  return (
                    <th key={cabecalho.id} scope="col" className={CLASSE_CABECALHO}>
                      {ordenavel ? (
                        <button
                          type="button"
                          onClick={cabecalho.column.getToggleSortingHandler()}
                          className="flex items-center gap-1.5 transition-colors duration-150 hover:text-[var(--tinta)]"
                          aria-label={`Ordenar por ${String(cabecalho.column.columnDef.header)}`}
                        >
                          {flexRender(
                            cabecalho.column.columnDef.header,
                            cabecalho.getContext(),
                          )}
                          <span aria-hidden className="text-[0.625rem]">
                            {direcao === "asc" ? "▲" : direcao === "desc" ? "▼" : "•"}
                          </span>
                        </button>
                      ) : (
                        flexRender(
                          cabecalho.column.columnDef.header,
                          cabecalho.getContext(),
                        )
                      )}
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {visiveis.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-5 py-8 text-[var(--tinta-3)]">
                  Nenhum atendimento corresponde a “{filtro}”.
                </td>
              </tr>
            ) : (
              visiveis.map((linha) => (
                <tr
                  key={linha.id}
                  onClick={() =>
                    router.push(
                      `/conversas/${encodeURIComponent(linha.original.id)}`,
                    )
                  }
                  className="cursor-pointer border-t border-[var(--filete)] transition-colors duration-150 hover:bg-[var(--superficie-2)]"
                >
                  {linha.getVisibleCells().map((celula) => (
                    <td key={celula.id} className="px-4 py-2.5">
                      {flexRender(
                        celula.column.columnDef.cell,
                        celula.getContext(),
                      )}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Paginacao
        pagina={tabela.getState().pagination.pageIndex + 1}
        paginas={Math.max(1, tabela.getPageCount())}
        podeVoltar={tabela.getCanPreviousPage()}
        podeAvancar={tabela.getCanNextPage()}
        voltar={() => tabela.previousPage()}
        avancar={() => tabela.nextPage()}
      />
    </div>
  );
}

function Paginacao({
  pagina,
  paginas,
  podeVoltar,
  podeAvancar,
  voltar,
  avancar,
}: {
  pagina: number;
  paginas: number;
  podeVoltar: boolean;
  podeAvancar: boolean;
  voltar: () => void;
  avancar: () => void;
}) {
  return (
    <nav
      aria-label="Paginação dos atendimentos"
      className="sem-impressao flex items-center justify-between gap-3 border-t border-[var(--filete)] px-5 py-3"
    >
      <span className="text-[0.75rem] tabular-nums text-[var(--tinta-3)]">
        Página {pagina} de {paginas}
      </span>
      <div className="flex gap-2">
        <BotaoPagina aoClicar={voltar} desabilitado={!podeVoltar}>
          Anterior
        </BotaoPagina>
        <BotaoPagina aoClicar={avancar} desabilitado={!podeAvancar}>
          Próxima
        </BotaoPagina>
      </div>
    </nav>
  );
}

function BotaoPagina({
  aoClicar,
  desabilitado,
  children,
}: {
  aoClicar: () => void;
  desabilitado: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={aoClicar}
      disabled={desabilitado}
      className="rounded-[2px] border border-[var(--filete)] px-2.5 py-1 text-[0.75rem] text-[var(--tinta-2)] transition-colors duration-150 hover:border-[var(--regua)] hover:text-[var(--tinta)] disabled:cursor-not-allowed disabled:border-[var(--filete)] disabled:text-[var(--tinta-3)] disabled:opacity-50"
    >
      {children}
    </button>
  );
}
