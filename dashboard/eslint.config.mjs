import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

/**
 * OS ARQUIVOS VENDORIZADOS do registry `@react-bits` (ver `components.json`).
 *
 * Eles entram no repositório pelo `shadcn add` e são substituídos por completo
 * a cada reinstalação — não são código autoral do projeto, e o `npm run lint`
 * existe para medir o código que ESTE time escreve. Sem esta exceção, nove
 * erros de estilo de terceiro (um `prefer-const`, dois `no-explicit-any`, um
 * `set-state-in-effect`) derrubavam o portão inteiro e o tornavam inútil: gate
 * que sempre reprova por motivo alheio deixa de ser lido.
 *
 * O QUE ESTA LISTA NÃO É: uma licença para ignorar problema de verdade nesses
 * arquivos. O `set-state-in-effect` do `GlassSurface` é defeito real e foi
 * TRATADO, não silenciado — ele produzia erro de hidratação, e a correção está
 * documentada em `components/lp/FechoVitrine.tsx` (carga com `ssr: false`).
 * A regra do repositório continua sendo: defeito de componente de terceiro se
 * resolve na fronteira de integração, e a fronteira mora em `components/lp/`.
 *
 * As adaptações de cor feitas dentro do `GlitchText` estão marcadas no próprio
 * arquivo e se perdem numa reinstalação — está escrito lá.
 */
const VENDORIZADOS = [
  "components/Particles.tsx",
  "components/GlassSurface.tsx",
  "components/StarBorder.tsx",
  "components/GlitchText.tsx",
  "components/WarpText.tsx",
];

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Ver VENDORIZADOS acima.
    ...VENDORIZADOS,
  ]),
]);

export default eslintConfig;
