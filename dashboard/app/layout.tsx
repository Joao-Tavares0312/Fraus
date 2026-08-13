import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import { NavegacaoLateral } from "@/components/shell/NavegacaoLateral";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";

export const metadata: Metadata = {
  title: "Fraus — satisfação em atendimentos por chatbot",
  description:
    "Painel de satisfação inferida a partir do texto, dos emojis e do tempo de resposta dos atendimentos.",
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
        <TooltipProvider>
          <SidebarProvider>
            {/* A navegacao le `useSearchParams` para carregar o periodo entre
                as secoes, e isso exige limite de Suspense no App Router. */}
            <Suspense fallback={null}>
              <NavegacaoLateral />
            </Suspense>
            <SidebarInset className="min-w-0">{children}</SidebarInset>
          </SidebarProvider>
        </TooltipProvider>
      </body>
    </html>
  );
}
