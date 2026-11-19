"use client";

import { useEffect, useRef, useState } from "react";
import type { AnimationEvent, RefObject } from "react";
import Image from "next/image";
import { Dialog } from "@base-ui/react/dialog";
import { Hand, RotateCcw, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import estilos from "./SegredoFraus.module.css";

const POSES = [
  { nome: "face", largura: 960, altura: 640 },
  { nome: "espiar", largura: 480, altura: 720 },
  { nome: "puxar", largura: 480, altura: 720 },
  { nome: "passo", largura: 480, altura: 720 },
  { nome: "hello", largura: 480, altura: 720 },
  { nome: "wink", largura: 800, altura: 1200 },
] as const;

type Cena = "espiar" | "puxar" | "entrar" | "ola" | "cumplice" | "curiosa";
const PROXIMA_CENA: Partial<Record<Cena, Cena>> = { espiar: "puxar", puxar: "entrar", entrar: "ola" };
const CENAS = {
  espiar: { pose: "espiar", fala: "Tem alguém do outro lado da logo…", acao: "Dar um oi" },
  puxar: { pose: "puxar", fala: "Só um instante. Essa fenda estava apertada.", acao: "Dar um oi" },
  entrar: { pose: "passo", fala: "Com licença. Mascote passando!", acao: "Dar um oi" },
  ola: { pose: "hello", fala: "Cinco toques? Você queria mesmo me encontrar. Oi, eu sou a Fraus-chan!", acao: "Dar um oi" },
  cumplice: { pose: "wink", fala: "Oi pra você também. Minha presença aqui fica entre a gente, combinado?", acao: "Guardar segredo" },
  curiosa: { pose: "face", fala: "Combinado. Agora, sobre esse seu hábito de clicar em tudo…", acao: "Eu? Imagina…" },
} as const;

/** Cena local: as falas sao fixas; nao le conversas nem altera indicadores. */
export function SegredoFraus({
  aoFechar,
  gatilho,
}: {
  aoFechar: () => void;
  gatilho: RefObject<HTMLButtonElement | null>;
}) {
  const fechar = useRef<HTMLButtonElement>(null);
  const [cena, setCena] = useState<Cena>("espiar");
  const [entrada, setEntrada] = useState(0);
  const [carregadas, setCarregadas] = useState<string[]>([]);
  const [erroImagem, setErroImagem] = useState(false);
  const prontas = carregadas.length === POSES.length && !erroImagem;
  const entrando = cena in PROXIMA_CENA;
  const atual = CENAS[cena];

  useEffect(() => {
    if (!prontas) return;
    // A sequencia avanca pelo fim de cada animacao CSS, nao por dois relogios
    // independentes. Reduce pula direto para a saudacao, inclusive se mudar
    // durante uma entrada. O frame unico tambem cobre imagens ja em cache.
    const consulta = window.matchMedia("(prefers-reduced-motion: reduce)");
    const concluirSemMovimento = () => { if (consulta.matches) setCena("ola"); };
    const quadro = window.requestAnimationFrame(concluirSemMovimento);
    consulta.addEventListener("change", concluirSemMovimento);
    return () => {
      window.cancelAnimationFrame(quadro);
      consulta.removeEventListener("change", concluirSemMovimento);
    };
  }, [entrada, prontas]);

  function avancarEntrada(evento: AnimationEvent<HTMLButtonElement>) {
    if (evento.target !== evento.currentTarget) return;
    setCena((anterior) => PROXIMA_CENA[anterior] ?? anterior);
  }

  function interagir() {
    setCena((anterior) => anterior === "ola" ? "cumplice" : anterior === "cumplice" ? "curiosa" : "ola");
  }

  function repetir() {
    setCena("espiar");
    setEntrada((anterior) => anterior + 1);
  }

  return (
    <Dialog.Root open onOpenChange={(aberto) => { if (!aberto) aoFechar(); }}>
      <Dialog.Portal>
        {/* O backdrop proprio impede que um clique feche tambem a gaveta movel. */}
        <Dialog.Backdrop forceRender className="fixed inset-0 z-[60] bg-black/75" />
        <Dialog.Popup
          initialFocus={fechar}
          finalFocus={gatilho}
          className={estilos.segredo}
          data-cena={cena}
          data-pronta={prontas}
        >
          <Dialog.Close
            render={<Button ref={fechar} variant="ghost" size="icon" className={estilos.fechar} />}
            aria-label="Fechar segredo"
          >
            <X aria-hidden />
          </Dialog.Close>

          <div className={estilos.conteudo}>
            <Dialog.Title className={estilos.titulo}>Fraus-chan</Dialog.Title>
            <Dialog.Description className={estilos.descricao}>
              Você encontrou o outro lado da logo.
            </Dialog.Description>
            <div className={estilos.balao}>
              <p role="status" aria-live="polite" aria-atomic="true">
                {erroImagem
                  ? "Minha arte não carregou. Feche e abra o segredo para tentar de novo."
                  : !prontas ? "Preparando minha entrada…" : atual.fala}
              </p>
            </div>
            <div className={estilos.acoes}>
              <Button className="min-h-11" disabled={!prontas || entrando} onClick={interagir}>
                <Hand aria-hidden />{atual.acao}
              </Button>
              <Button variant="ghost" className="min-h-11" disabled={!prontas} onClick={repetir}>
                <RotateCcw aria-hidden />Rever entrada
              </Button>
            </div>
          </div>

          <div key={entrada} className={estilos.palco}>
            <div className={estilos.fenda} aria-hidden />
            <button
              type="button"
              className={estilos.personagem}
              aria-label="Interagir com Fraus-chan"
              disabled={!prontas || entrando}
              onClick={interagir}
              onAnimationEnd={avancarEntrada}
            >
              {POSES.map((pose) => (
                <Image
                  key={pose.nome}
                  src={`/fraus-chan/${pose.nome}.webp`}
                  width={pose.largura}
                  height={pose.altura}
                  alt=""
                  draggable={false}
                  unoptimized
                  loading="eager"
                  className={estilos.pose}
                  data-visivel={prontas && atual.pose === pose.nome}
                  data-pose={pose.nome}
                  onLoad={() => setCarregadas((anteriores) => anteriores.includes(pose.nome) ? anteriores : [...anteriores, pose.nome])}
                  onError={() => setErroImagem(true)}
                />
              ))}
            </button>
            <div className={estilos.cortina} aria-hidden />
          </div>

          <footer className={estilos.rodape}>
            <p>Só uma aparição. Nada é salvo e seus indicadores não mudam.</p>
            <Dialog.Close render={<Button variant="ghost" className="min-h-11 shrink-0" />}>
              Voltar à dashboard
            </Dialog.Close>
          </footer>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
