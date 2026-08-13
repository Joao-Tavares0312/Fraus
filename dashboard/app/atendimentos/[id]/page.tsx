import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { obterAtribuicao, obterConversa } from "@/lib/api";
import {
  falasDecisivas,
  latenciaMediana,
  latenciasAnotadas,
  marcasDaAtribuicao,
  type MarcaAtribuicao,
} from "@/lib/derivacoes";
import {
  formatarDataHora,
  formatarSegundos,
  ROTULO_SEM_SINAL,
} from "@/lib/formato";
import { lerPeriodo, paraQuery } from "@/lib/periodo";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { CabecalhoPagina } from "@/components/shell/CabecalhoPagina";
import { EstadoVazio } from "@/components/EstadoVazio";
import { EtiquetaCategoria } from "@/components/EtiquetaCategoria";
import { Painel } from "@/components/Painel";
import { PainelContribuicoes } from "@/components/PainelContribuicoes";
import { Transcricao } from "@/components/Transcricao";

export const dynamic = "force-dynamic";

export default async function PaginaDoAtendimento(
  props: PageProps<"/atendimentos/[id]">,
) {
  const { id } = await props.params;
  const parametros = await props.searchParams;
  // O periodo nao filtra ESTA tela (ela e um atendimento so), mas viaja no
  // link de volta para nao perder o recorte de quem veio da tabela.
  const sufixo = paraQuery(lerPeriodo(parametros));

  // As duas leituras sao independentes de proposito: se a atribuicao falhar,
  // so os paineis dela mostram falha -- a transcricao continua na tela.
  const [resultado, resultadoAtribuicao] = await Promise.all([
    obterConversa(id),
    obterAtribuicao(id),
  ]);

  if (!resultado.ok) {
    if (/404/.test(resultado.erro)) notFound();
    return (
      <main className="flex min-w-0 flex-1 flex-col gap-4 px-4 py-10 sm:px-6">
        <h1 className="text-lg font-semibold text-foreground">
          Não foi possível abrir o atendimento
        </h1>
        <EstadoVazio
          titulo={id}
          explicacao={resultado.erro}
          endpoint="GET /conversas/{id}"
        />
        <p>
          <Link
            href={`/atendimentos${sufixo}`}
            className="text-sm text-primary underline underline-offset-4"
          >
            ← Todos os atendimentos
          </Link>
        </p>
      </main>
    );
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
  const decisivas = falasDecisivas(marcas);

  return (
    <>
      <CabecalhoPagina
        titulo={`Atendimento ${conversa.id}`}
        subtitulo="Nota, categoria e a transcrição inteira, com o tempo de espera anotado em cada resposta e os trechos marcados pela probabilidade que o classificador deu a cada fala."
        acoes={
          <Link
            href={`/atendimentos${sufixo}`}
            className="inline-flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm text-muted-foreground outline-none transition-colors duration-150 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
          >
            <ArrowLeft aria-hidden className="size-4" />
            Todos os atendimentos
          </Link>
        }
      />

      <main className="flex min-w-0 flex-1 flex-col gap-4 px-4 py-4 sm:px-6">
        <section
          aria-label="Resumo do atendimento"
          className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4"
        >
          <Card size="sm" className="quebra-evitar gap-2 px-4 py-3.5">
            <div className="flex items-start justify-between gap-2">
              <h2 className="text-xs font-medium text-muted-foreground">
                Nota inferida
              </h2>
              <Badge
                variant="outline"
                className="rounded-sm text-[0.625rem] text-muted-foreground"
              >
                estimativa
              </Badge>
            </div>
            {conversa.nota === null ? (
              <>
                <p className="text-lg leading-none font-medium text-muted-foreground">
                  {ROTULO_SEM_SINAL}
                </p>
                <p className="text-xs leading-relaxed text-muted-foreground">
                  O cliente não falou neste atendimento. Sem fala, não há sinal
                  de texto nem de emoji — e ausência de dado não é
                  insatisfação.
                </p>
              </>
            ) : (
              <p className="flex items-baseline gap-1.5">
                <span className="num estimado text-[1.75rem] leading-none font-semibold tracking-tight text-foreground">
                  {conversa.nota}
                </span>
                <span className="text-sm text-muted-foreground">/ 10</span>
              </p>
            )}
          </Card>

          <Celula rotulo="Categoria">
            <EtiquetaCategoria
              categoria={conversa.categoria}
              className="text-base"
            />
          </Celula>

          <Celula rotulo="Latência mediana" qualificacao="observado">
            <span className="num text-base text-foreground">
              {mediana === null ? "—" : formatarSegundos(mediana)}
            </span>
            <span className="block text-xs text-muted-foreground">
              sobre {respostas} {respostas === 1 ? "resposta" : "respostas"}
            </span>
          </Celula>

          <Celula rotulo="Atendimento" qualificacao="observado">
            <span className="text-sm text-foreground">{conversa.canal}</span>
            <span className="num block text-xs text-muted-foreground">
              {formatarDataHora(conversa.iniciada_em)}
              {duracao !== null ? ` · ${formatarSegundos(duracao)}` : ""}
            </span>
            <span className="block text-xs text-muted-foreground">
              {conversa.escalou_para_humano
                ? "escalou para humano"
                : "contido no bot"}
            </span>
          </Celula>
        </section>

        <Painel
          titulo="Transcrição"
          legenda="Fala do cliente sobre a superfície elevada e em âmbar — é o que foi dito. Resposta do bot ou do atendente recuada, em cinza. A espera do cliente aparece embaixo de cada resposta, e o realce de um trecho é proporcional à probabilidade real que o classificador deu àquela fala."
          semPadding
        >
          <Transcricao conversa={conversa} marcas={marcas} />
        </Painel>

        <div className="grid min-w-0 grid-cols-1 gap-4 xl:grid-cols-2">
          <Painel
            titulo="Falas que inclinaram a nota"
            legenda="Probabilidade por mensagem do classificador de texto, vinda de GET /conversas/{id}/atribuicao. O ranking usa o saldo P(satisfeito) − P(insatisfeito): uma fala 90% neutra não explica nota nenhuma, mesmo sendo a predição mais confiante da conversa."
            semPadding
          >
            {atribuicao === null ? (
              <EstadoVazio
                className="m-5"
                titulo="Atribuição indisponível"
                explicacao={`A transcrição carregou, mas a atribuição por sentença não: ${resultadoAtribuicao.ok ? "" : resultadoAtribuicao.erro}. Sem ela, marcar uma frase como “a que derrubou a nota” seria invenção — então nada é marcado.`}
                endpoint="GET /conversas/{id}/atribuicao"
              />
            ) : marcas.size === 0 ? (
              <EstadoVazio
                className="m-5"
                titulo="O cliente não falou neste atendimento"
                explicacao="Sem fala do cliente não há o que atribuir: o classificador pontua mensagem de cliente, e pontuar a fala do bot seria número inventado."
              />
            ) : decisivas.length === 0 ? (
              <EstadoVazio
                className="m-5"
                titulo="Nenhuma fala inclinou a nota de forma clara"
                explicacao="Todas as mensagens do cliente ficaram com P(satisfeito) e P(insatisfeito) próximas demais. A transcrição mostra a probabilidade de cada uma; apontar uma delas como causa seria ler ruído como evidência."
              />
            ) : (
              <ul className="divide-y divide-border">
                {decisivas.map((marca) => (
                  <li
                    key={marca.indice}
                    className="flex flex-col gap-1.5 px-5 py-3"
                  >
                    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                      <span
                        aria-hidden
                        className="size-2 shrink-0 -translate-y-px rounded-full"
                        style={{
                          background:
                            marca.sentido === "puxou_para_baixo"
                              ? "var(--detrator)"
                              : "var(--promotor)",
                        }}
                      />
                      <span className="text-sm font-medium text-foreground">
                        {marca.sentido === "puxou_para_baixo"
                          ? "Puxou para baixo"
                          : "Puxou para cima"}
                      </span>
                      <span className="num text-xs text-muted-foreground">
                        {marca.saldo > 0 ? "+" : "−"}
                        {Math.abs(marca.saldo).toFixed(2)} de saldo
                      </span>
                      <span className="num ml-auto text-xs text-muted-foreground">
                        mensagem {marca.indice + 1}
                      </span>
                    </div>
                    <p className="max-w-[70ch] text-sm leading-relaxed text-dito-texto">
                      “{atribuicao.mensagens[marca.indice]?.texto}”
                    </p>
                    <p className="num text-xs text-muted-foreground">
                      insatisfeito {Math.round(marca.probInsatisfeito * 100)}% ·
                      neutro {Math.round(marca.probNeutro * 100)}% · satisfeito{" "}
                      {Math.round(marca.probSatisfeito * 100)}%
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </Painel>

          <Painel
            titulo="Contribuições das features neste atendimento"
            legenda="Com sinal, ordenadas por magnitude. Isto é `contribuicoes` — o que pesou NESTE atendimento —, não `importancias`, que é o peso global do modelo e vive na tela Modelo."
            semPadding
          >
            {atribuicao === null ? (
              <EstadoVazio
                className="m-5"
                titulo="Contribuições indisponíveis"
                explicacao={`A chamada de atribuição falhou: ${resultadoAtribuicao.ok ? "" : resultadoAtribuicao.erro}.`}
                endpoint="GET /conversas/{id}/atribuicao"
              />
            ) : (
              <PainelContribuicoes
                atribuicao={atribuicao}
                totalDeFeatures={Object.keys(atribuicao.importancias).length}
              />
            )}
          </Painel>
        </div>
      </main>
    </>
  );
}

function Celula({
  rotulo,
  qualificacao,
  children,
}: {
  rotulo: string;
  qualificacao?: string;
  children: React.ReactNode;
}) {
  return (
    <Card size="sm" className="quebra-evitar gap-2 px-4 py-3.5">
      <div className="flex items-start justify-between gap-2">
        <h2 className="text-xs font-medium text-muted-foreground">{rotulo}</h2>
        {qualificacao ? (
          <Badge
            variant="outline"
            className="rounded-sm text-[0.625rem] text-muted-foreground"
          >
            {qualificacao}
          </Badge>
        ) : null}
      </div>
      <div>{children}</div>
    </Card>
  );
}
