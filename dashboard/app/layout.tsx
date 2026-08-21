import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import { Atelier } from "@/components/shell/Atelier";
import { AvisoApiFora } from "@/components/shell/AvisoApiFora";
import { NavegacaoLateral } from "@/components/shell/NavegacaoLateral";
import { SaudeProvider } from "@/components/shell/SaudeProvider";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";

const DESCRICAO =
  "Painel de satisfação inferida a partir do texto, dos emojis e do tempo de resposta dos atendimentos.";

export const metadata: Metadata = {
  title: "Fraus — satisfação em atendimentos por chatbot",
  description: DESCRICAO,
  // `openGraph` existe para quando o link for compartilhado na apresentacao ou
  // no repositorio: sem ele, o preview sai com o titulo cru e sem imagem.
  openGraph: {
    title: "Fraus — satisfação em atendimentos por chatbot",
    description: DESCRICAO,
    type: "website",
    locale: "pt_BR",
    images: [{ url: "/fraus-logo.png", width: 640, height: 640, alt: "Fraus" }],
  },
};

/**
 * Casca do aplicativo.
 *
 * `className="dark"` no `<html>` e fixo: o Fraus tem TEMA ESCURO UNICO, como o
 * chassi de onde ele vem. Nao existe alternador -- um contrato de contraste
 * verificado por calculo vale para uma paleta, e manter duas dobraria a
 * superficie a verificar sem ganho para quem opera o produto.
 */
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className="dark">
      <body className="min-h-svh antialiased">
        <Atelier />
        {/*
          Atalho para quem navega por teclado: sem ele, chegar ao conteudo
          exige percorrer a navegacao lateral inteira a cada troca de pagina.
          Fica invisivel ate receber foco -- e so aparece para quem precisa.
        */}
        <a
          href="#conteudo"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-sm focus:font-medium focus:text-primary-foreground"
        >
          Pular para o conteúdo
        </a>
        <TooltipProvider>
          <SaudeProvider>
            <SidebarProvider>
            {/* A navegacao le `useSearchParams` para carregar o periodo entre
                as secoes, e isso exige limite de Suspense no App Router. */}
              <Suspense fallback={null}>
                <NavegacaoLateral />
              </Suspense>
              <SidebarInset id="conteudo" className="min-w-0">
                {/* Acima do conteudo, em TODA tela: sem a API todas quebram
                    igual, e a instrucao tem que estar onde o Joao ja esta. */}
                <AvisoApiFora />
                {children}
              </SidebarInset>
            </SidebarProvider>
          </SaudeProvider>
        </TooltipProvider>
      </body>
    </html>
  );
}
