import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { TemaDaRota } from "@/components/shell/TemaDaRota";
import { SCRIPT_PRELOADER } from "@/lib/lp-nova/coreografia";
import { SCRIPT_ANTI_PISCADA } from "@/lib/tema";

/** Chakra Petch local: nenhuma busca de fonte no build nem em runtime. */
const quadrada = localFont({
  src: [
    { path: "../public/identidade/chakra-petch-400.woff2", weight: "400", style: "normal" },
    { path: "../public/identidade/chakra-petch-500.woff2", weight: "500", style: "normal" },
    { path: "../public/identidade/chakra-petch-600.woff2", weight: "600", style: "normal" },
  ],
  variable: "--fonte-quadrada",
  display: "swap",
  fallback: ["system-ui", "sans-serif"],
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
    // 1200x630, o formato que os cartoes de link esperam. Gerada por
    // `docs/assets/fonte/gerar-assets-instrumento.mjs` (proveniencia em
    // `public/PROVENIENCIA.md`); o monograma quadrado de 640px que estava aqui
    // era cortado pelos cartoes de preview.
    images: [
      {
        url: "/og-fraus.png",
        width: 1200,
        height: 630,
        alt: "Fraus — leia o que ficou nas entrelinhas",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Fraus — satisfação em atendimentos por chatbot",
    description: DESCRICAO,
    images: ["/og-fraus.png"],
  },
  // Os icones (app/icon.svg, app/apple-icon.png, app/favicon.ico) entram por
  // convencao de arquivo do Next -- nao ha `icons` aqui de proposito, ou o
  // `<head>` sairia com cada um declarado duas vezes.
};

/** O tema da rota sincroniza tambem a cor da barra do navegador. */
export const viewport: Viewport = {
  themeColor: "#171819",
  colorScheme: "dark light",
};

/** LP e acesso em grafite; a ferramenta respeita a preferencia claro/escuro. */
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // O script de tema pode alterar a classe antes da hidratacao.
    <html
      lang="pt-BR"
      className={`dark ${quadrada.variable}`}
      suppressHydrationWarning
    >
      <head>
        {/* A preferencia da ferramenta e aplicada antes da primeira pintura. */}
        <script
          dangerouslySetInnerHTML={{ __html: SCRIPT_ANTI_PISCADA }}
        />
        {/* A LP pula o preloader para quem ja o viu nesta sessao. */}
        <script dangerouslySetInnerHTML={{ __html: SCRIPT_PRELOADER }} />
      </head>
      <body className="min-h-svh antialiased">
        <TemaDaRota />
        {children}
      </body>
    </html>
  );
}
