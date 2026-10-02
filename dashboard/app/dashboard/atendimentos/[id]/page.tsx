import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import {
  obterAtribuicao,
  obterConfiguracoes,
  obterConversa,
} from "@/lib/api";
import {
  falasDecisivas,
  latenciaMediana,
  latenciasAnotadas,
  limiaresDe,
  marcasDaAtribuicao,
  type MarcaAtribuicao,
} from "@/lib/derivacoes";
import { EXPLICACAO_SEM_SINAL } from "@/lib/formato";
import { lerPeriodo, paraQuery } from "@/lib/periodo";
import { CabecalhoPagina } from "@/components/shell/CabecalhoPagina";
import { EstadoVazio } from "@/components/EstadoVazio";
import { ResumoDoAtendimento } from "@/components/atendimentos/ResumoDoAtendimento";
import { Painel } from "@/components/Painel";
import { PainelContribuicoes } from "@/components/PainelContribuicoes";
import { Transcricao } from "@/components/Transcricao";

export const dynamic = "force-dynamic";

export default async function PaginaDoAtendimento(
  props: PageProps<"/dashboard/atendimentos/[id]">,
) {
  const { id } = await props.params;
  const parametros = await props.searchParams;
  // O periodo nao filtra ESTA tela (ela e um atendimento so), mas viaja no
  // link de volta para nao perder o recorte de quem veio da tabela.
  const sufixo = paraQuery(lerPeriodo(parametros));

  // As duas leituras sao independentes de proposito: se a atribuicao falhar,
  // so os paineis dela mostram falha -- a transcricao continua na tela.
  const [resultado, resultadoAtribuicao, configuracoes] = await Promise.all([
    obterConversa(id),
    obterAtribuicao(id),
    obterConfiguracoes(),
  ]);

  const limiares = limiaresDe(
    configuracoes.ok ? configuracoes.dado.vigente.limiares_latencia_s : null,
  );

  if (!resultado.ok) {
    // Pelo STATUS, nunca pelo texto: a frase do erro carrega a rota, a rota
    // carrega o id, e `/404/.test(...)` fazia um 500 em `/conversas/c-1404`
    // abrir a pagina de "nao encontrado" -- afirmando que o atendimento nao
    // existe quando quem falhou foi o servidor.
    if (resultado.status === 404) notFound();
    // COM flex-1: mesmo padrao de app/dashboard/configuracoes/page.tsx e
    // app/dashboard/grafo/page.tsx -- EstadoVazio so centraliza verticalmente
    // se o pai estiver esticado. Aqui o sintoma era mais fraco (tem titulo e
    // link ALEM do vazio, entao sem flex-1 ele so ficava desalinhado, nao
    // colapsado), mas o defeito e o mesmo e o conserto e de graca: aplicado
    // por consistencia com os outros dois ramos de erro da tela.
    return (
      <div className="flex min-w-0 flex-1 flex-col gap-4 px-4 py-10 sm:px-6">
        <h1 className="titulo-instrumento text-lg text-foreground">
          Não foi possível abrir o atendimento
        </h1>
        <EstadoVazio
          titulo={id}
          explicacao={resultado.erro}
          endpoint="GET /conversas/{id}"
        />
        <p>
          <Link
            href={`/dashboard/atendimentos${sufixo}`}
            className="text-sm text-primary underline underline-offset-4"
          >
            ← Todos os atendimentos
          </Link>
        </p>
      </div>
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
            href={`/dashboard/atendimentos${sufixo}`}
            className="rotulo-instrumento inline-flex min-h-9 items-center gap-1.5 px-2 outline-none transition-colors duration-150 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
          >
            <ArrowLeft aria-hidden className="size-4" />
            Todos os atendimentos
          </Link>
        }
      />

      {/* SEM flex-1: ver o comentario identico em app/dashboard/page.tsx. */}
      <div className="flex min-w-0 flex-col gap-4 px-4 py-4 sm:px-6">
        <ResumoDoAtendimento
          conversa={conversa}
          mediana={mediana}
          respostas={respostas}
          duracao={duracao}
        />

        <Painel
          titulo="Transcrição"
          legenda="Fala do cliente em cartão com filete âmbar — é o que foi dito. Resposta do bot ou do atendente recuada, em contorno tracejado. A espera do cliente é um intervalo tracejado antes de cada resposta, com o comprimento proporcional ao tempo (a régua é o limiar de degradação vigente) e o tempo em display; o realce de um trecho é proporcional à probabilidade real que o classificador deu àquela fala."
          semPadding
        >
          <Transcricao
            conversa={conversa}
            marcas={marcas}
            limiares={limiares}
          />
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
            ) : conversa.motivo_sem_sinal === "so_cortesia" ? (
              <EstadoVazio
                className="m-5"
                titulo="Só cortesia: nenhuma fala explica nota"
                explicacao={`${EXPLICACAO_SEM_SINAL.so_cortesia} Sem nota, apontar uma delas como “a que puxou a nota” seria inventar a causa de um número que não existe.`}
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
              <ul className="divide-y divide-compasso">
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
                    {/* A fala e o DITO: filete ambar, como na transcricao. */}
                    <p className="max-w-[70ch] border-l-2 border-dito pl-3 text-sm leading-relaxed text-dito-texto">
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
                contribuicoes={atribuicao.contribuicoes}
                sinaisForaDoScore={atribuicao.sinais_fora_do_score}
                totalDeFeatures={Object.keys(atribuicao.importancias).length}
                motivoSemSinal={conversa.motivo_sem_sinal}
              />
            )}
          </Painel>
        </div>
      </div>
    </>
  );
}
