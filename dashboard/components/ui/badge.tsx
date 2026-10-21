import { mergeProps } from "@base-ui/react/merge-props"
import { useRender } from "@base-ui/react/use-render"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/* Canto cortado de 6px (`app/camadas.css`); o foco de quem o tem e o anel
   interno da camada. `ghost` e `link` seguem retos, com o anel de sempre. */
const CORTE = "chanfro [--chanfro:6px]"
const SEM_TRACO = "[--cor-borda-chanfro:transparent]"
const FOCO =
  "rounded-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/60"

const badgeVariants = cva(
  "group/badge inline-flex h-5 w-fit shrink-0 items-center justify-center gap-1 overflow-hidden border border-transparent px-2 py-0.5 font-sans text-[0.6875rem] font-medium tracking-normal whitespace-nowrap transition-all has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 aria-invalid:border-destructive [&>svg]:pointer-events-none [&>svg]:size-3!",
  {
    variants: {
      variant: {
        default: `${CORTE} ${SEM_TRACO} bg-primary text-primary-foreground [a]:hover:bg-primary/80`,
        secondary: `${CORTE} ${SEM_TRACO} bg-secondary text-secondary-foreground [a]:hover:bg-secondary/80`,
        destructive: `${CORTE} ${SEM_TRACO} bg-destructive/10 text-destructive dark:bg-destructive/20 [a]:hover:bg-destructive/20`,
        outline: `${CORTE} border-linha bg-transparent text-foreground [--cor-borda-chanfro:var(--linha)] [a]:hover:border-primary [a]:hover:text-primary [a]:hover:[--cor-borda-chanfro:var(--primary)]`,
        ghost: `${FOCO} hover:bg-muted hover:text-muted-foreground dark:hover:bg-muted/50`,
        link: `${FOCO} text-primary underline-offset-4 hover:underline`,
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant = "default",
  render,
  ...props
}: useRender.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return useRender({
    defaultTagName: "span",
    props: mergeProps<"span">(
      {
        className: cn(badgeVariants({ variant }), className),
      },
      props
    ),
    render,
    state: {
      slot: "badge",
      variant,
    },
  })
}

export { Badge, badgeVariants }
