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

import { ArrowUpRight, Download } from "lucide-react";
import Link from "next/link";
import { URL_RELATORIO_COMPARACAO, obterComparacao, obterModelo } from "@/lib/api";
import { CabecalhoPagina } from "@/components/shell/CabecalhoPagina";
import { EstadoVazio } from "@/components/EstadoVazio";
import { Painel } from "@/components/Painel";
import { ComparacaoAoVivo } from "@/components/modelo/ComparacaoAoVivo";
import { LaudoDaComparacao, TempoDeResposta } from "@/components/modelo/ComparacaoModelos";
import { EstadoDoModelo } from "@/components/modelo/EstadoDoModelo";
import { LexiconEmoji } from "@/components/modelo/LexiconEmoji";
import { LexicoCurado } from "@/components/modelo/LexicoCurado";
import { MetricasTreino } from "@/components/modelo/MetricasTreino";
import { PesosFeatures } from "@/components/modelo/PesosFeatures";
import { Simulador } from "@/components/modelo/Simulador";
import { SimuladorIroniaLaya } from "@/components/modelo/SimuladorIroniaLaya";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export const dynamic = "force-dynamic";

const COR_DA_CATEGORIA: Record<string, string> = {
  detrator: "var(--detrator)",
  neutro: "var(--neutro)",
  promotor: "var(--promotor)",
};

export default async function PaginaModelo() {
  // As duas leituras em paralelo: o laudo de comparacao falha SOZINHO, dentro
  // da aba dele, sem derrubar a ficha do modelo.
  const [resultado, comparacao] = await Promise.all([obterModelo(), obterComparacao()]);

  if (!resultado.ok) {
    return (
      <>
        <CabecalhoPagina
          titulo="Modelo"
          subtitulo="Pesos, métricas, lexicon e simulador — a ficha da IA que pontua os atendimentos."
        />
        {/* COM flex-1: ver o comentario identico em app/dashboard/configuracoes/page.tsx
            e app/dashboard/grafo/page.tsx -- o EstadoVazio depende do pai
            esticado ate a altura da tela para se centralizar verticalmente
            (empty.tsx usa flex-1 ... justify-center). O ramo de SUCESSO logo
            abaixo e que fica sem flex-1. */}
        <div className="flex min-w-0 flex-1 flex-col gap-4 px-4 py-4 sm:px-6">
          <EstadoVazio
            titulo="A ficha do modelo não carregou"
            explicacao={`${resultado.erro}. Sem ela não há peso, métrica nem faixa a exibir — e preencher com valores plausíveis seria descrever um modelo que ninguém consultou.`}
            endpoint="GET /modelo"
          />
        </div>
      </>
    );
  }

  const modelo = resultado.dado;
  const faixas = Object.entries(modelo.faixas_nps);

  return (
    <>
      <CabecalhoPagina
        titulo="Modelo"
        subtitulo="A ficha da IA que pontua os atendimentos: quanto cada sinal pesa, o que o treino mediu, que tabela de emoji está em uso e o que o classificador responde a uma frase nova."
      />

      {/* SEM flex-1: ver o comentario identico em app/dashboard/page.tsx.
          O ramo de erro/vazio logo acima continua com flex-1 -- o EstadoVazio
          depende dele para se centralizar na coluna. */}
      <div className="flex min-w-0 flex-col gap-4 px-4 py-4 sm:px-6">
        <Tabs defaultValue="fraus" className="min-w-0 gap-4">
          <TabsList aria-label="Visões do modelo" variant="line" className="max-w-full overflow-x-auto">
            <TabsTrigger value="fraus">Modelo completo</TabsTrigger>
            <TabsTrigger value="laya">Ironia · Laya</TabsTrigger>
            <TabsTrigger value="comparacao">Comparação</TabsTrigger>
          </TabsList>

          <TabsContent value="fraus" className="flex min-w-0 flex-col gap-4">
        <EstadoDoModelo modelo={modelo} />

        <Painel
          titulo="Simulador ao vivo"
          legenda="Escreva uma fala de cliente e veja a resposta do classificador agora. Nada é persistido, nada é inventado: as três probabilidades e os emojis detectados vêm inteiros de POST /modelo/simular."
          semPadding
          rodape="A ordem das classes é fixa em todo o sistema — 0 insatisfeito, 1 neutro, 2 satisfeito — no notebook, no sinal de texto, no fusor e aqui. Inverter não geraria erro: faria o sistema pontuar ao contrário em silêncio."
        >
          <Simulador />
        </Painel>

        <div className="grid min-w-0 grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
          <Painel
            titulo={`Peso global das ${Object.keys(modelo.importancias).length} features`}
            legenda="Coeficientes do fusor (regressão logística), agrupados pelas sete famílias do trabalho. Este é o peso do MODELO — vale para todos os atendimentos e não explica nenhum em particular."
            semPadding
            rodape={
              <>
                Para saber por que <em>um</em> atendimento tirou aquela nota,
                abra o atendimento: lá está <code className="num">contribuicoes</code>
                , que tem sinal e é específica daquela conversa.{" "}
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
              legenda="Medidas no conjunto de teste pelos notebooks, não recalculadas aqui. As três cabeças aparecem juntas porque só comparando dá para ver o que cada número vale: a satisfação é a única que entra no fusor, a emoção reporta também o F1 num corpus independente que ela nunca viu, e a ironia reporta 100% — que é verdade no corpus dela e não sobrevive a fala de atendimento. Cada procedência e cada limitação vêm do arquivo que o próprio notebook exportou, inteiras."
              semPadding
            >
              <MetricasTreino
                metricas={modelo.metricas}
                cabecas={modelo.cabecas}
              />
            </Painel>

            <Painel
              titulo="Faixas de NPS e classes"
              legenda="Lidas de GET /modelo, nunca digitadas no front — é a mesma constante FAIXAS_NPS que o servidor usa para gravar a categoria de cada atendimento."
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

        <Painel
          titulo={`Lexicon de emoji (${modelo.total_emojis_lexicon} entradas)`}
          legenda="Tabela do Emoji Sentiment Ranking usada pelo sinal de emoji. O score de cada linha vem da mesma função que pontua a conversa e o simulador — não há fórmula reimplementada na interface. As contagens são as anotações humanas originais."
          semPadding
        >
          <LexiconEmoji total={modelo.total_emojis_lexicon} />
        </Painel>

        {/* Depois do lexicon de emoji de propósito: primeiro o que o projeto
            trouxe pronto, depois o que esta instalação acrescentou por cima. */}
        <LexicoCurado totalEmojisLexicon={modelo.total_emojis_lexicon} />
          </TabsContent>

          <TabsContent value="laya" className="flex min-w-0 flex-col gap-4">
            <Painel
              titulo="Classificador de ironia · Laya"
              legenda="Teste isolado do checkpoint multilíngue convaiinnovations/laya. Esta leitura não executa satisfação, emoção, emojis ou fusor e não altera a nota dos atendimentos."
              semPadding
              rodape="A decisão binária é experimental. A promoção para uso corrente depende do gate de domínio e de calibração em dados portugueses separados do treino."
            >
              <SimuladorIroniaLaya />
            </Painel>
          </TabsContent>

          <TabsContent value="comparacao" className="flex min-w-0 flex-col gap-4">
            {(() => {
              const laudo = comparacao.ok ? comparacao.dado.laudo : null;
              return (
                <>
                  <Painel
                    titulo="Laudo · BERTimbau × Laya"
                    legenda="Os modelos leram exatamente os mesmos exemplos em cada conjunto. A comparação é do Laya treinado contra o BERTimbau: diferença de F1-macro com intervalo de confiança de 95% por bootstrap e McNemar exato. Intervalo que contém o zero não demonstra vantagem de nenhum dos dois. O corpus de emoção é tradução automática e o de ironia foi rotulado por hashtag e procedência; nenhum conjunto é conversa de cliente real."
                    semPadding
                    acessorio={
                      laudo ? (
                        <a
                          href={URL_RELATORIO_COMPARACAO}
                          download="comparacao-modelos.md"
                          className="inline-flex items-center gap-1.5 text-xs text-foreground underline underline-offset-4"
                        >
                          <Download aria-hidden className="size-3.5" />
                          Baixar relatório (.md)
                        </a>
                      ) : null
                    }
                    erro={
                      comparacao.ok ? undefined : (
                        <EstadoVazio
                          titulo="O laudo de comparação não carregou"
                          explicacao={comparacao.erro}
                          endpoint="GET /modelo/comparacao"
                        />
                      )
                    }
                    vazio={
                      comparacao.ok && !laudo ? (
                        <EstadoVazio
                          titulo="O laudo de comparação ainda não foi gerado"
                          explicacao="GET /modelo/comparacao respondeu laudo: null. Acurácia, verdadeiros e falsos por classe e tempo só existem depois que os dois modelos leem o mesmo conjunto de teste — e isso acontece no notebook, não nesta tela. Nenhum número é mostrado enquanto o arquivo não existir."
                          etapa="notebooks/07_treino_laya.ipynb, célula 12; depois copie comparacao_modelos.json para a pasta modelos/ da API"
                        />
                      ) : undefined
                    }
                  >
                    {laudo ? <LaudoDaComparacao laudo={laudo} /> : null}
                  </Painel>

                  {laudo?.latencia?.medidas.length ? (
                    <Painel
                      titulo="Tempo de resposta"
                      legenda="A latência foi medida em CPU, fora da GPU do treino, com os executores disponíveis no notebook. O número vale para aquela máquina: serve para comparar um modelo com o outro, não para prever o tempo deste servidor."
                      semPadding
                    >
                      <TempoDeResposta laudo={laudo} />
                    </Painel>
                  ) : null}

                  <Painel
                    titulo="Uma fala, os dois modelos"
                    legenda="Leitura isolada das cabeças carregadas neste servidor. Não executa satisfação nem fusor, não grava e não altera a nota de nenhum atendimento."
                    semPadding
                  >
                    <ComparacaoAoVivo />
                  </Painel>
                </>
              );
            })()}
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}
