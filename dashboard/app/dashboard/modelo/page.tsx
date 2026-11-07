/**
 * =============================================================================
 * MODELO — a superficie de configuracao e inspecao da IA
 *
 * As outras duas telas mostram o que o modelo DECIDIU. Esta mostra o modelo:
 * quanto cada sinal pesa, o que o treino mediu, que tabela de emoji ele usa e
 * o que ele responde a uma frase nova, agora, ao vivo.
 *
 * Ela e tambem onde a distincao mais importante do trabalho fica explicita:
 * aqui vive `importancias` -- peso GLOBAL, sempre positivo, agrupado por tipo
 * de sinal. `contribuicoes`, que tem sinal e vale para UM atendimento, vive na
 * tela do atendimento e em lugar nenhum mais.
 * =============================================================================
 */

import { ArrowUpRight, ChevronRight } from "lucide-react";
import Link from "next/link";
import { obterModelo } from "@/lib/api";
import { CabecalhoPagina } from "@/components/shell/CabecalhoPagina";
import { EstadoVazio } from "@/components/EstadoVazio";
import { Painel } from "@/components/Painel";
import { PainelDrivers } from "@/components/PainelDrivers";
import { EstadoDoModelo } from "@/components/modelo/EstadoDoModelo";
import { LexiconEmoji } from "@/components/modelo/LexiconEmoji";
import { LexicoCurado } from "@/components/modelo/LexicoCurado";
import { MetricasTreino } from "@/components/modelo/MetricasTreino";
import { PesosFeatures } from "@/components/modelo/PesosFeatures";
import { VisualizacaoModelo } from "@/components/modelo/VisualizacaoModelo";
import { erroParaTela } from "@/lib/erro-publico";
import { sessaoAtual } from "@/lib/sessao";

export const dynamic = "force-dynamic";

const COR_DA_CATEGORIA: Record<string, string> = {
  detrator: "var(--detrator)",
  neutro: "var(--neutro)",
  promotor: "var(--promotor)",
};

export default async function PaginaModelo() {
  const [resultado, sessao] = await Promise.all([obterModelo(), sessaoAtual()]);
  // Mesmo criterio do detalhe do atendimento: sem login, a instalacao local e dev.
  const ehDev = (sessao.estado === "logada" ? sessao.usuario.papel : "dev") === "dev";

  if (!resultado.ok) {
    return (
      <>
        <CabecalhoPagina
          titulo="Modelo"
          subtitulo="Pesos, métricas, lexicon e simulador: a ficha da IA que pontua os atendimentos."
        />
        {/* COM flex-1: ver o comentario identico em app/dashboard/configuracoes/page.tsx
            e app/dashboard/grafo/page.tsx -- o EstadoVazio depende do pai
            esticado ate a altura da tela para se centralizar verticalmente
            (empty.tsx usa flex-1 ... justify-center). O ramo de SUCESSO logo
            abaixo e que fica sem flex-1. */}
        <div className="flex min-w-0 flex-1 flex-col gap-4 px-4 py-4 sm:px-6">
          <EstadoVazio
            titulo="A ficha do modelo não carregou"
            explicacao={erroParaTela(resultado.erro, ehDev)}
            endpoint={ehDev ? "GET /modelo" : undefined}
          />
        </div>
      </>
    );
  }

  const modelo = resultado.dado;
  const faixas = Object.entries(modelo.faixas_nps);
  // Do dado, nunca cravado: se o retreino fizer a ironia pontuar, a frase muda.
  const ironiaPontua = modelo.cabecas.find((cabeca) => cabeca.nome === "ironia")?.pontua ?? false;

  return (
    <>
      <CabecalhoPagina
        titulo="Modelo"
      />

      {/* SEM flex-1: ver o comentario identico em app/dashboard/page.tsx.
          O ramo de erro/vazio logo acima continua com flex-1 -- o EstadoVazio
          depende dele para se centralizar na coluna. */}
      <div className="flex min-w-0 flex-col gap-4 px-4 py-4 sm:px-6">
        <Painel
          titulo="Classifique uma frase"
          nivel="dominante"
          legenda="Explore o caminho entre conversa, famílias de sinais e fusor. A classificação de frase usa uma única chamada a POST /modelo/simular e não persiste dados."
          semPadding
          rodape="A ordem das classes é fixa em todo o sistema (0 insatisfeito, 1 neutro, 2 satisfeito), no notebook, no sinal de texto, no fusor e aqui. Inverter não geraria erro: faria o sistema pontuar ao contrário em silêncio."
        >
          <div className="px-4 pb-2 sm:px-6">
            <VisualizacaoModelo modelo={modelo} />
          </div>
        </Painel>

        {/* Os limites ficam fora do recolhido: honestidade nao se recolhe inteira. */}
        <p className="max-w-prose text-sm leading-relaxed text-muted-foreground">
          O sinal de tempo é treinado em conversas sintéticas.
          {ironiaPontua ? " A ironia entra na nota." : " A ironia é lida por mensagem e não entra na nota."}
        </p>

        {/* KISS (04/11/2026): como no detalhe do atendimento, a leitura tecnica
            fica recolhida. Quem quer o porque abre; a banca encontra tudo aqui. */}
        <details className="group min-w-0 border-t border-linha pt-3">
          <summary className="flex cursor-pointer list-none items-center gap-1.5 text-sm font-medium text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring [&::-webkit-details-marker]:hidden">
            <ChevronRight aria-hidden className="size-4 transition-transform group-open:rotate-90" />
            Como o modelo foi avaliado
          </summary>
          <div className="flex min-w-0 flex-col gap-4 pt-4">
        <EstadoDoModelo modelo={modelo} nivel="apoio" />

        <div className="grid min-w-0 grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
          <Painel
            titulo={Object.keys(modelo.importancias).length ? `Peso global das ${Object.keys(modelo.importancias).length} features observadas` : "Pesos globais indisponíveis"}
            legenda="Coeficientes do fusor (regressão logística), agrupados pelas sete famílias do trabalho. Este é o peso do MODELO: vale para todos os atendimentos e não explica nenhum em particular."
            semPadding
            rodape={
              <>
                Para saber por que <em>um</em> atendimento tirou aquela nota,
                abra o atendimento: lá está a contribuição de cada sinal, específica
                daquela conversa.{" "}
                <Link
                  href="/dashboard/atendimentos"
                  className="inline-flex items-center gap-0.5 text-primary underline underline-offset-4"
                >
                  Ir para Atendimentos
                  <ArrowUpRight aria-hidden className="size-3" />
                </Link>
              </>
            }
          >
            <PesosFeatures importancias={modelo.importancias} />
          </Painel>

          <div className="flex min-w-0 flex-col gap-4">
            <Painel
              titulo="Métricas do treino"
              legenda="Medidas exportadas pelos notebooks, não recalculadas aqui. Satisfação e emoção alimentam o fusor conforme o campo pontua da ficha; ironia permanece leitura por mensagem no contrato vigente. As métricas históricas não provam generalização para atendimentos reais nem recuperam curvas antigas. Procedência e limitações vêm dos arquivos exportados."
              semPadding
            >
              <MetricasTreino
                metricas={modelo.metricas}
                cabecas={modelo.cabecas}
              />
            </Painel>

            <Painel
              titulo="Faixas de NPS e classes"
              legenda="Lidas de GET /modelo, nunca digitadas no front. É a mesma constante FAIXAS_NPS que o servidor usa para gravar a categoria de cada atendimento."
            >
              <dl className="flex flex-col gap-2">
                {faixas.map(([categoria, [minima, maxima]]) => (
                  <div
                    key={categoria}
                    className="flex items-center justify-between gap-3 border-b border-border pb-2 last:border-b-0 last:pb-0"
                  >
                    <dt className="flex items-center gap-2 text-sm text-foreground">
                      <span
                        aria-hidden
                        className="size-2 shrink-0 rounded-full"
                        style={{
                          background:
                            COR_DA_CATEGORIA[categoria] ??
                            "var(--muted-foreground)",
                        }}
                      />
                      {categoria}
                    </dt>
                    <dd className="num text-sm text-muted-foreground">
                      nota {minima}–{maxima}
                    </dd>
                  </div>
                ))}
              </dl>

              <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
                Classes do classificador, na ordem fixa:{" "}
                <span className="num text-foreground">
                  {modelo.classes.join(" · ")}
                </span>
                . Atendimento sem fala do cliente, ou só com fórmulas de
                cortesia, não cai em faixa nenhuma:
                fica como <strong className="text-foreground">sem sinal</strong>
                , que não é uma quarta categoria e não pertence à escala.
              </p>
            </Painel>
          </div>
        </div>

        {/* Veio da Visao geral em 30/10/2026 (KISS): influencia dos sinais e
            leitura de modelo, nao de operacao. Sem recorte: todo o periodo. */}
        <PainelDrivers de={null} ate={null} />

        <Painel
          titulo={`Lexicon de emoji (${modelo.total_emojis_lexicon} entradas)`}
          legenda="Tabela do Emoji Sentiment Ranking usada pelo sinal de emoji. O score de cada linha vem da mesma função que pontua a conversa e o simulador. Não há fórmula reimplementada na interface. As contagens são as anotações humanas originais."
          semPadding
        >
          <LexiconEmoji total={modelo.total_emojis_lexicon} />
        </Painel>

        {/* Depois do lexicon de emoji de propósito: primeiro o que o projeto
            trouxe pronto, depois o que esta instalação acrescentou por cima. */}
        {/* Curar e escrever (POST /lexico): segue dev mesmo com a tela publica. */}
        {ehDev ? <LexicoCurado totalEmojisLexicon={modelo.total_emojis_lexicon} /> : null}
          </div>
        </details>
      </div>
    </>
  );
}
