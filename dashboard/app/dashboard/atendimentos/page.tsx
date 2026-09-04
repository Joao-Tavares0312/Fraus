import { carregarRecorte } from "@/lib/carregar";
import { formatarDataHora } from "@/lib/formato";
import { CabecalhoPagina } from "@/components/shell/CabecalhoPagina";
import { EstadoVazio } from "@/components/EstadoVazio";
import { Painel } from "@/components/Painel";
import { ResumoDaLista } from "@/components/atendimentos/ResumoDaLista";
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
    // A ficha operacional vem DERIVADA do servidor (`fraus.resumo`), a mesma
    // funcao que alimenta `/conversas/{id}`. A tela nao recalcula tempo de
    // resposta: duas definicoes de latencia -- uma para a lista, outra para o
    // detalhe -- fariam as duas telas discordarem sobre o mesmo atendimento.
    qtd_mensagens: resumo.qtd_mensagens,
    qtd_cliente: resumo.qtd_cliente,
    qtd_bot: resumo.qtd_bot,
    qtd_humano: resumo.qtd_humano,
    latencia_primeira_resposta_s: resumo.latencia_primeira_resposta_s,
    latencia_mediana_bot_s: resumo.latencia_mediana_bot_s,
    latencia_mediana_humano_s: resumo.latencia_mediana_humano_s,
    desfecho: resumo.desfecho,
  };
}

export default async function PaginaAtendimentos(
  props: PageProps<"/dashboard/atendimentos">,
) {
  const parametros = await props.searchParams;
  // So a listagem: esta tela nunca leu transcricao nenhuma -- a ficha
  // operacional de cada linha (contagem por autor, latencias, desfecho) ja
  // vem derivada pelo servidor em `GET /conversas`.
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

      {/* SEM flex-1: ver o comentario identico em app/dashboard/page.tsx --
          esticar ate a altura minima de `main` so cria vazio quando o
          conteudo real e mais baixo que a tela. */}
      <div className="flex min-w-0 flex-col gap-4 px-4 py-4 sm:px-6">
        <Painel
          titulo={`Atendimentos de ${rotulo}`}
          nivel="dominante"
          legenda="Ordenar por nota ou por espera manda a ausência para o fim nos dois sentidos — atendimento sem fala do cliente não é o pior atendimento, e conversa que nunca teve resposta humana não é a mais rápida da operação. Os tempos são medianas, não médias: espera de atendimento tem cauda longa, e um punhado de conversas esquecidas por horas puxaria a média para um valor que não descreve atendimento nenhum. “Encerrada” diz que a conversa fechou, não que o problema foi resolvido — resolução é julgamento, e nada no dado a sustenta. O CSV exporta o que o filtro deixou em tela, com “sem sinal” por extenso e a célula de tempo em branco quando a espera não existiu."
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
            <>
              <ResumoDaLista linhas={resumos} />
              <TabelaConversas
                linhas={resumos.map(paraLinha)}
                sufixoDeQuery={sufixo}
                nomeCsv="fraus-atendimentos"
                rotuloDoPeriodo={rotulo}
              />
            </>
          )}
        </Painel>
      </div>
    </>
  );
}
