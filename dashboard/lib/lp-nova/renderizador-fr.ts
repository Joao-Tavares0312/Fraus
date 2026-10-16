import { criarVerticesFR, POSES_FR } from "./escultura";
import type { Etapa } from "./narrativa";

let verticesPreparados: Float32Array | null = null;

export type RenderizadorFR = {
  irPara: (etapa: Etapa, repetir?: boolean) => void;
  destruir: () => void;
};
const DURACAO = 650;
const VERTEX = `
attribute vec3 a_posicao;
attribute vec4 a_dados;
uniform mat3 u_rotacao;
uniform vec4 u_pose;
uniform vec2 u_tamanho;
uniform float u_escala;
varying vec3 v_local;
varying vec2 v_material;
void main() {
  vec3 p = a_posicao - vec3(200.0, 151.0, 0.0);
  p.xy += vec2(a_dados.y * u_pose.y, a_dados.y * u_pose.y * .3);
  p.x += a_dados.x * u_pose.z;
  p.z += a_dados.x * u_pose.x;
  p = u_rotacao * p;
  p.x += u_pose.w * u_escala;
  // Mesma camera CSS: perspectiva 1600, origem 48%/45%, objeto 50%/48%.
  // Coordenadas CSS tem y para baixo e z em direcao ao observador.
  float distancia = 1600.0 - p.z;
  vec2 origem = u_tamanho * vec2(.48, .45);
  vec2 centro = u_tamanho * vec2(.5, .48);
  vec2 projetada = (centro - origem + p.xy) * 1600.0;
  vec2 clip = (projetada + (origem - u_tamanho * .5) * distancia) * 2.0 / u_tamanho;
  // Near=100, far=3000: profundidade monotona, sem comprimir tudo em z=1.
  gl_Position = vec4(clip.x, -clip.y, (3100.0 * distancia - 600000.0) / 2900.0, distancia);
  v_local = a_posicao;
  v_material = a_dados.zw;
}`;
const FRAGMENT = `
precision mediump float;
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
  gl_FragColor = vec4(cor / 255.0, 1.0);
}`;

/** Um buffer, um draw por quadro, nenhum laço ocioso. A arte estatica e mantida
 * pelo componente ate o primeiro quadro e durante perda/ausencia do contexto. */
export function criarRenderizadorFR(canvas: HTMLCanvasElement, etapa: Etapa, aoAssentar: (animando: boolean) => void): RenderizadorFR {
  // Nao trocar o custo da malha DOM por rasterizacao 3D em software. O proprio
  // navegador decide se ha caveat grave; nesse caso a marca WebP continua visivel.
  const gl = canvas.getContext("webgl", { alpha: true, antialias: true, depth: true, stencil: false, premultipliedAlpha: true, preserveDrawingBuffer: false, powerPreference: "low-power", failIfMajorPerformanceCaveat: true });
  canvas.dataset.frBackend = "indisponivel";
  if (!gl) throw new Error("WebGL indisponivel para a arte Fraus.");
  const informacao = gl.getExtension("WEBGL_debug_renderer_info");
  const nomeBackend = String(gl.getParameter(informacao ? informacao.UNMASKED_RENDERER_WEBGL : gl.RENDERER));
  const software = /swiftshader|llvmpipe|softpipe|swrast|software|basic render driver|\bwarp\b|gdi generic/i.test(nomeBackend);
  canvas.dataset.frBackend = software ? "software" : "contexto";
  // Alguns Chromium permitem SwiftShader mesmo com caveat=true. Nao basta
  // confiar na criacao do contexto: backends CPU conhecidos usam o WebP.
  // Apenas QA/exportacao pede explicitamente attrs=false antes da criacao;
  // nao ha query string, permissao global nem heuristica adaptativa no produto.
  if (software && gl.getContextAttributes()?.failIfMajorPerformanceCaveat !== false) {
    gl.getExtension("WEBGL_lose_context")?.loseContext();
    throw new Error("Backend WebGL em software; mantendo a arte Fraus pre-renderizada.");
  }
  const programa = gl.createProgram();
  const buffer = gl.createBuffer();
  const shaders: WebGLShader[] = [];
  let quadro: number | null = null;
  let destruido = false;
  const destruir = () => {
    destruido = true;
    if (quadro !== null) cancelAnimationFrame(quadro);
    quadro = null;
    if (buffer) gl.deleteBuffer(buffer);
    if (programa) gl.deleteProgram(programa);
    shaders.forEach((shader) => gl.deleteShader(shader));
  };
  try {
    if (!programa || !buffer) throw new Error("Nao foi possivel alocar a arte Fraus.");
    // O caminho WebP nao triangula nem aloca a malha. Reutiliza o buffer CPU
    // somente depois de um contexto aceito (inclusive apos restauracao).
    const vertices = verticesPreparados ??= criarVerticesFR();
    for (const [tipo, fonte] of [[gl.VERTEX_SHADER, VERTEX], [gl.FRAGMENT_SHADER, FRAGMENT]] as const) {
      const shader = gl.createShader(tipo);
      if (!shader) throw new Error("Nao foi possivel criar o shader Fraus.");
      shaders.push(shader);
      gl.shaderSource(shader, fonte);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader) ?? "Shader Fraus invalido.");
      gl.attachShader(programa, shader);
    }
    gl.linkProgram(programa);
    if (!gl.getProgramParameter(programa, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(programa) ?? "Programa Fraus invalido.");
    gl.useProgram(programa);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
    for (const [nome, tamanho, offset] of [["a_posicao", 3, 0], ["a_dados", 4, 12]] as const) {
      const indice = gl.getAttribLocation(programa, nome);
      gl.enableVertexAttribArray(indice);
      gl.vertexAttribPointer(indice, tamanho, gl.FLOAT, false, 28, offset);
    }
    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.LEQUAL);
    // A projeção inverte y (CSS -> clip); frente positiva em xy vira CW.
    gl.enable(gl.CULL_FACE);
    gl.frontFace(gl.CW);
    gl.cullFace(gl.BACK);
    gl.clearColor(0, 0, 0, 0);
    const rotacao = gl.getUniformLocation(programa, "u_rotacao");
    const pose = gl.getUniformLocation(programa, "u_pose");
    const tamanho = gl.getUniformLocation(programa, "u_tamanho");
    const escala = gl.getUniformLocation(programa, "u_escala");
    const matriz = new Float32Array(9);
    const atual = new Float32Array(POSES_FR[etapa]);
    const origem = new Float32Array(atual);
    const destino = new Float32Array(atual);
    let inicio = 0;
    let animando = false;
    let largura = 0, altura = 0;
    const desenhar = () => {
      if (destruido || gl.isContextLost() || largura <= 0 || altura <= 0) return;
      const fator = window.innerWidth < 1200 ? .84 : 1;
      const x = atual[0] * Math.PI / 180, y = atual[1] * Math.PI / 180, z = atual[2] * Math.PI / 180;
      const cx = Math.cos(x), sx = Math.sin(x), cy = Math.cos(y), sy = Math.sin(y), cz = Math.cos(z), sz = Math.sin(z);
      const s = atual[5] * fator;
      // R_x R_y R_z, column-major, como a lista de transforms original.
      matriz[0]=cy*cz*s; matriz[1]=(cx*sz+sx*sy*cz)*s; matriz[2]=(sx*sz-cx*sy*cz)*s;
      matriz[3]=-cy*sz*s; matriz[4]=(cx*cz-sx*sy*sz)*s; matriz[5]=(sx*cz+cx*sy*sz)*s;
      matriz[6]=sy*s; matriz[7]=-sx*cy*s; matriz[8]=cx*cy*s;
      gl.uniformMatrix3fv(rotacao, false, matriz);
      gl.uniform4f(pose, atual[3], atual[4], atual[7], atual[6]);
      gl.uniform2f(tamanho, largura, altura);
      gl.uniform1f(escala, fator);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.drawArrays(gl.TRIANGLES, 0, vertices.length / 7);
    };
    const interpolar = (agora: number) => {
      const t = Math.min(1, Math.max(0, (agora - inicio) / DURACAO));
      // Inverte x do cubic-bezier(.16,1,.3,1); nao confunde tempo com parametro.
      let inferior = 0, superior = 1, u = t;
      for (let i = 0; i < 14; i++) {
        const bx = 3 * (1-u) * (1-u) * u * .16 + 3 * (1-u) * u * u * .3 + u*u*u;
        if (bx < t) inferior = u; else superior = u;
        u = (inferior + superior) / 2;
      }
      const progresso = t === 1 ? 1 : t === 0 ? 0 : 1 - (1-u) ** 3;
      for (let i = 0; i < atual.length; i++) atual[i] = origem[i] + (destino[i] - origem[i]) * progresso;
      return t < 1;
    };
    const avancar = (agora: number) => {
      quadro = null;
      if (destruido) return;
      animando = interpolar(agora);
      desenhar();
      if (animando) quadro = requestAnimationFrame(avancar);
      else aoAssentar(false);
    };
    const redimensionar = () => {
      const caixa = canvas.getBoundingClientRect();
      largura = caixa.width; altura = caixa.height;
      // Limite de 1.5 DPR e 1.6 megapixels, inclusive telas grandes/Retina.
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5, Math.sqrt(1600000 / Math.max(1, largura * altura)));
      const w = Math.max(1, Math.round(largura * dpr)), h = Math.max(1, Math.round(altura * dpr));
      if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
      gl.viewport(0, 0, w, h);
      if (animando) interpolar(performance.now());
      desenhar();
    };
    const observador = new ResizeObserver(redimensionar);
    observador.observe(canvas);
    window.addEventListener("resize", redimensionar);
    redimensionar();
    if (largura <= 0 || altura <= 0 || gl.isContextLost() || gl.getError() !== gl.NO_ERROR) {
      observador.disconnect();
      window.removeEventListener("resize", redimensionar);
      throw new Error("O primeiro quadro da arte Fraus nao pode ser desenhado.");
    }
    return {
      irPara(proxima: Etapa, repetir = false) {
        const agora = performance.now();
        if (quadro !== null) cancelAnimationFrame(quadro);
        if (animando) interpolar(agora);
        if (repetir) atual.set(POSES_FR[proxima === 0 ? 1 : (proxima - 1) as Etapa]);
        origem.set(atual);
        destino.set(POSES_FR[proxima]);
        inicio = agora;
        animando = true;
        aoAssentar(true);
        quadro = requestAnimationFrame(avancar);
      },
      destruir() {
        observador.disconnect();
        window.removeEventListener("resize", redimensionar);
        destruir();
      },
    };
  } catch (erro) {
    destruir();
    throw erro;
  }
}
