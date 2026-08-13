import Link from "next/link";
import { notFound } from "next/navigation";
import { obterConversa } from "@/lib/api";
import {
  evidenciasDaConversa,
  latenciaMediana,
  latenciasAnotadas,
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
  const resultado = await obterConversa(id);

  if (!resultado.ok) {
    if (/404/.test(resultado.erro)) notFound();
    return <Falha id={id} erro={resultado.erro} />;
  }

  const conversa = resultado.dado;
  const evidencias = evidenciasDaConversa(conversa);
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
      nomeCsv={`dolos-atendimento-${conversa.id}`}
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
          <Transcricao conversa={conversa} />
        </Painel>

        <Painel
          titulo="O que puxou a nota"
          legenda="Evidência observável na própria transcrição — é isto que transforma “nota ruim” em “oportunidade de melhoria”."
        >
          {evidencias.length === 0 ? (
            <EstadoVazio
              titulo="Nenhuma evidência observável nesta transcrição"
              explicacao="Não há emoji com polaridade relevante nem espera acima de 30 s. Isso não significa que a nota não tenha causa: a parcela de texto da atribuição depende da probabilidade por mensagem do classificador, que a API não expõe."
              endpoint="GET /conversas/{id}/atribuicao"
            />
          ) : (
            <ul className="divide-y divide-[var(--filete)]">
              {evidencias.map((evidencia) => (
                <li
                  key={`${evidencia.indice}-${evidencia.tipo}-${evidencia.rotulo}`}
                  className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-5 py-3"
                >
                  <span
                    aria-hidden
                    className="h-[7px] w-[7px] shrink-0 translate-y-[-1px] rounded-full"
                    style={{
                      background:
                        evidencia.sentido === "puxou_para_baixo"
                          ? "var(--detrator)"
                          : "var(--promotor)",
                    }}
                  />
                  <span className="text-[0.875rem] font-medium text-[var(--tinta)]">
                    {evidencia.rotulo}
                  </span>
                  <span className="text-[0.8125rem] text-[var(--tinta-2)]">
                    {evidencia.detalhe}
                  </span>
                  <span className="ml-auto text-[0.75rem] tabular-nums text-[var(--tinta-3)]">
                    mensagem {evidencia.indice + 1}
                  </span>
                </li>
              ))}
            </ul>
          )}

          <div className="border-t border-[var(--filete)]">
            <EstadoVazio
              titulo="Atribuição do sinal de texto: indisponível"
              explicacao="O classificador BERTimbau pontua cada mensagem individualmente, mas a API só devolve o score fundido do atendimento inteiro. Sem essa quebra por mensagem, marcar uma frase específica como “a que derrubou a nota” seria invenção — então a marcação acima usa apenas emoji e tempo, que são verificáveis na transcrição."
              endpoint="GET /conversas/{id}/atribuicao"
            />
          </div>
        </Painel>
      </main>
    </QuadroRelatorio>
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
