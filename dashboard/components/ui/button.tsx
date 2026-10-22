import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/*
 * Camadas do FR (opcao "contida" do mockup da dashboard): o canto cortado, as
 * placas e o fio vem de `app/camadas.css`; aqui so se escolhem classes e
 * variaveis. Botao de icone, `ghost` e `link` ficam arredondados e com o anel
 * de sempre; os demais tem o foco desenhado pela camada (por dentro no
 * `.chanfro`, afastado nas `.placas`), entao nao levam `ring-*`.
 */
const FOCO =
  "focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/60"
const PRESSIONA = "active:not-aria-[haspopup]:translate-y-px"
const REDONDO = "rounded-md border border-transparent bg-clip-padding"
const NAO_ICONE = ["default", "xs", "sm", "lg"] as const
const ICONES = ["icon", "icon-xs", "icon-sm", "icon-lg"] as const

const buttonVariants = cva(
  "group/button relative inline-flex shrink-0 items-center justify-center font-sans text-xs font-medium tracking-normal whitespace-nowrap transition-all outline-none select-none disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "font-semibold text-primary-foreground",
        outline: `border border-linha bg-transparent bg-clip-padding [--cor-borda-chanfro:var(--linha)] hover:border-primary hover:text-primary hover:[--cor-borda-chanfro:var(--primary)] aria-expanded:bg-muted aria-expanded:text-foreground aria-invalid:border-destructive ${PRESSIONA}`,
        secondary: `border border-border bg-secondary bg-clip-padding text-secondary-foreground [--cor-borda-chanfro:var(--border)] hover:border-linha hover:bg-[color-mix(in_oklch,var(--secondary),var(--foreground)_5%)] hover:[--cor-borda-chanfro:var(--linha)] aria-expanded:bg-secondary aria-expanded:text-secondary-foreground aria-invalid:border-destructive ${PRESSIONA}`,
        ghost: `${REDONDO} ${FOCO} hover:bg-muted hover:text-foreground aria-expanded:bg-muted aria-expanded:text-foreground aria-invalid:border-destructive dark:hover:bg-muted/50 ${PRESSIONA}`,
        destructive: `border border-destructive/40 bg-destructive/10 bg-clip-padding text-destructive [--cor-borda-chanfro:color-mix(in_oklch,var(--destructive)_40%,transparent)] hover:bg-destructive/20 dark:bg-destructive/15 dark:hover:bg-destructive/25 ${PRESSIONA}`,
        link: `${REDONDO} ${FOCO} text-primary underline-offset-4 hover:underline aria-invalid:border-destructive ${PRESSIONA}`,
      },
      size: {
        default:
          "h-8 gap-1.5 px-2.5 [--chanfro:9px] has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
        xs: "h-6 gap-1 px-2 text-[0.6875rem] [--chanfro:7px] has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-7 gap-1 px-2.5 text-[0.6875rem] [--chanfro:7px] has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-9 gap-1.5 px-2.5 [--chanfro:9px] has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
        icon: "size-8",
        "icon-xs":
          "size-6 rounded-[min(var(--radius-md),10px)] in-data-[slot=button-group]:rounded-lg [&_svg:not([class*='size-'])]:size-3",
        "icon-sm":
          "size-7 rounded-[min(var(--radius-md),12px)] in-data-[slot=button-group]:rounded-lg",
        "icon-lg": "size-9",
      },
    },
    compoundVariants: [
      // primario: placas empilhadas, deslocamento proporcional ao mockup
      {
        variant: "default",
        size: [...NAO_ICONE],
        class:
          "placas [--placa-repouso:2px] [--placa-fundo:4px] [--placa-sobe:-2px] [--placa-abre:5px] active:[--placa-sobe:2px]",
      },
      // secundario, contorno e destrutivo: canto cortado (e fio no hover)
      {
        variant: ["outline", "secondary", "destructive"],
        size: [...NAO_ICONE],
        class: "chanfro",
      },
      {
        variant: ["outline", "secondary"],
        size: [...NAO_ICONE],
        class: "fio-hover",
      },
      // ghost e link mantem o raio nos tamanhos pequenos
      {
        variant: ["ghost", "link"],
        size: "xs",
        class: "rounded-[min(var(--radius-md),10px)]",
      },
      {
        variant: ["ghost", "link"],
        size: "sm",
        class: "rounded-[min(var(--radius-md),12px)]",
      },
      // icone: sem canto cortado e sem placas, qualquer variante
      {
        variant: ["default", "outline", "secondary", "destructive"],
        size: [...ICONES],
        class: `rounded-md ${FOCO}`,
      },
      {
        variant: "default",
        size: [...ICONES],
        class: `${REDONDO} bg-primary hover:bg-primary/85 aria-invalid:border-destructive ${PRESSIONA}`,
      },
      {
        variant: "destructive",
        size: [...ICONES],
        class: "focus-visible:border-destructive focus-visible:ring-destructive/30",
      },
    ],
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
