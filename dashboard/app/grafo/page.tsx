/**
 * =============================================================================
 * GRAFO DA MEMORIA — o que o sistema guarda, como um graph view do Obsidian
 *
 * Ate a Task 8 nao ha canvas: os nos aparecem em lista, e essa lista NAO e
 * provisoria -- ela vira o fallback acessivel permanente, porque canvas e um
 * bitmap opaco para leitor de tela.
 * =============================================================================
 */

import { obterGrafo } from "@/lib/api";
import { lerPeriodo } from "@/lib/periodo";
import { CabecalhoPagina } from "@/components/shell/CabecalhoPagina";
import { EstadoVazio } from "@/components/EstadoVazio";
import { Painel } from "@/components/Painel";
import { ListaDeNos } from "@/components/grafo/ListaDeNos";

export const dynamic = "force-dynamic";

export default async function PaginaGrafo(props: PageProps<"/grafo">) {
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
          titulo={`${grafo.dado.nos.length} nós`}
          legenda="Lista dos nós do grafo — conversas, categorias, canais, desfechos, termos, emojis, features, fontes e importações. É o mesmo dado que o canvas (Task 8) vai desenhar, e continua sendo o caminho por teclado e leitor de tela depois que ele existir."
          semPadding
          rodape={
            grafo.dado.meta.truncado
              ? `Mostrando ${grafo.dado.meta.termos_exibidos} de ${grafo.dado.meta.termos_totais} termos — o resto ficou de fora para o grafo continuar legível.`
              : undefined
          }
        >
          <div className="px-2 py-2">
            <ListaDeNos nos={grafo.dado.nos} />
          </div>
        </Painel>
      </div>
    </>
  );
}
