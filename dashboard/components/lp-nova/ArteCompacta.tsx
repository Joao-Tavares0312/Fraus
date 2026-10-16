import { ArteEstatica } from "./ArteEstatica";
import type { Etapa } from "@/lib/lp-nova/narrativa";

export function ArteCompacta({ etapa }: { etapa: Etapa }) {
  return <div className="arte-compacta" data-pose={etapa} aria-hidden="true"><ArteEstatica etapa={etapa} /></div>;
}
