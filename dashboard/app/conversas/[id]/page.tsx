import Link from "next/link";
import { notFound } from "next/navigation";
import { obterAtribuicao, obterConversa, type Atribuicao } from "@/lib/api";
import {
  falasDecisivas,
  latenciaMediana,
  latenciasAnotadas,
  marcasDaAtribuicao,
  pesoPorSinal,
  ROTULO_SINAL,
  type MarcaAtribuicao,
} from "@/lib/derivacoes";
import {
  formatarDataHora,
  formatarSegundos,
  ROTULO_SEM_SINAL,
} from "@/lib/formato";
import { EstadoVazio } from "@/components/EstadoVazio";
import { EtiquetaCategoria } from "@/components/EtiquetaCategoria";
import { Painel } from "@/components/Painel";
import { QuadroRelatorio } from "@/components/QuadroRelatorio";
import { Transcricao } from "@/components/Transcricao";

export const dynamic = "force-dynamic";

export default async function PaginaDoAtendimento(
  props: PageProps<"/conversas/[id]">,
) {
  const { id } = await props.params;
  // As duas leituras sao independentes de proposito: se a atribuicao falhar,
  // so o painel dela mostra falha -- a transcricao continua na tela.
  const [resultado, resultadoAtribuicao] = await Promise.all([
    obterConversa(id),
    obterAtribuicao(id),
  ]);

  if (!resultado.ok) {
    if (/404/.test(resultado.erro)) notFound();
    return <Falha id={id} erro={resultado.erro} />;
  }

  const conversa = resultado.dado;
  const atribuicao = resultadoAtribuicao.ok ? resultadoAtribuicao.dado : null;
  const marcas = atribuicao
    ? marcasDaAtribuicao(atribuicao.mensagens)
    : new Map<number, MarcaAtribuicao>();
  const mediana = latenciaMediana(conversa.mensagens);
  const respostas = latenciasAnotadas(conversa.mensagens).length;
  const duracao = conversa.encerrada_em
    ? (new Date(conversa.encerrada_em).getTime() -
        new Date(conversa.iniciada_em).getTime()) /
      1000
    : null;

  return (
    <QuadroRelatorio
      titulo={`Atendimento ${conversa.id}`}
      subtitulo="Nota, categoria e a transcrição inteira, com o tempo de espera anotado em cada resposta e os trechos que puxaram a nota marcados."
      nomeCsv={`fraus-atendimento-${conversa.id}`}
    >
      <main className="mx-auto flex w-full max-w-[1000px] flex-1 flex-col gap-6 px-6 py-6">
        <p className="sem-impressao">
          <Link
            href="/"
            className="text-[0.8125rem] text-[var(--tinta-2)] underline decoration-[var(--filete)] underline-offset-[3px] transition-colors duration-150 hover:text-[var(--tinta)] hover:decoration-[var(--foco)]"
          >
            ← Todos os atendimentos
          </Link>
        </p>

        <section className="quebra-evitar grid grid-cols-1 divide-y divide-[var(--filete)] border border-[var(--filete)] bg-[var(--superficie)] sm:grid-cols-2 sm:divide-y-0 lg:grid-cols-4">
          <div className="flex flex-col gap-2 px-5 py-4 sm:border-b sm:border-[var(--filete)] lg:border-b-0 lg:border-r">
            <div className="flex items-baseline justify-between gap-2">
              <h2 className="text-[0.8125rem] font-medium text-[var(--tinta-2)]">
                Nota inferida
              </h2>
              <span className="rounded-[2px] border border-[var(--filete)] px-1.5 py-px text-[0.625rem] font-medium text-[var(--tinta-3)]">
                estimativa
              </span>
            </div>
            {conversa.nota === null ? (
              <>
                <p className="text-[1.5rem] leading-none font-semibold text-[var(--tinta-3)]">
                  {ROTULO_SEM_SINAL}
                </p>
                <p className="text-[0.75rem] leading-[1.45] text-[var(--tinta-3)]">
                  O cliente não falou neste atendimento. Sem fala, não há sinal
                  de texto nem de emoji — e ausência de dado não é
                  insatisfação.
                </p>
              </>
            ) : (
              <p className="flex items-baseline gap-1.5">
                <span className="estimado text-[2.125rem] leading-none font-semibold tracking-[-0.02em] text-[var(--tinta)]">
                  {conversa.nota}
                </span>
                <span className="text-[0.875rem] text-[var(--tinta-3)]">/ 10</span>
              </p>
            )}
          </div>

          <Celula rotulo="Categoria">
            <EtiquetaCategoria
              categoria={conversa.categoria}
              className="text-[1rem]"
            />
          </Celula>

          <Celula rotulo="Latência mediana">
            <span className="font-mono text-[1rem] tabular-nums text-[var(--tinta)]">
              {mediana === null ? "—" : formatarSegundos(mediana)}
            </span>
            <span className="block text-[0.75rem] text-[var(--tinta-3)]">
              sobre {respostas} {respostas === 1 ? "resposta" : "respostas"}
            </span>
          </Celula>

          <Celula rotulo="Atendimento">
            <span className="text-[0.875rem] text-[var(--tinta)]">
              {conversa.canal}
            </span>
            <span className="block text-[0.75rem] text-[var(--tinta-3)]">
              {formatarDataHora(conversa.iniciada_em)}
              {duracao !== null ? ` · ${formatarSegundos(duracao)}` : ""}
            </span>
            <span className="block text-[0.75rem] text-[var(--tinta-3)]">
              {conversa.escalou_para_humano
                ? "escalou para humano"
                : "contido no bot"}
            </span>
          </Celula>
        </section>

        <Painel
          titulo="Transcrição"
          legenda="Falas do cliente sobre a segunda camada de superfície; respostas do bot e do atendente sobre a superfície do painel. A espera do cliente aparece embaixo de cada resposta."
        >
          <Transcricao conversa={conversa} marcas={marcas} />
        </Painel>

        <Painel
          titulo="O que puxou a nota"
          legenda="Probabilidade por mensagem do classificador de texto, vinda de GET /conversas/{id}/atribuicao — é isto que transforma “nota ruim” em “oportunidade de melhoria”."
        >
          {atribuicao === null ? (
            <EstadoVazio
              titulo="Atribuição indisponível"
              explicacao={`A transcrição carregou, mas a atribuição por sentença não: ${resultadoAtribuicao.ok ? "" : resultadoAtribuicao.erro}. Sem ela, marcar uma frase como “a que derrubou a nota” seria invenção — então nada é marcado.`}
              endpoint="GET /conversas/{id}/atribuicao"
            />
          ) : (
            <PainelAtribuicao atribuicao={atribuicao} marcas={marcas} />
          )}
        </Painel>

      </main>
    </QuadroRelatorio>
  );
}

/**
 * As falas do cliente ordenadas pela forca com que inclinaram a nota, mais o
 * peso que o fusor deu a cada um dos tres sinais.
 *
 * O ranking usa o SALDO (P(satisfeito) - P(insatisfeito)) porque e ele que diz
 * a direcao: uma fala com 90% de neutro nao explica nota nenhuma, mesmo sendo
 * a predicao mais confiante da conversa.
 */
function PainelAtribuicao({
  atribuicao,
  marcas,
}: {
  atribuicao: Atribuicao;
  marcas: Map<number, MarcaAtribuicao>;
}) {
  const decisivas = falasDecisivas(marcas);
  const pesos = pesoPorSinal(atribuicao.importancias);
  const comFala = marcas.size > 0;

  return (
    <>
      {!comFala ? (
        <EstadoVazio
          titulo="O cliente não falou neste atendimento"
          explicacao="Sem fala do cliente não há o que atribuir: o classificador de texto pontua mensagem de cliente, e pontuar a fala do bot seria número inventado. Ausência de dado não é insatisfação."
        />
      ) : decisivas.length === 0 ? (
        <EstadoVazio
          titulo="Nenhuma fala inclinou a nota de forma clara"
          explicacao="Todas as mensagens do cliente ficaram com P(satisfeito) e P(insatisfeito) próximas demais. A transcrição mostra a probabilidade de cada uma; apontar uma delas como causa seria ler ruído como evidência."
        />
      ) : (
        <ul className="divide-y divide-[var(--filete)]">
          {decisivas.map((marca) => (
            <li
              key={marca.indice}
              className="flex flex-col gap-1.5 px-5 py-3"
            >
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <span
                  aria-hidden
                  className="h-[7px] w-[7px] shrink-0 translate-y-[-1px] rounded-full"
                  style={{
                    background:
                      marca.sentido === "puxou_para_baixo"
                        ? "var(--detrator)"
                        : "var(--promotor)",
                  }}
                />
                <span className="text-[0.875rem] font-medium text-[var(--tinta)]">
                  {marca.sentido === "puxou_para_baixo"
                    ? "Puxou para baixo"
                    : "Puxou para cima"}
                </span>
                <span className="font-mono text-[0.75rem] tabular-nums text-[var(--tinta-2)]">
                  {marca.saldo > 0 ? "+" : "−"}
                  {Math.abs(marca.saldo).toFixed(2)} de saldo
                </span>
                <span className="ml-auto text-[0.75rem] tabular-nums text-[var(--tinta-3)]">
                  mensagem {marca.indice + 1}
                </span>
              </div>
              <p className="max-w-[70ch] text-[0.8125rem] leading-[1.55] text-[var(--tinta-2)]">
                “{atribuicao.mensagens[marca.indice]?.texto}”
              </p>
              <p className="text-[0.75rem] tabular-nums text-[var(--tinta-3)]">
                insatisfeito {Math.round(marca.probInsatisfeito * 100)}% ·
                neutro {Math.round(marca.probNeutro * 100)}% · satisfeito{" "}
                {Math.round(marca.probSatisfeito * 100)}%
              </p>
            </li>
          ))}
        </ul>
      )}

      <div className="border-t border-[var(--filete)] px-5 py-4">
        <h3 className="text-[0.8125rem] font-medium text-[var(--tinta-2)]">
          Peso de cada sinal no fusor
        </h3>
        <p className="mt-1 max-w-[70ch] text-[0.75rem] leading-[1.5] text-[var(--tinta-3)]">
          Coeficiente absoluto médio da regressão logística, agregado por sinal
          sobre as {Object.keys(atribuicao.importancias).length} features. Vale
          para o modelo inteiro, não para este atendimento.
        </p>
        <ul className="mt-3 flex flex-col gap-2">
          {pesos.map((peso) => (
            <li key={peso.sinal} className="flex items-center gap-3">
              <span className="w-[3.5rem] shrink-0 text-[0.75rem] text-[var(--tinta-2)]">
                {ROTULO_SINAL[peso.sinal]}
              </span>
              <span className="h-[6px] flex-1 overflow-hidden rounded-[2px] bg-[var(--filete)]">
                <span
                  className="block h-full bg-[var(--tinta-2)]"
                  style={{ width: `${peso.fracao * 100}%` }}
                />
              </span>
              <span className="w-[3rem] shrink-0 text-right font-mono text-[0.75rem] tabular-nums text-[var(--tinta-2)]">
                {Math.round(peso.fracao * 100)}%
              </span>
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}

function Celula({
  rotulo,
  children,
}: {
  rotulo: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2 px-5 py-4 sm:border-b sm:border-[var(--filete)] lg:border-b-0 lg:border-r lg:last:border-r-0">
      <h2 className="text-[0.8125rem] font-medium text-[var(--tinta-2)]">
        {rotulo}
      </h2>
      <div>{children}</div>
    </div>
  );
}

function Falha({ id, erro }: { id: string; erro: string }) {
  return (
    <main className="mx-auto flex w-full max-w-[720px] flex-1 flex-col gap-4 px-6 py-16">
      <h1 className="text-[1.25rem] font-semibold text-[var(--tinta)]">
        Não foi possível abrir o atendimento
      </h1>
      <p className="text-[0.875rem] text-[var(--tinta-2)]">
        <span className="font-mono">{id}</span> — {erro}
      </p>
      <p>
        <Link
          href="/"
          className="text-[0.875rem] text-[var(--tinta-2)] underline underline-offset-[3px] hover:text-[var(--tinta)]"
        >
          ← Todos os atendimentos
        </Link>
      </p>
    </main>
  );
}
