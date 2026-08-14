"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import {
  Activity,
  BarChart3,
  MessagesSquare,
  PlugZap,
  ScanText,
  SlidersHorizontal,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { EstadoSaude } from "./EstadoSaude";

/**
 * Navegacao do aplicativo.
 *
 * Cada item CARREGA o periodo atual na propria URL. Sem isso o filtro global
 * nao seria global: bastaria trocar de secao para o recorte sumir, e as tres
 * telas passariam a falar de conjuntos diferentes sem avisar ninguem.
 *
 * A secao ativa nao e indicada so por cor (o dourado da marca): o item ativo
 * tambem carrega `aria-current="page"` e uma barra de 2px a esquerda -- cor
 * nunca e o unico canal.
 */
const SECOES = [
  { href: "/", rotulo: "Visão geral", Icone: BarChart3 },
  { href: "/atendimentos", rotulo: "Atendimentos", Icone: MessagesSquare },
  // Fica no grupo de OLHAR, e nao no de mexer, porque analisar nao grava nada:
  // nem conversa, nem nota, nem arquivo. Nenhum indicador se move por causa
  // dela, e e por isso que ela nao pertence ao lado das telas que alteram
  // configuracao e fonte de dado.
  { href: "/analisar", rotulo: "Analisar", Icone: ScanText },
  { href: "/modelo", rotulo: "Modelo", Icone: Activity },
] as const;

/**
 * As telas de MEXER, separadas das de olhar por um grupo proprio: elas mudam o
 * comportamento do sistema, e misturá-las com as tres de leitura esconderia
 * essa diferenca no unico lugar onde ela e obvia de graca.
 */
const AJUSTES = [
  { href: "/configuracoes", rotulo: "Configurações", Icone: SlidersHorizontal },
  { href: "/integracoes", rotulo: "Integrações", Icone: PlugZap },
] as const;

function estaAtiva(href: string, caminho: string): boolean {
  return href === "/" ? caminho === "/" : caminho.startsWith(href);
}

export function NavegacaoLateral() {
  const caminho = usePathname();
  const parametros = useSearchParams();

  const consulta = new URLSearchParams();
  for (const chave of ["de", "ate"] as const) {
    const valor = parametros.get(chave);
    if (valor) consulta.set(chave, valor);
  }
  const sufixo = consulta.toString() ? `?${consulta}` : "";

  function itemDaSecao({
    href,
    rotulo,
    Icone,
  }: {
    href: string;
    rotulo: string;
    Icone: typeof BarChart3;
  }) {
    const ativa = estaAtiva(href, caminho);
    return (
      <SidebarMenuItem key={href}>
        <SidebarMenuButton
          isActive={ativa}
          tooltip={rotulo}
          // O icone descansa em muted e so ACENDE no item ativo -- e acende em
          // dourado porque secao ativa e foco, territorio legitimo do
          // `--primary` (DESIGN.md 3.3). A barra de 2px e o aria-current
          // continuam: cor nunca e o unico canal.
          //
          // `data-[active]:`, sem `=true`: o base-ui seta `data-active=""`
          // como atributo booleano, e o seletor com valor nunca casava -- a
          // barra prometida aqui passou meses sem existir na tela.
          className="transition-colors duration-150 ease-fluid [&>svg]:text-muted-foreground [&>svg]:transition-colors [&>svg]:duration-150 hover:[&>svg]:text-sidebar-foreground data-[active]:border-l-2 data-[active]:border-primary data-[active]:font-medium data-[active]:[&>svg]:text-primary"
          render={
            <Link href={`${href}${sufixo}`} aria-current={ativa ? "page" : undefined} />
          }
        >
          <Icone aria-hidden />
          <span>{rotulo}</span>
        </SidebarMenuButton>
      </SidebarMenuItem>
    );
  }

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b border-sidebar-border">
        <Link
          href={`/${sufixo}`}
          aria-label="Fraus — voltar para a visão geral"
          className="flex items-center gap-2.5 rounded-md px-1 py-1.5 outline-none transition-colors duration-150 ease-fluid hover:bg-sidebar-accent/50 focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Image
            src="/fraus-logo.png"
            alt=""
            width={28}
            height={28}
            className="size-7 shrink-0 rounded-md"
            priority
          />
          <span className="flex min-w-0 flex-col group-data-[collapsible=icon]:hidden">
            <span className="truncate text-sm font-semibold tracking-tight">
              Fraus
            </span>
            <span className="truncate text-xs text-muted-foreground">
              satisfação inferida
            </span>
          </span>
        </Link>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Seções</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>{SECOES.map(itemDaSecao)}</SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Ajustes</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>{AJUSTES.map(itemDaSecao)}</SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border">
        <EstadoSaude />
      </SidebarFooter>
    </Sidebar>
  );
}
