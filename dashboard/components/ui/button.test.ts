import { describe, expect, it } from "vitest"

import { badgeVariants } from "./badge"
import { buttonVariants } from "./button"

const VARIANTES = ["default", "outline", "secondary", "ghost", "destructive", "link"] as const
const ICONES = ["icon", "icon-xs", "icon-sm", "icon-lg"] as const

const tem = (classes: string, nome: string) => classes.split(/\s+/).includes(nome)

describe("buttonVariants", () => {
  it("default usa as placas e perde o arredondamento", () => {
    const c = buttonVariants({})
    expect(tem(c, "placas")).toBe(true)
    expect(tem(c, "rounded-md")).toBe(false)
  })

  it("default nao desenha face, borda nem anel no proprio elemento", () => {
    const c = buttonVariants({})
    for (const proibida of ["bg-primary", "border", "border-transparent", "bg-clip-padding", "focus-visible:ring-2"]) {
      expect(tem(c, proibida)).toBe(false)
    }
    expect(c).not.toMatch(/(^|\s)(hover:)?bg-/)
    expect(c).not.toMatch(/(^|\s)active:not-aria-\[haspopup\]:translate-y-px/)
  })

  it("outline e secondary tem canto cortado e fio no hover, sem placas", () => {
    for (const variant of ["outline", "secondary"] as const) {
      const c = buttonVariants({ variant })
      expect(tem(c, "chanfro")).toBe(true)
      expect(tem(c, "fio-hover")).toBe(true)
      expect(tem(c, "placas")).toBe(false)
    }
  })

  it("destructive tem canto cortado, sem fio nem placas", () => {
    const c = buttonVariants({ variant: "destructive" })
    expect(tem(c, "chanfro")).toBe(true)
    expect(tem(c, "fio-hover")).toBe(false)
    expect(tem(c, "placas")).toBe(false)
  })

  it("ghost e link ficam sem canto cortado e sem placas", () => {
    for (const variant of ["ghost", "link"] as const) {
      const c = buttonVariants({ variant })
      expect(tem(c, "chanfro")).toBe(false)
      expect(tem(c, "placas")).toBe(false)
      expect(tem(c, "rounded-md")).toBe(true)
    }
  })

  it("tamanhos de icone nunca ganham canto cortado nem placas", () => {
    for (const size of ICONES) {
      for (const variant of VARIANTES) {
        const c = buttonVariants({ size, variant })
        expect(tem(c, "chanfro"), `${size}/${variant}`).toBe(false)
        expect(tem(c, "placas"), `${size}/${variant}`).toBe(false)
        expect(c, `${size}/${variant}`).toMatch(/rounded/)
      }
    }
  })

  it("icone default ainda tem face e foco visivel", () => {
    const c = buttonVariants({ size: "icon" })
    expect(tem(c, "bg-primary")).toBe(true)
    expect(c).toMatch(/focus-visible:ring-2/)
  })

  it("sm declara canto de 7px e o tamanho padrao 9px", () => {
    expect(tem(buttonVariants({ size: "sm" }), "[--chanfro:7px]")).toBe(true)
    expect(tem(buttonVariants({ size: "xs" }), "[--chanfro:7px]")).toBe(true)
    expect(tem(buttonVariants({}), "[--chanfro:9px]")).toBe(true)
  })

  it("o deslocamento das placas segue o mockup da dashboard", () => {
    const c = buttonVariants({})
    for (const v of ["[--placa-repouso:2px]", "[--placa-fundo:4px]", "[--placa-sobe:-2px]", "[--placa-abre:5px]"]) {
      expect(tem(c, v), v).toBe(true)
    }
    expect(c).toMatch(/active:\[--placa-sobe:2px\]/)
  })

  it("nao repete poligono nem hex de placa", () => {
    for (const variant of VARIANTES) expect(buttonVariants({ variant })).not.toMatch(/polygon|#[0-9a-f]{3,6}/i)
  })
})

describe("badgeVariants", () => {
  it("outline tem canto cortado de 6px", () => {
    const c = badgeVariants({ variant: "outline" })
    expect(tem(c, "chanfro")).toBe(true)
    expect(tem(c, "[--chanfro:6px]")).toBe(true)
  })

  it("ghost e link ficam sem canto cortado", () => {
    expect(tem(badgeVariants({ variant: "ghost" }), "chanfro")).toBe(false)
    expect(tem(badgeVariants({ variant: "link" }), "chanfro")).toBe(false)
  })
})
