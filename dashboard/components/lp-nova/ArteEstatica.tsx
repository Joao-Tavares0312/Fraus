import Image from "next/image";

/** O FR pre-renderizado: sem JS, sem WebGL elegivel ou com contexto perdido. */
export function ArteEstatica() {
  return (
    <picture>
      <source media="(max-width: 899px)" srcSet="/identidade/fr-lp-0-compacto.webp" />
      <Image className="arte-estatica" src="/identidade/fr-lp-0.webp" alt="" width={1280} height={1024} unoptimized loading="eager" decoding="async" />
    </picture>
  );
}
