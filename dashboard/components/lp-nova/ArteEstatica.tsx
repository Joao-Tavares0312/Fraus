import Image from "next/image";
import type { Etapa } from "@/lib/lp-nova/narrativa";

/** O mesmo FR pre-renderizado, sem malha ou composicao 3D no celular. */
export function ArteEstatica({ etapa }: { etapa: Etapa }) {
  return (
    <picture>
      <source media="(max-width: 899px)" srcSet={`/identidade/fr-lp-${etapa}-compacto.webp`} />
      <Image className="arte-estatica" src={`/identidade/fr-lp-${etapa}.webp`} alt="" width={1280} height={1024} unoptimized loading={etapa === 0 ? "eager" : "lazy"} fetchPriority={etapa === 0 ? "high" : "auto"} decoding="async" />
    </picture>
  );
}
