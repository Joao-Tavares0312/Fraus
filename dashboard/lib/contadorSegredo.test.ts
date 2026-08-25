import { describe, expect, it } from "vitest";
import {
  CLIQUES_PARA_ABRIR,
  CONTADOR_ZERADO,
  JANELA_MS,
  abriu,
  registrarClique,
} from "./contadorSegredo";

/** Aplica uma sequencia de instantes (ms) sobre o contador zerado. */
function sequencia(instantes: number[]) {
  return instantes.reduce(registrarClique, CONTADOR_ZERADO);
}

describe("contadorSegredo", () => {
  it("o primeiro clique conta um", () => {
    expect(registrarClique(CONTADOR_ZERADO, 1000).cliques).toBe(1);
  });

  it("cinco cliques dentro da janela abrem", () => {
    const estado = sequencia([0, 300, 600, 900, 1200]);
    expect(estado.cliques).toBe(CLIQUES_PARA_ABRIR);
    expect(abriu(estado)).toBe(true);
  });

  it("quatro cliques nao abrem", () => {
    expect(abriu(sequencia([0, 300, 600, 900]))).toBe(false);
  });

  it("silencio maior que a janela zera: o quinto clique vira o primeiro", () => {
    const estado = sequencia([0, 300, 600, 900, 900 + JANELA_MS + 500]);
    expect(estado.cliques).toBe(1);
    expect(abriu(estado)).toBe(false);
  });

  it("a janela conta do ULTIMO clique, nao do primeiro", () => {
    // Cinco cliques espacados de 1,5s: o total (6s) passa da janela, mas
    // nenhum intervalo passa. Tem que abrir.
    const estado = sequencia([0, 1500, 3000, 4500, 6000]);
    expect(abriu(estado)).toBe(true);
  });

  it("depois de abrir, o proximo clique recomeca do um", () => {
    const aberto = sequencia([0, 300, 600, 900, 1200]);
    expect(registrarClique(aberto, 1400).cliques).toBe(1);
  });
});

describe("os instantes da sequencia", () => {
  it("guarda um instante por clique, sem repetir", () => {
    // REGRESSAO: a primeira versao chamava setInstantes dentro do updater do
    // setContador. Updater tem que ser puro, o React invoca mais de uma vez, e
    // o painel mostrava OITO latencias para cinco cliques -- metade `0 ms`.
    const estado = sequencia([0, 300, 600, 900, 1200]);
    expect(estado.instantes).toEqual([0, 300, 600, 900, 1200]);
  });

  it("registrar o mesmo clique duas vezes nao e possivel a partir do mesmo estado", () => {
    // A pureza e o que garante isso: aplicar duas vezes o MESMO estado de
    // entrada devolve o MESMO resultado, nunca um acumulo.
    const um = registrarClique(CONTADOR_ZERADO, 500);
    const outra = registrarClique(CONTADOR_ZERADO, 500);
    expect(um.instantes).toEqual(outra.instantes);
    expect(um.instantes).toHaveLength(1);
  });

  it("recomecar descarta os instantes da sequencia anterior", () => {
    const expirado = sequencia([0, 300, 600, 900, 900 + JANELA_MS + 500]);
    expect(expirado.instantes).toEqual([900 + JANELA_MS + 500]);
  });

  it("depois de abrir, a sequencia seguinte comeca limpa", () => {
    const aberto = sequencia([0, 300, 600, 900, 1200]);
    expect(registrarClique(aberto, 1400).instantes).toEqual([1400]);
  });
});
