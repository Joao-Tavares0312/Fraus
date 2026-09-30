import type { Metadata } from "next";
import { Bricolage_Grotesque, Inter, Martian_Mono } from "next/font/google";
import "./globals.css";
import { Atelier } from "@/components/shell/Atelier";
import { Movimento } from "@/components/shell/Movimento";
import { SCRIPT_ANTI_PISCADA } from "@/lib/tema";

/**
 * As TRES FAMILIAS do Instrumento (spec 2026-09-30). `next/font` baixa os
 * arquivos NO BUILD e os serve do proprio deploy -- nenhuma chamada ao Google
 * em runtime, que e a regra da casa. As variaveis entram no `<html>` e o
 * globals.css as poe na frente de cada pilha, com fallback de sistema.
 *
 *  - Martian Mono: rotulo, nav, telemetria, dado e titulo de tela
 *    (`--fonte-mono`). E o que faz a interface parecer instrumento.
 *  - Inter: a PROSA (`--fonte-sans`) -- transcricao, explicacao, aparato --,
 *    onde mono cansa em texto corrido.
 *  - Bricolage Grotesque: a display da VITRINE e so dela (`--fonte-display`,
 *    `.display-vitrine` e `.titulo-vitrine`). DESIGN.md §4: fonte de display
 *    em rotulo e dado continua proibida; `lib/tipografia.test.ts` barra o
 *    vazamento pelo CSS. Ela substituiu a Mona Sans em 30/09/2026.
 */
const inter = Inter({
  subsets: ["latin", "latin-ext"],
  variable: "--fonte-inter",
  display: "swap",
});
const martian = Martian_Mono({
  subsets: ["latin", "latin-ext"],
  variable: "--fonte-martian",
  display: "swap",
});
const bricolage = Bricolage_Grotesque({
  subsets: ["latin", "latin-ext"],
  variable: "--fonte-bricolage",
  display: "swap",
});

const DESCRICAO =
  "Painel de satisfação inferida a partir do texto, dos emojis e do tempo de resposta dos atendimentos.";

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000",
  ),
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
 * Casca COMUM: html, tema e ateliê. O shell da ferramenta (sidebar, saúde,
 * provedores) desceu para `app/dashboard/layout.tsx` em 31/08/2026, quando a
 * raiz virou a página pública do produto — a LP não tem navegação lateral, e
 * um visitante sem sessão não precisa carregar os provedores da dashboard.
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
    <html
      lang="pt-BR"
      className={`dark ${inter.variable} ${martian.variable} ${bricolage.variable}`}
      suppressHydrationWarning
    >
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
        <Movimento>{children}</Movimento>
      </body>
    </html>
  );
}
