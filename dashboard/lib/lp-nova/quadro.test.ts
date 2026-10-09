import { describe, expect, it } from "vitest";
import { BYTES_POR_PARTICULA, aleatorioComSemente, sementeDasParticulas, uniformesDoQuadro } from "./quadro";
import { pesosDasFases } from "./fases";

const base = { aspecto: 1.6, alturaPx: 900, total: 16000, celular: false, progresso: 0.5, humor: 0, cinza: 0, tempo: 1, dt: 1 / 60 };

describe("uniformesDoQuadro", () => {
  it("leva os pesos da coreografia para o shader", () => {
    const u = uniformesDoQuadro(base);
    const p = pesosDasFases(0.5);
    expect(u.destino).toEqual([p.frase, p.disperso, p.enxame, p.orbe]);
    expect(u.leitura).toEqual([p.leitura, p.brilho, p.respira, 0]);
  });
  it("no desktop o campo espalhado mora na metade direita, longe do texto", () => {
    const [cx, , hx] = uniformesDoQuadro(base).campo;
    expect(cx - hx).toBeGreaterThanOrEqual(0);
  });
  it("um centro por familia", () => {
    expect(uniformesDoQuadro(base).centros).toHaveLength(7);
  });
  it("o ganho de alfa cai com mais particulas e nunca passa de 1", () => {
    expect(uniformesDoQuadro({ ...base, total: 120000 }).ponto[2]).toBeCloseTo(0.05);
    expect(uniformesDoQuadro({ ...base, total: 4000 }).ponto[2]).toBe(1);
  });
});

describe("sementeDasParticulas", () => {
  it("aloca 40 bytes por particula e guarda a familia de cada uma", () => {
    const bruto = sementeDasParticulas(70, new Float32Array(140), aleatorioComSemente(1));
    expect(bruto.byteLength).toBe(70 * BYTES_POR_PARTICULA);
    const familias = new Set<number>();
    const u32 = new Uint32Array(bruto);
    for (let i = 0; i < 70; i++) familias.add(u32[(i * BYTES_POR_PARTICULA) / 4 + 6]);
    expect([...familias].sort()).toEqual([0, 1, 2, 3, 4, 5, 6]);
  });
  it("mesma semente, mesmos bytes: o poster e reproduzivel", () => {
    const a = sementeDasParticulas(500, new Float32Array(1000), aleatorioComSemente(7));
    const b = sementeDasParticulas(500, new Float32Array(1000), aleatorioComSemente(7));
    expect(new Uint8Array(a)).toEqual(new Uint8Array(b));
  });
});
