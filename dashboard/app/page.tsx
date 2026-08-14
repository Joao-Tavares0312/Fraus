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
  obterDetalhes,
  obterIndicadores,
  obterLexico,
  obterSerieTemporal,
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
  serieDoServidor,
  tempoMedianoDeResposta,
} from "@/lib/derivacoes";
import { formatarDataHora } from "@/lib/formato";
import { lerPeriodo, periodoEstaAtivo } from "@/lib/periodo";
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

  // As leituras sao independentes de proposito: se `/indicadores` cair, a
  // serie, a distribuicao e o lexico continuam de pe, e vice-versa.
  const periodoPedido = lerPeriodo(parametros);
  const [recorte, indicadoresDoServidor, configuracoes, serieDaApi, lexicoDaApi] =
    await Promise.all([
      // Sem transcricoes: serie, lexico e tempo mediano vem AGREGADOS do
      // servidor agora, e baixar toda conversa so para derivar de novo era o
      // ultimo N+1 desta tela.
      carregarRecorte(parametros, { comDetalhes: false }),
      obterIndicadores(periodoPedido.de, periodoPedido.ate),
      obterConfiguracoes(),
      obterSerieTemporal(periodoPedido.de, periodoPedido.ate),
      obterLexico(periodoPedido.de, periodoPedido.ate),
    ]);

  // PLANO B: as transcricoes so sao baixadas se algum agregado do servidor
  // falhou -- e o unico caso em que a derivacao no cliente ainda roda. No
  // caminho feliz esta tela nao le transcricao nenhuma.
  let detalhes = recorte.detalhes;
  let falhasDeDetalhe = recorte.falhas;
  if (
    (!serieDaApi.ok || !indicadoresDoServidor.ok || !lexicoDaApi.ok) &&
    !recorte.erro
  ) {
    const baixados = await obterDetalhes(recorte.resumos.map((r) => r.id));
    detalhes = baixados.detalhes;
    falhasDeDetalhe = baixados.falhas;
  }

  // As faixas de referencia da latencia sao as VIGENTES, nao constantes do
  // front -- e a tela de Configuracoes que as move.
  const limiares = limiaresDe(
    configuracoes.ok ? configuracoes.dado.vigente.limiares_latencia_s : null,
  );

  const { periodo, extensao, rotulo, sufixo, resumos, erro } = recorte;

  /*
   * O SERVIDOR responde pelo recorte: `/indicadores?de=&ate=` recebe o mesmo
   * periodo da URL, entao o numero dele e a fonte da verdade com ou sem
   * filtro -- calculado em Python pelas mesmas funcoes que gravam a
   * categoria. A agregacao no cliente sobrevive so como plano B de falha do
   * endpoint, agregando a CATEGORIA gravada, nunca recalculando score.
   */
  const filtrado = periodoEstaAtivo(periodo);
  const indicadores = indicadoresDoServidor.ok
    ? {
        nps: indicadoresDoServidor.dado.nps,
        csat: indicadoresDoServidor.dado.csat,
        containment: indicadoresDoServidor.dado.total_conversas
          ? indicadoresDoServidor.dado.containment_rate
          : null,
        total: indicadoresDoServidor.dado.total_conversas,
        semSinal: indicadoresDoServidor.dado.sem_sinal,
        comSinal:
          indicadoresDoServidor.dado.total_conversas -
          indicadoresDoServidor.dado.sem_sinal,
      }
    : indicadoresDoPeriodo(resumos, detalhes);

  // A serie vem AGREGADA do servidor. O calculo sobre as transcricoes fica
  // como plano B: se `/serie-temporal` falhar, o grafico continua de pe com o
  // que o plano B baixou, em vez de sumir junto com o endpoint.
  const serie = serieDaApi.ok
    ? serieDoServidor(serieDaApi.dado.pontos)
    : serieDiaria(detalhes);
  const distribuicao = distribuicaoDeNotas(resumos);
  const classes = lexicoDaApi.ok
    ? lexicoDaApi.dado.classes
    : lexicoPorClasse(detalhes);
  const tempoMediano = indicadoresDoServidor.ok
    ? indicadoresDoServidor.dado.tempo_mediano_resposta_s
    : tempoMedianoDeResposta(detalhes);
  const piores: ResumoConversa[] = pioresAtendimentos(resumos, PIORES_NA_TELA);

  return (
    <>
      {/* Sem subtitulo, por decisao do Joao (14/08): o pitch morava aqui e
          empurrava a tese da tela para baixo. A honestidade metodologica nao
          saiu -- ela vive na NotaMetodologica e nos rotulos de estimativa. */}
      <CabecalhoPagina titulo="Visão geral" periodo={periodo} extensao={extensao} />

      <div className="flex min-w-0 flex-1 flex-col gap-7 px-4 py-5 sm:px-6">
        {/*
          O PRIMEIRO SISTEMA. A tese da tela — o trade-off entre satisfação e
          tempo — abre a página, e os indicadores agregados ficam à esquerda
          como armadura: lidos de uma vez, não relidos a cada compasso.

          Antes, quatro cartões de métrica ocupavam a primeira dobra inteira e
          empurravam este gráfico para 560px abaixo do topo. Quem chega quer
          ver a forma da semana, não quatro números soltos.
        */}
        <div className="grid min-w-0 grid-cols-1 gap-6 xl:grid-cols-[15rem_minmax(0,1fr)]">
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
                titulo="Série indisponível"
                explicacao={`Não foi possível listar os atendimentos: ${erro}. A série temporal é derivada dessa lista.`}
              />
            ) : (
              <GraficoNpsLatencia serie={serie} />
            )}
          </Painel>
        </div>

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

        {/* A lista de "derivado na interface" agora so existe em FALHA de
            endpoint: no caminho feliz, serie, indicadores, tempo mediano e
            lexico vem agregados do servidor e nao ha derivacao a declarar. */}
        <NotaMetodologica
          derivados={[
            ...(!serieDaApi.ok
              ? [
                  `a série diária de NPS e de latência de ${rotulo}, agregada das transcrições — porque GET /serie-temporal falhou`,
                ]
              : []),
            ...(!indicadoresDoServidor.ok
              ? [
                  "os indicadores e o tempo mediano de resposta, agregados das categorias e timestamps que o servidor gravou — porque GET /indicadores falhou",
                ]
              : []),
            ...(!lexicoDaApi.ok
              ? [
                  "as palavras e emojis característicos de cada categoria, contados das falas do cliente — porque GET /lexico falhou",
                ]
              : []),
          ]}
        />

        {falhasDeDetalhe > 0 ? (
          <p className="text-xs text-muted-foreground">
            {falhasDeDetalhe} transcrição(ões) não carregaram e ficaram fora dos
            agregados derivados. O último atendimento lido começou em{" "}
            {detalhes.length > 0
              ? formatarDataHora(detalhes[detalhes.length - 1].iniciada_em)
              : "—"}
            .
          </p>
        ) : null}
      </div>
    </>
  );
}
