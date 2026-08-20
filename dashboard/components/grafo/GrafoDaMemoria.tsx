"use client";

import dynamic from "next/dynamic";
import type { ComponentType, RefObject } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  ForceGraphMethods,
  ForceGraphProps,
  LinkObject,
  NodeObject,
} from "react-force-graph-2d";
import type { ArestaDoGrafo, Camada, Grafo, NoDoGrafo } from "@/lib/api";
import { ListaDeNos } from "./ListaDeNos";
import { FichaDoNo } from "./FichaDoNo";
import { ReguaDeCamadas } from "./ReguaDeCamadas";
import { LegendaDeCores } from "./LegendaDeCores";
import {
  comOpacidade,
  desenharNo,
  espessuraDaAresta,
  paletaAtual,
  pintarAreaDoNo,
  type NoPosicionado,
} from "./desenho";

type NoDaSimulacao = NodeObject<NoPosicionado>;
type ArestaDaSimulacao = LinkObject<NoPosicionado, ArestaDoGrafo>;
type Metodos = ForceGraphMethods<NoPosicionado, ArestaDoGrafo>;

/**
 * `ssr: false` nao e permitido em Server Component no App Router -- e por isso
 * que este arquivo e cliente e a pagina fica sendo servidor. A tipagem
 * generica se perde no `dynamic`, entao ela e reafirmada aqui: sem isso todas
 * as callbacks abaixo cairiam em `any` calado.
 */
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full animate-pulse rounded-md bg-muted" />
  ),
}) as ComponentType<
  ForceGraphProps<NoPosicionado, ArestaDoGrafo> & {
    ref?: RefObject<Metodos | undefined>;
  }
>;

/** Opacidade da camada fora de foco. Presente, e quase apagada. */
const APAGADO = 0.08;
/** Opacidade de quem nao e vizinho do no sob o mouse. */
const AFASTADO = 0.15;

/** A ponta de uma aresta e string antes da simulacao e objeto depois. */
function idDaPonta(ponta: ArestaDaSimulacao["source"]): string {
  return typeof ponta === "object" && ponta !== null
    ? String(ponta.id)
    : String(ponta);
}

export function GrafoDaMemoria({ grafo }: { grafo: Grafo }) {
  const refGrafo = useRef<Metodos | undefined>(undefined);
  const refCaixa = useRef<HTMLDivElement | null>(null);
  const [foco, setFoco] = useState<Camada | "todas">("todas");
  const [selecionado, setSelecionado] = useState<NoDoGrafo | null>(null);
  const [aceso, setAceso] = useState<string | null>(null);
  const [medida, setMedida] = useState({ largura: 0, altura: 0 });

  /**
   * A simulacao precisa de largura e altura em pixel; sem elas o force-graph
   * assume a janela inteira e desenha metade do grafo fora do painel.
   */
  useEffect(() => {
    const caixa = refCaixa.current;
    if (!caixa) return;
    const observador = new ResizeObserver(([entrada]) => {
      const { width, height } = entrada.contentRect;
      setMedida({ largura: Math.round(width), altura: Math.round(height) });
    });
    observador.observe(caixa);
    return () => observador.disconnect();
  }, []);

  /**
   * `graphData` estavel: e a memoria espacial da pessoa que esta em jogo.
   *
   * Toda vez que este objeto muda de identidade o force-graph reinicia a
   * simulacao e o grafo inteiro se rearranja. Por isso ele depende SO do
   * `grafo`, e nunca do foco ou da selecao -- interagir com a tela nao pode
   * redesenhar o mapa que a pessoa acabou de memorizar.
   *
   * Os nos sao copias porque a simulacao MUTA o objeto (escreve `x`, `y`,
   * `vx`, `vy`); sujar os nos que vieram do servidor faria o dado da API e o
   * estado da fisica virarem a mesma coisa.
   */
  const dados = useMemo(
    () => ({
      nodes: grafo.nos.map((no): NoDaSimulacao => ({ ...no })),
      links: grafo.arestas.map(
        (aresta): ArestaDaSimulacao => ({
          ...aresta,
          source: aresta.de,
          target: aresta.para,
        }),
      ),
    }),
    [grafo],
  );

  /** Do id para o no que a simulacao esta movendo -- e nele que ha `x`/`y`. */
  const porId = useMemo(
    () => new Map(dados.nodes.map((no) => [String(no.id), no])),
    [dados],
  );

  /**
   * Adjacencia pre-computada: o hover consulta em O(1).
   *
   * Varrer a lista de arestas a cada movimento do mouse faria a simulacao
   * engasgar justamente enquanto alguem explora -- que e o unico momento em
   * que a tela precisa responder rapido.
   */
  const vizinhos = useMemo(() => {
    const mapa = new Map<string, Set<string>>();
    for (const aresta of grafo.arestas) {
      if (!mapa.has(aresta.de)) mapa.set(aresta.de, new Set());
      if (!mapa.has(aresta.para)) mapa.set(aresta.para, new Set());
      mapa.get(aresta.de)!.add(aresta.para);
      mapa.get(aresta.para)!.add(aresta.de);
    }
    return mapa;
  }, [grafo.arestas]);

  /**
   * Opacidade do no: o foco de camada APAGA, nunca remove.
   *
   * Remover re-dispararia a simulacao e embaralharia o layout inteiro a cada
   * troca de camada -- a pessoa perderia a orientacao espacial que acabou de
   * construir. Apagando, as pontes ENTRE camadas continuam visiveis, que e o
   * motivo de o grafo ser um so em vez de tres abas.
   */
  const opacidadeDe = useCallback(
    (id: string, camada: Camada) => {
      if (foco !== "todas" && camada !== foco) return APAGADO;
      if (aceso && aceso !== id && !vizinhos.get(aceso)?.has(id)) return AFASTADO;
      return 1;
    },
    [foco, aceso, vizinhos],
  );

  /**
   * Seleciona e leva a camera ate o no -- venha o gesto do canvas ou da lista.
   *
   * A lista `sr-only` chama exatamente esta funcao: se ela apenas abrisse a
   * ficha, o fallback acessivel seria uma tela paralela em vez do MESMO
   * caminho. O zoom passa do limiar de rotulo de proposito: quem selecionou
   * quer ler o nome.
   */
  const selecionar = useCallback(
    (no: NoDoGrafo) => {
      setSelecionado(no);
      const posicionado = porId.get(no.id);
      if (posicionado?.x !== undefined && posicionado.y !== undefined) {
        refGrafo.current?.centerAt(posicionado.x, posicionado.y, 400);
        refGrafo.current?.zoom(Math.max(refGrafo.current.zoom(), 2.5), 400);
      }
    },
    [porId],
  );

  /**
   * A fisica so pode ser ajustada depois da montagem: `d3Force` e um metodo do
   * kapsule, e ele nao existe enquanto o `dynamic` nao resolveu o modulo.
   *
   * A repulsao maior que o padrao e o teto de distancia sao o que separa os
   * aglomerados: com o padrao, um `canal` de grau alto puxa tudo para uma
   * bola unica e nao se enxerga camada nenhuma.
   */
  useEffect(() => {
    if (medida.largura === 0) return;
    refGrafo.current?.d3Force("charge")?.strength(-120).distanceMax(400);
    refGrafo.current?.d3Force("link")?.distance(40);
  }, [medida.largura]);

  /**
   * O enquadramento acontece UMA vez, quando o layout assenta.
   *
   * Arrastar um no reaquece a simulacao e dispara `onEngineStop` de novo; sem
   * esta trava a camera saltaria de volta para o grafo inteiro toda vez que
   * alguem mexesse num ponto, desfazendo o zoom que a pessoa deu.
   */
  const jaEnquadrou = useRef(false);
  const aoParar = useCallback(() => {
    if (jaEnquadrou.current) return;
    jaEnquadrou.current = true;
    refGrafo.current?.zoomToFit(400, 40);
  }, []);

  const corDaAresta = useCallback(
    (aresta: ArestaDaSimulacao) => {
      const linha = paletaAtual().linha;
      const origem = porId.get(idDaPonta(aresta.source));
      const destino = porId.get(idDaPonta(aresta.target));
      if (!origem || !destino) return comOpacidade(linha, APAGADO);
      // A aresta vale o MENOR dos dois lados: uma ponte para a camada apagada
      // continua desenhada, mas discreta -- ela mostra que a ligacao existe
      // sem competir com a camada que esta em foco.
      return comOpacidade(
        linha,
        Math.min(
          opacidadeDe(String(origem.id), origem.camada),
          opacidadeDe(String(destino.id), destino.camada),
        ),
      );
    },
    [porId, opacidadeDe],
  );

  const contagem = `${grafo.nos.length} nós, ${grafo.arestas.length} arestas`;

  /**
   * Os tipos que de fato existem no grafo em tela -- e so eles entram na
   * legenda. Depende do `grafo`, nao do foco: apagar uma camada nao apaga a
   * cor dela do canvas, entao tirar o item da legenda deixaria uma cor
   * visivel sem nome.
   */
  const tiposPresentes = useMemo(
    () => new Set(grafo.nos.map((no) => no.tipo)),
    [grafo.nos],
  );

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <ReguaDeCamadas
        camadas={grafo.meta.camadas}
        foco={foco}
        aoFocar={setFoco}
        meta={grafo.meta}
      />

      <LegendaDeCores tipos={tiposPresentes} />

      <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1fr)_16rem]">
        <div className="relative min-w-0">
          {/* O canvas e um bitmap: nenhuma tecnologia assistiva le o que foi
              pintado nele. Escondê-lo da arvore de acessibilidade evita
              anunciar um elemento vazio, e o conteudo equivalente esta na
              lista abaixo -- que e alcancavel por Tab. */}
          <div
            ref={refCaixa}
            aria-hidden
            className="h-[70vh] min-h-[26rem] w-full overflow-hidden rounded-md border border-linha bg-background"
          >
            {medida.largura > 0 ? (
              <ForceGraph2D
                ref={refGrafo}
                width={medida.largura}
                height={medida.altura}
                graphData={dados}
                backgroundColor="transparent"
                nodeLabel={(no: NoDaSimulacao) => no.rotulo}
                nodeCanvasObject={(no, ctx, escala) =>
                  desenharNo(
                    no,
                    ctx,
                    escala,
                    opacidadeDe(String(no.id), no.camada),
                    String(no.id) === selecionado?.id,
                    paletaAtual(),
                  )
                }
                nodePointerAreaPaint={(no, cor, ctx) =>
                  pintarAreaDoNo(no, cor, ctx)
                }
                linkColor={corDaAresta}
                linkWidth={(aresta: ArestaDaSimulacao) =>
                  espessuraDaAresta(aresta.peso)
                }
                onNodeHover={(no) => setAceso(no ? String(no.id) : null)}
                onNodeClick={(no) => selecionar(no)}
                onBackgroundClick={() => setSelecionado(null)}
                warmupTicks={20}
                /* A simulacao PARA. Grafo grande recebe menos ticks porque o
                   custo por tick cresce com o numero de nos, e o notebook que
                   vai apresentar isto nao pode ficar queimando CPU num laço
                   de fisica que nunca termina. */
                cooldownTicks={grafo.nos.length > 1500 ? 60 : 200}
                d3VelocityDecay={0.3}
                onEngineStop={aoParar}
              />
            ) : null}
          </div>

          {/*
            O FALLBACK ACESSIVEL, e ele nao e consolo: seleciona o MESMO no que
            o clique no canvas seleciona e abre a MESMA ficha.

            Ele sai do `sr-only` quando recebe foco: um teclado sem leitor de
            tela existe, e mandar o cursor de foco para dentro de uma regiao
            invisivel e perder o cursor. Ao focar, a lista vira um painel por
            cima do canvas -- que e a unica superficie livre da tela.
          */}
          <div className="sr-only focus-within:not-sr-only focus-within:absolute focus-within:inset-0 focus-within:z-10 focus-within:overflow-auto focus-within:rounded-md focus-within:border focus-within:border-linha focus-within:bg-background focus-within:p-3">
            <h3 className="mb-2 text-xs text-muted-foreground">
              Os nós do grafo em lista — {contagem}. Selecionar um nó aqui abre
              a mesma ficha que o clique no canvas.
            </h3>
            <ListaDeNos nos={grafo.nos} aoSelecionar={selecionar} />
          </div>
        </div>

        <aside className="min-w-0 lg:border-l lg:border-linha lg:pl-4">
          <FichaDoNo no={selecionado} />
        </aside>
      </div>
    </div>
  );
}
