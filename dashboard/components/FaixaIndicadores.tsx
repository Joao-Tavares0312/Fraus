"use client";

import { motion } from "motion/react";
import { Aparato } from "./Aparato";
import { CartaoIndicador, type Trilho } from "./CartaoIndicador";
import { pilha } from "@/lib/movimento";
import {
  CSAT_SAUDAVEL,
  emMinutos,
  type IndicadoresDoPeriodo,
  type LimiaresLatencia,
} from "@/lib/derivacoes";
import {
  formatarNps,
  formatarNumero,
  formatarSegundos,
} from "@/lib/formato";
import { useEspecular } from "@/hooks/useEspecular";

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
      ? `${indicadores.semSinal} de ${indicadores.total} sem fala do cliente — fora do cálculo, nunca como zero.`
      : undefined;

  const refEspecular = useEspecular<HTMLElement>();

  return (
    // A ARMADURA: empilhada, lida de uma vez, como a armadura de clave que nao
    // se rele a cada compasso. Ela mora a ESQUERDA da linha do tempo, entao a
    // pilha vertical e a forma certa em tela larga -- a fileira de quatro
    // colunas era o template de metrica-heroi, e ele empurrava a tese da tela
    // para baixo da dobra.
    <motion.section
      ref={refEspecular}
      aria-label={`Indicadores de ${rotuloDoPeriodo}`}
      // A ARMADURA e o container da pilha: ela escalona os quatro indicadores
      // em 40ms, e cada `CartaoIndicador` herda a variante daqui. Escalonar
      // aqui, e nao no `Painel`, e o que da a leitura de cima para baixo --
      // que e a ordem em que a armadura de clave se le.
      variants={pilha}
      initial="oculto"
      whileInView="presente"
      viewport={{ once: true, margin: "0px 0px -64px 0px" }}
      className="vidro especular chanfro grid grid-cols-1 gap-3 rounded-lg p-4 sm:grid-cols-2 sm:p-5 xl:grid-cols-1"
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

      {/*
        O METODO dos quatro indicadores vira UM aparato so, no pe da armadura —
        antes cada cartao carregava o proprio paragrafo e a pilha inteira
        gastava mais tela em prosa fixa do que em numero (regra ja paga duas
        vezes: ressalva repetida vira ruido e para de ser lida). O que continua
        colado ao numero e DADO do recorte — a contagem de "com sinal" do NPS e
        a legenda de cortes do trilho — porque muda com o filtro.
      */}
      <Aparato className="sm:col-span-2 xl:col-span-1">
        <dl className="mt-2 flex max-w-[52ch] flex-col gap-1.5 text-[0.6875rem] leading-snug text-muted-foreground">
          <div>
            <dt className="inline font-medium">CSAT inferido:</dt>{" "}
            <dd className="inline">
              proporção de atendimentos com nota ≥ 7, a mesma regra do servidor.
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
      </Aparato>
    </motion.section>
  );
}
