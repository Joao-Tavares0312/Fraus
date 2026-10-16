"use client";

import { motion } from "motion/react";
import type { ReactNode } from "react";
import { ehFalhaDeConexao } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { ValorNumerico } from "@/components/ValorNumerico"
import { TRANSICAO, itemDaPilha } from "@/lib/movimento";

/**
 * Uma faixa de referencia no trilho do indicador.
 *
 * `de` e `ate` estao na MESMA unidade do indicador; a conversao para
 * percentual do trilho acontece aqui, uma vez so.
 */
export type FaixaReferencia = {
  de: number;
  ate: number;
  rotulo: string;
  /** Classe de fundo do token; sempre chapada -- degrade distorce leitura de area. */
  cor: string;
};

export type Trilho = {
  minimo: number;
  maximo: number;
  faixas: FaixaReferencia[];
  /** Marcas de escala (o valor extremo e o zero do NPS, por exemplo). */
  marcas?: { valor: number; rotulo: string }[];
};

function posicao(valor: number, trilho: Trilho): number {
  const fracao = (valor - trilho.minimo) / (trilho.maximo - trilho.minimo);
  return Math.min(100, Math.max(0, fracao * 100));
}

/** Cada indicador mantém sua própria falha, ausência e proveniência. */
export function CartaoIndicador({
  rotulo,
  valor,
  unidade,
  formatado,
  qualificacao,
  estimativa,
  explicacaoVazio,
  erro,
  trilho,
  rodape,
}: {
  rotulo: string;
  valor: number | null;
  unidade?: string;
  /** Ja formatado em pt-BR pelo chamador -- uma fonte so de formatacao. */
  formatado?: string;
  /** Etiqueta curta ao lado do rotulo: "estimativa", "observado". */
  qualificacao?: string;
  /** Marca o numero com o sublinhado pontilhado de proveniencia. */
  estimativa?: boolean;
  /** Por que nao ha numero. Obrigatorio na pratica quando `valor` e null. */
  explicacaoVazio?: string;
  erro?: string;
  trilho?: Trilho;
  rodape?: ReactNode;
}) {
  return (
    <motion.div
      variants={itemDaPilha}
      className="quebra-evitar flex min-w-0 flex-col gap-3 p-4 sm:p-5"
      data-slot="indicador"
    >
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-sm font-medium">{rotulo}</h3>
        {qualificacao ? (
          <Badge variant="outline" className="shrink-0 border-0 px-0 text-muted-foreground">
            {qualificacao}
          </Badge>
        ) : null}
      </div>

      {erro ? (
        ehFalhaDeConexao(erro) ? (
          /* A armadura tem quatro indicadores lado a lado. Com a mensagem
             inteira, a MESMA url aparecia quatro vezes em vermelho, e o que o
             olho lia era o endereco, nao a ausencia de dado. O estado da API e
             da conexao ja esta na telemetria do topo e no rodape da navegacao,
             dito uma vez. */
          <p className="text-lg leading-none font-medium text-muted-foreground">
            <span className="num" aria-hidden>
              —
            </span>
            <span className="sr-only">sem dado: a API não respondeu</span>
          </p>
        ) : (
          <p className="text-xs leading-relaxed text-destructive">{erro}</p>
        )
      ) : valor === null ? (
        <>
          <ValorNumerico
            valor={null}
            rotulo={rotulo}
            ausencia={estimativa ? "Sem estimativa" : "Sem dados"}
            className="text-xl sm:text-2xl"
          />
          {explicacaoVazio ? (
            <p className="text-xs leading-relaxed text-muted-foreground">
              {explicacaoVazio}
            </p>
          ) : null}
        </>
      ) : (
        <>
          <div className="flex items-end gap-2">
            <span
              className={cn("inline-flex", estimativa && "estimado")}
            >
              <ValorNumerico
                valor={formatado ?? String(valor)}
                rotulo={rotulo}
                className="text-3xl"
                cor={estimativa ? "medido" : "tinta"}
              />
            </span>
            {unidade ? (
              <span className="rotulo-instrumento pb-1.5 tracking-normal normal-case">
                {unidade}
              </span>
            ) : null}
          </div>
          {trilho ? (
            <TrilhoDeReferencia valor={valor} trilho={trilho} />
          ) : null}
        </>
      )}

      {/* O metodo do indicador e APARATO: fica na tipografia menor, abaixo do
          numero, e nunca entre o rotulo e o valor. */}
      {rodape ? (
        <p className="text-[0.6875rem] leading-snug text-muted-foreground">
          {rodape}
        </p>
      ) : null}
    </motion.div>
  );
}

function TrilhoDeReferencia({
  valor,
  trilho,
}: {
  valor: number;
  trilho: Trilho;
}) {
  const legenda = trilho.faixas.map((faixa) => faixa.rotulo).join(" · ");

  return (
    <div className="mt-1 flex flex-col gap-1">
      <div
        className="relative h-1.5 w-full overflow-hidden bg-muted"
        role="img"
        aria-label={`Faixas de referência: ${legenda}.`}
      >
        {trilho.faixas.map((faixa) => (
          <span
            key={faixa.rotulo}
            aria-hidden
            title={faixa.rotulo}
            className={cn("absolute inset-y-0", faixa.cor)}
            style={{
              left: `${posicao(faixa.de, trilho)}%`,
              width: `${posicao(faixa.ate, trilho) - posicao(faixa.de, trilho)}%`,
            }}
          />
        ))}
        {trilho.marcas?.map((marca) => (
          <span
            key={marca.rotulo}
            aria-hidden
            title={marca.rotulo}
            className="absolute inset-y-0 w-px bg-border"
            style={{ left: `${posicao(marca.valor, trilho)}%` }}
          />
        ))}
        {/* O ponteiro do valor: barra de 2px na cor do texto, sempre por cima
            das faixas -- e o unico elemento do trilho que representa medicao.

            ELE NASCE ONDE PERTENCE, crescendo na vertical. A alternativa obvia
            -- deslizar da esquerda ate a posicao final -- foi rejeitada: o
            olho leria a corrida do zero ate 62 como se o indicador tivesse
            subido de zero a 62, uma progressao que dado nenhum aqui afirma.
            Movimento que insinua o que a medicao nao diz e o mesmo erro que
            plotar ausencia como zero, so em outra dimensao.

            `scaleY` e `opacity` sao transformacoes, entao o
            `reducedMotion="user"` do MotionConfig as descarta sozinho. */}
        <motion.span
          aria-hidden
          className="absolute inset-y-0 w-0.5 origin-center bg-foreground"
          style={{ left: `calc(${posicao(valor, trilho)}% - 1px)` }}
          initial={{ opacity: 0, scaleY: 0.3 }}
          animate={{ opacity: 1, scaleY: 1 }}
          transition={TRANSICAO.amplo}
        />
      </div>
      <p className="text-[0.6875rem] leading-tight text-muted-foreground">
        {legenda}
      </p>
    </div>
  );
}
