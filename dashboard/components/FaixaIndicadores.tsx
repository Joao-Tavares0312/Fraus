"use client";

import { motion } from "motion/react";
import { RessalvaDaTela } from "./AparatoDaTela";
import { CartaoIndicador, type Trilho } from "./CartaoIndicador";
import { DiscordanciaContida } from "./DiscordanciaContida";
import { IntervaloDoNps } from "./IntervaloDoNps";
import { pilha } from "@/lib/movimento";
import { cn } from "@/lib/utils";
import {
  CSAT_SAUDAVEL,
  emMinutos,
  type IndicadoresDoPeriodo,
  type LimiaresLatencia,
} from "@/lib/derivacoes";
import {
  DEFINICAO_SEM_SINAL_AGREGADO,
  formatarNps,
  formatarNumero,
  formatarSegundosLED,
} from "@/lib/formato";

/**
 * Os quatro indicadores do periodo.
 *
 * NPS e CSAT levam a etiqueta "estimativa" e o sublinhado de proveniencia: os
 * dois sao INFERIDOS do texto, nao perguntados ao cliente. Contencao e latencia
 * sao OBSERVADAS -- saem de `escalou_para_humano` e dos timestamps -- e por
 * isso nao levam nem etiqueta nem sublinhado. A diferenca entre as duas
 * origens e o produto inteiro.
 *
 * Cada cartao falha sozinho: `erro` pinta so o proprio cartao.
 */

const TRILHO_NPS: Trilho = {
  minimo: -100,
  maximo: 100,
  // O NPS nao tem "faixa saudavel" universal publicada que caiba aqui sem
  // inventar limiar, entao o trilho marca apenas o ZERO -- a fronteira entre
  // mais detratores e mais promotores, que e definicao, nao benchmark.
  faixas: [],
  marcas: [{ valor: 0, rotulo: "zero: tantos promotores quanto detratores" }],
};

const TRILHO_CSAT: Trilho = {
  minimo: 0,
  maximo: 100,
  faixas: [
    {
      de: CSAT_SAUDAVEL.de,
      ate: CSAT_SAUDAVEL.ate,
      rotulo: `banda saudável ${CSAT_SAUDAVEL.de}–${CSAT_SAUDAVEL.ate}%`,
      cor: "bg-medido-fraco",
    },
  ],
};

/**
 * As faixas de referencia da latencia saem dos limiares VIGENTES
 * (`GET /configuracoes`), nao de constante do front: e a tela de Configuracoes
 * que decide onde este trilho corta.
 */
function trilhoDeLatencia(limiares: LimiaresLatencia): Trilho {
  return {
    minimo: 0,
    maximo: limiares.degradando,
    faixas: [
      {
        de: 0,
        ate: limiares.pico,
        rotulo: `até ${limiares.pico}s resposta imediata`,
        cor: "bg-promotor",
      },
      {
        de: limiares.pico,
        ate: limiares.saudavel,
        rotulo: `até ${limiares.saudavel}s saudável`,
        cor: "bg-neutro",
      },
      {
        de: limiares.saudavel,
        ate: limiares.degradando,
        rotulo: `até ${emMinutos(limiares.degradando)}min degradando`,
        cor: "bg-detrator",
      },
    ],
  };
}

export function FaixaIndicadores({
  indicadores,
  tempoMediano,
  limiares,
  erro,
  rotuloDoPeriodo,
}: {
  indicadores: IndicadoresDoPeriodo;
  tempoMediano: number | null;
  /** Limiares vigentes de latencia, lidos de `GET /configuracoes`. */
  limiares: LimiaresLatencia;
  /** Falha da listagem: todos os quatro dependem dela. */
  erro?: string;
  rotuloDoPeriodo: string;
}) {
  const semSinalTexto =
    indicadores.semSinal > 0
      ? `${indicadores.semSinal} de ${indicadores.total} sem sinal (${DEFINICAO_SEM_SINAL_AGREGADO}) — fora do cálculo, nunca como zero.`
      : undefined;

  // A faixa de leitura do NPS so existe se ha o que dizer sobre ele: o texto de
  // "com sinal" (so com NPS) ou o intervalo (so quando o SERVIDOR o calculou).
  const temLeituraDoNps =
    indicadores.nps !== null || indicadores.npsIntervalo !== null;

  return (
    <>
      <div className="flex min-w-0 flex-col gap-3">
        {/* A ARMADURA: uma faixa horizontal de quatro celulas, lida de uma vez --
            como o painel de leitura de um instrumento. Desde 30/09/2026
            (Instrumento) ela abre a tela em largura total, e nao mais empilhada
            a esquerda: o numero em LED pede corpo, e quatro leituras lado a
            lado cabem na dobra sem empurrar o grafico. O que continua valendo
            da regra antiga: e rotulo mais numero, sem barra de progresso
            decorativa. As quatro celulas tem a MESMA altura curta: o texto do
            NPS e o intervalo moram na faixa logo abaixo, nao aqui dentro. */}
        <motion.section
          aria-label={`Indicadores de ${rotuloDoPeriodo}`}
          // A ARMADURA e o container da pilha: ela escalona os quatro
          // indicadores em 40ms, e cada `CartaoIndicador` herda a variante
          // daqui. Escalonar aqui, e nao no `Painel`, e o que da a leitura de
          // cima para baixo -- que e a ordem em que a armadura de clave se le.
          variants={pilha}
          initial="oculto"
          whileInView="presente"
          viewport={{ once: true, margin: "0px 0px -64px 0px" }}
          // O HAIRLINE ENTRE CELULAS e o `gap-px` sobre fundo de regua: cada
          // celula pinta o proprio fundo opaco e o vao de 1px deixa aparecer a
          // `--linha` por baixo. Uma tecnica so serve a qualquer numero de
          // colunas (1, 2 ou 4) sem cada breakpoint recontar qual celula leva
          // qual borda.
          className="grid min-w-0 grid-cols-1 gap-px border border-linha bg-linha sm:grid-cols-2 xl:grid-cols-4 [&>*]:bg-background"
        >
          <CartaoIndicador
            rotulo="NPS inferido"
            qualificacao="estimativa"
            estimativa
            erro={erro}
            valor={indicadores.nps}
            formatado={
              indicadores.nps === null
                ? undefined
                : formatarNps(indicadores.nps)
            }
            trilho={TRILHO_NPS}
            explicacaoVazio={
              indicadores.total === 0
                ? "Nenhum atendimento no período selecionado."
                : "Nenhum atendimento do período tem fala do cliente, então não há categoria para agregar."
            }
          />

          <CartaoIndicador
            rotulo="CSAT inferido"
            qualificacao="estimativa"
            estimativa
            unidade="%"
            erro={erro}
            valor={indicadores.csat}
            formatado={
              indicadores.csat === null
                ? undefined
                : formatarNumero(indicadores.csat)
            }
            trilho={TRILHO_CSAT}
            explicacaoVazio="Sem atendimento pontuado no período, não há proporção de satisfeitos a calcular."
          />

          <CartaoIndicador
            rotulo="Taxa de contenção"
            qualificacao="observado"
            unidade="%"
            erro={erro}
            valor={indicadores.containment}
            formatado={
              indicadores.containment === null
                ? undefined
                : formatarNumero(indicadores.containment)
            }
            trilho={{ minimo: 0, maximo: 100, faixas: [] }}
            explicacaoVazio="Nenhuma transcrição carregada no período — a contenção sai de escalou_para_humano, que vem com a conversa."
          />

          <CartaoIndicador
            rotulo="Latência mediana"
            qualificacao="observado"
            erro={erro}
            valor={tempoMediano}
            formatado={
              tempoMediano === null
                ? undefined
                : formatarSegundosLED(tempoMediano).valor
            }
            unidade={
              tempoMediano === null
                ? undefined
                : formatarSegundosLED(tempoMediano).unidade
            }
            trilho={trilhoDeLatencia(limiares)}
            explicacaoVazio="Nenhum par pergunta → resposta no período: sem duas mensagens seguidas não há espera a medir."
          />
        </motion.section>

        {/* A LEITURA DO NPS. O texto de "com sinal" e a incerteza amostral
            moravam DENTRO da celula do NPS e esticavam as quatro celulas ate a
            altura dela: ~60% de vazio nas outras tres, e o grafico dominante
            empurrado para baixo da dobra. Nada foi removido -- a contagem, o
            intervalo de 95% e a contencao que nao convenceu continuam visiveis
            POR PADRAO, so ganharam uma faixa propria, colada a armadura. */}
        {erro ? null : (
          <div
            className={cn(
              "grid min-w-0 gap-px border border-linha bg-linha [&>*]:bg-background",
              temLeituraDoNps && "lg:grid-cols-[1.35fr_1fr]",
            )}
          >
            {temLeituraDoNps ? (
              <div
                className="flex min-w-0 flex-col gap-2 p-4"
                data-slot="leitura-do-nps"
              >
                <h3 className="rotulo-instrumento">
                  Leitura do NPS · quantas conversas sustentam o número
                </h3>
                {indicadores.nps === null ? null : (
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    Sobre {indicadores.comSinal} atendimento(s) com sinal.{" "}
                    {semSinalTexto ?? ""}
                  </p>
                )}
                {/* A INCERTEZA AMOSTRAL do NPS, colada nele. Sem isto o mesmo
                    "-12" aparecia com 8 atendimentos e com 8.000, e o
                    intervalo e a resposta da tela para "quantas conversas
                    sustentam esse numero?". So aparece quando o SERVIDOR
                    calculou: o plano B deixa `npsIntervalo` nulo de
                    proposito, porque derivar aqui duplicaria N_MINIMO_NPS em
                    TypeScript -- a divergencia que a invariante 3 existe
                    para impedir. */}
                {indicadores.npsIntervalo ? (
                  <IntervaloDoNps intervalo={indicadores.npsIntervalo} />
                ) : null}
              </div>
            ) : null}

            {/* O FALSO CONTAINMENT e a leitura critica da contencao e da
                latencia acima, e nao um quinto cartao: e o unico ponto da tela
                onde dito e medido se contradizem -- ver DiscordanciaContida. */}
            <DiscordanciaContida
              percentual={indicadores.falsoContainment}
              contidos={indicadores.contidosComSinal}
              className="p-4"
            />
          </div>
        )}
      </div>

      {/* O METODO dos quatro indicadores vira UM aparato so, no pe da tela --
          antes cada cartao carregava o proprio paragrafo e a pilha inteira
          gastava mais tela em prosa fixa do que em numero (regra ja paga duas
          vezes: ressalva repetida vira ruido e para de ser lida). O que
          continua colado ao numero e DADO do recorte -- a contagem de "com
          sinal" do NPS e a legenda de cortes do trilho -- porque muda com o
          filtro. Por ser filho de verdade (RessalvaDaTela via portal, nao
          estado copiado), este texto acompanha `limiares` e `indicadores`
          sempre que a tela re-renderiza, em vez de congelar no valor do
          primeiro registro. */}
      <RessalvaDaTela titulo="Indicadores">
        <dl className="flex max-w-[52ch] flex-col gap-1.5 text-[0.6875rem] leading-snug text-muted-foreground">
          <div>
            <dt className="inline font-medium">CSAT inferido:</dt>{" "}
            <dd className="inline">
              proporção de atendimentos com nota ≥ 7, a mesma regra do
              servidor.
            </dd>
          </div>
          <div>
            <dt className="inline font-medium">Taxa de contenção:</dt>{" "}
            <dd className="inline">
              atendimentos resolvidos sem passar para um humano. Não depende de
              score.
            </dd>
          </div>
          <div>
            <dt className="inline font-medium">Latência mediana:</dt>{" "}
            <dd className="inline">
              mediana do intervalo entre a fala do cliente e a resposta
              seguinte, derivada dos timestamps. Os cortes do trilho (
              {limiares.pico} s, {limiares.saudavel} s e{" "}
              {emMinutos(limiares.degradando)} min) são configuráveis em
              Configurações.
            </dd>
          </div>
        </dl>
      </RessalvaDaTela>
    </>
  );
}
