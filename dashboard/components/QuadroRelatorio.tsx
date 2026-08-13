"use client";

import { useRef, type ReactNode } from "react";
import { useReactToPrint } from "react-to-print";
import type { LinhaConversa } from "./TabelaConversas";
import { ROTULO_CATEGORIA, ROTULO_SEM_SINAL } from "@/lib/formato";

/**
 * Casca da pagina que sabe se exportar.
 *
 * PDF reaproveita a propria tela via `react-to-print` (as regras de impressao
 * moram no `globals.css`), e o CSV sai de um `Blob` nativo -- exportar texto
 * separado por virgula nao justifica uma dependencia.
 *
 * O CSV escreve "sem sinal" na coluna de nota; escrever 0 ali seria propagar
 * para a planilha exatamente a mentira que o produto combate.
 */

/** Caracteres que fazem o Excel/Sheets tratar a celula como FORMULA. */
const GATILHOS_DE_FORMULA = ["=", "+", "-", "@"];

/**
 * Escapa um campo para CSV.
 *
 * Alem das aspas, neutraliza injecao de formula: `id` e `canal` vem do CSV
 * ingerido, entao um campo como `=HYPERLINK(...)` viraria formula executavel
 * ao abrir a planilha. A aspa simples a frente faz a planilha tratar tudo
 * como texto, e some da exibicao.
 */
function escaparCampo(campo: string): string {
  const seguro = GATILHOS_DE_FORMULA.some((gatilho) => campo.startsWith(gatilho))
    ? `'${campo}`
    : campo;
  return `"${seguro.replaceAll('"', '""')}"`;
}
export function QuadroRelatorio({
  titulo,
  subtitulo,
  linhas,
  nomeCsv,
  children,
}: {
  titulo: string;
  subtitulo: string;
  linhas?: LinhaConversa[];
  nomeCsv?: string;
  children: ReactNode;
}) {
  const area = useRef<HTMLDivElement>(null);

  const imprimir = useReactToPrint({
    contentRef: area,
    documentTitle: nomeCsv ?? "dolos-relatorio",
  });

  const baixarCsv = () => {
    if (!linhas || linhas.length === 0) return;
    const cabecalho = ["id", "inicio", "canal", "nota_inferida", "categoria"];
    const corpo = linhas.map((linha) => [
      linha.id,
      linha.ordenacao,
      linha.canal,
      linha.nota === null ? ROTULO_SEM_SINAL : String(linha.nota),
      linha.categoria ? ROTULO_CATEGORIA[linha.categoria] : ROTULO_SEM_SINAL,
    ]);

    const texto = [cabecalho, ...corpo]
      .map((campos) =>
        campos.map(escaparCampo).join(","),
      )
      .join("\r\n");

    // BOM para o Excel em pt-BR abrir os acentos corretamente.
    const blob = new Blob([`﻿${texto}`], {
      type: "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const ancora = document.createElement("a");
    ancora.href = url;
    ancora.download = `${nomeCsv ?? "dolos-atendimentos"}.csv`;
    ancora.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div ref={area}>
      <header className="border-b border-[var(--filete)] bg-[var(--superficie)]">
        <div className="mx-auto flex max-w-[1220px] flex-wrap items-end justify-between gap-4 px-6 py-5">
          <div className="min-w-0">
            <p className="flex items-center gap-2 text-[0.6875rem] font-medium tracking-[0.08em] text-[var(--tinta-3)]">
              <span
                aria-hidden
                className="inline-block h-[9px] w-[9px] rotate-45 border border-[var(--regua)]"
              />
              DOLOS
            </p>
            <h1 className="mt-1.5 text-[1.5rem] leading-[1.2] font-semibold tracking-[-0.02em] text-[var(--tinta)]">
              {titulo}
            </h1>
            <p className="mt-1 max-w-[72ch] text-[0.875rem] leading-[1.5] text-[var(--tinta-2)]">
              {subtitulo}
            </p>
          </div>

          <div className="sem-impressao flex shrink-0 gap-2">
            {linhas && linhas.length > 0 ? (
              <Botao aoClicar={baixarCsv}>Exportar CSV</Botao>
            ) : null}
            <Botao aoClicar={() => imprimir()}>Imprimir / PDF</Botao>
          </div>
        </div>
      </header>

      {children}
    </div>
  );
}

function Botao({
  aoClicar,
  children,
}: {
  aoClicar: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={aoClicar}
      className="rounded-[2px] border border-[var(--regua)] bg-[var(--plano)] px-3 py-1.5 text-[0.8125rem] text-[var(--tinta)] transition-colors duration-150 hover:bg-[var(--superficie-2)] active:translate-y-px"
    >
      {children}
    </button>
  );
}
