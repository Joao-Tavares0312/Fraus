"use client";

import { motion } from "motion/react";
import { RessalvaDaTela } from "./AparatoDaTela";
import { CartaoIndicador, type Trilho } from "./CartaoIndicador";
import { DiscordanciaContida } from "./DiscordanciaContida";
import { IntervaloDoNps } from "./IntervaloDoNps";
import { pilha } from "@/lib/movimento";
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
  formatarSegundos,
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

  return (
    <>
    {/* A ARMADURA: empilhada, lida de uma vez, como a armadura de clave que nao
        se rele a cada compasso. Ela mora a ESQUERDA da linha do tempo, entao a
        pilha vertical e a forma certa em tela larga -- a fileira de quatro
        colunas era o template de metrica-heroi, e ele empurrava a tese da tela
        para baixo da dobra. */}
    <motion.section
      aria-label={`Indicadores de ${rotuloDoPeriodo}`}
      // A ARMADURA e o container da pilha: ela escalona os quatro indicadores
      // em 40ms, e cada `CartaoIndicador` herda a variante daqui. Escalonar
      // aqui, e nao no `Painel`, e o que da a leitura de cima para baixo --
      // que e a ordem em que a armadura de clave se le.
      variants={pilha}
      initial="oculto"
      whileInView="presente"
      viewport={{ once: true, margin: "0px 0px -64px 0px" }}
      // A §2.2 do DESIGN.md sempre disse que os indicadores sao "rotulo mais
      // numero tabular, sem barra de progresso decorativa e sem cartao": a
      // armadura NAO e um painel, entao perde vidro/chanfro/borda -- ela le
      // como pilha compacta, separada por regua (`CartaoIndicador` usa
      // `border-linha`, nao mais `border-compasso`, porque compasso e a linha
      // fraca pensada para viver DENTRO de uma superficie de vidro).
      className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-x-5 xl:grid-cols-1"
    >
      <CartaoIndicador
        rotulo="NPS inferido"
        qualificacao="estimativa"
        estimativa
        erro={erro}
        valor={indicadores.nps}
        formatado={
          indicadores.nps === null ? undefined : formatarNps(indicadores.nps)
        }
        trilho={TRILHO_NPS}
        explicacaoVazio={
          indicadores.total === 0
            ? "Nenhum atendimento no período selecionado."
            : "Nenhum atendimento do período tem fala do cliente, então não há categoria para agregar."
        }
        rodape={
          indicadores.nps === null
            ? undefined
            : `Sobre ${indicadores.comSinal} atendimento(s) com sinal. ${semSinalTexto ?? ""}`
        }
      />

      {/* A INCERTEZA AMOSTRAL do NPS, colada nele. Sem isto o mesmo "-12"
          aparecia com 8 atendimentos e com 8.000, e o intervalo e a resposta
          da tela para "quantas conversas sustentam esse numero?". So aparece
          quando o SERVIDOR calculou: o plano B deixa `npsIntervalo` nulo de
          proposito, porque derivar aqui duplicaria N_MINIMO_NPS em
          TypeScript -- a divergencia que a invariante 3 existe para impedir. */}
      {erro || !indicadores.npsIntervalo ? null : (
        <IntervaloDoNps
          intervalo={indicadores.npsIntervalo}
          className="-mt-1"
        />
      )}

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
          tempoMediano === null ? undefined : formatarSegundos(tempoMediano)
        }
        trilho={trilhoDeLatencia(limiares)}
        explicacaoVazio="Nenhum par pergunta → resposta no período: sem duas mensagens seguidas não há espera a medir."
      />

      {/* O FALSO CONTAINMENT vem logo DEPOIS da taxa de contencao e da
          latencia, e nao como quinto cartao: ele e a leitura critica dos dois
          numeros acima. Composicao propria porque e o unico ponto da tela
          onde dito e medido se contradizem -- ver DiscordanciaContida. */}
      {erro ? null : (
        <DiscordanciaContida
          percentual={indicadores.falsoContainment}
          contidos={indicadores.contidosComSinal}
          className="border-t border-linha pt-3"
        />
      )}
    </motion.section>
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
