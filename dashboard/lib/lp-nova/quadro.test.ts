import { describe, expect, it } from "vitest";
import { BYTES_POR_PARTICULA, aleatorioComSemente, sementeDasParticulas, uniformesDoQuadro } from "./quadro";
import { pesosDasFases } from "./fases";
import { nosDasFeatures } from "./constelacao";
import { FAMILIAS_DO_VETOR } from "../../components/lp/fatos";

const base = { aspecto: 1.6, alturaPx: 900, total: 16000, celular: false, progresso: 0.5, humor: 0, cinza: 0, tempo: 1, dt: 1 / 60 };

describe("uniformesDoQuadro", () => {
  it("leva os pesos da coreografia para o shader", () => {
    const u = uniformesDoQuadro(base);
    const p = pesosDasFases(0.5);
    expect(u.destino).toEqual([p.frase, p.disperso, p.mascara, p.nos]);
    expect(u.extra[0]).toBe(p.orbe);
    expect(u.leitura).toEqual([p.leitura, p.brilho, p.respira, 0]);
  });
  it("no desktop o campo espalhado mora na metade direita, longe do texto", () => {
    const [cx, , hx] = uniformesDoQuadro(base).campo;
    expect(cx - hx).toBeGreaterThanOrEqual(0);
  });
  it("a mascara tem escala propria, menor no celular", () => {
    expect(uniformesDoQuadro({ ...base, celular: true }).ponto[3]).toBeLessThan(uniformesDoQuadro(base).ponto[3]);
  });
  it("o ganho de alfa cai com mais particulas e nunca passa de 1", () => {
    expect(uniformesDoQuadro({ ...base, total: 120000 }).ponto[2]).toBeCloseTo(0.05);
    expect(uniformesDoQuadro({ ...base, total: 4000 }).ponto[2]).toBe(1);
  });
});

describe("sementeDasParticulas", () => {
  it("cada particula vai para um no da SUA familia", () => {
    const bruto = sementeDasParticulas(390, new Float32Array(780), aleatorioComSemente(5));
    const f32 = new Float32Array(bruto);
    const u32 = new Uint32Array(bruto);
    const nos = nosDasFeatures();
    const ordem = FAMILIAS_DO_VETOR.map((f) => f.chave);
    for (let i = 0; i < 390; i++) {
      const b = (i * BYTES_POR_PARTICULA) / 4;
      const familia = ordem[u32[b + 10]];
      // o no gravado e um dos nos daquela familia (y invertido: a cena e y-para-cima)
      const casa = nos.some((n) => n.familia === familia && Math.abs(n.x - f32[b + 8]) < 1e-6 && Math.abs(-n.y - f32[b + 9]) < 1e-6);
      expect(casa).toBe(true);
    }
  });

  it("aloca 56 bytes por particula e guarda a familia de cada uma", () => {
    const bruto = sementeDasParticulas(70, new Float32Array(140), aleatorioComSemente(1));
    expect(bruto.byteLength).toBe(70 * BYTES_POR_PARTICULA);
    const familias = new Set<number>();
    const u32 = new Uint32Array(bruto);
    for (let i = 0; i < 70; i++) familias.add(u32[(i * BYTES_POR_PARTICULA) / 4 + 10]);
    expect([...familias].sort()).toEqual([0, 1, 2, 3, 4, 5, 6]);
  });
  it("mesma semente, mesmos bytes: o poster e reproduzivel", () => {
    const a = sementeDasParticulas(500, new Float32Array(1000), aleatorioComSemente(7));
    const b = sementeDasParticulas(500, new Float32Array(1000), aleatorioComSemente(7));
    expect(new Uint8Array(a)).toEqual(new Uint8Array(b));
  });
});
