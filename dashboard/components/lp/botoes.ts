/**
 * Os botões da VITRINE, e só dela. O chassi da ferramenta usa radius 2px — o
 * chanfro do monograma — e isso é identidade certa no Operate e dura demais
 * numa landing page: os CTAs saíam com cara de controle de formulário. Aqui o
 * raio sobe para 10px e o corpo cresce (padrão Stripe/Revolut: alvo generoso,
 * peso médio, hover discreto). O dourado continua sendo a única cor de ação.
 *
 * String de classe em vez de componente porque todo uso é <Link>: um wrapper
 * só para concatenar classe seria camada sem função.
 */

const BASE =
  "botao-vitrine-base relative isolate overflow-hidden inline-flex items-center justify-center gap-2 font-medium whitespace-nowrap " +
  "transition-all duration-150 ease-fluid outline-none select-none " +
  "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 " +
  "focus-visible:ring-offset-background active:translate-y-px " +
  "[&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0";

/** CTA principal: dourado cheio, 48px de altura. */
export const botaoVitrine =
  BASE +
  " botao-vitrine-primario h-12 rounded-[10px] bg-primary px-6 text-base text-primary-foreground";

/** Ação secundária ao lado do CTA: contorno, mesma estatura. */
export const botaoVitrineContorno =
  BASE +
  " botao-vitrine-contorno h-12 rounded-[10px] border border-border bg-transparent px-6 text-base text-foreground";

/** A versão do header fixo: mesma família, um degrau menor. */
export const botaoVitrineMiudo =
  BASE +
  " botao-vitrine-primario h-9 rounded-[8px] bg-primary px-4 text-sm text-primary-foreground";

/** Link discreto do header (ex.: criar conta). */
export const botaoVitrineFantasma =
  BASE +
  " botao-vitrine-fantasma h-9 rounded-[8px] px-3 text-sm text-muted-foreground";
