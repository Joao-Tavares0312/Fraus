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

/**
 * Impede o rodape de OSCILAR entre "no ar" e "aquecendo".
 *
 * Em serverless a API tem varias instancias, cada uma com o proprio motor: a
 * sonda de saude cai numa quente, depois numa fria recem-criada, e o estado
 * pulava de um lado para o outro. Uma instancia fria NAO e uma regressao da
 * API -- quem ja viu o motor pronto mantem "no-ar". So o que e realmente pior
 * (erro do motor, dublê, fora do ar) rebaixa.
 */
export function suavizarSaude(
  anterior: EstadoDeSaude,
  novo: EstadoDeSaude,
): EstadoDeSaude {
  if (anterior === "no-ar" && (novo === "frio" || novo === "aquecendo")) {
    return "no-ar";
  }
  return novo;
}

/** Enquanto a API nao esta pronta, consulta rapido; depois, com calma. */
export function intervaloDeSaudeMs(estado: EstadoDeSaude): number {
  return estado === "no-ar" ? 20_000 : 4_000;
}
