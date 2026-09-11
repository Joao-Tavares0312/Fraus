"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import {
  Activity,
  BarChart3,
  BookOpen,
  ExternalLink,
  LogOut,
  MessagesSquare,
  PlugZap,
  ScanText,
  Share2,
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
import { MarcaFraus } from "./MarcaFraus";
import { SeletorTema } from "./SeletorTema";

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
  { href: "/dashboard", rotulo: "Visão geral", Icone: BarChart3 },
  { href: "/dashboard/atendimentos", rotulo: "Atendimentos", Icone: MessagesSquare },
  // Fica no grupo de OLHAR, e nao no de mexer, porque analisar nao grava nada:
  // nem conversa, nem nota, nem arquivo. Nenhum indicador se move por causa
  // dela, e e por isso que ela nao pertence ao lado das telas que alteram
  // configuracao e fonte de dado.
  { href: "/dashboard/analisar", rotulo: "Analisar", Icone: ScanText },
  { href: "/dashboard/modelo", rotulo: "Modelo", Icone: Activity },
  // Tambem fica em OLHAR, nao em AJUSTES: o grafo mostra o que o sistema
  // guarda, e nao grava nada -- nenhuma configuracao ou fonte muda por causa
  // dele.
  { href: "/dashboard/grafo", rotulo: "Grafo", Icone: Share2 },
] as const;

// O que o papel `usuario` VE: visao geral e atendimentos -- decisao de
// produto de 31/08/2026 (dev administra, usuario analisa). Esconder aqui e
// cortesia de interface; quem nega mesmo e o middleware da API, com 403.
const SECOES_DO_USUARIO = new Set(["/dashboard", "/dashboard/atendimentos"]);

/**
 * As telas de MEXER, separadas das de olhar por um grupo proprio: elas mudam o
 * comportamento do sistema, e misturá-las com as tres de leitura esconderia
 * essa diferenca no unico lugar onde ela e obvia de graca.
 */
const AJUSTES = [
  { href: "/dashboard/configuracoes", rotulo: "Configurações", Icone: SlidersHorizontal },
  { href: "/dashboard/integracoes", rotulo: "Integrações", Icone: PlugZap },
] as const;

/**
 * A DOCUMENTACAO -- o unico item do menu que sai do aplicativo.
 *
 * Ela e um site proprio (MkDocs), e nao uma rota do Next, por um motivo
 * concreto: as docstrings do Python sao metade da documentacao deste projeto,
 * e nenhuma ferramenta do mundo JS as le. Trazer tudo para dentro do
 * dashboard significaria reescreve-las a mao em MDX, que apodrece na primeira
 * mudanca de codigo.
 *
 * O que ela NAO faz e parecer outro produto: o site importa os mesmos tokens
 * OKLCH (`docs/assets/fraus.css`), a mesma tipografia e o mesmo monograma.
 *
 * A SAIDA E SINALIZADA, nao disfarcada. O item leva o icone de link externo e
 * abre em aba nova: um item de menu que parece interno e troca o site inteiro
 * quebra o botao "voltar" e faz quem clicou perder o filtro de periodo ativo.
 *
 * O endereco vem do AMBIENTE (`NEXT_PUBLIC_URL_DOCS`) porque muda entre a
 * previa local e o deploy. Sem ele, o item NAO aparece -- item de menu que
 * leva a uma pagina que nao existe e pior que item ausente.
 */
function ItemDaDocumentacao({ url }: { url: string }) {
  return (
    <SidebarMenuItem>
      <SidebarMenuButton
        tooltip="Documentação (abre em nova aba)"
        className="transition-colors duration-150 ease-fluid [&>svg]:text-muted-foreground [&>svg]:transition-colors [&>svg]:duration-150 hover:[&>svg]:text-sidebar-foreground"
        render={
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
          />
        }
      >
        <BookOpen aria-hidden />
        <span className="flex flex-1 items-center justify-between gap-2">
          Documentação
          {/* O icone de saida e `aria-hidden` porque o rotulo acessivel ja
              diz "abre em nova aba" no tooltip do botao -- anunciar duas
              vezes e o mesmo defeito que a CabecaVazada ja pagou. */}
          <ExternalLink aria-hidden className="size-3 shrink-0 opacity-50" />
        </span>
      </SidebarMenuButton>
    </SidebarMenuItem>
  );
}

/**
 * Quem esta logado e a porta de saida. So renderiza com sessao ativa: no modo
 * aberto (sem FRAUS_JWT_SEGREDO na API) nao ha de quem sair, e um botao
 * "Sair" que nao muda nada seria promessa vazia.
 */
function SessaoNoRodape({
  usuario,
  papel,
}: {
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
      // Mesmo se a chamada falhar, ir para a raiz -- e `refresh` para o
      // servidor re-renderizar sem o cookie: sem ele, o cache do roteador
      // ainda mostraria a LP "logada".
      roteador.push("/");
      roteador.refresh();
    }
  }

  return (
    <div className="flex items-center gap-2 rounded-md px-2 py-1.5 group-data-[collapsible=icon]:justify-center">
      <span className="flex min-w-0 flex-col group-data-[collapsible=icon]:hidden">
        <span className="truncate text-xs font-medium">{usuario.nome}</span>
        <span className="truncate text-xs text-muted-foreground">
          {papel === "dev" ? "desenvolvedor" : "analista"}
        </span>
      </span>
      <button
        type="button"
        onClick={sair}
        disabled={saindo}
        aria-label="Sair da conta"
        title="Sair da conta"
        className="ml-auto rounded-md p-1.5 text-muted-foreground transition-colors duration-150 ease-fluid hover:bg-sidebar-accent hover:text-sidebar-foreground focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 group-data-[collapsible=icon]:ml-0"
      >
        <LogOut aria-hidden className="size-4" />
      </button>
    </div>
  );
}

function estaAtiva(href: string, caminho: string): boolean {
  return href === "/dashboard" ? caminho === "/dashboard" : caminho.startsWith(href);
}

export function NavegacaoLateral({
  papel,
  usuario,
}: {
  papel: "dev" | "usuario";
  usuario: { nome: string; email: string } | null;
}) {
  const caminho = usePathname();
  const parametros = useSearchParams();
  // Lido aqui, e nao dentro do item: o GRUPO inteiro depende dele. Um
  // `SidebarGroupLabel` "Referência" sem nenhum item abaixo e a mesma promessa
  // vazia que faz o grupo "Ajustes" sumir para o papel `usuario`.
  //
  // `NEXT_PUBLIC_` e obrigatorio: este componente e de CLIENTE, e variavel sem
  // esse prefixo e `undefined` no navegador -- o item simplesmente nunca
  // apareceria, sem erro nenhum dizendo por que.
  const urlDaDocumentacao = process.env.NEXT_PUBLIC_URL_DOCS;
  const secoes =
    papel === "dev" ? SECOES : SECOES.filter((s) => SECOES_DO_USUARIO.has(s.href));

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
          href={`/dashboard${sufixo}`}
          aria-label="Fraus — voltar para a visão geral"
          className="flex items-center gap-2.5 rounded-md px-1 py-1.5 outline-none transition-colors duration-150 ease-fluid hover:bg-sidebar-accent/50 focus-visible:ring-2 focus-visible:ring-ring"
        >
          {/* O monograma e SVG INLINE, e nao mais `<Image src="/fraus-logo.svg">`.
              Um SVG servido por `<img>` e documento externo: `var(--marca-cor-pe)`
              nao atravessa a fronteira e nao ha como animar uma parte dele.
              Inline, a marca herda o tema (dourada no grafite, magenta na chuva)
              e a fenda pode abrir. Ver `MarcaFraus`. */}
          <MarcaFraus tamanho={28} />
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
            <SidebarMenu>{secoes.map(itemDaSecao)}</SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* A DOCUMENTACAO fica em grupo proprio, e NAO dentro de "Seções":
            aquele grupo e a lista de telas do produto, e um link que sai do
            aplicativo no meio delas leria como mais uma tela. Ela tambem NAO
            entra em "Ajustes", que e o grupo do que MUDA o comportamento do
            sistema -- ler documentacao nao muda nada.

            Ela aparece para os DOIS papeis de proposito: `usuario` analisa e
            precisa saber o que "NPS inferido" significa tanto quanto `dev`. */}
        {urlDaDocumentacao && (
          <SidebarGroup>
            <SidebarGroupLabel>Referência</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <ItemDaDocumentacao url={urlDaDocumentacao} />
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {/* O grupo inteiro some para o papel `usuario`: mostrar o rotulo
            "Ajustes" sem nenhum item seria uma promessa vazia. */}
        {papel === "dev" && (
          <SidebarGroup>
            <SidebarGroupLabel>Ajustes</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>{AJUSTES.map(itemDaSecao)}</SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border">
        {usuario && <SessaoNoRodape usuario={usuario} papel={papel} />}
        <SidebarMenu>
          <SidebarMenuItem>
            <SeletorTema />
          </SidebarMenuItem>
        </SidebarMenu>
        <EstadoSaude />
      </SidebarFooter>
    </Sidebar>
  );
}
