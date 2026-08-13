import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // A dashboard vive dentro do repositorio Python do Dolos. Sem fixar a raiz,
  // o Turbopack sobe a arvore procurando lockfile e reclama de um
  // package-lock.json fora do repositorio.
  turbopack: {
    root: path.resolve(process.cwd()),
  },
};

export default nextConfig;
