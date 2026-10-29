import type { CSSProperties } from "react";
import { gerarCeu, SEMENTE_CEU, type Ponto } from "@/lib/lp-nova/ceu";

const ceu = gerarCeu(SEMENTE_CEU);

/* Tres planos de profundidade, como o pó do filme "A fenda": o indice do ponto
   escolhe o plano, entao o ceu continua o mesmo em servidor e cliente. */
const PLANOS = [0, 1, 2].map((plano) => ceu.pontos.filter((_, i) => i % 3 === plano));

function PontoDoCeu({ p }: { p: Ponto }) {
  return (
    <i
      className={p.pisca ? "lp-ponto pisca" : "lp-ponto"}
      style={{
        left: `${p.x}%`,
        top: `${p.y}%`,
        "--s": `${p.tamanho}px`,
        "--o": p.opacidade,
        "--d": `${p.ciclo}s`,
        animationDelay: `${p.atraso}s`,
      } as CSSProperties}
    />
  );
}

/** Fundo vivo da LP: renderizado no servidor, so opacity/transform animam.
 * Nevoa, grade e feixe respiram em CSS; o parallax vem da linha do tempo da
 * rolagem (CSS), sem script por quadro. */
export function Ceu() {
  return (
    <div className="lp-ceu" aria-hidden="true">
      <div className="lp-nevoa" />
      <div className="lp-grade" />
      <div className="lp-feixe" />
      {PLANOS.map((pontos, plano) => (
        <div className="lp-plano" key={plano} style={{ "--z": plano } as CSSProperties}>
          {pontos.map((p) => <PontoDoCeu key={`${p.x}-${p.y}`} p={p} />)}
        </div>
      ))}
      {ceu.riscos.map((r, i) => (
        <b
          key={`r${i}`}
          className="lp-risco"
          style={{
            left: `${r.x}%`,
            top: `${r.y}%`,
            "--l": `${r.comprimento}px`,
            "--a": r.alfa,
            animationDuration: `${r.duracao}s`,
            animationDelay: `${r.atraso}s`,
          } as CSSProperties}
        />
      ))}
    </div>
  );
}
