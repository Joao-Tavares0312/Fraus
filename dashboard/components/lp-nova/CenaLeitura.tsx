"use client";

import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { iniciarCena, type CenaLeitura as Cena, type Frase } from "@/lib/lp-nova/cena";
import { MARCOS, faseDominante, progressoDaRolagem, type Ancora } from "@/lib/lp-nova/fases";
import { rotuloDoRegime, type EstadoRegime } from "@/lib/lp-nova/regime";

/**
 * A CASCA DA CENA da LP nova: o unico componente de cliente com canvas.
 *
 * Mede o progresso da rolagem (0 no topo, 1 no fim) e entrega a cena; as
 * secoes sao Server Components passados como `children`, legiveis antes de
 * qualquer JavaScript. O diagnostico da cena fica em detalhe no rodape,
 * sem competir com a leitura do produto.
 */
const ContextoCena = createContext<{ definirHumor(humor: number, cinza: number): void }>({
  definirHumor() {},
});

export function useCena() {
  return useContext(ContextoCena);
}

/**
 * A frase do hero medida em coordenadas de DOCUMENTO: quem recarrega no meio
 * da pagina (o navegador restaura a rolagem) ou entra por `#leituras` ainda
 * ve as particulas cairem nos glifos quando sobe ate o topo.
 */
function medirFrase(): Frase | null {
  const elemento = document.querySelector<HTMLElement>("[data-ln='frase']");
  if (!elemento) return null;
  const r = elemento.getBoundingClientRect();
  const e = getComputedStyle(elemento);
  return {
    texto: elemento.textContent ?? "",
    caixa: { left: r.left + window.scrollX, top: r.top + window.scrollY, width: r.width, height: r.height },
    // O atalho `font` volta vazio no Chrome; o canvas cairia em 10px.
    fonte: `${e.fontWeight} ${e.fontSize} ${e.fontFamily}`,
  };
}

function montar(
  alvoCanvas: HTMLCanvasElement,
  cena: { current: Cena | null },
  humor: { current: [number, number] },
  preferencias: { celular: boolean; movimentoReduzido: boolean },
  aoMudarRegime: (estado: EstadoRegime) => void,
): () => void {
  const nova = iniciarCena(alvoCanvas, {
    ...preferencias,
    frase: medirFrase(),
    aoMudarRegime,
  });
  cena.current = nova;
  // O seletor pode ter escolhido a leitura antes de a cena existir (ela espera
  // as fontes): o ultimo humor pedido vale assim que ela nasce.
  nova.definirHumor(...humor.current);

  // Cada secao marca ONDE o seu momento acontece; o fecho e o fim da rolagem.
  let ancoras: Ancora[] = [];
  const ancorar = () => {
    const meio = window.innerHeight * 0.5;
    ancoras = [...document.querySelectorAll<HTMLElement>("[data-marco]")].flatMap((el) => {
      const marco = el.dataset.marco as keyof typeof MARCOS;
      if (!(marco in MARCOS)) return [];
      const caixa = el.getBoundingClientRect();
      // Descendentes de details fechado nao tem caixa: top=0 nao e ancora.
      if (caixa.width <= 0 && caixa.height <= 0) return [];
      const y =
        marco === "fecho"
          ? document.documentElement.scrollHeight - window.innerHeight
          : Math.max(0, caixa.top + window.scrollY - meio);
      return [{ y: marco === "frase" ? 0 : y, p: MARCOS[marco] }];
    });
  };
  // A fase dominante vai para a raiz: o texto da mascara acende o passo dela.
  const raiz = alvoCanvas.closest<HTMLElement>(".ln");
  const medir = () => {
    const progresso = progressoDaRolagem(window.scrollY, ancoras);
    nova.definirProgresso(progresso, window.scrollY);
    const fase = faseDominante(progresso);
    if (raiz && raiz.dataset.fase !== fase) raiz.dataset.fase = fase;
  };
  const atualizarLayout = () => {
    ancorar();
    medir();
  };
  // Rotacao e resize mudam a caixa e o aspecto: a frase e refeita, com folga
  // para nao ressemear a cada pixel de um arrasto de janela.
  let espera = 0;
  const redimensionar = () => {
    atualizarLayout();
    window.clearTimeout(espera);
    espera = window.setTimeout(() => nova.refazerFrase(medirFrase()), 200);
  };
  atualizarLayout();
  const observar = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(atualizarLayout);
  if (raiz) observar?.observe(raiz);
  document.addEventListener("toggle", atualizarLayout, { capture: true });
  window.addEventListener("scroll", medir, { passive: true });
  window.addEventListener("resize", redimensionar);
  return () => {
    window.removeEventListener("scroll", medir);
    window.removeEventListener("resize", redimensionar);
    document.removeEventListener("toggle", atualizarLayout, { capture: true });
    observar?.disconnect();
    window.clearTimeout(espera);
    nova.dispose();
    if (cena.current === nova) cena.current = null;
  };
}

/** Ciclo imperativo isolado do React para cobrir media/fontes e desmontagem. */
export function acompanharCena(
  alvo: HTMLCanvasElement,
  cena: { current: Cena | null },
  humor: { current: [number, number] },
  aoMudarRegime: (estado: EstadoRegime | null) => void,
) {
  let desmontado = false;
  const celular = window.matchMedia("(max-width: 899px)");
  const movimento = window.matchMedia("(prefers-reduced-motion: reduce)");
  let fontesProntas = false;
  let soltar = () => {};
  const remontar = () => {
    // Dispose e sincrono: o device antigo nao pode submeter outro quadro
    // enquanto o novo aguarda import/init. Ler os dois media evita snapshots
    // conflitantes quando resize e preferencia mudam no mesmo turno.
    soltar();
    soltar = () => {};
    if (desmontado) return;
    const preferencias = { celular: celular.matches, movimentoReduzido: movimento.matches };
    if (!preferencias.movimentoReduzido) aoMudarRegime(null);
    if (!fontesProntas && !preferencias.movimentoReduzido) return;
    soltar = montar(alvo, cena, humor, preferencias, aoMudarRegime);
  };
  celular.addEventListener("change", remontar);
  movimento.addEventListener("change", remontar);
  // Reduce nao precisa esperar a fonte para interromper a GPU ou mostrar o
  // poster. Cada remontagem mede a rolagem atual e reaplica o ultimo humor.
  remontar();
  // A frase so pode ser rasterizada com a fonte carregada: antes disso o
  // canvas 2D mede a fonte reserva e as particulas nao caem nos glifos.
  void document.fonts.ready.then(() => {
    if (desmontado) return;
    fontesProntas = true;
    remontar();
  });
  return () => {
    if (desmontado) return;
    desmontado = true;
    celular.removeEventListener("change", remontar);
    movimento.removeEventListener("change", remontar);
    soltar();
  };
}

export function CenaLeitura({ children }: { children: React.ReactNode }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const cena = useRef<Cena | null>(null);
  const humor = useRef<[number, number]>([0, 0]);
  const [estado, setEstado] = useState<EstadoRegime | null>(null);

  useEffect(() => {
    if (!canvas.current) return;
    return acompanharCena(canvas.current, cena, humor, setEstado);
  }, []);

  const regime = estado?.regime;
  // Estavel entre renders: o seletor o usa como dependencia de efeito.
  const contexto = useMemo(
    () => ({
      definirHumor: (h: number, c: number) => {
        humor.current = [h, c];
        cena.current?.definirHumor(h, c);
      },
    }),
    [],
  );
  return (
    <ContextoCena.Provider value={contexto}>
      <div className="ln" data-regime={regime ?? "carregando"}>
        <canvas ref={canvas} aria-hidden className="ln-cena" />
        {children}
        <div className="ln-wrap ln-diagnostico">
          <details className="ln-detalhe">
            <summary>Sobre a cena visual</summary>
            <p className="ln-regime" role="status">
              {estado ? rotuloDoRegime(estado.regime, estado.motivo, estado.pausa) : "Cena estática até a inicialização do navegador."}
            </p>
            <p>A cena é ilustrativa. Sua qualidade não altera a análise dos atendimentos.</p>
          </details>
        </div>
      </div>
    </ContextoCena.Provider>
  );
}
