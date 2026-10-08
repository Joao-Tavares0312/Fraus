import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { AnotarIronia } from "@/components/anotacao/AnotarIronia";
import { tokenDeAnotador } from "@/lib/anotacao";

export const dynamic = "force-dynamic";
// Pagina publica por construcao (fora de app/dashboard/): quem anota nao tem
// conta. O token vai na URL, entao nada de indexar e nada de Referer.
export const metadata: Metadata = { title: "Anotação de ironia — Fraus", robots: { index: false, follow: false }, referrer: "no-referrer" };

export default async function PaginaAnotar({ params }: { params: Promise<{ token: string }> }) {
  const token = tokenDeAnotador((await params).token);
  if (!token) notFound();
  return <AnotarIronia token={token} />;
}
