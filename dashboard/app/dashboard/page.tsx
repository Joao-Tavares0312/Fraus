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
  type DetalheConversa,
  type ResumoConversa,
} from "@/lib/api";
import { carregarRecorte } from "@/lib/carregar";
import {
  distribuicaoDeNotas,
  FAIXAS_NPS,
  indicadoresDoPeriodo,
  limiaresDe,
  lexicoPorClasse,
  pioresAtendimentos,
  serieDiaria,
  serieDoServidor,
  tempoMedianoDeResposta,
} from "@/lib/derivacoes";
import { formatarDataHora } from "@/lib/formato";
import { lerPeriodo } from "@/lib/periodo";
import { AvisoLexicoAntigo } from "@/components/AvisoLexicoAntigo";
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

export default async function Pagina(props: PageProps<"/dashboard">) {
  const parametros = await props.searchParams;

  // As leituras sao independentes de proposito: se `/indicadores` cair, a
  // serie, a distribuicao e o lexico continuam de pe, e vice-versa.
  const periodoPedido = lerPeriodo(parametros);
  const [recorte, indicadoresDoServidor, configuracoes, serieDaApi, lexicoDaApi] =
    await Promise.all([
      // Sem transcricoes: serie, lexico e tempo mediano vem AGREGADOS do
      // servidor agora, e baixar toda conversa so para derivar de novo era o
      // ultimo N+1 desta tela.
      carregarRecorte(parametros),
      obterIndicadores(periodoPedido.de, periodoPedido.ate),
      obterConfiguracoes(),
      obterSerieTemporal(periodoPedido.de, periodoPedido.ate),
      obterLexico(periodoPedido.de, periodoPedido.ate),
    ]);

  // PLANO B: as transcricoes so sao baixadas se algum agregado do servidor
  // falhou -- e o unico caso em que a derivacao no cliente ainda roda. No
  // caminho feliz esta tela nao le transcricao nenhuma.
  let detalhes: DetalheConversa[] = [];
  let falhasDeDetalhe = 0;
  let truncadasNoPlanoB = 0;
  if (
    (!serieDaApi.ok || !indicadoresDoServidor.ok || !lexicoDaApi.ok) &&
    !recorte.erro
  ) {
    const baixados = await obterDetalhes(recorte.resumos.map((r) => r.id));
    detalhes = baixados.detalhes;
    falhasDeDetalhe = baixados.falhas;
    // `obterDetalhes` corta em TETO_DETALHES_PLANO_B para o periodo "todos" nao
    // virar uma cadeia de dezenas de lotes sequenciais dentro do render. O
    // corte E sobre o RECORTE, entao os agregados derivados aqui (serie,
    // lexico, tempo mediano) passam a valer so para uma AMOSTRA do periodo --
    // e a tela precisa dizer isso, nao fingir que cobriu tudo.
    truncadasNoPlanoB = baixados.truncadas;
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
  const indicadores = indicadoresDoServidor.ok
    ? {
        nps: indicadoresDoServidor.dado.nps,
        npsIntervalo: indicadoresDoServidor.dado.nps_intervalo ?? null,
        csat: indicadoresDoServidor.dado.csat,
        // A guarda `total_conversas ? ... : null` que morava aqui saiu em
        // 10/09/2026: ela existia porque o servidor devolvia 0.0 no conjunto
        // vazio e o cliente nao acreditava. Agora o servidor diz `null`, e
        // uma ponta so decide -- o `?? null` cobre apenas API antiga.
        containment: indicadoresDoServidor.dado.containment_rate ?? null,
        // `?? null` e `?? 0` aqui NAO sao o zero proibido: eles cobrem uma API
        // antiga que nao devolve os campos. O ausente vira null (nao sei) e o
        // denominador vira 0, que e o que faz a peca dizer "sem sinal" em vez
        // de inventar percentual.
        falsoContainment: indicadoresDoServidor.dado.falso_containment ?? null,
        contidosComSinal: indicadoresDoServidor.dado.contidos_com_score ?? 0,
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

  /*
   * QUANDO A SERIE VAZIA NAO SIGNIFICA "NAO HOUVE ATENDIMENTO".
   *
   * `GraficoNpsLatencia` so recebe `serie`, entao serie vazia era sempre
   * traduzida como "Nenhum atendimento no período selecionado". Isso e verdade
   * quando a listagem respondeu e veio vazia -- e mentira quando
   * `/serie-temporal` caiu, o plano B tambem caiu, e a lista ao lado esta
   * cheia de atendimentos. A tela afirmava ausencia sem ter como saber, e com
   * a confianca de quem sabe.
   *
   * O ramo do `erro` (falha da LISTAGEM) ja existia; este cobre o buraco entre
   * ele e o grafico -- a mesma correcao que a distribuicao e o lexico ja
   * tinham recebido, aplicada ao unico painel que dependia de um agregado
   * proprio. O criterio e o plano B ter REPOSTO o que faltava: se todas as
   * transcricoes do recorte foram baixadas, a serie derivada e completa e o
   * grafico pode falar normalmente.
   */
  const erroDaSerie = serieDaApi.ok ? null : serieDaApi.erro;
  const serieIncompleta = erroDaSerie !== null && detalhes.length < resumos.length;
  // As faixas VIGENTES governam a cor de cada barra, do mesmo jeito que
  // governam a categoria gravada. Digitadas aqui, a tela dava dois vereditos
  // para o mesmo atendimento assim que alguem mexesse em Configuracoes.
  const faixasVigentes = configuracoes.ok
    ? configuracoes.dado.vigente.faixas_nps
    : undefined;
  const distribuicao = distribuicaoDeNotas(resumos, faixasVigentes);
  const classes = lexicoDaApi.ok
    ? lexicoDaApi.dado.classes
    : lexicoPorClasse(detalhes);
  const tempoMediano = indicadoresDoServidor.ok
    ? indicadoresDoServidor.dado.tempo_mediano_resposta_s
    : tempoMedianoDeResposta(detalhes);
  const piores: ResumoConversa[] = pioresAtendimentos(resumos, PIORES_NA_TELA);

  // Só existe quando o servidor de fato respondeu a contagem E ela é maior que
  // zero. Com `/indicadores` fora, nada é afirmado: não saber com qual léxico o
  // banco foi pontuado não é o mesmo que saber que está em dia.
  const defasadas = indicadoresDoServidor.ok
    ? (indicadoresDoServidor.dado.pontuadas_com_lexico_antigo ?? 0)
    : 0;
  const totalNoBanco = indicadoresDoServidor.ok
    ? (indicadoresDoServidor.dado.total_no_banco ?? 0)
    : 0;

  return (
    <>
      {/* Sem subtitulo, por decisao do Joao (14/08): o pitch morava aqui e
          empurrava a tese da tela para baixo. A honestidade metodologica nao
          saiu -- ela vive na NotaMetodologica e nos rotulos de estimativa. */}
      <CabecalhoPagina titulo="Visão geral" periodo={periodo} extensao={extensao} />

      {/* SEM flex-1: esta div so cresce ate onde o conteudo pede. Com
          flex-1 ela esticava ate a altura de `main` (que o SidebarProvider
          forca a no minimo min-h-svh), e como o conteudo real era mais baixo
          que a tela, sobrava vazio DEPOIS do ultimo painel e ANTES da nota
          metodologica -- o buraco de ~600px que a hierarquia veio fechar. O
          buraco nunca foi a altura da barra lateral: ela e `fixed`, e ja
          acompanha o viewport por conta propria (ver components/ui/sidebar.tsx). */}
      <div className="flex min-w-0 flex-col gap-7 px-4 py-5 sm:px-6">
        {defasadas > 0 ? (
          <AvisoLexicoAntigo defasadas={defasadas} total={totalNoBanco} />
        ) : null}

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
            nivel="dominante"
            rodape="As duas escalas são independentes: a altura de uma curva em relação à outra não significa nada, só o formato de cada uma ao longo do tempo. Dias sem nenhum atendimento pontuado ficam com a linha do NPS interrompida — nunca em zero."
          >
            {erro ? (
              <EstadoVazio
                titulo="Série indisponível"
                explicacao={`Não foi possível listar os atendimentos: ${erro}. A série temporal é derivada dessa lista.`}
              />
            ) : serieIncompleta ? (
              /* Nomeia o que falhou em vez de afirmar ausência de dado. A
                 contagem ao lado é a prova de que houve atendimento: sem ela,
                 "indisponível" pareceria o mesmo "vazio" de sempre. */
              <EstadoVazio
                titulo="Série indisponível"
                explicacao={`GET /serie-temporal não respondeu (${erroDaSerie}), e a agregação de reserva não conseguiu ler as transcrições. Não é ausência de atendimento: ${resumos.length} foram listados no período. Os outros painéis desta tela seguem valendo.`}
              />
            ) : (
              <GraficoNpsLatencia serie={serie} />
            )}
          </Painel>
        </div>

        <div className="grid min-w-0 grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
          <Painel
            titulo="Distribuição das notas inferidas"
            legenda={
              faixasVigentes
                ? `Faixas vigentes: ${FAIXAS_NPS.map(({ categoria }) => {
                    const faixa = faixasVigentes[categoria];
                    return faixa
                      ? `${faixa[0]}–${faixa[1]} ${categoria}`
                      : categoria;
                  }).join(", ")} — lidas de GET /configuracoes, não digitadas aqui.`
                : "Faixas de fábrica: 0–6 detrator, 7–8 neutro, 9–10 promotor. GET /configuracoes não respondeu, então as faixas vigentes não puderam ser confirmadas."
            }
            semPadding
          >
            {/* Sem este ramo, a distribuição recebia zero barras e anunciava
                "Nenhum atendimento no período" quando a causa era a API fora --
                afirmando ausência de atendimento sem ter como saber. Numa
                ferramenta batizada com o nome do daemon do engano, esse é o
                erro mais caro que uma tela vazia pode cometer. Mesmo ramo que
                a lista e o vocabulário já tinham. */}
            {erro ? (
              <EstadoVazio
                className="m-5"
                titulo="Distribuição indisponível"
                explicacao={erro}
              />
            ) : (
              <DistribuicaoScores
                barras={distribuicao.barras}
                semSinal={distribuicao.semSinal}
              />
            )}
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

        {truncadasNoPlanoB > 0 ? (
          <p className="text-xs text-muted-foreground">
            {rotulo} tem mais atendimentos do que a agregação de reserva
            consegue processar de uma vez: {truncadasNoPlanoB} ficaram de fora
            dos indicadores, da série e do léxico derivados aqui. Isto só afeta
            o plano B — a tabela de atendimentos continua completa.
          </p>
        ) : null}
      </div>
    </>
  );
}
