"use client";

import { useId, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Check, RotateCcw } from "lucide-react";
import { salvarConfiguracoes, type ValoresConfiguracao } from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  CATEGORIAS,
  categoriasDaNota,
  COR_DA_CATEGORIA,
  EscalaNps,
  NOTAS,
  ROTULO_DA_CATEGORIA,
  type Faixas,
} from "./EscalaNps";

type Rascunho = Record<string, { de: string; ate: string }>;

function paraRascunho(faixas: Faixas): Rascunho {
  return Object.fromEntries(
    Object.entries(faixas).map(([categoria, [minima, maxima]]) => [
      categoria,
      { de: String(minima), ate: String(maxima) },
    ]),
  );
}

/** Ordem estavel: as tres categorias do trabalho primeiro, o resto depois. */
function ordenar(faixas: Faixas): string[] {
  const chaves = Object.keys(faixas);
  const conhecidas = CATEGORIAS.filter((categoria) =>
    chaves.includes(categoria),
  );
  return [
    ...conhecidas,
    ...chaves.filter((chave) => !conhecidas.includes(chave as never)),
  ];
}

/**
 * Le o rascunho como numero. Campo em branco ou nao inteiro vira `null`, e o
 * `null` NAO vai para a API: mandar `NaN` faria o servidor recusar por um
 * motivo que nao e o do operador ("precisa ser de numeros inteiros" quando o
 * que houve foi um campo vazio).
 */
function comoFaixas(rascunho: Rascunho): { faixas: Faixas; incompleto: string[] } {
  const faixas: Faixas = {};
  const incompleto: string[] = [];

  for (const [categoria, { de, ate }] of Object.entries(rascunho)) {
    const minima = Number(de);
    const maxima = Number(ate);
    if (
      de.trim() === "" ||
      ate.trim() === "" ||
      !Number.isInteger(minima) ||
      !Number.isInteger(maxima)
    ) {
      incompleto.push(ROTULO_DA_CATEGORIA[categoria] ?? categoria);
      continue;
    }
    faixas[categoria] = [minima, maxima];
  }

  return { faixas, incompleto };
}

function saoIguais(a: Faixas, b: Faixas): boolean {
  const chaves = new Set([...Object.keys(a), ...Object.keys(b)]);
  for (const chave of chaves) {
    const esquerda = a[chave];
    const direita = b[chave];
    if (!esquerda || !direita) return false;
    if (esquerda[0] !== direita[0] || esquerda[1] !== direita[1]) return false;
  }
  return true;
}

/**
 * O controle das faixas de NPS.
 *
 * Duas decisoes de projeto vivem aqui:
 *
 * 1. Os seis campos sao LIVRES -- de e ate por categoria, sem trava de
 *    contiguidade no cliente. A regra ("cobrir 0..10 de forma contigua") mora
 *    no servidor, e uma segunda copia dela no TypeScript seria a mesma
 *    duplicacao que ja custou divergencia de arredondamento a este projeto. O
 *    `400` da API nomeia o problema, e e a mensagem DELE que aparece na tela.
 * 2. A consequencia e dita ANTES: a categoria e derivada na leitura, entao
 *    mexer na faixa reclassifica atendimento ja pontuado. O score, esse, nao
 *    muda. Quem aperta salvar precisa saber disso antes, nao depois.
 */
export function FaixasNps({
  vigente,
  fabrica,
}: {
  vigente: Faixas;
  fabrica: Faixas;
}) {
  const router = useRouter();
  const identificador = useId();
  const [gravado, setGravado] = useState<Faixas>(vigente);
  const [rascunho, setRascunho] = useState<Rascunho>(() => paraRascunho(vigente));
  const [erro, setErro] = useState<string | null>(null);
  const [confirmacao, setConfirmacao] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  const { faixas, incompleto } = useMemo(() => comoFaixas(rascunho), [rascunho]);
  const categorias = ordenar(gravado);

  const mudou = incompleto.length > 0 || !saoIguais(faixas, gravado);
  const jaEDeFabrica = incompleto.length === 0 && saoIguais(faixas, fabrica);

  const notasOrfas = NOTAS.filter(
    (nota) => categoriasDaNota(faixas, nota).length === 0,
  );
  const notasEmConflito = NOTAS.filter(
    (nota) => categoriasDaNota(faixas, nota).length > 1,
  );

  function alterar(categoria: string, campo: "de" | "ate", valor: string) {
    setRascunho((atual) => ({
      ...atual,
      [categoria]: { ...atual[categoria], [campo]: valor },
    }));
    setConfirmacao(null);
  }

  async function salvar() {
    if (incompleto.length > 0) {
      setConfirmacao(null);
      setErro(
        `preencha as duas notas de: ${incompleto.join(", ")} — a faixa precisa de mínima e máxima inteiras`,
      );
      return;
    }

    setSalvando(true);
    setErro(null);
    setConfirmacao(null);

    const resposta = await salvarConfiguracoes({
      faixas_nps: faixas as ValoresConfiguracao["faixas_nps"],
    });

    setSalvando(false);

    if (!resposta.ok) {
      setErro(resposta.erro);
      return;
    }

    const novas = resposta.dado.vigente.faixas_nps as Faixas;
    setGravado(novas);
    setRascunho(paraRascunho(novas));
    setConfirmacao(
      "Faixas gravadas. Os atendimentos já pontuados passam a ser lidos por elas agora — indicadores, tabela e distribuição respondem pela mesma faixa.",
    );
    router.refresh();
  }

  function voltarAoPadrao() {
    setRascunho(paraRascunho(fabrica));
    setErro(null);
    setConfirmacao(null);
  }

  return (
    <div className="flex flex-col gap-4 p-5">
      <EscalaNps faixas={faixas} />

      <p className="text-xs leading-relaxed text-muted-foreground">
        {notasOrfas.length === 0 && notasEmConflito.length === 0 ? (
          <>
            As onze notas estão cobertas, cada uma por uma faixa só. O servidor
            aceita esta configuração.
          </>
        ) : (
          <>
            {notasOrfas.length > 0 ? (
              <>
                Sem faixa:{" "}
                <strong className="num font-medium text-foreground">
                  {notasOrfas.join(", ")}
                </strong>
                .{" "}
              </>
            ) : null}
            {notasEmConflito.length > 0 ? (
              <>
                Reivindicadas por mais de uma faixa:{" "}
                <strong className="num font-medium text-foreground">
                  {notasEmConflito.join(", ")}
                </strong>
                .{" "}
              </>
            ) : null}
            O servidor recusa e diz exatamente o que falta.
          </>
        )}
      </p>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {categorias.map((categoria) => (
          <fieldset
            key={categoria}
            className="flex min-w-0 flex-col gap-2 rounded-md border border-border p-3"
          >
            <legend className="sr-only">
              Faixa de {ROTULO_DA_CATEGORIA[categoria] ?? categoria}
            </legend>
            <p className="flex items-center gap-2 text-sm font-medium text-foreground">
              <span
                aria-hidden
                className="size-2 shrink-0 rounded-full"
                style={{
                  background:
                    COR_DA_CATEGORIA[categoria] ?? "var(--muted-foreground)",
                }}
              />
              {ROTULO_DA_CATEGORIA[categoria] ?? categoria}
            </p>
            <div className="flex items-end gap-2">
              <div className="min-w-0 flex-1">
                <Label
                  htmlFor={`${identificador}-${categoria}-de`}
                  className="text-xs text-muted-foreground"
                >
                  nota mínima
                </Label>
                <Input
                  id={`${identificador}-${categoria}-de`}
                  className="num mt-1 tabular-nums"
                  type="number"
                  inputMode="numeric"
                  min={0}
                  max={10}
                  step={1}
                  value={rascunho[categoria]?.de ?? ""}
                  onChange={(evento) =>
                    alterar(categoria, "de", evento.target.value)
                  }
                  onKeyDown={(evento) => {
                    if (evento.key === "Enter" && mudou && !salvando) salvar();
                  }}
                />
              </div>
              <span
                aria-hidden
                className="pb-2 text-xs text-muted-foreground"
              >
                até
              </span>
              <div className="min-w-0 flex-1">
                <Label
                  htmlFor={`${identificador}-${categoria}-ate`}
                  className="text-xs text-muted-foreground"
                >
                  nota máxima
                </Label>
                <Input
                  id={`${identificador}-${categoria}-ate`}
                  className="num mt-1 tabular-nums"
                  type="number"
                  inputMode="numeric"
                  min={0}
                  max={10}
                  step={1}
                  value={rascunho[categoria]?.ate ?? ""}
                  onChange={(evento) =>
                    alterar(categoria, "ate", evento.target.value)
                  }
                  onKeyDown={(evento) => {
                    if (evento.key === "Enter" && mudou && !salvando) salvar();
                  }}
                />
              </div>
            </div>
          </fieldset>
        ))}
      </div>

      <Alert>
        <AlertTriangle aria-hidden />
        <AlertTitle>Salvar reclassifica atendimentos já pontuados</AlertTitle>
        <AlertDescription>
          A categoria é derivada na leitura, a partir do score gravado e da
          faixa vigente. Mudar o corte muda a fatia de quem já foi medido — o
          NPS da visão geral, a distribuição e a etiqueta de cada atendimento
          mudam junto. O <span className="num">score</span> não é recalculado:
          ele continua sendo o que o modelo disse na importação.
        </AlertDescription>
      </Alert>

      {erro ? (
        <Alert variant="destructive">
          <AlertTriangle aria-hidden />
          <AlertTitle>A API recusou a configuração</AlertTitle>
          <AlertDescription>
            <span className="text-destructive">{erro}</span>
          </AlertDescription>
        </Alert>
      ) : null}

      {confirmacao ? (
        <Alert>
          <Check aria-hidden />
          <AlertTitle>Configuração gravada</AlertTitle>
          <AlertDescription>{confirmacao}</AlertDescription>
        </Alert>
      ) : null}

      <div className="flex flex-wrap items-center gap-2">
        <Button type="button" onClick={salvar} disabled={salvando || !mudou}>
          {salvando ? "Salvando…" : "Salvar faixas"}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={voltarAoPadrao}
          disabled={jaEDeFabrica}
        >
          <RotateCcw aria-hidden />
          Voltar ao padrão de fábrica
        </Button>
        <p className="num text-xs text-muted-foreground">
          padrão:{" "}
          {ordenar(fabrica)
            .map(
              (categoria) =>
                `${fabrica[categoria][0]}–${fabrica[categoria][1]} ${categoria}`,
            )
            .join(" · ")}
        </p>
      </div>
    </div>
  );
}
