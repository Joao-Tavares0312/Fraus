import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { EntrarNoGrupo } from "@/components/anotacao/EntrarNoGrupo";
import { tokenDeAnotador } from "@/lib/anotacao";

export const dynamic = "force-dynamic";
// Publica como /anotar/[token]: o link do grupo tambem e um token na URL, entao
// nada de indexar e nada de Referer. O token do grupo tem o mesmo formato.
export const metadata: Metadata = { title: "Anotação de ironia — Fraus", robots: { index: false, follow: false }, referrer: "no-referrer" };

export default async function PaginaEntrarNoGrupo({ params }: { params: Promise<{ token: string }> }) {
  const token = tokenDeAnotador((await params).token);
  if (!token) notFound();
  return <EntrarNoGrupo token={token} />;
}
