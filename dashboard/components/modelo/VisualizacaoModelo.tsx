"use client";

import { useId, useState, type ReactNode } from "react";
import { ArrowDown, ArrowRight, CornerDownRight } from "lucide-react";
import type { CabecaDeModelo, FichaModelo, Simulacao } from "@/lib/api";
import { agruparPorSinal, ORDEM_SINAIS, ROTULO_SINAL, type SinalDaFeature } from "@/lib/derivacoes";
import { cn } from "@/lib/utils";
import { Simulador } from "./Simulador";

type Familia = Exclude<SinalDaFeature, "outros">;
type Etapa = "conversa" | "sinais" | Familia | "vetor" | "fusor" | "saida";
type Explicacao = { entrada: string; transformacao: string; saida: string; limite: string };

const FAMILIAS = ORDEM_SINAIS.filter((sinal): sinal is Familia => sinal !== "outros");
const CABECA_DA_FAMILIA: Partial<Record<Familia, string>> = {
  texto: "satisfacao", emocao: "emocao", ironia: "ironia",
};
const SO_CONVERSA = "somente no processamento de conversa";
const EXPLICACOES: Record<Etapa, Explicacao> = {
  conversa: {
    entrada: "Mensagens com autor e timestamps com fuso horário.",
    transformacao: "O adaptador organiza a conversa canônica e separa as falas do cliente das respostas do bot e do humano.",
    saida: "Texto por mensagem e contexto temporal da conversa.",
    limite: "Sem fala informativa do cliente, a conversa fica sem sinal — não recebe score zero. O simulador abaixo lê uma frase, não um atendimento completo.",
  },
  sinais: {
    entrada: "Falas do cliente, emojis, forma da escrita e contexto da conversa.",
    transformacao: "Oito famílias leem aspectos diferentes. Texto, emoção e ironia usam classificadores; as demais usam regras, léxicos ou timestamps.",
    saida: "Leituras por mensagem e medidas para agregação por conversa.",
    limite: "Leitura de uma frase não equivale ao vetor de uma conversa. Só as famílias efetivamente retornadas pela simulação recebem a marca azul.",
  },
  texto: {
    entrada: "Texto de cada mensagem do cliente.",
    transformacao: "Tokenização, encoder Transformer BERTimbau e cabeça fine-tunada de satisfação.",
    saida: "Probabilidades na ordem: insatisfeito, neutro, satisfeito.",
    limite: "Probabilidade de uma classe não é score de atendimento nem explicação causal das palavras.",
  },
  emoji: {
    entrada: "Emojis presentes nas falas do cliente.",
    transformacao: "Consulta ao Emoji Sentiment Ranking, com a curadoria vigente, e posição relativa no texto.",
    saida: "Polaridades, contagens e posições; agregados na conversa alimentam o vetor.",
    limite: "Emoji positivo não prova satisfação. Uma lista vazia retornada indica que nenhum emoji foi detectado, não falha de leitura.",
  },
  tempo: {
    entrada: "Timestamps, turnos, escalação e abandono da conversa.",
    transformacao: "Deriva latências e duração; as quatro medidas de espera recebem log1p na vetorização.",
    saida: "Medidas de tempo e estrutura do atendimento.",
    limite: "O treino do sinal temporal usa conversas sintéticas. Uma frase isolada não tem o contexto necessário para medi-lo.",
  },
  emocao: {
    entrada: "Texto de cada mensagem do cliente.",
    transformacao: "BERTimbau fine-tunado em sete classes de emoção. Desprezo é derivado da díade raiva + nojo, não uma oitava classe treinada.",
    saida: "Sete probabilidades treinadas e desprezo derivado; agregação por conversa para o fusor.",
    limite: "É inferência textual, não emoção declarada pelo cliente nem leitura biométrica. O Fraus não pontua atendentes.",
  },
  lexico: {
    entrada: "Palavras das falas do cliente e termos curados pelo analista.",
    transformacao: "SentiLex-PT02, escopo de negação e curadoria vigente.",
    saida: "Medidas de polaridade lexical agregadas por conversa.",
    limite: "Esta resposta de simulação não traz o sinal léxico. Não se deduz sua saída a partir das palavras digitadas.",
  },
  ironia: {
    entrada: "Texto de cada mensagem do cliente.",
    transformacao: "BERTimbau com cabeça binária treinada para ironia.",
    saida: "Probabilidade por mensagem; o caminho para o fusor segue o campo pontua da ficha consultada.",
    limite: "Cabeça pouco confiável em atendimento: o corpus histórico permite atalhos de sentimento. Leia como indício, nunca como veredito.",
  },
  estilo: {
    entrada: "Forma da escrita do cliente.",
    transformacao: "Regras para caixa alta, pontuação enfática, alongamento, palavrão e censura.",
    saida: "Marcas por frase; proporções e intensidades agregadas na conversa.",
    limite: "Uma marca de estilo não determina satisfação e não informa sozinha o quanto pesou no score.",
  },
  incongruencia: {
    entrada: "Polaridades do texto e do emoji, marcadores de contraste e situação descrita.",
    transformacao: "Regras de conflito entre sinais, hipérbole, aspas e elogio contra situação negativa.",
    saida: "Features de incongruência na conversa.",
    limite: "Não é a cabeça neural de ironia. O endpoint de frase não retorna estas features; o explorador não as inventa.",
  },
  vetor: {
    entrada: "Leituras das famílias que entram no fusor e contexto da conversa.",
    transformacao: "Agrega médias, máximos, proporções e outras medidas na ordem do contrato; aplica log1p às quatro features de espera.",
    saida: "Contrato vigente: sete famílias e 39 features. A contagem observada na ficha é mostrada separadamente.",
    limite: "Sem pesos disponíveis, não é possível confirmar a composição observada do vetor. A simulação de frase não devolve este vetor.",
  },
  fusor: {
    entrada: "Vetor da conversa, com as transformações do contrato de treino.",
    transformacao: "StandardScaler usa a escala aprendida no treino. LogisticRegression combina as features e estima as probabilidades de classe.",
    saida: "Probabilidades da conversa e score calculado no servidor.",
    limite: "Não é uma rede neural densa. Pesos globais não explicam uma conversa; contribuições em logits não são pontos de nota. Não calculado nesta simulação de frase.",
  },
  saida: {
    entrada: "Probabilidades do fusor e faixas de NPS vigentes no servidor.",
    transformacao: "O servidor deriva score de 0–100, nota de 0–10 e categoria; depois agrega os indicadores.",
    saida: "Score, nota e categoria inferidos por conversa; NPS inferido no agregado.",
    limite: "Estimativa não é resposta de pesquisa. Ausência de sinal permanece nula. Nenhuma nota ou categoria de conversa é calculada nesta simulação de frase.",
  },
};

const ETAPAS_CABECA = [
  { titulo: "Texto", transformacao: "Recebe a fala do cliente, sem transformá-la numa nota.", saida: "Texto para o tokenizador.", limite: "Nenhuma palavra recebe influência causal neste esquema." },
  { titulo: "Tokenização", transformacao: "O tokenizador do checkpoint converte o texto em tokens, IDs e máscara de atenção, respeitando seu limite de entrada.", saida: "Sequência numérica para o encoder.", limite: "A resposta desta API não expõe os tokens nem o truncamento da frase." },
  { titulo: "Encoder Transformer", transformacao: "O BERTimbau constrói representações contextuais dos tokens, aprendidas durante o pré-treino e o fine-tuning.", saida: "Representação contextual para a cabeça de classificação.", limite: "A ficha não expõe camadas, dimensões, atenção nem ativações internas. Este desenho não as reconstrói." },
  { titulo: "Cabeça", transformacao: "A cabeça fine-tunada transforma a representação em logits para as classes da tarefa selecionada.", saida: "Logits por classe.", limite: "Satisfação, emoção e ironia são tarefas distintas; seus números não devem ser somados." },
  { titulo: "Probabilidades", transformacao: "Os logits são convertidos em probabilidades, usando a temperatura do artefato quando disponível.", saida: "Probabilidades de classe desta mensagem.", limite: "Confiança alta não garante acerto e não revela o motivo causal da classificação." },
] as const;

function cabecaDaFamilia(modelo: FichaModelo, familia: Familia): CabecaDeModelo | undefined {
  const nome = CABECA_DA_FAMILIA[familia];
  return nome ? modelo.cabecas.find((cabeca) => cabeca.nome === nome) : undefined;
}

/** Presença na resposta, não valor positivo: probabilidade zero também foi medida. */
export function sinaisRetornados(resultado: Simulacao | null): Familia[] {
  if (!resultado) return [];
  const sinais: Familia[] = [];
  if ([resultado.prob_insatisfeito, resultado.prob_neutro, resultado.prob_satisfeito].every(Number.isFinite)) sinais.push("texto");
  if (Array.isArray(resultado.emojis)) sinais.push("emoji");
  if (resultado.emocao && Object.values(resultado.emocao).some(Number.isFinite)) sinais.push("emocao");
  if (typeof resultado.prob_ironia === "number" && Number.isFinite(resultado.prob_ironia)) sinais.push("ironia");
  if (resultado.estilo) sinais.push("estilo");
  return sinais;
}

/**
 * KISS (30/10/2026): a tela abre so com o simulador. O diagrama aparece
 * DEPOIS da primeira frase classificada, ja marcando o que ela acendeu --
 * antes disso ele era um mapa de "aguardando classificação" em toda caixa.
 */
export function VisualizacaoModelo({ modelo }: { modelo: FichaModelo }) {
  const [resultado, setResultado] = useState<Simulacao | null>(null);
  const id = useId();
  return (
    <div className="min-w-0">
      <section className="min-w-0" aria-labelledby={`${id}-simulador`}>
        <h3 id={`${id}-simulador`} className="sr-only">Classifique uma frase</h3>
        <p className="max-w-[75ch] text-sm text-muted-foreground">Nada é gravado.</p>
        <Simulador onResultado={setResultado} />
      </section>
      {resultado ? (
        <section className="mt-7 min-w-0 border-t border-border pt-5" aria-labelledby={`${id}-diagrama`}>
          <h3 id={`${id}-diagrama`} className="mb-4 text-lg font-medium text-foreground">Como o modelo leu esta frase</h3>
          <DiagramaDoModelo modelo={modelo} resultado={resultado} />
        </section>
      ) : null}
    </div>
  );
}

export function DiagramaDoModelo({ modelo, resultado }: { modelo: FichaModelo; resultado: Simulacao | null }) {
  const [selecao, setSelecao] = useState<Etapa>("conversa");
  const [etapaCabeca, setEtapaCabeca] = useState(2);
  const id = useId();
  const grupos = agruparPorSinal(modelo.importancias).filter((grupo) => grupo.features.length > 0);
  const quantidade = Object.keys(modelo.importancias).length;
  const retornados = sinaisRetornados(resultado);
  const selecionar = (etapa: Etapa) => { setSelecao(etapa); setEtapaCabeca(2); };
  const familiaSelecionada = FAMILIAS.find((familia) => familia === selecao);
  const cabeca = familiaSelecionada ? cabecaDaFamilia(modelo, familiaSelecionada) : undefined;
  const explicacao = EXPLICACOES[selecao];
  const tituloSelecionado = familiaSelecionada ? ROTULO_SINAL[familiaSelecionada] : {
    conversa: "Conversa", sinais: "Oito famílias de sinais", vetor: "Vetor da conversa", fusor: "Fusor", saida: "Score, nota e categoria",
  }[selecao as Exclude<Etapa, Familia>];

  function explicacaoSelecionada(sufixo: string) {
    return (
      <section aria-labelledby={`${id}-${sufixo}-titulo`} className="min-w-0 space-y-4 text-sm leading-relaxed">
        <h3 id={`${id}-${sufixo}-titulo`} className="text-lg font-medium text-foreground">{tituloSelecionado}</h3>
        <CamposExplicacao explicacao={explicacao} />
        {familiaSelecionada && CABECA_DA_FAMILIA[familiaSelecionada] ? (
          <p className="border-t border-border pt-3 text-muted-foreground">
            {cabeca ? cabeca.pontua ? "Esta cabeça entra no fusor, segundo a ficha consultada." : "Esta cabeça segue para leitura por mensagem, fora do fusor, segundo a ficha consultada." : "Cabeça ausente da ficha: caminho para o fusor não confirmado."}
          </p>
        ) : null}
        {familiaSelecionada && CABECA_DA_FAMILIA[familiaSelecionada] ? (
          <div className="space-y-3 border-t border-border pt-4">
            <h4 className="font-medium text-foreground">Por dentro da cabeça</h4>
            <ol className="flex flex-col gap-1" aria-label={`Processamento da cabeça de ${tituloSelecionado.toLowerCase()}`}>
              {ETAPAS_CABECA.map((etapa, indice) => (
                <li key={etapa.titulo}>
                  <button type="button" aria-pressed={etapaCabeca === indice} onClick={() => setEtapaCabeca(indice)} className={cn("chanfro min-h-11 w-full border px-3 py-2 text-left text-sm [--cor-borda-chanfro:var(--border)] hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring focus-visible:-outline-offset-2", etapaCabeca === indice ? "border-primary bg-muted font-medium [--cor-borda-chanfro:var(--primary)]" : "border-border")}>
                    {etapa.titulo}
                  </button>
                </li>
              ))}
            </ol>
            <CamposExplicacao explicacao={{ entrada: etapaCabeca === 0 ? "Fala do cliente." : ETAPAS_CABECA[etapaCabeca - 1].saida, ...ETAPAS_CABECA[etapaCabeca] }} />
            {cabeca?.classes.length ? <p className="text-muted-foreground">Classes da ficha: {cabeca.classes.join(" · ")}.</p> : <p className="text-muted-foreground">Classes não disponíveis na ficha consultada.</p>}
          </div>
        ) : null}
      </section>
    );
  }

  function controle(etapa: Etapa, titulo: string, detalhe: ReactNode, medido = false) {
    return <button type="button" aria-pressed={selecao === etapa} onClick={() => selecionar(etapa)} className={cn("chanfro flex min-h-11 w-full min-w-0 flex-col gap-1 border px-3 py-3 text-left text-sm [--cor-borda-chanfro:var(--border)] hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring focus-visible:-outline-offset-2", selecao === etapa ? "border-primary bg-muted [--cor-borda-chanfro:var(--primary)]" : "border-border")}>
      <span className="flex items-center gap-2 font-medium text-foreground">
        <span aria-hidden className={cn("size-2 shrink-0", medido ? "bg-medido" : etapa === "conversa" ? "bg-dito" : "border border-muted-foreground")} />
        {titulo}
      </span>
      <span className="text-xs leading-relaxed text-muted-foreground">{detalhe}</span>
    </button>;
  }

  function explicacaoMovel(etapas: Etapa[]) {
    return etapas.includes(selecao) ? <div className="border-b border-border py-4 md:hidden">{explicacaoSelecionada("movel")}</div> : null;
  }

  const leiturasSemFusor = FAMILIAS.filter((familia) => cabecaDaFamilia(modelo, familia)?.pontua === false);

  return (
    <div className="min-w-0">
      <p className="mb-5 max-w-[75ch] text-sm leading-relaxed text-muted-foreground">
        Esquema didático do processamento. Não mostra ativações internas, atenção ou influência causal das palavras.
      </p>
      <div className="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="min-w-0">
          <p className="mb-4 text-sm text-muted-foreground">Clique numa etapa para ver o que ela faz.</p>
          <ol aria-label="Fluxo de processamento do Fraus" className="grid min-w-0 gap-3 md:grid-cols-[minmax(0,.85fr)_minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,1.1fr)_minmax(0,.9fr)] md:items-center">
            <li className="relative min-w-0">
              {controle("conversa", "Conversa", "Falas, autores e timestamps")}
              {explicacaoMovel(["conversa"])}
              <Ligacao />
            </li>
            <li className="relative min-w-0 space-y-2">
              {controle("sinais", "8 famílias de sinais", "Três cabeças neurais; cinco famílias por regras, léxicos e contexto")}
              {explicacaoMovel(["sinais"])}
              <ul className="space-y-2" aria-label="Famílias de sinais">
                {FAMILIAS.map((familia) => {
                  const neural = CABECA_DA_FAMILIA[familia];
                  const ficha = cabecaDaFamilia(modelo, familia);
                  const grupo = grupos.find((grupo) => grupo.sinal === familia);
                  const temResposta = retornados.includes(familia);
                  const caminho = neural ? ficha ? ficha.pontua ? "Entra no vetor" : "Ramo por mensagem · fora do vetor" : "Caminho não confirmado" : quantidade ? grupo ? `${grupo.features.length} features na ficha` : "Sem features na ficha" : "Pesos indisponíveis";
                  const estado = familia === "tempo" || familia === "lexico" || familia === "incongruencia" ? SO_CONVERSA : temResposta ? "Retornado nesta frase" : resultado ? "Não retornado nesta frase" : "Aguardando classificação";
                  return <li key={familia} className="min-w-0">
                    {controle(familia, ROTULO_SINAL[familia], <>{caminho}<br />{estado}</>, temResposta)}
                    {explicacaoMovel([familia])}
                  </li>;
                })}
              </ul>
              {leiturasSemFusor.length ? (
                <div aria-label="Ramo de leitura por mensagem" className="flex items-start gap-2 border-t border-dashed border-border pt-3 text-xs leading-relaxed text-muted-foreground">
                  <CornerDownRight aria-hidden className="size-4 shrink-0" />
                  <p><strong className="font-medium text-foreground">Leitura por mensagem</strong><br />{leiturasSemFusor.map((familia) => ROTULO_SINAL[familia]).join(" · ")}<br />Este ramo não segue para o vetor nem para o fusor.</p>
                </div>
              ) : null}
              <Ligacao />
            </li>
            <li className="relative min-w-0">
              {controle("vetor", "7 famílias · 39 features", "Contrato vigente · agregação por conversa")}
              <p className="mt-3 text-xs leading-relaxed text-muted-foreground">{quantidade ? `Ficha consultada: ${quantidade} features em ${grupos.length} famílias.` : "Pesos indisponíveis: contagem observada não disponível."}</p>
              {quantidade ? <ul className="mt-2 space-y-1 text-xs text-muted-foreground" aria-label="Composição observada do vetor">{grupos.map((grupo) => <li key={grupo.sinal}>{ROTULO_SINAL[grupo.sinal]}: {grupo.features.length}</li>)}</ul> : null}
              <p className="mt-3 text-xs leading-relaxed text-muted-foreground">{SO_CONVERSA}</p>
              {explicacaoMovel(["vetor"])}
              <Ligacao />
            </li>
            <li className="relative min-w-0">
              {controle("fusor", "Fusor", <>StandardScaler<br />+ LogisticRegression</>)}
              <p className="mt-3 text-xs leading-relaxed text-muted-foreground">não calculado nesta simulação de frase</p>
              {explicacaoMovel(["fusor"])}
              <Ligacao />
            </li>
            <li className="min-w-0">
              {controle("saida", "Score → nota → categoria", "Inferidos no servidor · não são resultados desta frase")}
              {explicacaoMovel(["saida"])}
            </li>
          </ol>
          <p className="mt-5 flex items-start gap-2 text-sm leading-relaxed text-muted-foreground"><span aria-hidden className="mt-1.5 size-2 shrink-0 bg-medido" />Marca azul: família retornada na última classificação de frase. Não indica influência no score. Sem marca não significa valor zero.</p>
        </div>
        <div className="hidden min-w-0 border-t border-border pt-5 md:block xl:border-t-0 xl:border-l xl:pl-5 xl:pt-0" aria-live="polite">{explicacaoSelecionada("lateral")}</div>
      </div>
    </div>
  );
}

function CamposExplicacao({ explicacao }: { explicacao: Explicacao }) {
  return <dl className="space-y-3">{([
    ["Entrada", explicacao.entrada], ["Transformação", explicacao.transformacao], ["Saída", explicacao.saida], ["Limite", explicacao.limite],
  ] as const).map(([rotulo, texto]) => <div key={rotulo}><dt className="font-medium text-foreground">{rotulo}</dt><dd className="mt-0.5 text-muted-foreground">{texto}</dd></div>)}</dl>;
}

function Ligacao() {
  return <span aria-hidden className="pointer-events-none flex justify-center py-2 text-muted-foreground md:absolute md:top-1/2 md:-right-3 md:-translate-y-1/2 md:py-0"><ArrowDown className="size-4 md:hidden" /><ArrowRight className="hidden size-3 md:block" /></span>;
}
