import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // A dashboard vive dentro do repositorio Python do Fraus. Sem fixar a raiz,
  // o Turbopack sobe a arvore procurando lockfile e reclama de um
  // package-lock.json fora do repositorio.
  turbopack: {
    root: path.resolve(process.cwd()),
  },
  // As telas moraram na raiz ate 31/08/2026, quando a raiz virou a pagina
  // publica do produto. Link salvo, favorito e documentacao anterior nao podem
  // quebrar em silencio -- cada rota antiga aponta para a nova casa.
  // `permanent: false` de proposito: 308 fica cacheado no navegador, e um
  // redirect gravado para sempre e o tipo de decisao que nao se desfaz.
  async redirects() {
    const telas = [
      "atendimentos",
      "analisar",
      "modelo",
      "configuracoes",
      "integracoes",
      "grafo",
    ];
    return telas.map((tela) => ({
      source: `/${tela}/:caminho*`,
      destination: `/dashboard/${tela}/:caminho*`,
      permanent: false,
    }));
  },
};

export default nextConfig;
