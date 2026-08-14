"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { Importacao } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

/**
 * O historico de importacao.
 *
 * Ele e o lastro da tela: sem ele, "importado com sucesso" e alegacao sem
 * prova -- some no instante seguinte e ninguem consegue mais dizer o que ficou
 * de fora. Por isso a linha com rejeicao nao mostra so a contagem: os motivos,
 * com o numero da linha do CSV, ficam a um clique, na propria tabela.
 *
 * A API guarda ate 20 motivos por importacao. Quando o arquivo tinha mais
 * rejeicoes que isso, a tela DIZ que a lista esta truncada, em vez de deixar
 * parecer que sao todas.
 */
export function HistoricoImportacoes({ historico }: { historico: Importacao[] }) {
  const [aberta, setAberta] = useState<number | null>(null);

  return (
    <div className="min-w-0 overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Quando</TableHead>
            <TableHead>Arquivo</TableHead>
            <TableHead className="text-right">Aceitas</TableHead>
            <TableHead className="text-right">Rejeitadas</TableHead>
            <TableHead>Motivos</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {historico.map((importacao) => {
            const expandida = aberta === importacao.id;
            const truncados =
              importacao.rejeitadas > importacao.motivos.length
                ? importacao.rejeitadas - importacao.motivos.length
                : 0;

            return (
              <TableRow key={importacao.id}>
                <TableCell className="num align-top text-xs whitespace-nowrap text-muted-foreground">
                  {formatarDataHora(importacao.ocorrida_em)}
                </TableCell>
                <TableCell className="num align-top text-xs text-foreground">
                  {importacao.arquivo}
                </TableCell>
                <TableCell className="num align-top text-right text-sm tabular-nums text-foreground">
                  {importacao.aceitas}
                </TableCell>
                <TableCell
                  className={`num align-top text-right text-sm tabular-nums ${
                    importacao.rejeitadas > 0
                      ? "text-detrator-texto"
                      : "text-muted-foreground"
                  }`}
                >
                  {importacao.rejeitadas}
                </TableCell>
                <TableCell className="min-w-72 align-top">
                  {importacao.rejeitadas === 0 ? (
                    <span className="text-xs text-muted-foreground">
                      nenhuma linha ficou de fora
                    </span>
                  ) : importacao.motivos.length === 0 ? (
                    <span className="text-xs text-muted-foreground">
                      contagem registrada sem os motivos — importação anterior ao
                      registro do relato
                    </span>
                  ) : (
                    <>
                      <Button
                        type="button"
                        size="xs"
                        variant="ghost"
                        aria-expanded={expandida}
                        onClick={() =>
                          setAberta(expandida ? null : importacao.id)
                        }
                      >
                        {expandida ? (
                          <ChevronDown aria-hidden />
                        ) : (
                          <ChevronRight aria-hidden />
                        )}
                        {expandida ? "Ocultar" : "Ver"} {importacao.motivos.length}{" "}
                        motivo(s)
                      </Button>

                      {expandida ? (
                        <ul className="mt-2 flex flex-col gap-1.5 border-l border-border pl-3">
                          {importacao.motivos.map((motivo, indice) => (
                            <li
                              key={`${motivo.numero_linha}-${indice}`}
                              className="text-xs leading-relaxed"
                            >
                              <span className="num text-muted-foreground">
                                linha {motivo.numero_linha}
                              </span>{" "}
                              <span className="text-foreground">
                                {motivo.motivo}
                              </span>
                            </li>
                          ))}
                          {truncados > 0 ? (
                            <li className="text-xs text-muted-foreground">
                              e mais{" "}
                              <span className="num">{truncados}</span> rejeição
                              (ões) sem motivo guardado — a API registra até 20
                              por importação; o resto continua no arquivo de
                              origem.
                            </li>
                          ) : null}
                        </ul>
                      ) : null}
                    </>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
