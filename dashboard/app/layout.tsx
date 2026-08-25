import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import { Atelier } from "@/components/shell/Atelier";
import { AvisoApiFora } from "@/components/shell/AvisoApiFora";
import { Movimento } from "@/components/shell/Movimento";
import { NavegacaoLateral } from "@/components/shell/NavegacaoLateral";
import { SaudeProvider } from "@/components/shell/SaudeProvider";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ProvedorDaMentira } from "@/lib/mentira";
import { SCRIPT_ANTI_PISCADA } from "@/lib/tema";

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
 * `className="dark"` no `<html>` e fixo, e continua fixo: os DOIS temas do
 * Fraus sao escuros, entao o `dark` do chassi vale para os dois e nao ha
 * modo claro a alternar.
 *
 * O que MUDOU, e este comentario dizia o contrario ate 24/08/2026: existe
 * alternador. Ele nao troca `dark` por `light` -- poe (ou tira) a classe
 * `.tema-chuva` no mesmo `<html>`, e o tema sobrepoe so o chassi. O argumento
 * antigo ("um contrato de contraste verificado por calculo vale para uma
 * paleta") nao caiu: `scripts/contraste.mjs` passou a ser CIENTE DE TEMA e
 * roda a matriz inteira por tema, entao as duas paletas sao verificadas, nao
 * uma. Ver DESIGN.md, seccao 8.
 */
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // `suppressHydrationWarning` no `<html>`: o script abaixo pode adicionar a
    // classe do tema antes da hidratacao, e o React acusaria a diferenca entre
    // o HTML que o servidor mandou e o que encontrou no DOM. A divergencia e
    // intencional e e o ponto do script.
    <html lang="pt-BR" className="dark" suppressHydrationWarning>
      <head>
        {/* ANTES DE TUDO. Ver SCRIPT_ANTI_PISCADA em lib/tema.ts: sem isto,
            quem escolheu "chuva de neon" ve a tela pintar em grafite e trocar
            depois da hidratacao, a cada navegacao. */}
        <script
          dangerouslySetInnerHTML={{ __html: SCRIPT_ANTI_PISCADA }}
        />
      </head>
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
        <Movimento>
          <TooltipProvider>
            <SaudeProvider>
              {/* O easter egg da marca liga a mentira na NAVEGACAO e ela e
                  exibida pelos INDICADORES, noutra sub-arvore -- o provedor
                  precisa ficar acima das duas, e este e o ponto onde elas se
                  encontram. Fora do painel o valor e sempre `false`, e nenhum
                  indicador sabe mentir por conta propria. Ver lib/mentira.tsx. */}
              <ProvedorDaMentira>
              <SidebarProvider>
                {/* A navegacao le `useSearchParams` para carregar o periodo
                    entre as secoes, e isso exige limite de Suspense no App
                    Router. */}
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
              </ProvedorDaMentira>
            </SaudeProvider>
          </TooltipProvider>
        </Movimento>
      </body>
    </html>
  );
}
