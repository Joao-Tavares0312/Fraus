/**
 * =============================================================================
 * VISAO GERAL — superficie Operate
 *
 * A tela responde, nesta ordem: quanto os clientes estao satisfeitos no
 * periodo, que esse numero e ESTIMADO, quanto ele custa em tempo de resposta,
 * e quais atendimentos merecem ser abertos primeiro.
 *
 * A espinha nao sao os cartoes: e a sobreposicao NPS x latencia. Cartao
 * isolado esconde o trade-off que o produto existe para mostrar.
 * =============================================================================
 */

import {
  obterConfiguracoes,
  obterIndicadores,
  type ResumoConversa,
} from "@/lib/api";
import { carregarRecorte } from "@/lib/carregar";
import {
  distribuicaoDeNotas,
  indicadoresDoPeriodo,
  limiaresDe,
  lexicoPorClasse,
  pioresAtendimentos,
  serieDiaria,
  tempoMedianoDeResposta,
} from "@/lib/derivacoes";
import { formatarDataHora } from "@/lib/formato";
import { periodoEstaAtivo } from "@/lib/periodo";
import { CabecalhoPagina } from "@/components/shell/CabecalhoPagina";
import { DistribuicaoScores } from "@/components/DistribuicaoScores";
import { EstadoVazio } from "@/components/EstadoVazio";
import { FaixaIndicadores } from "@/components/FaixaIndicadores";
import { GraficoNpsLatencia } from "@/components/GraficoNpsLatencia";
import { NotaMetodologica } from "@/components/NotaMetodologica";
import { Painel } from "@/components/Painel";
import { PainelLexico } from "@/components/PainelLexico";
import { PioresAtendimentos } from "@/components/PioresAtendimentos";

export const dynamic = "force-dynamic";

const PIORES_NA_TELA = 6;

export default async function Pagina(props: PageProps<"/">) {
  const parametros = await props.searchParams;

  // As duas leituras sao independentes de proposito: se `/indicadores` cair, a
  // serie, a distribuicao e o lexico continuam de pe, e vice-versa.
  const [recorte, indicadoresDoServidor, configuracoes] = await Promise.all([
    carregarRecorte(parametros),
    obterIndicadores(),
    obterConfiguracoes(),
  ]);

  // As faixas de referencia da latencia sao as VIGENTES, nao constantes do
  // front -- e a tela de Configuracoes que as move.
  const limiares = limiaresDe(
    configuracoes.ok ? configuracoes.dado.vigente.limiares_latencia_s : null,
  );

  const { periodo, extensao, rotulo, sufixo, resumos, detalhes, erro } = recorte;

  /*
   * De onde vem cada indicador:
   *
   * SEM filtro, o numero e o do SERVIDOR (`/indicadores`) -- fonte da verdade,
   * calculada em Python pelas mesmas funcoes que gravam a categoria.
   *
   * COM filtro, `/indicadores` responde a outra pergunta (o banco inteiro), e
   * exibi-lo ao lado de uma tabela recortada seria mentira. Entao o recorte
   * agrega no cliente -- mas agregando a CATEGORIA que o servidor ja gravou,
   * nunca recalculando score ou nota (invariante 3).
   */
  const filtrado = periodoEstaAtivo(periodo);
  const doCliente = indicadoresDoPeriodo(resumos, detalhes);
  const indicadores =
    filtrado || !indicadoresDoServidor.ok
      ? doCliente
      : {
          ...doCliente,
          nps: indicadoresDoServidor.dado.nps,
          csat: indicadoresDoServidor.dado.csat,
          containment: indicadoresDoServidor.dado.total_conversas
            ? indicadoresDoServidor.dado.containment_rate
            : null,
          total: indicadoresDoServidor.dado.total_conversas,
          semSinal: indicadoresDoServidor.dado.sem_sinal,
        };

  const serie = serieDiaria(detalhes);
  const distribuicao = distribuicaoDeNotas(resumos);
  const classes = lexicoPorClasse(detalhes);
  const tempoMediano = tempoMedianoDeResposta(detalhes);
  const piores: ResumoConversa[] = pioresAtendimentos(resumos, PIORES_NA_TELA);

  return (
    <>
      <CabecalhoPagina
        titulo="Visão geral"
        subtitulo="O cliente escreve “ok, obrigado 🙂” e sai insatisfeito. Esta tela lê o que foi dito de verdade — texto, emoji e tempo de resposta — e estima a satisfação sem perguntar nada a ele."
        periodo={periodo}
        extensao={extensao}
      />

      <main className="flex min-w-0 flex-1 flex-col gap-4 px-4 py-4 sm:px-6">
        <FaixaIndicadores
          indicadores={indicadores}
          tempoMediano={tempoMediano}
          limiares={limiares}
          erro={erro}
          rotuloDoPeriodo={rotulo}
        />

        <Painel
          titulo="NPS inferido × latência mediana, por dia"
          legenda="As duas séries aparecem sobrepostas de propósito: otimizar um indicador isolado costuma quebrar o outro — empurrar a deflexão para cima derruba a satisfação. Cada eixo tem domínio fixo, a latência é sempre tracejada, e a visão de tabela mostra os números exatos sem geometria entre eles."
          semPadding
          rodape="As duas escalas são independentes: a altura de uma curva em relação à outra não significa nada, só o formato de cada uma ao longo do tempo. Dias sem nenhum atendimento pontuado ficam com a linha do NPS interrompida — nunca em zero."
        >
          {erro ? (
            <EstadoVazio
              className="m-5"
              titulo="Série indisponível"
              explicacao={`Não foi possível listar os atendimentos: ${erro}. A série temporal é derivada dessa lista.`}
            />
          ) : (
            <GraficoNpsLatencia serie={serie} />
          )}
        </Painel>

        <div className="grid min-w-0 grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
          <Painel
            titulo="Distribuição das notas inferidas"
            legenda="Faixas canônicas de NPS: 0–6 detrator, 7–8 neutro, 9–10 promotor — lidas de GET /modelo, não digitadas aqui."
            semPadding
          >
            <DistribuicaoScores
              barras={distribuicao.barras}
              semSinal={distribuicao.semSinal}
            />
          </Painel>

          <Painel
            titulo="Piores atendimentos do período"
            legenda="Menor nota inferida primeiro. Atendimento sem fala do cliente não entra: sem nota não há “pior”."
            semPadding
            acessorio={
              <span className="num text-xs text-muted-foreground">
                {distribuicao.semSinal} sem sinal
              </span>
            }
          >
            {erro ? (
              <EstadoVazio
                className="m-5"
                titulo="Lista indisponível"
                explicacao={erro}
              />
            ) : (
              <PioresAtendimentos
                piores={piores}
                semSinal={distribuicao.semSinal}
                sufixoDeQuery={sufixo}
              />
            )}
          </Painel>
        </div>

        <Painel
          titulo="Vocabulário característico de cada categoria"
          legenda="Ordenado por distinção, não por frequência: o termo que aparece em toda parte não explica nada; o que só aparece entre detratores é onde mora a oportunidade de melhoria."
          semPadding
        >
          {erro ? (
            <EstadoVazio
              className="m-5"
              titulo="Léxico indisponível"
              explicacao={`O léxico é contado a partir das transcrições, e a listagem falhou: ${erro}.`}
            />
          ) : (
            <PainelLexico classes={classes} />
          )}
        </Painel>

        <NotaMetodologica
          derivados={[
            `a série diária de NPS e de latência de ${rotulo}, agregada por data de início a partir das transcrições`,
            "o tempo mediano de resposta, calculado dos timestamps de cada par cliente → resposta",
            "as palavras e emojis característicos de cada categoria, contados das falas do cliente",
            ...(filtrado
              ? [
                  "os quatro indicadores do recorte, agregados a partir das categorias que o servidor gravou — porque a API não aceita filtro de data",
                ]
              : []),
          ]}
        />

        {recorte.falhas > 0 ? (
          <p className="text-xs text-muted-foreground">
            {recorte.falhas} transcrição(ões) não carregaram e ficaram fora dos
            agregados derivados. O último atendimento lido começou em{" "}
            {detalhes.length > 0
              ? formatarDataHora(detalhes[detalhes.length - 1].iniciada_em)
              : "—"}
            .
          </p>
        ) : null}
      </main>
    </>
  );
}
