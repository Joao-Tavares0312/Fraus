import { type FC, type CSSProperties } from 'react';

interface GlitchTextProps {
  children: string;
  speed?: number;
  enableShadows?: boolean;
  enableOnHover?: boolean;
  /** Cor da camada deslocada para a esquerda. Ver a nota de adaptacao abaixo. */
  corAntes?: string;
  /** Cor da camada deslocada para a direita. */
  corDepois?: string;
  className?: string;
}

interface CustomCSSProperties extends CSSProperties {
  '--after-duration': string;
  '--before-duration': string;
  '--after-shadow': string;
  '--before-shadow': string;
}

/**
 * ADAPTADO AO SISTEMA DE COR DO FRAUS (01/09/2026). O componente do registry
 * chega com quatro valores cravados que nao sobrevivem a este projeto:
 *
 *   - `bg-[#120F17]` nas duas pseudo-camadas. Elas PRECISAM ter a cor do fundo
 *     atras do texto, senao o glitch le como dois retangulos coloridos
 *     piscando em volta da frase em vez de como o proprio texto se descolando.
 *     Virou `bg-background`, que e o token -- e assim o efeito acompanha a
 *     troca de tema sozinho;
 *   - `text-white` (tres vezes). Virou `text-current`, para a frase herdar a
 *     cor de quem a usa. E o que permite aplicar o glitch numa frase ambar
 *     (`--dito-texto`) sem que as camadas de cima voltem a ser brancas;
 *   - o par de sombras `red`/`cyan`, que ficou como PADRAO da prop
 *     `enableShadows` mas agora aceita cores por prop (`corAntes`/`corDepois`).
 *     Vermelho e ciano puros sao a aberracao cromatica canonica do efeito, e
 *     tambem sao duas cores que este projeto reserva: vermelho e erro
 *     (`--destructive`) e nenhum dos dois pertence a camada de vitrine.
 *
 * O resto do arquivo e o do registry. Reinstalar por cima com
 * `shadcn add @react-bits/GlitchText-TS-TW` desfaz estas quatro trocas.
 */
const GlitchText: FC<GlitchTextProps> = ({
  children,
  speed = 0.5,
  enableShadows = true,
  enableOnHover = false,
  corAntes = 'oklch(0.86 0.19 200)',
  corDepois = 'oklch(0.75 0.21 10)',
  className = ''
}) => {
  const inlineStyles: CustomCSSProperties = {
    '--after-duration': `${speed * 3}s`,
    '--before-duration': `${speed * 2}s`,
    '--after-shadow': enableShadows ? `-5px 0 ${corDepois}` : 'none',
    '--before-shadow': enableShadows ? `5px 0 ${corAntes}` : 'none'
  };

  const baseClasses = 'relative select-none';

  const pseudoClasses = !enableOnHover
    ? 'after:content-[attr(data-text)] after:absolute after:top-0 after:left-[10px] after:text-current after:bg-background after:overflow-hidden after:[clip-path:inset(0_0_0_0)] after:[text-shadow:var(--after-shadow)] after:animate-glitch-after ' +
      'before:content-[attr(data-text)] before:absolute before:top-0 before:left-[-10px] before:text-current before:bg-background before:overflow-hidden before:[clip-path:inset(0_0_0_0)] before:[text-shadow:var(--before-shadow)] before:animate-glitch-before'
    : "after:content-[''] after:absolute after:top-0 after:left-[10px] after:text-current after:bg-background after:overflow-hidden after:[clip-path:inset(0_0_0_0)] after:opacity-0 " +
      "before:content-[''] before:absolute before:top-0 before:left-[-10px] before:text-current before:bg-background before:overflow-hidden before:[clip-path:inset(0_0_0_0)] before:opacity-0 " +
      'hover:after:content-[attr(data-text)] hover:after:opacity-100 hover:after:[text-shadow:var(--after-shadow)] hover:after:animate-glitch-after ' +
      'hover:before:content-[attr(data-text)] hover:before:opacity-100 hover:before:[text-shadow:var(--before-shadow)] hover:before:animate-glitch-before';

  const combinedClasses = `${baseClasses} ${pseudoClasses} ${className}`;

  return (
    <div style={inlineStyles} data-text={children} className={combinedClasses}>
      {children}
    </div>
  );
};

export default GlitchText;

// tailwind.config.js
// module.exports = {
//   theme: {
//     extend: {
//       keyframes: {
//         glitch: {
//           "0%": { "clip-path": "inset(20% 0 50% 0)" },
//           "5%": { "clip-path": "inset(10% 0 60% 0)" },
//           "10%": { "clip-path": "inset(15% 0 55% 0)" },
//           "15%": { "clip-path": "inset(25% 0 35% 0)" },
//           "20%": { "clip-path": "inset(30% 0 40% 0)" },
//           "25%": { "clip-path": "inset(40% 0 20% 0)" },
//           "30%": { "clip-path": "inset(10% 0 60% 0)" },
//           "35%": { "clip-path": "inset(15% 0 55% 0)" },
//           "40%": { "clip-path": "inset(25% 0 35% 0)" },
//           "45%": { "clip-path": "inset(30% 0 40% 0)" },
//           "50%": { "clip-path": "inset(20% 0 50% 0)" },
//           "55%": { "clip-path": "inset(10% 0 60% 0)" },
//           "60%": { "clip-path": "inset(15% 0 55% 0)" },
//           "65%": { "clip-path": "inset(25% 0 35% 0)" },
//           "70%": { "clip-path": "inset(30% 0 40% 0)" },
//           "75%": { "clip-path": "inset(40% 0 20% 0)" },
//           "80%": { "clip-path": "inset(20% 0 50% 0)" },
//           "85%": { "clip-path": "inset(10% 0 60% 0)" },
//           "90%": { "clip-path": "inset(15% 0 55% 0)" },
//           "95%": { "clip-path": "inset(25% 0 35% 0)" },
//           "100%": { "clip-path": "inset(30% 0 40% 0)" },
//         },
//       },
//       animation: {
//         "glitch-after": "glitch var(--after-duration) infinite linear alternate-reverse",
//         "glitch-before": "glitch var(--before-duration) infinite linear alternate-reverse",
//       },
//     },
//   },
//   plugins: [],
// };
