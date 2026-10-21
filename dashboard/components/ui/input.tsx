import * as React from "react"
import { Input as InputPrimitive } from "@base-ui/react/input"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <InputPrimitive
      type={type}
      data-slot="input"
      className={cn(
        "superficie h-8 w-full min-w-0 [--chanfro:7px] px-2.5 py-1 font-sans text-base transition-colors outline-none file:inline-flex file:h-6 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-input/50 disabled:opacity-50 aria-invalid:border-destructive aria-invalid:[--cor-borda-chanfro:var(--destructive)] md:text-sm dark:disabled:bg-input/80",
        className
      )}
      {...props}
    />
  )
}

export { Input }
