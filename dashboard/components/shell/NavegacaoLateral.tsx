"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import type { MouseEvent } from "react";
import { BookOpen, ExternalLink, LogOut } from "lucide-react";
import { Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarGroupContent, SidebarGroupLabel, SidebarHeader, SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarTrigger, useSidebar } from "@/components/ui/sidebar";
import { consultaDoPeriodo, gruposDoPapel, telaEstaAtiva } from "@/lib/navegacao";
import { EstadoSaude } from "./EstadoSaude";
import { MarcaFraus } from "./MarcaFraus";
import { SeletorTema } from "./SeletorTema";

const ITEM = "h-11 rounded-lg px-3 text-sm text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground data-[active]:bg-sidebar-accent data-[active]:font-semibold data-[active]:text-sidebar-accent-foreground data-[active]:after:absolute data-[active]:after:inset-y-3 data-[active]:after:left-0 data-[active]:after:w-px data-[active]:after:bg-primary focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring";

function SessaoNoRodape({ usuario, papel }: {
  usuario: { nome: string; email: string };
  papel: "dev" | "usuario";
}) {
  const roteador = useRouter();
  const [saindo, setSaindo] = useState(false);
  async function sair() {
    setSaindo(true);
    try {
      await fetch("/api/sessao/sair", { method: "POST" });
    } finally {
      roteador.push("/");
      roteador.refresh();
    }
  }
  return <div className="flex items-center gap-2 rounded-md px-2 py-1 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0">
    <span className="flex min-w-0 flex-1 flex-col group-data-[collapsible=icon]:hidden">
      <span className="truncate text-xs font-medium" title={usuario.email}>{usuario.nome}</span>
      <span className="truncate text-xs text-muted-foreground">{papel === "dev" ? "desenvolvedor" : "analista"}</span>
    </span>
    <button type="button" onClick={sair} disabled={saindo} aria-label={saindo ? "Saindo da conta…" : `Sair da conta de ${usuario.nome}`} title="Sair da conta" className="flex size-11 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring disabled:opacity-50"><LogOut aria-hidden className="size-4" /></button>
  </div>;
}

/** Todos os destinos preservam período, sessão e permissões existentes. */
export function NavegacaoLateral({ papel, usuario }: {
  papel: "dev" | "usuario";
  usuario: { nome: string; email: string } | null;
}) {
  const caminho = usePathname();
  const parametros = useSearchParams();
  const urlDaDocumentacao = process.env.NEXT_PUBLIC_URL_DOCS;
  const grupos = gruposDoPapel(papel);
  const sufixo = consultaDoPeriodo(parametros);
  const { isMobile, setOpenMobile } = useSidebar();

  function aoNavegar(evento: MouseEvent<HTMLAnchorElement>) {
    if (isMobile && !evento.defaultPrevented && evento.button === 0 &&
      !evento.metaKey && !evento.ctrlKey && !evento.shiftKey && !evento.altKey) {
      setOpenMobile(false);
    }
  }

  return <Sidebar collapsible="icon" aria-label="Navegação principal">
    <SidebarHeader className="flex-row items-center gap-2 px-3 py-4 group-data-[collapsible=icon]:flex-col group-data-[collapsible=icon]:px-2.5">
      <MarcaFraus tamanho={32} />
      <Link href={`/dashboard${sufixo}`} onClick={aoNavegar} aria-label="Fraus — voltar para a visão geral" className="min-w-0 flex-1 rounded-md py-2 text-2xl font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring group-data-[collapsible=icon]:hidden">
        Fraus
      </Link>
      <SidebarTrigger className="ml-auto group-data-[collapsible=icon]:ml-0" />
    </SidebarHeader>
    <SidebarContent className="gap-4 px-2.5 pb-3">
      <nav aria-label="Seções da ferramenta" className="flex flex-col gap-4 group-data-[collapsible=icon]:gap-3">
        {grupos.map(({ rotulo, telas }) => <SidebarGroup key={rotulo} className="p-0" role="group" aria-label={rotulo}>
          <SidebarGroupLabel className="px-3">{rotulo}</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">{telas.map(({ href, rotulo: nome, icone: Icone }) => {
              const ativa = telaEstaAtiva(caminho, href);
              return <SidebarMenuItem key={href}>
                <SidebarMenuButton
                  isActive={ativa}
                  aria-label={nome}
                  tooltip={ativa ? `${nome} — seção atual` : nome}
                  className={ITEM}
                  render={<Link href={`${href}${sufixo}`} onClick={aoNavegar} aria-current={ativa ? (caminho === href ? "page" : "location") : undefined} />}
                >
                  <Icone aria-hidden className="size-4 shrink-0" />
                  <span className="truncate group-data-[collapsible=icon]:hidden">{nome}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>;
            })}</SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>)}
      </nav>
    </SidebarContent>
    <SidebarFooter className="gap-1 border-t border-sidebar-border px-2.5 py-3">
      <EstadoSaude />
      <SidebarMenu className="gap-1">
        {urlDaDocumentacao ? <SidebarMenuItem>
          <SidebarMenuButton aria-label="Documentação (abre em nova aba)" tooltip="Documentação (abre em nova aba)" className="h-10 px-3 text-xs text-muted-foreground" render={<a href={urlDaDocumentacao} target="_blank" rel="noopener noreferrer" />}>
            <BookOpen aria-hidden /><span className="flex flex-1 items-center justify-between gap-2 group-data-[collapsible=icon]:hidden">Documentação<ExternalLink aria-hidden className="size-3" /></span>
          </SidebarMenuButton>
        </SidebarMenuItem> : null}
        <SidebarMenuItem><SeletorTema /></SidebarMenuItem>
      </SidebarMenu>
      {usuario ? <SessaoNoRodape usuario={usuario} papel={papel} /> : null}
    </SidebarFooter>
  </Sidebar>;
}
