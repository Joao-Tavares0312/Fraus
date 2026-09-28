import type { Resultado } from "./api";

export type EstadoDeSaude =
  | "verificando"
  | "frio"
  | "aquecendo"
  | "no-ar"
  | "erro-motor"
  | "duble"
  | "fora-do-ar";

type Saude = {
  status: string;
  motor?: "real" | "duble";
  estado_motor?: "frio" | "carregando" | "pronto" | "erro";
};

/** Traduz o contrato da API para os estados visuais sem confundir frio com carga. */
export function classificarSaude(resultado: Resultado<Saude>): EstadoDeSaude {
  if (!resultado.ok) return "fora-do-ar";
  if (resultado.dado?.motor !== "real") return "duble";
  if (resultado.dado.estado_motor === "erro") return "erro-motor";
  if (resultado.dado.estado_motor === "frio") return "frio";
  if (resultado.dado.estado_motor === "carregando") return "aquecendo";
  // `estado_motor` ausente preserva compatibilidade com uma API anterior.
  return "no-ar";
}
