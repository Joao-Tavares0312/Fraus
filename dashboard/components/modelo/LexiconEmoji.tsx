"use client";

import { useEffect, useState } from "react";
import { obterLexicon, type ItemLexicon } from "@/lib/api";
import { formatarNumero } from "@/lib/formato";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EstadoVazio } from "@/components/EstadoVazio";

const POR_PAGINA = 20;

/**
 * Lexicon de emoji navegavel.
 *
 * A paginacao e do SERVIDOR (`limite`/`deslocamento`): sao quase mil emojis, e
 * baixar a tabela inteira para paginar no navegador seria trocar rede por nada.
 * A busca tambem e do servidor -- e importante saber que ela casa o emoji
 * EXATO, e nao um nome ou uma descricao, senao quem digita "coracao" acha que
 * o lexicon esta vazio.
 *
 * O score de cada emoji e o MESMO `score_do_emoji` usado no sinal de emoji e na
 * simulacao. Nao ha formula reimplementada aqui.
 */
export function LexiconEmoji({ total }: { total: number }) {
  const [busca, setBusca] = useState("");
  const [rascunho, setRascunho] = useState("");
  const [pagina, setPagina] = useState(0);
  /*
   * A resposta carrega a CHAVE do pedido que a produziu (`busca|pagina`).
   * Comparar a chave guardada com a chave atual e o que diz se a tela esta
   * carregando -- em vez de zerar o estado dentro do efeito, o que dispararia
   * render em cascata. Efeito so escreve estado no callback assincrono.
   */
  const chave = `${busca}|${pagina}`;
  const [resposta, setResposta] = useState<{
    chave: string;
    itens: ItemLexicon[];
    total: number;
    erro: string | null;
  } | null>(null);

  useEffect(() => {
    let vivo = true;

    obterLexicon({
      busca: busca || undefined,
      limite: POR_PAGINA,
      deslocamento: pagina * POR_PAGINA,
    }).then((resultado) => {
      if (!vivo) return;
      setResposta(
        resultado.ok
          ? {
              chave,
              itens: resultado.dado.itens,
              total: resultado.dado.total,
              erro: null,
            }
          : { chave, itens: [], total: 0, erro: resultado.erro },
      );
    });

    return () => {
      vivo = false;
    };
  }, [busca, pagina, chave]);

  const atual = resposta?.chave === chave ? resposta : null;
  const itens = atual ? atual.itens : null;
  const erro = atual?.erro ?? null;
  const totalFiltrado = atual ? atual.total : total;

  const paginas = Math.max(1, Math.ceil(totalFiltrado / POR_PAGINA));

  return (
    <div className="min-w-0">
      <form
        className="flex flex-wrap items-end gap-3 border-b border-border px-5 py-3"
        onSubmit={(evento) => {
          evento.preventDefault();
          setPagina(0);
          setBusca(rascunho.trim());
        }}
      >
        <div className="flex flex-col gap-1">
          <Label
            htmlFor="busca-lexicon"
            className="text-xs font-normal text-muted-foreground"
          >
            Buscar emoji (cole o emoji, não o nome)
          </Label>
          <Input
            id="busca-lexicon"
            value={rascunho}
            onChange={(evento) => setRascunho(evento.target.value)}
            placeholder="😡"
            className="h-9 w-40"
          />
        </div>
        <Button type="submit" size="sm" variant="outline" className="mb-0.5">
          Buscar
        </Button>
        {busca ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="mb-0.5"
            onClick={() => {
              setRascunho("");
              setBusca("");
              setPagina(0);
            }}
          >
            Limpar
          </Button>
        ) : null}
        <p className="num mb-2 ml-auto text-xs text-muted-foreground">
          {totalFiltrado} de {total} emojis
        </p>
      </form>

      {erro ? (
        <EstadoVazio
          className="m-5"
          titulo="Não foi possível carregar o lexicon"
          explicacao={erro}
          endpoint="GET /modelo/lexicon"
        />
      ) : itens === null ? (
        <div className="flex flex-col gap-2 px-5 py-4">
          {Array.from({ length: 6 }).map((_, indice) => (
            <Skeleton key={indice} className="h-7 w-full" />
          ))}
        </div>
      ) : itens.length === 0 ? (
        <EstadoVazio
          className="m-5"
          titulo={
            busca
              ? `Nenhuma entrada para “${busca}”`
              : "O lexicon está vazio"
          }
          explicacao={
            busca
              ? "A busca casa o emoji exato, não o nome dele. Um emoji com modificador de tom de pele ou em sequência ZWJ é outra entrada — cole o caractere como ele aparece na conversa."
              : "GET /modelo/lexicon respondeu sem itens. O lexicon é gerado por scripts/gerar_lexico_emoji.py a partir do Emoji Sentiment Ranking."
          }
        />
      ) : (
        <>
          <div className="w-full overflow-x-auto">
            <Table className="min-w-[560px] text-sm">
              <TableHeader className="bg-muted">
                <TableRow>
                  <TableHead scope="col">Emoji</TableHead>
                  <TableHead scope="col" className="text-right">
                    Score
                  </TableHead>
                  <TableHead scope="col" className="text-right">
                    Negativo
                  </TableHead>
                  <TableHead scope="col" className="text-right">
                    Neutro
                  </TableHead>
                  <TableHead scope="col" className="text-right">
                    Positivo
                  </TableHead>
                  <TableHead scope="col" className="text-right">
                    Anotações
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {itens.map((item) => {
                  const anotacoes =
                    item.negativo + item.neutro + item.positivo;
                  return (
                    <TableRow key={item.emoji}>
                      <TableCell className="text-xl leading-none">
                        <span aria-hidden>{item.emoji}</span>
                        <span className="sr-only">{`emoji ${item.emoji}`}</span>
                      </TableCell>
                      <TableCell className="num text-right">
                        <span
                          className={
                            item.score > 0.05
                              ? "text-promotor-texto"
                              : item.score < -0.05
                                ? "text-detrator-texto"
                                : "text-muted-foreground"
                          }
                        >
                          {item.score > 0 ? "+" : ""}
                          {formatarNumero(item.score, 3)}
                        </span>
                      </TableCell>
                      <TableCell className="num text-right text-muted-foreground">
                        {item.negativo}
                      </TableCell>
                      <TableCell className="num text-right text-muted-foreground">
                        {item.neutro}
                      </TableCell>
                      <TableCell className="num text-right text-muted-foreground">
                        {item.positivo}
                      </TableCell>
                      <TableCell className="num text-right text-foreground">
                        {anotacoes}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>

          <nav
            aria-label="Paginação do lexicon"
            className="flex items-center justify-between gap-3 border-t border-border px-5 py-3"
          >
            <span className="num text-xs text-muted-foreground">
              Página {pagina + 1} de {paginas}
            </span>
            <div className="flex gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={pagina === 0}
                onClick={() => setPagina((atual) => Math.max(0, atual - 1))}
              >
                Anterior
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={pagina + 1 >= paginas}
                onClick={() => setPagina((atual) => atual + 1)}
              >
                Próxima
              </Button>
            </div>
          </nav>
        </>
      )}
    </div>
  );
}
