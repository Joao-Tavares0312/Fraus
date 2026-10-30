"use client";

import { motion } from "motion/react";
import { RessalvaDaTela } from "./AparatoDaTela";
import { Explicacao } from "./Explicacao";
import { CartaoIndicador, type Trilho } from "./CartaoIndicador";
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
  formatarDuracaoCompacta,
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
  // O intervalo decide se ha amostra para mostrar o ponto. `??` aqui
  // ressuscitaria o NPS bruto quando o servidor se abstem com `null`.
  // Sem intervalo (API antiga ou plano B), preserva a leitura disponivel.
  const npsExibido = indicadores.npsIntervalo
    ? indicadores.npsIntervalo.nps
    : indicadores.nps;
  const intervalo = indicadores.npsIntervalo;

  // KISS (30/10/2026): a contagem com/sem sinal fica colada ao NPS em uma
  // linha; o intervalo amostral e o "nunca como zero" vao para o ⓘ. Nada de
  // honestidade sumiu -- so saiu da frente do numero.
  const contagemNps =
    indicadores.total > 0
      ? `${indicadores.comSinal} com sinal · ${indicadores.semSinal} sem sinal`
      : undefined;

  return (
    <>
      <div className="flex min-w-0 flex-col gap-3">
        <motion.section
          aria-label={`Indicadores de ${rotuloDoPeriodo}`}
          // A ARMADURA e o container da pilha: ela escalona os quatro
          // indicadores em 40ms, e cada `CartaoIndicador` herda a variante.
          variants={pilha}
          initial="oculto"
          whileInView="presente"
          viewport={{ once: true, margin: "0px 0px -64px 0px" }}
          className="faixa-indicadores min-w-0"
        >
          <CartaoIndicador
            rotulo="NPS inferido"
            destaque
            qualificacao="estimativa"
            estimativa
            erro={erro}
            valor={npsExibido}
            formatado={
              npsExibido === null
                ? undefined
                : formatarNps(npsExibido)
            }
            trilho={TRILHO_NPS}
            explicacaoVazio={
              intervalo?.nps === null
                ? `Amostra insuficiente: ${intervalo.n} atendimento(s) com sinal.`
                : indicadores.total === 0
                  ? "Nenhum atendimento no período selecionado."
                  : "Nenhum atendimento do período tem sinal de satisfação suficiente para agregar."
            }
            rodape={contagemNps}
            explicacao={
              <>
                <strong>Inferido do texto, não perguntado ao cliente.</strong>{" "}
                Sem sinal = {DEFINICAO_SEM_SINAL_AGREGADO}; fica fora do
                cálculo e nunca entra como zero.
                {intervalo ? (
                  <>
                    {" "}
                    Intervalo de 95%:{" "}
                    <span className="num">{formatarNps(intervalo.ic_inferior)}</span> a{" "}
                    <span className="num">{formatarNps(intervalo.ic_superior)}</span>{" "}
                    (n={intervalo.n}). Mede a incerteza amostral, não o erro do
                    modelo.
                  </>
                ) : null}
              </>
            }
          />

          <CartaoIndicador
            rotulo="CSAT estimado"
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
            explicacaoVazio="Nenhum atendimento com nota para estimar a satisfação."
            explicacao={
              <>
                Proporção de atendimentos com nota ≥ 7. Faixa de referência:{" "}
                {CSAT_SAUDAVEL.de}–{CSAT_SAUDAVEL.ate}%.
              </>
            }
          />

          <CartaoIndicador
            rotulo="Contenção"
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
            explicacaoVazio="Nenhuma conversa disponível para verificar se houve transferência a uma pessoa."
            rodape={
              indicadores.falsoContainment === null ? undefined : <ContencaoQueNaoConvenceu
                percentual={indicadores.falsoContainment}
                contidos={indicadores.contidosComSinal}
              />
            }
            explicacao="Atendimentos resolvidos sem transferência para uma pessoa. Não comprova que o cliente saiu satisfeito."
          />

          <CartaoIndicador
            rotulo="Latência mediana"
            qualificacao="observado"
            erro={erro}
            valor={tempoMediano}
            formatado={
              tempoMediano === null
                ? undefined
                : formatarDuracaoCompacta(tempoMediano).valor
            }
            unidade={
              tempoMediano === null
                ? undefined
                : formatarDuracaoCompacta(tempoMediano).unidade
            }
            trilho={trilhoDeLatencia(limiares)}
            explicacaoVazio="Nenhuma resposta registrada para medir a espera."
            explicacao={
              <>
                Tempo típico entre a fala do cliente e a resposta. Faixas: até{" "}
                {limiares.pico} s imediata, até {limiares.saudavel} s saudável,
                até {emMinutos(limiares.degradando)} min degradando.
              </>
            }
          />
        </motion.section>
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
        <dl className="flex max-w-prose flex-col gap-2 text-sm leading-relaxed text-muted-foreground">
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
              atendimentos sem transferência para uma pessoa, a partir do campo{" "}
              <code>escalou_para_humano</code>. Não depende da nota nem comprova resolução.
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

/**
 * O falso containment em uma linha, dentro do cartao Contencao: o pedaco que o
 * cliente DISSE (ambar) contra o que o log MEDIU. `null` quando nenhum
 * contido tem nota -- zero se leria como "ninguem saiu insatisfeito".
 */
function ContencaoQueNaoConvenceu({
  percentual,
  contidos,
}: {
  percentual: number | null;
  contidos: number;
}) {
  if (percentual === null) return null;
  const insatisfeitos = Math.round((percentual / 100) * contidos);
  return (
    <span className="inline-flex items-center gap-1">
      <span>
        <strong className="num font-medium text-dito-texto">
          {percentual.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%
        </strong>{" "}
        saíram detratores sem escalar
      </span>
      <Explicacao rotulo="Sobre a contenção que não convenceu">
        {insatisfeitos} de {contidos} atendimento(s) contido(s) com sinal
        terminaram como detrator e não foram transferidos para uma pessoa.
        Contenção alta com essa taxa alta é sucesso falso.
      </Explicacao>
    </span>
  );
}
