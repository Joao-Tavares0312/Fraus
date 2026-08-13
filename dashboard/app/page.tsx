/**
 * =============================================================================
 * CONTRATO DE DIREÇÃO — painel principal do Fraus (modo Operate)
 *
 * THESIS: a tela é um instrumento de leitura de um depoimento não confiável.
 *   Recusa a grade de KPIs isolados, que é o arranjo padrão da categoria e é
 *   exatamente o que esconde o trade-off do produto: os quatro números vivem
 *   num único painel dividido por filetes, e a espinha da página é a
 *   sobreposição NPS × latência, não os cartões.
 * OWN-WORLD: papel quase-branco (#f9f9f7) com tinta quase-preta, filetes de 1px
 *   no lugar de sombra e raio, zero preenchimento decorativo. Dois acentos de
 *   série apenas: azul = inferido, laranja = observado; a paleta de status
 *   (detrator/neutro/promotor) é reservada e nunca vira cor de série. A marca
 *   está no sublinhado pontilhado de proveniência sob todo número estimado.
 * STORY: o visitante entende, em segundos, quanto os clientes estão satisfeitos,
 *   que esse número é estimado, e o que ele custa em tempo de resposta; então
 *   desce até um atendimento específico e vê onde a nota se formou.
 * FIRST VIEWPORT: barra de identificação com as ações de exportação à direita;
 *   a faixa dos quatro indicadores, cada um com o próprio trilho de escala;
 *   e, imediatamente abaixo, o gráfico sobreposto em largura total.
 * FORM: painel de instrumentos com filetes — 1ª da lista ordenada de estruturas
 *   derivadas da tarefa; escolhido diretamente por ser uma superfície Operate
 *   com requisitos de composição fixados pelo brief (sem sorteio de conceito).
 * =============================================================================
 */

import {
  listarConversas,
  obterDetalhes,
  obterIndicadores,
  type ResumoConversa,
} from "@/lib/api";
import {
  distribuicaoDeNotas,
  lexicoPorClasse,
  serieDiaria,
  tempoMedianoDeResposta,
} from "@/lib/derivacoes";
import { formatarDataHora } from "@/lib/formato";
import { DistribuicaoScores } from "@/components/DistribuicaoScores";
import { EstadoVazio } from "@/components/EstadoVazio";
import { FaixaIndicadores } from "@/components/FaixaIndicadores";
import { GraficoNpsLatencia } from "@/components/GraficoNpsLatencia";
import { NotaMetodologica } from "@/components/NotaMetodologica";
import { Painel } from "@/components/Painel";
import { PainelLexico } from "@/components/PainelLexico";
import { QuadroRelatorio } from "@/components/QuadroRelatorio";
import { TabelaConversas, type LinhaConversa } from "@/components/TabelaConversas";

export const dynamic = "force-dynamic";

function paraLinha(resumo: ResumoConversa): LinhaConversa {
  return {
    id: resumo.id,
    canal: resumo.canal,
    data: formatarDataHora(resumo.iniciada_em),
    ordenacao: resumo.iniciada_em,
    // A nota vem DERIVADA DO SERVIDOR em `/conversas`. Recalcular aqui já
    // divergiu do Python nas fronteiras 6/7 e 8/9 (arredondamento bancário
    // contra meio-para-cima) e fazia a tabela exibir nota 7 ao lado da
    // categoria "Detrator". A fonte da verdade é uma só.
    nota: resumo.nota,
    categoria: resumo.categoria,
  };
}

export default async function Pagina() {
  // Os dois blocos são independentes de propósito: se `/indicadores` cair, a
  // lista, o gráfico e a tabela continuam de pé, e vice-versa.
  const [indicadores, conversas] = await Promise.all([
    obterIndicadores(),
    listarConversas(),
  ]);

  const resumos = conversas.ok ? conversas.dado : [];
  const { detalhes, falhas } = conversas.ok
    ? await obterDetalhes(resumos.map((resumo) => resumo.id))
    : { detalhes: [], falhas: 0 };

  const serie = serieDiaria(detalhes);
  const distribuicao = distribuicaoDeNotas(resumos);
  const classes = lexicoPorClasse(detalhes);
  const tempoMediano = tempoMedianoDeResposta(detalhes);
  const linhas = resumos.map(paraLinha);

  const erroDaLista = conversas.ok ? undefined : conversas.erro;

  return (
    <QuadroRelatorio
      titulo="Satisfação nos atendimentos"
      subtitulo="O cliente escreve “ok, obrigado 🙂” e sai insatisfeito. Esta tela lê o que foi dito de verdade — texto, emoji e tempo de resposta — e estima a satisfação sem perguntar nada a ele."
      linhas={linhas}
      nomeCsv="fraus-atendimentos"
    >
      <main className="mx-auto flex w-full max-w-[1220px] flex-1 flex-col gap-6 px-6 py-6">
        <FaixaIndicadores
          indicadores={indicadores}
          tempoMediano={tempoMediano}
          erroTempo={erroDaLista}
        />

        <Painel
          titulo="NPS inferido × latência mediana, por dia"
          legenda="As duas séries aparecem sobrepostas de propósito: otimizar um indicador isolado costuma quebrar o outro — empurrar a deflexão para cima derruba a satisfação. O trade-off só fica visível quando as duas curvas dividem o mesmo eixo do tempo."
        >
          {erroDaLista ? (
            <EstadoVazio
              titulo="Série indisponível"
              explicacao={`Não foi possível listar os atendimentos: ${erroDaLista}. A série temporal é derivada dessa lista.`}
            />
          ) : (
            <GraficoNpsLatencia serie={serie} />
          )}
        </Painel>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
          <Painel
            titulo="Distribuição das notas inferidas"
            legenda="Faixas canônicas de NPS: 0–6 detrator, 7–8 neutro, 9–10 promotor."
          >
            <DistribuicaoScores
              barras={distribuicao.barras}
              semSinal={distribuicao.semSinal}
            />
          </Painel>

          <Painel
            titulo="Vocabulário característico de cada classe"
            legenda="Ordenado por distinção, não por frequência: o termo que aparece em toda parte não explica nada; o que só aparece entre detratores é onde mora a oportunidade de melhoria."
          >
            <PainelLexico classes={classes} />
          </Painel>
        </div>

        <Painel
          titulo="Atendimentos"
          legenda="Clique em qualquer linha para abrir a transcrição e ver onde a nota se formou."
          acessorio={
            falhas > 0 ? (
              <span className="text-[0.75rem] text-[var(--tinta-3)]">
                {falhas} transcrição(ões) não carregaram
              </span>
            ) : null
          }
        >
          {erroDaLista ? (
            <EstadoVazio
              titulo="Não foi possível listar os atendimentos"
              explicacao={erroDaLista}
            />
          ) : (
            <TabelaConversas linhas={linhas} />
          )}
        </Painel>

        <NotaMetodologica
          derivados={[
            "a série diária de NPS e de latência, agregada por data de início a partir das transcrições",
            "o tempo mediano de resposta, calculado dos timestamps de cada par cliente → resposta",
            "as palavras e emojis característicos de cada classe, contados das falas do cliente",
          ]}
        />
      </main>
    </QuadroRelatorio>
  );
}
