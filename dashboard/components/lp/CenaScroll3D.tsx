"use client";

import { Canvas, useFrame, useLoader, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import {
  motion,
  type MotionValue,
  useMotionValueEvent,
  useInView,
  useReducedMotion,
  useScroll,
  useTransform,
} from "motion/react";
import * as THREE from "three";
import { RGBELoader } from "three/examples/jsm/loaders/RGBELoader.js";
import { Constelacao } from "@/components/lp/Constelacao";

const CORES = ["#e8bd68", "#e1905b", "#73c6f1", "#8ea8ff", "#a18cff", "#df79bc", "#81d0ba"];
const NOMES = ["texto", "emoji", "tempo", "emoção", "léxico", "ironia", "estilo"];

function IluminacaoAmbiente() {
  const textura = useLoader(RGBELoader, "/assets/hdri/studio_small_06_1k.hdr");
  const ambiente = useMemo(() => {
    const copia = textura.clone();
    copia.mapping = THREE.EquirectangularReflectionMapping;
    copia.needsUpdate = true;
    return copia;
  }, [textura]);

  useEffect(() => () => ambiente.dispose(), [ambiente]);

  return <primitive object={ambiente} attach="environment" />;
}

function limitar(valor: number) {
  return Math.max(0, Math.min(1, valor));
}

function criarTexturaMineral() {
  const tamanho = 128;
  const dados = new Uint8Array(tamanho * tamanho * 4);

  for (let y = 0; y < tamanho; y += 1) {
    for (let x = 0; x < tamanho; x += 1) {
      const indice = (y * tamanho + x) * 4;
      const ondas = Math.sin(x * 0.31 + Math.sin(y * 0.12) * 3.2);
      const veios = Math.sin((x + y) * 0.13) * Math.cos((x - y) * 0.08);
      const ruido = ((x * 17 + y * 29 + x * y * 3) % 37) / 37;
      const relevo = limitar(0.5 + ondas * 0.18 + veios * 0.2 + ruido * 0.12);
      const valor = Math.round(relevo * 255);
      dados[indice] = valor;
      dados[indice + 1] = valor;
      dados[indice + 2] = valor;
      dados[indice + 3] = 255;
    }
  }

  const textura = new THREE.DataTexture(dados, tamanho, tamanho, THREE.RGBAFormat);
  textura.wrapS = THREE.RepeatWrapping;
  textura.wrapT = THREE.RepeatWrapping;
  textura.repeat.set(2.4, 1.7);
  textura.colorSpace = THREE.NoColorSpace;
  textura.needsUpdate = true;
  return textura;
}

function CampoProfundo() {
  const posicoes = useMemo(() => {
    const dados = new Float32Array(180 * 3);
    for (let indice = 0; indice < 180; indice += 1) {
      const angulo = indice * 2.399963;
      const raio = 4.2 + ((indice * 47) % 100) / 17;
      dados[indice * 3] = Math.cos(angulo) * raio;
      dados[indice * 3 + 1] = Math.sin(angulo) * raio * 0.62;
      dados[indice * 3 + 2] = -2.2 - ((indice * 31) % 100) / 24;
    }
    return dados;
  }, []);

  return <points>
    <bufferGeometry><bufferAttribute attach="attributes-position" args={[posicoes, 3]} /></bufferGeometry>
    <pointsMaterial color="#b8d8ff" size={0.025} transparent opacity={0.42} sizeAttenuation />
  </points>;
}

function Instrumento({ progresso }: { progresso: MotionValue<number> }) {
  const nucleo = useRef<THREE.Mesh>(null);
  const armadura = useRef<THREE.Group>(null);
  const anelA = useRef<THREE.Mesh>(null);
  const anelB = useRef<THREE.Mesh>(null);
  const anelC = useRef<THREE.Mesh>(null);
  const trilhas = useRef<THREE.LineSegments>(null);
  const energia = useRef<THREE.Mesh>(null);
  const casca = useRef<THREE.Mesh>(null);
  const particulas = useRef<THREE.Points>(null);
  const materialNucleo = useRef<THREE.MeshPhysicalMaterial>(null);
  const sinais = useRef<Array<THREE.Mesh | null>>([]);
  const alvo = useRef(0);
  const progressoSuave = useRef(0);
  const larguraViewport = useThree((estado) => estado.viewport.width);
  const deslocamentoX = larguraViewport >= 9 ? 1.85 : larguraViewport >= 6 ? 1.05 : 0;
  const texturaMineral = useMemo(() => criarTexturaMineral(), []);
  const posicoesParticulas = useMemo(() => new Float32Array(210 * 3), []);

  useEffect(() => () => texturaMineral.dispose(), [texturaMineral]);

  const atualizar = (valor: number, tempo: number) => {
    const entrada = limitar(valor / 0.36);
    const convergencia = limitar((valor - 0.36) / 0.46);
    const leitura = limitar((valor - 0.8) / 0.2);

    sinais.current.forEach((sinal, indice) => {
      if (!sinal) return;
      const angulo = (indice / sinais.current.length) * Math.PI * 2 - Math.PI / 2;
      const raioInicial = 4.8 + (indice % 2) * 0.65;
      const raioOrbital = THREE.MathUtils.lerp(raioInicial, 3.15, entrada);
      const raio = THREE.MathUtils.lerp(raioOrbital, 0.82, convergencia);
      const dispersaoY = ((indice % 3) - 1) * (1 - entrada) * 1.5;
      sinal.position.set(
        Math.cos(angulo + valor * 1.15 + tempo * 0.08) * raio,
        Math.sin(angulo + tempo * 0.06) * raio * 0.55 + dispersaoY,
        Math.sin(angulo + valor * 1.8 + tempo * 0.12) * (0.62 + convergencia * 0.7),
      );
      const escala = THREE.MathUtils.lerp(0.13, 0.23, entrada) * (1 - convergencia * 0.32);
      sinal.scale.setScalar(escala);

      const atributo = trilhas.current?.geometry.getAttribute("position") as THREE.BufferAttribute | undefined;
      if (atributo) {
        atributo.setXYZ(indice * 2, sinal.position.x, sinal.position.y, sinal.position.z);
        atributo.setXYZ(indice * 2 + 1, 0, 0, 0);
        atributo.needsUpdate = true;
      }
    });

    if (armadura.current) {
      armadura.current.rotation.y = valor * Math.PI * 0.72;
      armadura.current.rotation.x = THREE.MathUtils.lerp(-0.18, 0.18, valor);
    }
    if (nucleo.current) {
      nucleo.current.rotation.x = valor * Math.PI * 1.1;
      nucleo.current.rotation.y = valor * Math.PI * 1.65;
      nucleo.current.scale.setScalar(THREE.MathUtils.lerp(0.62, 1.08, convergencia) + leitura * 0.18);
    }
    if (casca.current) {
      casca.current.rotation.x = -valor * Math.PI * 1.45;
      casca.current.rotation.z = valor * Math.PI * 2.1;
      casca.current.scale.setScalar(1.42 + Math.sin(valor * Math.PI * 8) * 0.055 + leitura * 0.18);
    }
    if (anelA.current) anelA.current.rotation.z = valor * Math.PI * 1.5;
    if (anelB.current) anelB.current.rotation.x = Math.PI / 2 + valor * Math.PI;
    if (anelC.current) anelC.current.rotation.y = valor * Math.PI * -1.25;
    if (energia.current) energia.current.scale.setScalar(0.72 + convergencia * 0.64 + leitura * 0.14);
    if (materialNucleo.current) {
      materialNucleo.current.emissiveIntensity = 0.55 + convergencia * 2.2 + leitura * 1.4;
      materialNucleo.current.transmission = 0.18 + leitura * 0.34;
    }

    const atributoParticulas = particulas.current?.geometry.getAttribute("position") as THREE.BufferAttribute | undefined;
    if (atributoParticulas) {
      for (let indice = 0; indice < 210; indice += 1) {
        const grupo = indice % CORES.length;
        const passo = Math.floor(indice / CORES.length) / 29;
        const anguloBase = (grupo / CORES.length) * Math.PI * 2 - Math.PI / 2;
        const espiral = anguloBase + passo * Math.PI * 2.8 + tempo * (0.08 + grupo * 0.004);
        const origem = 4.8 + (grupo % 2) * 0.65;
        const destino = 0.22 + passo * 0.72;
        const mistura = limitar(convergencia * 1.14 - passo * 0.12);
        const raio = THREE.MathUtils.lerp(origem - passo * 1.1, destino, mistura);
        const turbulencia = Math.sin(tempo * 1.4 + indice * 1.71) * 0.055 * (0.3 + convergencia);
        atributoParticulas.setXYZ(
          indice,
          Math.cos(espiral) * raio + turbulencia,
          Math.sin(espiral) * raio * 0.5 + Math.sin(indice * 2.13) * 0.16 * (1 - mistura),
          Math.sin(espiral * 1.7 + indice) * (0.34 + mistura * 0.72),
        );
      }
      atributoParticulas.needsUpdate = true;
    }
  };

  useMotionValueEvent(progresso, "change", (valor) => { alvo.current = valor; });
  useFrame((estado, delta) => {
    progressoSuave.current = THREE.MathUtils.damp(progressoSuave.current, alvo.current, 5.2, delta);
    atualizar(progressoSuave.current, estado.clock.elapsedTime);
  });

  return (
    <group ref={armadura} position={[deslocamentoX, 0, 0]}>
      <CampoProfundo />
      <lineSegments ref={trilhas}>
        <bufferGeometry><bufferAttribute attach="attributes-position" args={[new Float32Array(7 * 2 * 3), 3]} /></bufferGeometry>
        <lineBasicMaterial color="#85bcea" transparent opacity={0.34} blending={THREE.AdditiveBlending} />
      </lineSegments>
      <points ref={particulas}>
        <bufferGeometry><bufferAttribute attach="attributes-position" args={[posicoesParticulas, 3]} /></bufferGeometry>
        <pointsMaterial color="#91d7ff" size={0.038} transparent opacity={0.68} sizeAttenuation blending={THREE.AdditiveBlending} depthWrite={false} />
      </points>
      <mesh ref={anelA} rotation={[1.08, 0.2, 0.12]}>
        <torusGeometry args={[3.16, 0.012, 8, 180]} />
        <meshBasicMaterial color="#6b90bd" transparent opacity={0.34} />
      </mesh>
      <mesh ref={anelB} rotation={[Math.PI / 2, 0.18, -0.1]}>
        <torusGeometry args={[2.52, 0.009, 8, 160]} />
        <meshBasicMaterial color="#e8bd68" transparent opacity={0.22} />
      </mesh>
      <mesh ref={anelC} rotation={[0.35, Math.PI / 2, 0.82]}>
        <torusGeometry args={[1.92, 0.007, 8, 140]} />
        <meshBasicMaterial color="#df79bc" transparent opacity={0.2} />
      </mesh>

      {CORES.map((cor, indice) => (
        <mesh
          key={cor}
          ref={(elemento) => { sinais.current[indice] = elemento; }}
          position={[Math.cos(indice) * 4.8, ((indice % 3) - 1) * 1.5, Math.sin(indice)]}
        >
          <icosahedronGeometry args={[1, 1]} />
          <meshPhysicalMaterial color={cor} emissive={cor} emissiveIntensity={1.7} roughness={0.2} metalness={0.34} clearcoat={0.8} clearcoatRoughness={0.16} envMapIntensity={0.55} />
          <mesh scale={2.1}>
            <sphereGeometry args={[0.62, 12, 12]} />
            <meshBasicMaterial color={cor} transparent opacity={0.075} blending={THREE.AdditiveBlending} depthWrite={false} />
          </mesh>
        </mesh>
      ))}

      <mesh ref={energia} scale={0.72}>
        <sphereGeometry args={[1.9, 20, 20]} />
        <meshBasicMaterial color="#68b7ef" transparent opacity={0.032} blending={THREE.AdditiveBlending} depthWrite={false} />
      </mesh>
      <mesh ref={nucleo} scale={0.62}>
        <icosahedronGeometry args={[1.38, 3]} />
        <meshPhysicalMaterial
          ref={materialNucleo}
          color="#4c83b7"
          emissive="#244d78"
          emissiveIntensity={0.72}
          metalness={0.34}
          roughness={0.16}
          transmission={0.28}
          thickness={1.2}
          clearcoat={1}
          clearcoatRoughness={0.12}
          iridescence={0.42}
          iridescenceIOR={1.32}
          envMapIntensity={0.55}
          map={texturaMineral}
          bumpMap={texturaMineral}
          bumpScale={0.14}
        />
      </mesh>
      <mesh ref={casca} scale={1.42}>
        <icosahedronGeometry args={[1.38, 2]} />
        <meshBasicMaterial color="#8dd4ff" transparent opacity={0.16} wireframe blending={THREE.AdditiveBlending} depthWrite={false} />
      </mesh>
    </group>
  );
}

function Etapa({
  progresso,
  indice,
  numero,
  titulo,
  texto,
}: {
  progresso: MotionValue<number>;
  indice: number;
  numero: string;
  titulo: string;
  texto: string;
}) {
  const janelas: number[][] = [
    [0, 0.02, 0.27, 0.315],
    [0.32, 0.365, 0.61, 0.655],
    [0.66, 0.705, 0.96, 1],
  ];
  const janela = janelas[indice];
  const opacidade = useTransform(progresso, janela, indice === 0 ? [1, 1, 1, 0] : indice === 2 ? [0, 1, 1, 1] : [0, 1, 1, 0]);
  const y = useTransform(progresso, [janela[0], janela[1], janela[3]], indice === 0 ? [0, 0, -42] : [48, 0, indice === 2 ? 0 : -42]);
  const desfoque = useTransform(opacidade, [0, 1], ["blur(8px)", "blur(0px)"]);
  const visibilidade = useTransform(progresso, (valor) => {
    if (indice === 0) return valor < 0.32 ? "visible" : "hidden";
    if (indice === 1) return valor >= 0.32 && valor < 0.66 ? "visible" : "hidden";
    return valor >= 0.66 ? "visible" : "hidden";
  });

  return (
    <div className="pointer-events-none absolute inset-0 flex items-center">
      <motion.article style={{ opacity: opacidade, y, filter: desfoque, visibility: visibilidade }} className="w-full rounded-2xl border border-linha/60 bg-background/80 p-6 shadow-[0_24px_80px_oklch(0_0_0/35%)] backdrop-blur-md sm:p-8 lg:border-transparent lg:bg-transparent lg:p-0 lg:shadow-none lg:backdrop-blur-none">
        <p className="font-mono text-xs uppercase tracking-[.18em] text-primary">{numero} / 03</p>
        <h3 className="mt-5 text-4xl font-medium leading-[1.02] tracking-[-.035em] sm:text-5xl">{titulo}</h3>
        <p className="mt-5 max-w-md text-base leading-[1.65] text-muted-foreground sm:text-lg">{texto}</p>
      </motion.article>
    </div>
  );
}

export function CenaScroll3D() {
  const secao = useRef<HTMLElement>(null);
  const reduzirMovimento = useReducedMotion();
  const visivel = useInView(secao, { margin: "35% 0px 35% 0px" });
  const { scrollYProgress } = useScroll({ target: secao, offset: ["start start", "end end"] });

  return (
    <section ref={secao} className="relative h-[320svh] border-y border-linha bg-card/10">
      <div className="sticky top-0 h-svh overflow-hidden">
        <div aria-hidden className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_70%_50%,color-mix(in_oklch,var(--medido)_8%,transparent),transparent_38%)]" />
        <div aria-hidden className="absolute bottom-[8%] right-5 top-[8%] z-20 hidden w-px bg-compasso lg:block">
          <motion.div style={{ scaleY: scrollYProgress }} className="h-full origin-top bg-primary shadow-[0_0_10px_var(--primary)]" />
          <span className="absolute -left-8 top-0 font-mono text-[.6875rem] text-muted-foreground">00</span>
          <span className="absolute -left-8 bottom-0 font-mono text-[.6875rem] text-muted-foreground">100</span>
        </div>
        <div className="absolute inset-0 z-0">
          {!reduzirMovimento && <div aria-hidden className="pointer-events-none absolute inset-[5%] opacity-[.1]"><Constelacao /></div>}
          {reduzirMovimento ? (
            <div className="absolute inset-0 flex items-center justify-center opacity-70"><Constelacao /></div>
          ) : (
            <Canvas
              aria-label="Sete sinais convergindo em um núcleo conforme a rolagem"
              dpr={[1, 1.25]}
              frameloop={visivel ? "always" : "never"}
              camera={{ position: [0, 0, 9.2], fov: 44 }}
              gl={{ alpha: true, antialias: true, powerPreference: "high-performance", toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.08 }}
              fallback={<div className="flex h-full items-center justify-center"><Constelacao /></div>}
            >
              <fog attach="fog" args={["#050912", 8, 18]} />
              <IluminacaoAmbiente />
              <ambientLight intensity={0.26} />
              <pointLight position={[-4, 5, 5]} intensity={15} color="#e8bd68" />
              <pointLight position={[4, -2, 4]} intensity={12} color="#73c6f1" />
              <Instrumento progresso={scrollYProgress} />
            </Canvas>
          )}
          <div aria-hidden className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_68%_50%,transparent_20%,color-mix(in_oklch,var(--background)_48%,transparent)_74%,var(--background)_112%)]" />
        </div>

        <div className="relative z-10 mx-auto flex h-full w-full max-w-[88rem] items-center px-5 sm:px-8 lg:px-12">
          <div className="relative h-[48svh] w-full lg:h-[56svh] lg:w-[34%]">
            <Etapa progresso={scrollYProgress} indice={0} numero="01" titulo="Sinais se apresentam." texto="Texto, emoji, tempo, emoção, léxico, ironia e estilo entram como leituras independentes da mesma conversa." />
            <Etapa progresso={scrollYProgress} indice={1} numero="02" titulo="Evidências convergem." texto="As 39 features se aproximam do núcleo. Nenhuma camada decide sozinha e cada contribuição mantém sua proveniência." />
            <Etapa progresso={scrollYProgress} indice={2} numero="03" titulo="O contexto produz o score." texto="O fusor transforma o conjunto em uma leitura operacional de 0 a 100, acompanhada pelos trechos que sustentam o resultado." />
          </div>
        </div>
        <div className="pointer-events-none absolute inset-x-5 bottom-8 z-10 mx-auto flex max-w-[76rem] justify-between font-mono text-[.6875rem] uppercase tracking-[.16em] text-muted-foreground sm:inset-x-8 lg:inset-x-12">
          <span className="pl-12 sm:pl-0">arraste a rolagem</span><span>{NOMES.length} sinais / 1 fusor</span>
        </div>
      </div>
    </section>
  );
}
