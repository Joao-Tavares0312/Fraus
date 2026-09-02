/**
 * =============================================================================
 * GRAFO DA MEMORIA — o que o sistema guarda, como um graph view do Obsidian
 *
 * Esta pagina e SERVIDOR: ela busca, trata erro e vazio, e entrega o grafo
 * pronto. O canvas e cliente (`GrafoDaMemoria`) porque `dynamic` com
 * `ssr: false` so vale em Client Component -- e o force-graph precisa de
 * `window` para existir.
 *
 * A lista de nos nao sumiu com a chegada do canvas: ela virou o fallback
 * acessivel permanente dentro do `GrafoDaMemoria`, porque canvas e um bitmap
 * opaco para leitor de tela.
 * =============================================================================
 */

import { obterGrafo } from "@/lib/api";
import { lerPeriodo } from "@/lib/periodo";
import { CabecalhoPagina } from "@/components/shell/CabecalhoPagina";
import { EstadoVazio } from "@/components/EstadoVazio";
import { Painel } from "@/components/Painel";
import { GrafoDaMemoria } from "@/components/grafo/GrafoDaMemoria";

export const dynamic = "force-dynamic";

export default async function PaginaGrafo(props: PageProps<"/dashboard/grafo">) {
  const parametros = await props.searchParams;
  const periodo = lerPeriodo(parametros);
  const grafo = await obterGrafo(periodo.de, periodo.ate);

  if (!grafo.ok) {
    return (
      <>
        <CabecalhoPagina titulo="Grafo da memória" periodo={periodo} />
        <div className="flex min-w-0 flex-1 flex-col gap-4 px-4 py-4 sm:px-6">
          <EstadoVazio
            titulo="O grafo não carregou"
            explicacao={grafo.erro}
            endpoint="GET /grafo"
          />
        </div>
      </>
    );
  }

  if (grafo.dado.nos.length === 0) {
    return (
      <>
        <CabecalhoPagina titulo="Grafo da memória" periodo={periodo} />
        <div className="flex min-w-0 flex-1 flex-col gap-4 px-4 py-4 sm:px-6">
          <EstadoVazio
            titulo="Nenhuma conversa analisada ainda"
            explicacao="O grafo mostra o que o sistema guarda sobre os atendimentos — importe um arquivo em Analisar para ele ter o que exibir."
            etapa="importar um arquivo em Analisar"
          />
        </div>
      </>
    );
  }

  return (
    <>
      <CabecalhoPagina titulo="Grafo da memória" periodo={periodo} />
      <div className="flex min-w-0 flex-1 flex-col gap-4 px-4 py-4 sm:px-6">
        <Painel
          titulo={`${grafo.dado.nos.length} nós, ${grafo.dado.arestas.length} arestas`}
          legenda="Conversas, categorias, canais, desfechos, termos, emojis, features, fontes e importações. Âmbar é o que foi dito; azul é o que foi medido. O tamanho do ponto é o número de conexões — nunca a nota, porque então um atendimento sem sinal encolheria até sumir. Conversa sem sinal aparece vazada: o marcador existe, ocupa a posição, e é oco. A lista equivalente ao canvas fica a um Tab de distância, e seleciona os mesmos nós."
          semPadding
          rodape={
            grafo.dado.meta.truncado
              ? `Mostrando ${grafo.dado.meta.termos_exibidos} de ${grafo.dado.meta.termos_totais} termos — o resto ficou de fora para o grafo continuar legível.`
              : undefined
          }
        >
          <GrafoDaMemoria grafo={grafo.dado} />
        </Painel>
      </div>
    </>
  );
}
