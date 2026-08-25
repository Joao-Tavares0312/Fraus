import { describe, expect, it } from "vitest";
import { lerCliques, LIMIAR_DE_HESITACAO, PISO_SEM_PENA } from "./pontuarCliques";

describe("lerCliques", () => {
  it("menos de dois cliques nao tem latencia nenhuma para ler", () => {
    expect(lerCliques([])).toBeNull();
    expect(lerCliques([1000])).toBeNull();
  });

  it("extrai as latencias entre cliques consecutivos", () => {
    const leitura = lerCliques([0, 340, 530, 1730, 2140]);
    expect(leitura?.latenciasMs).toEqual([340, 190, 1200, 410]);
  });

  it("a mediana e o meio das latencias ordenadas", () => {
    // [340, 190, 1200, 410] ordenado = [190, 340, 410, 1200] -> (340+410)/2
    expect(lerCliques([0, 340, 530, 1730, 2140])?.medianaMs).toBe(375);
  });

  it("clique muito acima da mediana e HESITACAO, e ela e localizada", () => {
    const leitura = lerCliques([0, 340, 530, 1730, 2140]);
    // 1200 > 375 * LIMIAR_DE_HESITACAO
    expect(leitura?.hesitou).toBe(true);
    // O terceiro intervalo (indice 2) e o longo.
    expect(leitura?.indiceDaHesitacao).toBe(2);
  });

  it("ritmo regular nao acusa hesitacao", () => {
    const leitura = lerCliques([0, 300, 600, 900, 1200]);
    expect(leitura?.hesitou).toBe(false);
    expect(leitura?.indiceDaHesitacao).toBeNull();
  });

  it("clicar rapido e sem hesitar da a leitura cheia", () => {
    const leitura = lerCliques([0, 200, 400, 600, 800]);
    expect(leitura?.leitura).toBe(100);
  });

  it("a leitura cai com a lentidao e com a hesitacao", () => {
    // mediana 375 -> (375-250)/25 = 5 de pena; hesitou -> 20. 100-25 = 75.
    expect(lerCliques([0, 340, 530, 1730, 2140])?.leitura).toBe(75);
  });

  it("a leitura nunca escapa de 0..100", () => {
    const arrastado = lerCliques([0, 60_000, 120_000, 180_000, 240_000]);
    expect(arrastado?.leitura).toBeGreaterThanOrEqual(0);
    expect(arrastado?.leitura).toBeLessThanOrEqual(100);
  });

  it("latencia no piso nao cobra pena nenhuma", () => {
    const leitura = lerCliques([0, PISO_SEM_PENA, PISO_SEM_PENA * 2, PISO_SEM_PENA * 3]);
    expect(leitura?.leitura).toBe(100);
  });

  it("NAO devolve nota nem categoria de NPS", () => {
    // Invariante 3: derivar nota/categoria no cliente ja causou divergencia de
    // arredondamento nas fronteiras 6/7 e 8/9. Este modulo nao repete isso --
    // a leitura 0-100 nao e a escada do NPS e nao vira uma.
    const leitura = lerCliques([0, 300, 600, 900, 1200]);
    expect(leitura).not.toHaveProperty("nota");
    expect(leitura).not.toHaveProperty("categoria");
  });

  it("o limiar de hesitacao e o documentado", () => {
    expect(LIMIAR_DE_HESITACAO).toBe(2.5);
  });
});
