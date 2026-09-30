import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { MolduraDeConta } from "@/components/auth/MolduraDeConta";
import { AceitarConvite } from "@/components/operacao/Convites";
import { sessaoAtual } from "@/lib/sessao";
import { tokenDeConvite } from "@/lib/destino-auth";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Convite de equipe — Fraus", robots: { index: false, follow: false }, referrer: "no-referrer" };

export default async function PaginaConvite({ params }: { params: Promise<{ token: string }> }) {
  const token = tokenDeConvite((await params).token);
  if (!token) notFound();
  const sessao = await sessaoAtual();
  return <MolduraDeConta titulo="Convite de equipe"><AceitarConvite token={token} logado={sessao.estado === "logada"} nome={sessao.estado === "logada" ? sessao.usuario.nome : null} /></MolduraDeConta>;
}
