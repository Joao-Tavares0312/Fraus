import { carregarRecorte } from "@/lib/carregar";
import { formatarDataHora } from "@/lib/formato";
import { CabecalhoPagina } from "@/components/shell/CabecalhoPagina";
import { EstadoVazio } from "@/components/EstadoVazio";
import { Painel } from "@/components/Painel";
import {
  TabelaConversas,
  type LinhaConversa,
} from "@/components/TabelaConversas";
import type { ResumoConversa } from "@/lib/api";

export const dynamic = "force-dynamic";

function paraLinha(resumo: ResumoConversa): LinhaConversa {
  return {
    id: resumo.id,
    canal: resumo.canal,
    data: formatarDataHora(resumo.iniciada_em),
    ordenacao: resumo.iniciada_em,
    // A nota vem DERIVADA DO SERVIDOR em `/conversas`. Recalcular aqui ja
    // divergiu do Python nas fronteiras 6/7 e 8/9 (arredondamento bancario
    // contra meio-para-cima) e fazia a tabela exibir nota 7 ao lado da
    // categoria "Detrator". A fonte da verdade e uma so.
    nota: resumo.nota,
    categoria: resumo.categoria,
  };
}

export default async function PaginaAtendimentos(
  props: PageProps<"/atendimentos">,
) {
  const parametros = await props.searchParams;
  const { periodo, extensao, rotulo, sufixo, resumos, erro } =
    await carregarRecorte(parametros);

  return (
    <>
      <CabecalhoPagina
        titulo="Atendimentos"
        subtitulo="Cada linha é uma conversa inteira com a nota que o modelo inferiu. Abra uma para ver a transcrição, quanto o cliente esperou em cada resposta e o que pesou naquela nota."
        periodo={periodo}
        extensao={extensao}
      />

      <main className="flex min-w-0 flex-1 flex-col gap-4 px-4 py-4 sm:px-6">
        <Painel
          titulo={`Atendimentos de ${rotulo}`}
          legenda="Ordenar por nota manda “sem sinal” para o fim nos dois sentidos — atendimento sem fala do cliente não é o pior atendimento, é um atendimento sem medição. O CSV exporta exatamente o que o filtro deixou em tela, com “sem sinal” escrito por extenso."
          semPadding
        >
          {erro ? (
            <EstadoVazio
              className="m-5"
              titulo="Não foi possível listar os atendimentos"
              explicacao={erro}
              endpoint="GET /conversas"
            />
          ) : (
            <TabelaConversas
              linhas={resumos.map(paraLinha)}
              sufixoDeQuery={sufixo}
              nomeCsv="fraus-atendimentos"
              rotuloDoPeriodo={rotulo}
            />
          )}
        </Painel>
      </main>
    </>
  );
}
