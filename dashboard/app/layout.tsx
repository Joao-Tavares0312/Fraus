import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Dolos — satisfação em atendimentos por chatbot",
  description:
    "Painel de satisfação inferida a partir do texto, dos emojis e do tempo de resposta dos atendimentos.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className="h-full">
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
