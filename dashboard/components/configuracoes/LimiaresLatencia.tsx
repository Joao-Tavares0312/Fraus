"use client";

import { useId, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Check, RotateCcw } from "lucide-react";
import { salvarConfiguracoes } from "@/lib/api";
import {
  emMinutos,
  limiaresDe,
  rotulosLatencia,
  type SeveridadeLatencia,
} from "@/lib/derivacoes";
import { formatarSegundos } from "@/lib/formato";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const CAMPOS: {
  chave: "pico" | "saudavel" | "degradando";
  indice: number;
  rotulo: string;
  ajuda: string;
}[] = [
  {
    chave: "pico",
    indice: 0,
    rotulo: "Resposta imediata até",
    ajuda: "Padrão 10 s — pico de CSAT observado na literatura de live chat.",
  },
  {
    chave: "saudavel",
    indice: 1,
    rotulo: "Espera saudável até",
    ajuda: "Padrão 60 s — fora do pico, ainda sem perda relevante.",
  },
  {
    chave: "degradando",
    indice: 2,
    rotulo: "Espera longa até",
    ajuda: "Padrão 180 s — acima disso é a faixa de abandono (57% desistem).",
  },
];

const COR_DA_SEVERIDADE: Record<SeveridadeLatencia, string> = {
  pico: "var(--promotor)",
  saudavel: "var(--neutro)",
  degradando: "var(--detrator)",
  abandono: "var(--muted-foreground)",
};

function paraRascunho(limiares: number[]): string[] {
  return limiares.map((valor) => String(valor));
}

function saoIguais(a: number[], b: number[]): boolean {
  return a.length === b.length && a.every((valor, i) => valor === b[i]);
}

/**
 * Os cortes de latencia da interface.
 *
 * Eles sao de EXIBICAO: movem onde a leitura chama a espera de imediata,
 * saudavel, longa ou critica. Nenhuma feature do modelo depende deles --
 * `fraus/sinais/tempo.py` continua lendo os timestamps crus, e latencia segue
 * sem ser persistida. A tela diz isso, porque um controle que parece treinar o
 * modelo e so pinta faixa seria a promessa vazia que este trabalho combate.
 */
export function LimiaresLatencia({
  vigente,
  fabrica,
}: {
  vigente: number[];
  fabrica: number[];
}) {
  const router = useRouter();
  const identificador = useId();
  const [gravado, setGravado] = useState<number[]>(vigente);
  const [rascunho, setRascunho] = useState<string[]>(() => paraRascunho(vigente));
  const [erro, setErro] = useState<string | null>(null);
  const [confirmacao, setConfirmacao] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  const valores = useMemo(
    () => rascunho.map((texto) => (texto.trim() === "" ? NaN : Number(texto))),
    [rascunho],
  );
  const completo = valores.every((valor) => Number.isInteger(valor) && valor > 0);
  const crescente = completo && valores[0] < valores[1] && valores[1] < valores[2];

  const mudou = !completo || !saoIguais(valores, gravado);
  const jaEDeFabrica = completo && saoIguais(valores, fabrica);

  const previa = limiaresDe(completo && crescente ? valores : gravado);
  const rotulos = rotulosLatencia(previa);

  // A cauda existe para a faixa de abandono (que nao tem teto) ter largura na
  // regua: sem ela, "acima de X" seria uma linha de zero pixel.
  const fim = previa.degradando * 1.35;
  const faixas: { severidade: SeveridadeLatencia; de: number; ate: number }[] = [
    { severidade: "pico", de: 0, ate: previa.pico },
    { severidade: "saudavel", de: previa.pico, ate: previa.saudavel },
    { severidade: "degradando", de: previa.saudavel, ate: previa.degradando },
    { severidade: "abandono", de: previa.degradando, ate: fim },
  ];

  function alterar(indice: number, valor: string) {
    setRascunho((atual) =>
      atual.map((texto, i) => (i === indice ? valor : texto)),
    );
    setConfirmacao(null);
  }

  async function salvar() {
    if (!completo) {
      setConfirmacao(null);
      setErro(
        "preencha os três cortes com números inteiros de segundos, maiores que zero",
      );
      return;
    }

    setSalvando(true);
    setErro(null);
    setConfirmacao(null);

    const resposta = await salvarConfiguracoes({ limiares_latencia_s: valores });

    setSalvando(false);

    if (!resposta.ok) {
      setErro(resposta.erro);
      return;
    }

    const novos = resposta.dado.vigente.limiares_latencia_s;
    setGravado(novos);
    setRascunho(paraRascunho(novos));
    setConfirmacao(
      "Cortes gravados. A faixa de referência do cartão de latência e a anotação de espera de cada atendimento passam a usá-los.",
    );
    router.refresh();
  }

  return (
    <div className="flex flex-col gap-4 p-5">
      <div className="min-w-0">
        <div
          className="flex h-3 w-full overflow-hidden rounded-xs border border-border"
          aria-hidden
        >
          {faixas.map(({ severidade, de, ate }) => (
            <span
              key={severidade}
              style={{
                width: `${((ate - de) / fim) * 100}%`,
                background: COR_DA_SEVERIDADE[severidade],
              }}
            />
          ))}
        </div>
        <dl className="mt-2 grid grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-2">
          {faixas.map(({ severidade, de, ate }) => (
            <div key={severidade} className="flex items-baseline gap-2">
              <span
                aria-hidden
                className="size-2 shrink-0 translate-y-px rounded-full"
                style={{ background: COR_DA_SEVERIDADE[severidade] }}
              />
              <dt className="rotulo-instrumento text-foreground">
                {rotulos[severidade].titulo}
              </dt>
              <dd className="num text-xs text-muted-foreground">
                {severidade === "abandono"
                  ? `acima de ${formatarSegundos(de)}`
                  : `${formatarSegundos(de)} – ${formatarSegundos(ate)}`}
              </dd>
            </div>
          ))}
        </dl>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {CAMPOS.map(({ chave, indice, rotulo, ajuda }) => (
          <div key={chave} className="min-w-0">
            <Label
              htmlFor={`${identificador}-${chave}`}
              className="text-xs text-foreground"
            >
              {rotulo}
            </Label>
            <div className="mt-1 flex items-center gap-2">
              <Input
                id={`${identificador}-${chave}`}
                className="num tabular-nums"
                type="number"
                inputMode="numeric"
                min={1}
                step={1}
                value={rascunho[indice] ?? ""}
                onChange={(evento) => alterar(indice, evento.target.value)}
                onKeyDown={(evento) => {
                  if (evento.key === "Enter" && mudou && !salvando) salvar();
                }}
                aria-describedby={`${identificador}-${chave}-ajuda`}
              />
              <span className="num shrink-0 text-xs text-muted-foreground">
                s
              </span>
            </div>
            <p
              id={`${identificador}-${chave}-ajuda`}
              className="mt-1 text-[0.6875rem] leading-relaxed text-muted-foreground"
            >
              {ajuda}
            </p>
          </div>
        ))}
      </div>

      {completo && !crescente ? (
        <p className="text-xs text-muted-foreground">
          Os três cortes precisam ser crescentes — a régua acima continua
          mostrando os valores gravados até que sejam.
        </p>
      ) : null}

      <p className="text-xs leading-relaxed text-muted-foreground">
        Estes cortes são de <strong className="text-foreground">exibição</strong>
        : eles movem onde a interface chama a espera de imediata, saudável,
        longa ou crítica — no trilho do cartão de latência da visão geral e na
        anotação embaixo de cada resposta da transcrição. Nenhuma feature do
        modelo depende deles: o sinal de tempo continua lendo os timestamps
        crus, e latência segue sem ser persistida. Fora do padrão de fábrica, a
        interface para de citar as porcentagens da literatura ao lado do corte —
        elas foram medidas em 10 s e 3 min, não no corte novo.
      </p>

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
          {salvando ? "Salvando…" : "Salvar limiares"}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            setRascunho(paraRascunho(fabrica));
            setErro(null);
            setConfirmacao(null);
          }}
          disabled={jaEDeFabrica}
        >
          <RotateCcw aria-hidden />
          Voltar ao padrão de fábrica
        </Button>
        <p className="num text-xs text-muted-foreground">
          padrão: {fabrica[0]} s · {fabrica[1]} s ·{" "}
          {emMinutos(fabrica[2])} min
        </p>
      </div>
    </div>
  );
}
