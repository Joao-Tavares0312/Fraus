import { Fragment } from "react";
import type { DetalheConversa } from "@/lib/api";
import {
  latenciasAnotadas,
  rotulosLatencia,
  severidadeLatencia,
  type LimiaresLatencia,
  type MarcaAtribuicao,
  type SentidoAtribuicao,
  type SeveridadeLatencia,
} from "@/lib/derivacoes";
import {
  formatarHora,
  formatarSegundos,
  formatarSegundosLED,
  ROTULO_AUTOR,
} from "@/lib/formato";
import { fracaoDaPausa } from "@/lib/pausa";
import { cn } from "@/lib/utils";
import { SegmentoLED } from "@/components/instrumento/SegmentoLED";

const COR_SEVERIDADE: Record<SeveridadeLatencia, string> = {
  pico: "var(--promotor)",
  saudavel: "var(--muted-foreground)",
  degradando: "var(--neutro)",
  abandono: "var(--detrator)",
};

const COR_SENTIDO: Record<SentidoAtribuicao, string> = {
  puxou_para_baixo: "var(--detrator)",
  puxou_para_cima: "var(--promotor)",
  sem_inclinacao: "var(--muted-foreground)",
};

const ROTULO_SENTIDO: Record<SentidoAtribuicao, string> = {
  puxou_para_baixo: "puxou a nota para baixo",
  puxou_para_cima: "puxou a nota para cima",
  sem_inclinacao: "sem inclinação clara",
};

function porcentagem(valor: number): string {
  return `${Math.round(valor * 100)}%`;
}

/**
 * Intensidade do realce de um trecho, PROPORCIONAL a probabilidade real.
 *
 * O saldo (P(satisfeito) - P(insatisfeito)) vive em [-1, 1]; o realce usa o
 * modulo dele, com teto de 26% de opacidade -- acima disso o texto perde
 * contraste, e nenhuma marcacao vale um paragrafo ilegivel.
 *
 * A intensidade e o TERCEIRO canal, nunca o primeiro: a direcao ja esta no
 * ponto colorido E no rotulo textual embaixo. Quem nao distingue as cores
 * continua lendo "puxou a nota para baixo · 82% de insatisfeito".
 */
function realce(marca: MarcaAtribuicao): string | undefined {
  if (marca.sentido === "sem_inclinacao") return undefined;
  const intensidade = Math.min(1, Math.abs(marca.saldo)) * 26;
  return `color-mix(in oklch, ${COR_SENTIDO[marca.sentido]} ${intensidade.toFixed(1)}%, transparent)`;
}

/**
 * Transcricao com as tres coisas que transformam "nota ruim" em "oportunidade
 * de melhoria":
 *
 *   1. cliente e maquina visualmente distintos, em CARTOES RETANGULARES -- a
 *      fala do cliente e o que foi DITO, entao leva o filete ambar (`--dito`) e
 *      o fundo do papel; a resposta do bot ou do atendente fica RECUADA e em
 *      contorno TRACEJADO, porque nao e fala que o classificador de texto
 *      pontue. A prosa fica em Inter: mono em paragrafo cansa;
 *   2. a ESPERA do cliente, desenhada como a PAUSA da notacao (DESIGN.md §1.1):
 *      um intervalo tracejado entre a fala e a resposta, com o COMPRIMENTO
 *      proporcional a latencia e o tempo em LED. Ela sai dos timestamps, nao do
 *      modelo, e a faixa de severidade da literatura de live chat continua
 *      escrita por extenso ao lado (o ponto colorido nunca e o unico canal);
 *   3. a marcacao das falas do cliente pela probabilidade POR MENSAGEM do
 *      classificador, vinda de `GET /conversas/{id}/atribuicao`, com
 *      intensidade proporcional a essa probabilidade.
 *
 * A marcacao do item 3 e do SERVIDOR. Quando `marcas` vem vazio (a chamada da
 * atribuicao falhou), a transcricao aparece SEM marcacao nenhuma em vez de
 * cair de volta numa heuristica de emoji: uma fonte so para "o que puxou a
 * nota".
 *
 * A pausa mora ANTES da resposta que ela antecede (era uma legenda embaixo da
 * resposta): a leitura de cima para baixo passa a ser fala, silencio, resposta
 * -- a ordem em que o cliente viveu.
 */
export function Transcricao({
  conversa,
  marcas,
  limiares,
}: {
  conversa: DetalheConversa;
  marcas: Map<number, MarcaAtribuicao>;
  /** Limiares vigentes de latencia, lidos de `GET /configuracoes`. */
  limiares: LimiaresLatencia;
}) {
  const rotulos = rotulosLatencia(limiares);
  const latencias = new Map(
    latenciasAnotadas(conversa.mensagens).map((l) => [l.indice, l.segundos]),
  );

  return (
    <ol className="flex flex-col gap-2.5 bg-card p-3 sm:p-5">
      {conversa.mensagens.map((mensagem, indice) => {
        const doCliente = mensagem.autor === "cliente";
        const latencia = latencias.get(indice);
        const marca = marcas.get(indice);
        const severidade =
          latencia === undefined
            ? null
            : severidadeLatencia(latencia, limiares);
        const marcada = doCliente && marca && marca.sentido !== "sem_inclinacao";

        return (
          <Fragment key={`${indice}-${mensagem.enviada_em}`}>
            {latencia !== undefined && severidade ? (
              <li
                className="quebra-evitar grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-3 gap-y-1 py-0.5 sm:pl-10"
                aria-label={`espera de ${formatarSegundos(latencia)} do cliente até esta resposta`}
              >
                <PausaEmLED segundos={latencia} />
                <span aria-hidden className="relative block h-4 min-w-0">
                  <span
                    className="absolute inset-y-0 left-0 border-x border-medido"
                    style={{ width: `${fracaoDaPausa(latencia, limiares) * 100}%` }}
                  >
                    <span className="absolute inset-x-0 top-1/2 border-t border-dashed border-medido" />
                  </span>
                </span>
                <p className="col-span-2 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[0.6875rem] text-muted-foreground">
                  <span
                    aria-hidden
                    className="inline-block size-1.5 rounded-full"
                    style={{ background: COR_SEVERIDADE[severidade] }}
                  />
                  <span>
                    de espera do cliente até esta resposta ·{" "}
                    {rotulos[severidade].titulo.toLowerCase()} (
                    {rotulos[severidade].detalhe})
                  </span>
                </p>
              </li>
            ) : null}

            <li
              className={cn(
                "quebra-evitar min-w-0 border p-3.5",
                doCliente
                  ? "border-linha border-l-2 border-l-dito bg-background"
                  : "border-dashed border-border sm:ml-10",
              )}
            >
              <div className="mb-1.5 flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
                <span
                  className={cn(
                    "rotulo-instrumento",
                    doCliente && "text-dito-texto",
                  )}
                >
                  {ROTULO_AUTOR[mensagem.autor] ?? mensagem.autor}
                </span>
                <span className="num text-[0.6875rem] text-muted-foreground">
                  {formatarHora(mensagem.enviada_em)}
                </span>
              </div>

              <p
                className={cn(
                  "max-w-[70ch] text-sm leading-relaxed",
                  doCliente ? "text-foreground" : "text-muted-foreground",
                  marcada && "-mx-2 px-2 py-1",
                )}
                style={
                  marcada && marca ? { backgroundColor: realce(marca) } : undefined
                }
              >
                {mensagem.texto}
              </p>

              {marca ? (
                <div className="mt-2 flex flex-col gap-1">
                  <p className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                    <span className="inline-flex items-baseline gap-1.5 text-xs font-medium text-foreground">
                      <span
                        aria-hidden
                        className="inline-block size-2 -translate-y-px rounded-full"
                        style={{ background: COR_SENTIDO[marca.sentido] }}
                      />
                      {ROTULO_SENTIDO[marca.sentido]}
                    </span>
                    <span className="num text-xs text-muted-foreground">
                      {porcentagem(marca.probabilidade)} de {marca.classe} no
                      classificador de texto
                    </span>
                  </p>
                  <BarraProbabilidade marca={marca} />
                </div>
              ) : null}
            </li>
          </Fragment>
        );
      })}
    </ol>
  );
}

/** A duracao da pausa no display: so digitos, e a unidade escrita ao lado. */
function PausaEmLED({ segundos }: { segundos: number }) {
  const { valor, unidade } = formatarSegundosLED(segundos);
  return (
    <span className="flex items-end gap-1">
      <SegmentoLED
        valor={valor}
        rotulo="espera do cliente até esta resposta"
        altura={18}
      />
      <span className="pb-px text-[0.6875rem] leading-none text-muted-foreground">
        {unidade}
      </span>
    </span>
  );
}

/**
 * Barra das tres probabilidades da mensagem, na ordem fixa das classes
 * (0 insatisfeito, 1 neutro, 2 satisfeito -- invariante 8). E a leitura mais
 * rapida possivel de "o quanto o modelo esta convencido": a largura E a
 * probabilidade. Intensidade RELATIVA, nao confianca: probabilidade nao
 * calibrada nao e confianca.
 */
function BarraProbabilidade({ marca }: { marca: MarcaAtribuicao }) {
  const faixas = [
    { chave: "insatisfeito", valor: marca.probInsatisfeito, cor: "var(--detrator)" },
    { chave: "neutro", valor: marca.probNeutro, cor: "var(--neutro)" },
    { chave: "satisfeito", valor: marca.probSatisfeito, cor: "var(--promotor)" },
  ];

  return (
    <span
      className="flex h-1 w-full max-w-[22rem] gap-px overflow-hidden bg-muted"
      role="img"
      aria-label={faixas
        .map((faixa) => `${faixa.chave} ${porcentagem(faixa.valor)}`)
        .join(", ")}
      title={faixas
        .map((faixa) => `${faixa.chave}: ${porcentagem(faixa.valor)}`)
        .join(" · ")}
    >
      {faixas.map((faixa) => (
        <span
          key={faixa.chave}
          style={{ width: `${faixa.valor * 100}%`, background: faixa.cor }}
        />
      ))}
    </span>
  );
}
