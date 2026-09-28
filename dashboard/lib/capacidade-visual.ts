export type SinaisDoDispositivo = {
  largura: number;
  movimentoReduzido: boolean;
  economizarDados: boolean;
  memoriaGb?: number;
  nucleos?: number;
};

/**
 * WebGL e um aprimoramento da vitrine, nunca um requisito para entender o
 * produto. Mantemos a experiencia completa apenas quando a tela e o aparelho
 * oferecem margem suficiente para sustentar uma animacao continua.
 */
export function permiteCena3D(sinais: SinaisDoDispositivo): boolean {
  if (sinais.movimentoReduzido || sinais.economizarDados) return false;
  if (sinais.largura < 768) return false;
  if (sinais.memoriaGb !== undefined && sinais.memoriaGb <= 4) return false;
  if (sinais.nucleos !== undefined && sinais.nucleos <= 4) return false;
  return true;
}

export function permiteParticulas(sinais: SinaisDoDispositivo): boolean {
  if (sinais.movimentoReduzido || sinais.economizarDados) return false;
  if (sinais.memoriaGb !== undefined && sinais.memoriaGb <= 2) return false;
  if (sinais.nucleos !== undefined && sinais.nucleos <= 2) return false;
  return sinais.largura >= 768;
}
