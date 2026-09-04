import type { FichaModelo } from "@/lib/api";
import { formatarNumero } from "@/lib/formato";
import { Painel } from "@/components/Painel";
import { EstadoVazio } from "@/components/EstadoVazio";
import { LIMIAR_SUSPEITO } from "./MetricasTreino";

/**
 * O VEREDITO: as tres ressalvas estruturais que o avaliador precisa ler ANTES
 * de qualquer numero desta tela, num sistema `dominante` -- o unico da tela
 * Modelo, e por isso o primeiro do arquivo, antes do simulador.
 *
 * Ate 04/09/2026 estes tres fatos estavam espalhados: os dois de ironia
 * enterrados em `MetricasTreino.tsx` num paragrafo do mesmo peso visual que a
 * contagem do lexicon de emoji, e o de tempo em lugar nenhum desta tela (so
 * na visao geral, em `NotaMetodologica.tsx`). Nenhum dos tres foi inventado
 * aqui -- os dois de ironia leem os MESMOS campos de `GET /modelo` que
 * `MetricasTreino` ja lia (`cabecas` e `metricas`), e o de tempo e uma
 * limitacao declarada de arquitetura (nao ha cabeca de tempo a treinar; o
 * sinal vem de `fraus/sinais/tempo.py` sobre timestamps, nunca de fine-tuning),
 * por isso nao depende de nenhum campo numerico da API.
 *
 * MANCHETE E ETIQUETA SEGUEM A API, NUNCA UM TEXTO CRAVADO: ate 04/09/2026 a
 * etiqueta "fora do vetor" e a manchete "A ironia nao pontua" eram
 * incondicionais, e so o paragrafo pequeno abaixo ramificava em
 * `ironia.pontua` -- se o retreino entrar e a API passar a reportar
 * `pontua === true`, o painel dominante da tela que a banca le primeiro
 * afirmaria uma falsidade no maior tipo da pagina, com a ressalva certa em
 * letra miuda ao lado. Por isso os dois -- etiqueta E manchete -- ramificam
 * no MESMO dado que o paragrafo le.
 */
export function EstadoDoModelo({ modelo }: { modelo: FichaModelo }) {
  const ironia = modelo.cabecas.find((cabeca) => cabeca.nome === "ironia") ?? null;
  const metricasIronia = ironia?.metricas ?? null;

  const f1Bruto =
    metricasIronia && typeof metricasIronia.f1_ironico === "number"
      ? metricasIronia.f1_ironico
      : null;
  // Normaliza ANTES de comparar com LIMIAR_SUSPEITO: o campo pode vir em
  // fracao [0,1] ou ja em pontos percentuais. Comparar o valor cru contra um
  // limiar em fracao (0.999) rotulava 5.0 (5%, resultado pessimo) como
  // "suspeito" -- suspeito de bom demais, quando o numero e ruim demais.
  const f1Fracao = f1Bruto !== null ? (f1Bruto <= 1 ? f1Bruto : f1Bruto / 100) : null;
  const f1Percentual = f1Fracao !== null ? formatarNumero(f1Fracao * 100) : null;
  const f1Suspeito = f1Fracao !== null && f1Fracao >= LIMIAR_SUSPEITO;

  return (
    <Painel
      titulo="O veredito, antes do número"
      nivel="dominante"
      legenda={
        <>
          A ironia foi a primeira família a entrar no vetor do fusor, em
          21/08/2026, e a primeira a sair dele, em 04/09/2026 -- a cabeça (IDPT
          2021, treinada em tweet e notícia) mede sentimento positivo no corpus
          de treino deste projeto, não ironia, porque frase educada com queixa
          real (&ldquo;que atendimento maravilhoso, só esperei 3 horas&rdquo;) é exatamente
          o padrão que ela aprendeu a reconhecer como irônica em outro domínio.
          Ela continua carregada, obrigatória e lida por mensagem -- aparece em
          `mensagens[].prob_ironia` e no simulador abaixo -- só não pesa mais em
          `contribuicoes` nem em `importancias`. O F1 de 100% mede acerto no
          MESMO corpus sintético que gerou o treino: métrica perfeita em tarefa
          de linguagem quase nunca significa modelo bom, significa que o teste
          se parece demais com o treino. O sinal de tempo tem a mesma limitação
          por um motivo diferente: nenhum corpus público de review em
          português tem timestamps de diálogo, então ele é treinado em
          conversas sintéticas calibradas por literatura de live chat, não em
          atendimento real.
        </>
      }
    >
      <ul className="flex flex-col gap-4">
        <li className="flex flex-col gap-1">
          <span className="flex flex-wrap items-baseline gap-2">
            <span className="rounded-full bg-warning-rich-text/10 px-2 py-0.5 text-xs font-medium text-warning-rich-text">
              {ironia === null ? "fora do vetor" : ironia.pontua ? "no vetor" : "fora do vetor"}
            </span>
            <span className="text-sm font-medium text-foreground">
              {ironia?.pontua ? "A ironia pontua" : "A ironia não pontua"}
            </span>
          </span>
          {ironia ? (
            <p className="text-xs leading-relaxed text-muted-foreground">
              {ironia.pontua
                ? "A API reporta esta cabeça como parte do fusor agora — o texto acima já reflete isso, mas as demais ressalvas desta tela sobre a ironia (métrica medida em corpus sintético) continuam valendo."
                : "Carregada, obrigatória e lida por mensagem, mas fora de `importancias` e `contribuicoes` desde 04/09/2026: medida no corpus de treino, ela funciona como detector de sentimento positivo, não de ironia."}
            </p>
          ) : (
            <EstadoVazio
              className="mt-1"
              titulo="A cabeça de ironia não subiu"
              explicacao="GET /modelo não trouxe uma cabeça chamada `ironia` em `cabecas`. Sem ela não há como confirmar se continua fora do fusor."
              etapa="notebook 04 (ironia), descrito em docs/treinamento.md"
            />
          )}
        </li>

        <li className="flex flex-col gap-1">
          <span className="flex flex-wrap items-baseline gap-2">
            <span className="rounded-full bg-warning-rich-text/10 px-2 py-0.5 text-xs font-medium text-warning-rich-text">
              {f1Suspeito ? "suspeito" : "abaixo do limiar"}
            </span>
            <span className="text-sm font-medium text-foreground">
              O F1 da ironia é medido em corpus sintético
            </span>
          </span>
          {f1Percentual !== null ? (
            <p className="text-xs leading-relaxed text-muted-foreground">
              <span className="num text-foreground">{f1Percentual}%</span> de
              F1 na classe irônica, {f1Suspeito ? "acima" : "abaixo"} do limiar
              que este projeto trata como suspeito.{" "}
              {f1Suspeito
                ? "Métrica perfeita em tarefa de linguagem quase nunca significa modelo bom."
                : ""}
            </p>
          ) : (
            <EstadoVazio
              className="mt-1"
              titulo="O F1 da ironia ainda não foi exportado"
              explicacao="`metricas.f1_ironico` não veio de GET /modelo — nem para a cabeça de ironia, nem com valor 0, que seria dizer que ela erra tudo."
              etapa="notebook 04 (ironia), que exporta metricas.json"
            />
          )}
        </li>

        <li className="flex flex-col gap-1">
          <span className="flex flex-wrap items-baseline gap-2">
            <span className="rounded-full bg-warning-rich-text/10 px-2 py-0.5 text-xs font-medium text-warning-rich-text">
              sintético
            </span>
            <span className="text-sm font-medium text-foreground">
              O sinal de tempo é treinado em dados sintéticos
            </span>
          </span>
          <p className="text-xs leading-relaxed text-muted-foreground">
            Latência, escalação e abandono aprendem de conversas sintéticas
            calibradas por literatura de live chat — nenhum corpus público de
            review em português tem timestamps de diálogo. Limitação
            declarada, não escondida.
          </p>
        </li>
      </ul>
    </Painel>
  );
}
