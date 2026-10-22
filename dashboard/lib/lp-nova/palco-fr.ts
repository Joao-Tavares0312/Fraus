import { criarVerticesFR } from "./escultura";
import { criarParticulas } from "./coreografia";
import type { PoseFR } from "./coreografia";

/** Estado de um quadro: a pose do FR mais o giro proprio da poeira. */
export type QuadroFR = PoseFR & { giroPoeira: number };

export type PalcoFR = {
  desenhar: (quadro: QuadroFR) => void;
  destruir: () => void;
};

// Camera do mockup: perspectiva 35 graus, olho em z=11, near .1, far 100.
const FOCAL = 1 / Math.tan((35 / 2) * Math.PI / 180);
const PERTO = 0.1, LONGE = 100;
const PROJECAO = `
uniform vec2 u_focal;
vec4 projetar(vec3 p) {
  p.z -= 11.0;
  return vec4(p.x * u_focal.x, p.y * u_focal.y, (p.z * ${(LONGE + PERTO).toFixed(1)} + ${(2 * LONGE * PERTO).toFixed(1)}) / ${(PERTO - LONGE).toFixed(1)}, -p.z);
}`;

const VERTEX_FR = `
attribute vec3 a_posicao;
attribute vec4 a_dados;
uniform mat3 u_rotacao;
uniform vec3 u_posicao;
uniform float u_gap;
varying vec3 v_local;
varying vec2 v_material;
${PROJECAO}
void main() {
  // SVG 400x302 com y para baixo -> cena com y para cima, 3,8 unidades de largura.
  vec3 p = (a_posicao - vec3(200.0, 151.0, 0.0)) * .0095;
  p.y = -p.y;
  p.z += a_dados.x * u_gap;
  gl_Position = projetar(u_rotacao * p + u_posicao);
  v_local = a_posicao;
  v_material = a_dados.zw;
}`;

const FRAGMENT_FR = `
precision mediump float;
uniform float u_inv;
varying vec3 v_local;
varying vec2 v_material;
void main() {
  float tipo = v_material.x;
  vec3 cor;
  if (tipo > 3.5) {
    vec3 escura = vec3(48.0,52.0,53.0);
    vec3 clara = vec3(104.0,108.0,103.0);
    if (tipo > 5.5) { escura=vec3(107.0,82.0,40.0); clara=vec3(185.0,155.0,91.0); }
    else if (tipo > 4.5) { escura=vec3(141.0,141.0,131.0); clara=vec3(216.0,214.0,201.0); }
    cor = mix(escura, clara, clamp((v_local.z + 9.0) / 18.0, 0.0, 1.0)) * v_material.y;
  } else if (tipo > 2.5) {
    cor = vec3(36.0,40.0,41.0);
  } else if (tipo > 1.5) {
    cor = mix(vec3(170.0,134.0,80.0), vec3(226.0,195.0,148.0), 1.0 - v_local.y / 302.0);
  } else {
    float t = tipo > .5
      ? ((v_local.x - 200.0) * .819152 + (v_local.y - 151.0) * .573576) / 500.880752 + .5
      : (v_local.x + v_local.y) / 702.0;
    float meio = tipo > .5 ? .52 : .48;
    vec3 a = tipo > .5 ? vec3(241.0,238.0,229.0) : vec3(90.0,96.0,94.0);
    vec3 b = tipo > .5 ? vec3(217.0,214.0,202.0) : vec3(51.0,56.0,56.0);
    vec3 c = tipo > .5 ? vec3(182.0,180.0,170.0) : vec3(31.0,36.0,37.0);
    cor = t < meio ? mix(a,b,clamp(t/meio,0.0,1.0)) : mix(b,c,clamp((t-meio)/(1.0-meio),0.0,1.0));
  }
  // Fecho: o mundo vira ouro e o FR vira relevo do proprio ouro, um tom abaixo.
  // Grafite puro apagava o titulo escuro escrito por cima dele.
  cor = mix(cor, vec3(150.0,124.0,66.0) + cor * .22, u_inv);
  gl_FragColor = vec4(cor / 255.0, 1.0);
}`;

const VERTEX_POEIRA = `
attribute vec3 a_ponto;
uniform mat3 u_rotacao;
uniform vec3 u_posicao;
uniform float u_tamanho;
${PROJECAO}
void main() {
  vec4 clip = projetar(u_rotacao * a_ponto + u_posicao);
  gl_Position = clip;
  gl_PointSize = u_tamanho / clip.w;
}`;

const FRAGMENT_POEIRA = `
precision mediump float;
uniform float u_opacidade;
void main() {
  // Disco com borda suave: um ponto quadrado grande parece pixel morto.
  float a = u_opacidade * smoothstep(.5, .32, length(gl_PointCoord - .5));
  gl_FragColor = vec4(vec3(.839, .729, .447) * a, a);
}`;

let verticesPreparados: Float32Array | null = null;
let poeiraPreparada: Float32Array | null = null;

/** Euler XYZ (como o three.js), column-major, com escala uniforme. */
function rotacionar(destino: Float32Array, x: number, y: number, z: number, s = 1) {
  const cx = Math.cos(x), sx = Math.sin(x), cy = Math.cos(y), sy = Math.sin(y), cz = Math.cos(z), sz = Math.sin(z);
  destino[0] = cy * cz * s; destino[1] = (cx * sz + sx * sy * cz) * s; destino[2] = (sx * sz - cx * sy * cz) * s;
  destino[3] = -cy * sz * s; destino[4] = (cx * cz - sx * sy * sz) * s; destino[5] = (sx * cz + cx * sy * sz) * s;
  destino[6] = sy * s; destino[7] = -sx * cy * s; destino[8] = cx * cy * s;
}

/** Canvas fixo de tela cheia: dois programas, dois buffers estaticos, dois draws.
 * Nao agenda quadros: quem chama `desenhar` e o ticker do GSAP. */
export function criarPalcoFR(canvas: HTMLCanvasElement): PalcoFR {
  // Em tela densa o proprio DPR suaviza a borda: MSAA 4x num buffer de 2,2 MP
  // a cada quadro e GPU gasta sem diferenca visivel.
  const gl = canvas.getContext("webgl", { alpha: true, antialias: (window.devicePixelRatio || 1) < 1.5, depth: true, stencil: false, premultipliedAlpha: true, preserveDrawingBuffer: false, powerPreference: "low-power", failIfMajorPerformanceCaveat: true });
  canvas.dataset.frBackend = "indisponivel";
  if (!gl) throw new Error("WebGL indisponivel para a arte Fraus.");
  const informacao = gl.getExtension("WEBGL_debug_renderer_info");
  const nomeBackend = String(gl.getParameter(informacao ? informacao.UNMASKED_RENDERER_WEBGL : gl.RENDERER));
  // Alguns Chromium aceitam SwiftShader mesmo com caveat=true: 700 pontos e a
  // malha a cada quadro em CPU custam mais que a arte vale. Fica o WebP.
  if (/swiftshader|llvmpipe|softpipe|swrast|software|basic render driver|\bwarp\b|gdi generic/i.test(nomeBackend)) {
    canvas.dataset.frBackend = "software";
    gl.getExtension("WEBGL_lose_context")?.loseContext();
    throw new Error("Backend WebGL em software; mantendo a arte Fraus pre-renderizada.");
  }
  canvas.dataset.frBackend = "contexto";

  const recursos: { programas: WebGLProgram[]; shaders: WebGLShader[]; buffers: WebGLBuffer[] } = { programas: [], shaders: [], buffers: [] };
  let destruido = false;
  const liberar = () => {
    destruido = true;
    if (gl.isContextLost()) return;
    recursos.buffers.forEach((b) => gl.deleteBuffer(b));
    recursos.programas.forEach((p) => gl.deleteProgram(p));
    recursos.shaders.forEach((s) => gl.deleteShader(s));
  };
  const compilar = (vertex: string, fragment: string) => {
    const programa = gl.createProgram();
    if (!programa) throw new Error("Nao foi possivel alocar a arte Fraus.");
    recursos.programas.push(programa);
    for (const [tipo, fonte] of [[gl.VERTEX_SHADER, vertex], [gl.FRAGMENT_SHADER, fragment]] as const) {
      const shader = gl.createShader(tipo);
      if (!shader) throw new Error("Nao foi possivel criar o shader Fraus.");
      recursos.shaders.push(shader);
      gl.shaderSource(shader, fonte);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader) ?? "Shader Fraus invalido.");
      gl.attachShader(programa, shader);
    }
    gl.linkProgram(programa);
    if (!gl.getProgramParameter(programa, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(programa) ?? "Programa Fraus invalido.");
    return programa;
  };
  const carregar = (dados: Float32Array) => {
    const buffer = gl.createBuffer();
    if (!buffer) throw new Error("Nao foi possivel alocar a arte Fraus.");
    recursos.buffers.push(buffer);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, dados, gl.STATIC_DRAW);
    return buffer;
  };

  try {
    const vertices = verticesPreparados ??= criarVerticesFR();
    const poeira = poeiraPreparada ??= criarParticulas(700);
    const fr = compilar(VERTEX_FR, FRAGMENT_FR);
    const pontos = compilar(VERTEX_POEIRA, FRAGMENT_POEIRA);
    const bufferFR = carregar(vertices);
    const bufferPoeira = carregar(poeira);
    const local = (programa: WebGLProgram, nome: string) => gl.getUniformLocation(programa, nome);
    const u = {
      frRotacao: local(fr, "u_rotacao"), frPosicao: local(fr, "u_posicao"), frGap: local(fr, "u_gap"), frInv: local(fr, "u_inv"), frFocal: local(fr, "u_focal"),
      ptRotacao: local(pontos, "u_rotacao"), ptPosicao: local(pontos, "u_posicao"), ptTamanho: local(pontos, "u_tamanho"), ptOpacidade: local(pontos, "u_opacidade"), ptFocal: local(pontos, "u_focal"),
    };
    const aPosicao = gl.getAttribLocation(fr, "a_posicao");
    const aDados = gl.getAttribLocation(fr, "a_dados");
    const aPonto = gl.getAttribLocation(pontos, "a_ponto");
    gl.clearColor(0, 0, 0, 0);
    gl.depthFunc(gl.LEQUAL);
    // As faces de tras das placas aparecem quando o FR gira: sem culling.
    gl.disable(gl.CULL_FACE);

    const matriz = new Float32Array(9);
    let largura = 0, altura = 0, aspecto = 1;
    let ultimo: QuadroFR | null = null;

    const desenhar = (quadro: QuadroFR) => {
      ultimo = quadro;
      if (destruido || gl.isContextLost() || largura <= 0 || altura <= 0) return;
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

      gl.useProgram(fr);
      gl.enable(gl.DEPTH_TEST);
      gl.depthMask(true);
      gl.disable(gl.BLEND);
      gl.bindBuffer(gl.ARRAY_BUFFER, bufferFR);
      gl.enableVertexAttribArray(aPosicao);
      gl.vertexAttribPointer(aPosicao, 3, gl.FLOAT, false, 28, 0);
      gl.enableVertexAttribArray(aDados);
      gl.vertexAttribPointer(aDados, 4, gl.FLOAT, false, 28, 12);
      rotacionar(matriz, quadro.rx, quadro.ry, quadro.rz, quadro.s);
      gl.uniformMatrix3fv(u.frRotacao, false, matriz);
      gl.uniform3f(u.frPosicao, quadro.x, quadro.y, 0);
      gl.uniform1f(u.frGap, quadro.gap);
      gl.uniform1f(u.frInv, quadro.inv);
      gl.uniform2f(u.frFocal, FOCAL / aspecto, FOCAL);
      gl.drawArrays(gl.TRIANGLES, 0, vertices.length / 7);
      gl.disableVertexAttribArray(aDados);

      const opacidade = 0.85 * (1 - quadro.inv);
      if (opacidade > 0.01) {
        gl.useProgram(pontos);
        gl.depthMask(false);
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.ONE, gl.ONE);
        gl.bindBuffer(gl.ARRAY_BUFFER, bufferPoeira);
        gl.enableVertexAttribArray(aPonto);
        gl.vertexAttribPointer(aPonto, 3, gl.FLOAT, false, 12, 0);
        rotacionar(matriz, quadro.rx * 0.3, quadro.giroPoeira, 0);
        gl.uniformMatrix3fv(u.ptRotacao, false, matriz);
        gl.uniform3f(u.ptPosicao, quadro.x * 0.4, 0, 0);
        // Tamanho .05 em unidades de cena, atenuado pela distancia como no mockup.
        gl.uniform1f(u.ptTamanho, Math.max(1, 0.05 * FOCAL * canvas.height / 2));
        gl.uniform1f(u.ptOpacidade, opacidade);
        gl.uniform2f(u.ptFocal, FOCAL / aspecto, FOCAL);
        gl.drawArrays(gl.POINTS, 0, poeira.length / 3);
      }
    };

    const redimensionar = () => {
      largura = window.innerWidth; altura = window.innerHeight;
      aspecto = largura / Math.max(1, altura);
      // Tela cheia: DPR ate 1,5 e no maximo 2,2 megapixels de buffer.
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5, Math.sqrt(2200000 / Math.max(1, largura * altura)));
      const w = Math.max(1, Math.round(largura * dpr)), h = Math.max(1, Math.round(altura * dpr));
      if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
      gl.viewport(0, 0, w, h);
      if (ultimo) desenhar(ultimo);
    };
    window.addEventListener("resize", redimensionar);
    redimensionar();
    if (gl.isContextLost() || gl.getError() !== gl.NO_ERROR) {
      window.removeEventListener("resize", redimensionar);
      throw new Error("O primeiro quadro da arte Fraus nao pode ser desenhado.");
    }
    return {
      desenhar,
      destruir() {
        window.removeEventListener("resize", redimensionar);
        liberar();
      },
    };
  } catch (erro) {
    liberar();
    throw erro;
  }
}
