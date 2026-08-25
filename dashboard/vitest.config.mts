/**
 * O runner de teste da dashboard.
 *
 * POR QUE ELE EXISTE, ja que os 350 testes do projeto sao pytest: ate 25/08/2026
 * o front so tinha RENDERIZACAO, e renderizacao o `npm run build` e o
 * `npm run contraste` ja cobriam. `lib/contadorSegredo.ts` e a primeira logica
 * COMPORTAMENTAL daqui -- maquina de estado com janela de tempo, que erra em
 * silencio e nao aparece em build nenhum. Dependencia nova com motivo declarado,
 * como manda o CLAUDE.md.
 *
 * `environment: node` de proposito: o que se testa aqui e funcao pura. Quando
 * alguem precisar montar componente, troque para `jsdom` e adicione a
 * dependencia AI, nao antes.
 */
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["lib/**/*.test.ts"],
  },
});
