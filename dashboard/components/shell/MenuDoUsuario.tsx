"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useSyncExternalStore } from "react";
import { Menu } from "@base-ui/react/menu";
import { BookOpen, ChevronsUpDown, ExternalLink, LogOut, Moon, Sun } from "lucide-react";
import { aplicarTema, assinarTema, lerTema, temaDoServidor } from "@/lib/tema";
import { telasDaConta } from "@/lib/navegacao";

const ITEM = "flex w-full cursor-default items-center gap-2 rounded-md px-2 py-2 text-sm outline-hidden select-none text-muted-foreground data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground data-[highlighted]:shadow-[inset_2px_0_0_var(--primary)] data-disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0";

/**
 * O menu da conta, no rodapé da lateral (19/10/2026).
 *
 * A lateral ficou com as tarefas do dia a dia; gestão (Operação), integrações,
 * configurações, documentação, tema e sair moram aqui. A permissão continua
 * sendo da API — este menu só esconde o que o papel não alcança.
 */
export function MenuDoUsuario({ usuario, papel, sufixo, aoNavegar }: {
  usuario: { nome: string; email: string } | null;
  papel: "dev" | "usuario";
  /** A consulta de período, preservada como nos destinos da lateral. */
  sufixo: string;
  aoNavegar?: () => void;
}) {
  const roteador = useRouter();
  const [saindo, setSaindo] = useState(false);
  const tema = useSyncExternalStore(assinarTema, lerTema, temaDoServidor);
  const urlDaDocumentacao = process.env.NEXT_PUBLIC_URL_DOCS;
  const nome = usuario?.nome ?? "Instalação local";
  const papelLegivel = papel === "dev" ? "desenvolvedor" : "analista";

  async function sair() {
    setSaindo(true);
    try {
      await fetch("/api/sessao/sair", { method: "POST" });
    } finally {
      roteador.push("/");
      roteador.refresh();
    }
  }

  return (
    <Menu.Root>
      <Menu.Trigger
        aria-label={`Menu da conta de ${nome}`}
        title={usuario?.email ?? nome}
        className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left outline-none hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring data-[popup-open]:bg-sidebar-accent group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0"
      >
        <span aria-hidden className="flex size-8 shrink-0 items-center justify-center rounded-md bg-sidebar-accent text-xs font-semibold uppercase text-sidebar-foreground">
          {nome.trim().charAt(0) || "F"}
        </span>
        <span className="flex min-w-0 flex-1 flex-col group-data-[collapsible=icon]:hidden">
          <span className="truncate text-xs font-medium">{nome}</span>
          <span className="truncate text-xs text-muted-foreground">{papelLegivel}</span>
        </span>
        <ChevronsUpDown aria-hidden className="size-4 shrink-0 text-muted-foreground group-data-[collapsible=icon]:hidden" />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Positioner side="top" align="start" sideOffset={6} className="isolate z-50">
          <Menu.Popup className="min-w-56 origin-(--transform-origin) rounded-md p-1 superficie-flutuante text-popover-foreground duration-100 data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95">
            {usuario ? (
              <div className="px-2 pt-1.5 pb-2">
                <p className="truncate text-sm font-medium">{usuario.nome}</p>
                <p className="truncate text-xs text-muted-foreground">{usuario.email}</p>
              </div>
            ) : null}
            <Menu.Group>
              {telasDaConta(papel).map(({ href, rotulo, icone: Icone }) => (
                <Menu.LinkItem
                  key={href}
                  className={ITEM}
                  closeOnClick
                  render={<Link href={`${href}${sufixo}`} onClick={aoNavegar} />}
                >
                  <Icone aria-hidden />
                  {rotulo}
                </Menu.LinkItem>
              ))}
            </Menu.Group>
            <Menu.Separator className="my-1 h-px bg-border" />
            {urlDaDocumentacao ? (
              <Menu.LinkItem
                className={ITEM}
                href={urlDaDocumentacao}
                target="_blank"
                rel="noopener noreferrer"
              >
                <BookOpen aria-hidden />
                <span className="flex-1">Documentação</span>
                <ExternalLink aria-hidden className="size-3!" />
              </Menu.LinkItem>
            ) : null}
            <Menu.Item
              className={ITEM}
              closeOnClick={false}
              onClick={() => aplicarTema(tema === "escuro" ? "claro" : "escuro")}
            >
              {tema === "escuro" ? <Sun aria-hidden /> : <Moon aria-hidden />}
              {tema === "escuro" ? "Usar tema claro" : "Usar tema escuro"}
            </Menu.Item>
            {usuario ? (
              <>
                <Menu.Separator className="my-1 h-px bg-border" />
                <Menu.Item className={ITEM} disabled={saindo} onClick={sair}>
                  <LogOut aria-hidden />
                  {saindo ? "Saindo…" : "Sair"}
                </Menu.Item>
              </>
            ) : null}
          </Menu.Popup>
        </Menu.Positioner>
      </Menu.Portal>
    </Menu.Root>
  );
}
