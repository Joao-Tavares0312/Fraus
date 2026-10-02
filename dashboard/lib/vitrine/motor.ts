import Lenis from "lenis";
import { FAMILIAS_DO_VETOR } from "@/components/lp/fatos";
import {
  ESTADOS_DO_ORBE,
  estagioDaConstelacao,
  grampear01,
  misturar,
  monotonizar,
  orbeEntreQuadros,
  suave,
  type EstadoDoOrbe,
  type Quadro,
} from "./coreografia";

/**
 * O MOTOR DA VITRINE: o lado imperativo da coreografia.
 *
 * UM canvas, UM contexto WebGL, quatro programas: o fosforo do osciloscopio
 * com o orbe por cima (tela cheia), os pontos da constelacao, os fios ate o
 * fusor e o aglomerado cinza do "sem sinal". Sem three.js e sem GSAP: a
 * constelacao e so ponto e linha em pixel, e a secao fixada e `position:
 * sticky` com o progresso medido aqui -- o pin do GSAP injeta wrapper no DOM
 * e briga com a reconciliacao do React.
 *
 * Mora SO na vitrine (`app/page.tsx`), nunca no layout raiz: a ferramenta e
 * lida por horas e nao pode ter GPU girando atras de tabela (DESIGN.md).
 *
 * Dois regimes:
 *  - VIVO: Lenis na rolagem, laco de quadros, secao fixada, passos em fade.
 *  - ESTATICO (`prefers-reduced-motion`, ou WebGL ausente): nada gira, a
 *    secao nao fixa, os passos aparecem empilhados e a constelacao fica no
 *    estagio dos 39 nos. Sem WebGL o canvas some e a pagina segue legivel.
 *
 * Devolve a funcao de limpeza: a navegacao para /entrar desmonta a vitrine e
 * o contexto WebGL e liberado na hora.
 */

const LARGURA_ESTREITA = 900;
const DESLOCAMENTO_DO_TOPO = -52;

/* ---------------------------------------------------------------- shaders */

const VS_TELA = "attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}";

const FS_FUNDO = `precision highp float;
uniform vec2 R,C,M; uniform float T,TO,RAD,SAT,SP,TR,A,WD,WM,WH;
float h(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float n(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(h(i),h(i+vec2(1,0)),f.x),mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x),f.y);}
float fbm(vec2 p){float v=0.,a=.5;for(int i=0;i<5;i++){v+=a*n(p);p*=2.03;a*=.5;}return v;}
float hs(float x){return fract(sin(x)*43758.5453);}
float vn(float x){float i=floor(x),f=fract(x);f=f*f*(3.-2.*f);return mix(hs(i),hs(i+1.),f)*2.-1.;}
float c1(float x){float e=pow(max(0.,sin(x*9.42478+.6)),4.);return e*(sin(x*150.+T*1.3)*.55+vn(x*70.+T*.8)*.45);}
float c2(float x){return .18*sin(x*14.+T*.7)+.09*vn(x*35.+T*.9)+.06*sin(x*61.-T*1.7);}
float traco(float y,float v,float dv){float dpx=(y-v)*R.y;float sl=dv*R.y/R.x;float d=abs(dpx)/sqrt(1.+sl*sl);
  return exp(-d*d/1.8)+.38*exp(-d/6.5)+.09*exp(-d/34.);}
vec3 scr(vec3 a,vec3 b){return 1.-(1.-a)*(1.-b);}
void main(){
  vec2 uv=gl_FragCoord.xy/R;
  vec2 cc=uv*2.-1.; cc*=1.+.025*dot(cc,cc); vec2 u=cc*.5+.5;
  vec3 bg=vec3(.04,.04,.047);
  vec3 col=bg*.6;
  if(u.x>=0.&&u.x<=1.&&u.y>=0.&&u.y<=1.){
    col=bg;
    float gx=abs(fract(u.x*10.+.5)-.5)/10.*R.x, gy=abs(fract(u.y*8.+.5)-.5)/8.*R.y;
    float grid=max(step(gx,.6),step(gy,.6));
    float tick=step(abs(u.y-.5)*R.y,4.)*step(abs(fract(u.x*50.+.5)-.5)/50.*R.x,.6)
              +step(abs(u.x-.5)*R.x,4.)*step(abs(fract(u.y*40.+.5)-.5)/40.*R.y,.6);
    col+=vec3(.93,.93,.96)*(grid*.05+min(tick,1.)*.07);
    float x=u.x, e=1./R.x;
    float hx=fract(T*.11); float atras=fract(hx-x); float p=.25+.75*exp(-atras*5.);
    float Y1=.64, Y2=.36;
    float a1=.05; float v1=Y1+a1*c1(x); float d1=a1*(c1(x+e)-c1(x-e))/(2.*e);
    float a2=.04; float v2=Y2+a2*c2(x); float d2=a2*(c2(x+e)-c2(x-e))/(2.*e);
    float i1=traco(u.y,v1,d1)*p*(1.-A);
    float i2=traco(u.y,v2,d2)*p;
    float tracej=step(.5,fract(gl_FragCoord.x/14.));
    float b1=exp(-pow((u.y-Y1)*R.y,2.)/1.2)*tracej*A;
    vec3 tr=vec3(1.,.62,.2)*i1+vec3(.32,.58,1.)*i2+vec3(.62,.63,.68)*b1*.55;
    col+=tr*TR*.55;
    float vig=smoothstep(1.25,.35,length(cc*vec2(.92,1.)));
    col*=.55+.45*vig;
    col*=.965+.035*sin(gl_FragCoord.y*3.14159);
  }
  vec2 q0=(gl_FragCoord.xy-C)/RAD; float d=length(q0);
  if(d<1.8){
    vec2 q=q0+.22*vec2(fbm(q0*1.8+TO*.07),fbm(q0*1.8-TO*.09+3.1))-.11;
    float s=SP*.5;
    vec2 a1=s*vec2(cos(TO*6.283/14.),sin(TO*6.283/14.))+M*.12;
    vec2 a2=s*vec2(cos(TO*6.283/18.+2.1),sin(TO*6.283/18.+2.1));
    vec2 a3=s*vec2(cos(-TO*6.283/22.+4.2),sin(-TO*6.283/22.+4.2))-M*.1;
    vec3 o=vec3(.02,.02,.03);
    o=scr(o,vec3(1.,.6,.16)*WD*exp(-dot(q-a1,q-a1)*2.6));
    o=scr(o,vec3(.22,.5,1.)*WM*exp(-dot(q-a2,q-a2)*2.4));
    o=scr(o,vec3(.8,.18,.75)*.85*WH*exp(-dot(q-a3,q-a3)*3.2));
    o=clamp(o,0.,1.);
    o*=mix(.3,1.,smoothstep(1.,.35,d));
    o+=.08*smoothstep(.75,1.,d)*smoothstep(1.02,.98,d);
    float g=dot(o,vec3(.299,.587,.114));
    o=mix(vec3(g*.55),o,SAT);
    float mask=smoothstep(1.,.985,d);
    float halo=(1.-mask)*exp(-(d-1.)*5.)*.16*SAT*WH;
    col=mix(col,o,mask)+vec3(.55,.16,.55)*halo;
  }
  col+=(h(gl_FragCoord.xy+fract(T))-.5)*.02;
  gl_FragColor=vec4(col,1.);
}`;

const VS_PONTOS = `
attribute vec2 p0; attribute vec2 p1; attribute vec2 p2; attribute vec2 p3; attribute vec2 p4;
attribute vec3 c1; attribute vec3 c2; attribute float seed;
uniform float uK, uT, uPix, uTam; uniform vec3 uC0, uC3, uC4; uniform vec2 uRes, uDesl;
varying vec3 vC;
float st(float x){ return smoothstep(0., 1., clamp(x * 1.35 - seed * .35, 0., 1.)); }
void main(){
  float s1 = st(uK), s2 = st(uK - 1.), s3 = st(uK - 2.), s4 = st(uK - 3.);
  vec2 p = mix(mix(mix(mix(p0, p1, s1), p2, s2), p3, s3), p4, s4);
  float calma = 1. - s4;
  p += vec2(sin(uT * .6 + seed * 31.), cos(uT * .5 + seed * 17.)) * (1.2 + 5. * (1. - s1)) * calma;
  vec3 c = mix(mix(mix(mix(uC0, c1, s1), c2, s2), uC3, s3), uC4, s4);
  p += uDesl;
  gl_Position = vec4(p.x / uRes.x * 2. - 1., 1. - p.y / uRes.y * 2., 0., 1.);
  float tw = .78 + .22 * sin(uT * 2. + seed * 40.);
  gl_PointSize = uTam * uPix * (.6 + seed * .8) * tw * mix(1., .55, s4);
  vC = c;
}`;

const FS_PONTOS = `precision mediump float;
uniform float uOp; varying vec3 vC;
void main(){ float a = smoothstep(.5, .15, length(gl_PointCoord - .5)); gl_FragColor = vec4(vC, a * uOp); }`;

const VS_FIOS = `attribute vec2 p; uniform vec2 uRes, uDesl;
void main(){ vec2 q = p + uDesl; gl_Position = vec4(q.x / uRes.x * 2. - 1., 1. - q.y / uRes.y * 2., 0., 1.); }`;

const FS_FIOS = `precision mediump float; uniform vec3 uCor; uniform float uOp;
void main(){ gl_FragColor = vec4(uCor, uOp); }`;

const VS_VAZIO = `attribute float ang; attribute float rf; attribute float seed;
uniform float uT, uR, uPix; uniform vec2 uCentro, uRes;
void main(){
  float a = ang + uT * .025 * (seed - .5);
  float r = rf * uR * (1. + .07 * sin(uT * .3 + seed * 9.));
  vec2 q = uCentro + vec2(cos(a) * r, sin(a) * r * .9);
  gl_Position = vec4(q.x / uRes.x * 2. - 1., 1. - q.y / uRes.y * 2., 0., 1.);
  gl_PointSize = (1.4 + seed * 1.2) * uPix;
}`;

const FS_VAZIO = `precision mediump float; uniform float uOp; uniform vec3 uCor;
void main(){ float a = smoothstep(.5, .15, length(gl_PointCoord - .5)); gl_FragColor = vec4(uCor, a * uOp * .7); }`;

/* ------------------------------------------------------------- utilidades */

type Cor = [number, number, number];

/** OKLCH -> sRGB, para os pontos usarem os mesmos matizes dos tokens. */
function oklch(L: number, C: number, h: number): Cor {
  const a = C * Math.cos((h * Math.PI) / 180);
  const b = C * Math.sin((h * Math.PI) / 180);
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const f = (x: number) => {
    const y = Math.max(0, Math.min(1, x));
    return y <= 0.0031308 ? 12.92 * y : 1.055 * Math.pow(y, 1 / 2.4) - 0.055;
  };
  return [
    f(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
    f(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
    f(-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s),
  ];
}

const COR = {
  dito: oklch(0.8, 0.15, 72),
  medido: oklch(0.76, 0.13, 250),
  bot: oklch(0.6, 0.012, 286),
  poeira: oklch(0.62, 0.01, 285),
  fusor: oklch(0.9, 0.05, 250),
  sem: oklch(0.66, 0.012, 286),
};

function compilar(gl: WebGLRenderingContext, vs: string, fs: string): WebGLProgram | null {
  const sombra = (tipo: number, fonte: string) => {
    const s = gl.createShader(tipo);
    if (!s) return null;
    gl.shaderSource(s, fonte);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      console.error("vitrine: shader nao compilou", gl.getShaderInfoLog(s));
      return null;
    }
    return s;
  };
  const v = sombra(gl.VERTEX_SHADER, vs);
  const f = sombra(gl.FRAGMENT_SHADER, fs);
  const p = gl.createProgram();
  if (!v || !f || !p) return null;
  gl.attachShader(p, v);
  gl.attachShader(p, f);
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
    console.error("vitrine: programa nao ligou", gl.getProgramInfoLog(p));
    return null;
  }
  return p;
}

type Atributo = { nome: string; buffer: WebGLBuffer; tamanho: number };

/** Liga os atributos de um programa; devolve quem desligar depois do draw. */
function ligar(gl: WebGLRenderingContext, prog: WebGLProgram, atributos: readonly Atributo[]): number[] {
  const ligados: number[] = [];
  for (const a of atributos) {
    const loc = gl.getAttribLocation(prog, a.nome);
    if (loc < 0) continue;
    gl.bindBuffer(gl.ARRAY_BUFFER, a.buffer);
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, a.tamanho, gl.FLOAT, false, 0, 0);
    ligados.push(loc);
  }
  return ligados;
}

const gauss = () => (Math.random() + Math.random() + Math.random() - 1.5) / 1.5;

/* ------------------------------------------------------------------ motor */

export function iniciarMotor(raiz: HTMLElement, canvas: HTMLCanvasElement): () => void {
  const $ = <T extends Element>(seletor: string) => raiz.querySelector<T>(seletor);
  const secao = $<HTMLElement>("#constelacao");
  const pin = $<HTMLElement>('[data-vt="pin"]');
  const palco = $<HTMLElement>('[data-vt="palco"]');
  const ancora = $<HTMLElement>('[data-vt="ancora-vazio"]');
  const sistema = $<HTMLElement>("#sistema");
  const fecho = $<HTMLElement>("#fecho");
  const tituloHero = $<HTMLElement>('[data-vt="titulo-hero"]');
  const hero = $<HTMLElement>("#hero");
  const passos = Array.from(raiz.querySelectorAll<HTMLElement>('[data-vt="passo"]'));
  const notaFim = $<HTMLElement>('[data-vt="nota-fim"]');
  const leitura = $<HTMLElement>('[data-vt="leitura"]');
  const barra = $<HTMLElement>('[data-vt="progresso"]');
  if (!secao || !pin || !palco || !ancora || !sistema || !fecho || !hero) return () => {};

  const reduz = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const gl = canvas.getContext("webgl", { antialias: false, alpha: false, powerPreference: "low-power" });
  const programas = gl && {
    fundo: compilar(gl, VS_TELA, FS_FUNDO),
    pontos: compilar(gl, VS_PONTOS, FS_PONTOS),
    fios: compilar(gl, VS_FIOS, FS_FIOS),
    vazio: compilar(gl, VS_VAZIO, FS_VAZIO),
  };
  const comGL = !!(gl && programas && programas.fundo && programas.pontos && programas.fios && programas.vazio);
  const vivo = comGL && !reduz;

  raiz.classList.add(vivo ? "vt-vivo" : "vt-estatico");
  if (!comGL) {
    canvas.style.display = "none";
    return () => raiz.classList.remove("vt-estatico");
  }
  const g = gl!;
  const P = programas! as Record<"fundo" | "pontos" | "fios" | "vazio", WebGLProgram>;

  /* ---------------------------------------------------------- geometria */
  let W = innerWidth;
  let H = innerHeight;
  let dpr = Math.min(devicePixelRatio || 1, 1.5);
  const estreito = () => W <= LARGURA_ESTREITA;
  const estados = () => (estreito() ? ESTADOS_DO_ORBE.estreito : ESTADOS_DO_ORBE.largo);
  const topoAbs = (el: HTMLElement) => el.getBoundingClientRect().top + scrollY;

  /** O palco em coordenadas locais do pin (x da viewport, y desde o topo do pin). */
  let PL = { pw: 0, ph: 0, px: 0, py: 0, cx: 0, cy: 0 };
  function medirPalco() {
    const rp = pin!.getBoundingClientRect();
    const r = palco!.getBoundingClientRect();
    PL = { pw: r.width, ph: r.height, px: r.left, py: r.top - rp.top, cx: r.left + r.width / 2, cy: r.top - rp.top + r.height / 2 };
  }

  let pinInicio = 0;
  let pinFim = 1;
  let preInicio = 0;
  function medirPin() {
    const topo = topoAbs(secao!);
    pinInicio = topo;
    pinFim = topo + Math.max(1, secao!.offsetHeight - H);
    preInicio = topo - H * 0.85;
  }

  /* --------------------------------------------------- estado e quadros */
  const S = { k: vivo ? 0 : 3, mx: 0, my: 0, mxA: 0, myA: 0 };

  /** k: 0 poeira, 1 palavras, 2 mascara, 3 nos, 4 dentro do fusor. */
  function kDaRolagem(): number {
    if (!vivo) return 3;
    const y = scrollY;
    if (y <= preInicio) return 0;
    if (y < pinInicio) return grampear01((y - preInicio) / Math.max(1, pinInicio - preInicio));
    return estagioDaConstelacao((y - pinInicio) / Math.max(1, pinFim - pinInicio));
  }

  function orbeNoPin(): EstadoDoOrbe {
    const e = estados();
    const topo = pin!.getBoundingClientRect().top;
    const centro = { x: PL.cx / W, y: (topo + PL.cy) / H };
    const nucleo = { ...e.nucleo, ...centro };
    const fusor = { ...e.fusor, ...centro };
    if (S.k <= 2) return e.canto;
    if (S.k <= 3) return misturar(e.canto, nucleo, suave(S.k - 2));
    return misturar(nucleo, fusor, suave(Math.min(1, S.k - 3)));
  }

  function orbeNoVazio(): EstadoDoOrbe {
    const r = ancora!.getBoundingClientRect();
    return { ...estados().vazio, x: (r.left + r.width / 2) / W, y: (r.top + r.height / 2) / H };
  }

  let quadros: Quadro[] = [];
  function montarQuadros() {
    W = innerWidth;
    H = innerHeight;
    medirPalco();
    medirPin();
    const maxY = Math.max(1, document.documentElement.scrollHeight - H);
    const lista: Array<[number, () => EstadoDoOrbe]> = [
      [0, () => estados().hero],
      [pinInicio - H * 0.55, () => estados().canto],
      [pinInicio, orbeNoPin],
      [pinFim, orbeNoPin],
      [topoAbs(ancora!) + ancora!.offsetHeight / 2 - H / 2, orbeNoVazio],
      [topoAbs(sistema!) - H * 0.3, () => estados().sistema],
      [Math.min(topoAbs(fecho!) - H * 0.3, maxY), () => estados().fecho],
    ];
    const ys = monotonizar(lista.map(([y]) => y));
    quadros = lista.map(([, estado], i) => ({ y: ys[i], estado }));
  }

  /* ------------------------------------------------------------ buffers */
  const buf = () => g.createBuffer()!;
  const tela = buf();
  g.bindBuffer(g.ARRAY_BUFFER, tela);
  g.bufferData(g.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), g.STATIC_DRAW);

  const B = {
    p0: buf(), p1: buf(), p2: buf(), p3: buf(), p4: buf(), c1: buf(), c2: buf(), seed: buf(),
    fios: buf(), ang: buf(), rf: buf(), seedV: buf(),
  };
  let nPontos = 0;
  let nVazio = 0;
  const rotulos: HTMLElement[] = [];

  function carregar(buffer: WebGLBuffer, dados: Float32Array) {
    g.bindBuffer(g.ARRAY_BUFFER, buffer);
    g.bufferData(g.ARRAY_BUFFER, dados, g.STATIC_DRAW);
  }

  /** As falas da conversa sintetica, desenhadas num canvas 2D e amostradas em pontos. */
  function amostrarTexto(): Array<[number, number, Cor]> {
    const cw = Math.max(10, Math.round(PL.pw));
    const ch = Math.max(10, Math.round(PL.ph));
    const cv = document.createElement("canvas");
    cv.width = cw;
    cv.height = ch;
    const x = cv.getContext("2d", { willReadFrequently: true });
    if (!x) return [];
    const display = tituloHero ? getComputedStyle(tituloHero).fontFamily : "sans-serif";
    const prosa = getComputedStyle(document.body).fontFamily;
    const linhas = [
      { t: "Meu pedido chegou", f: `500 %px ${prosa}`, s: 0.07, c: COR.dito },
      { t: "quebrado pela terceira vez.", f: `500 %px ${prosa}`, s: 0.07, c: COR.dito },
      { t: "Sinto muito. Vou abrir uma solicitação.", f: `400 %px ${prosa}`, s: 0.04, c: COR.bot },
      { t: "tá. ok, obrigado 🙂", f: `800 %px ${display}`, s: 0.14, c: COR.dito },
    ].map((l) => {
      let sz = l.s * cw;
      x.font = l.f.replace("%", sz.toFixed(1));
      const w = x.measureText(l.t).width;
      if (w > cw * 0.94) sz *= (cw * 0.94) / w;
      return { ...l, sz };
    });
    const vaos = [0.5, 1.1, 1.2];
    const altura = linhas.reduce((t, l, i) => t + l.sz * 1.05 + (i < 3 ? l.sz * vaos[i] * 0.5 : 0), 0);
    let y = (ch - altura) / 2;
    const pts: Array<[number, number, Cor]> = [];
    linhas.forEach((l, i) => {
      x.clearRect(0, 0, cw, ch);
      x.font = l.f.replace("%", l.sz.toFixed(1));
      x.textBaseline = "top";
      x.fillStyle = "#fff";
      const w = x.measureText(l.t).width;
      x.fillText(l.t, (cw - w) / 2, y);
      const y0 = Math.max(0, Math.floor(y - l.sz * 0.2));
      const y1 = Math.min(ch, Math.ceil(y + l.sz * 1.3));
      if (y1 > y0) {
        const d = x.getImageData(0, y0, cw, y1 - y0).data;
        for (let yy = 0; yy < y1 - y0; yy += 2)
          for (let xx = 0; xx < cw; xx += 2) if (d[(yy * cw + xx) * 4 + 3] > 120) pts.push([xx, yy + y0, l.c]);
      }
      y += l.sz * 1.05 + (i < 3 ? l.sz * vaos[i] * 0.5 : 0);
    });
    return pts;
  }

  function construirCeu() {
    W = innerWidth;
    H = innerHeight;
    medirPalco();
    const N = estreito() ? 2400 : 5200;
    const p0 = new Float32Array(N * 2), p1 = new Float32Array(N * 2), p2 = new Float32Array(N * 2);
    const p3 = new Float32Array(N * 2), p4 = new Float32Array(N * 2);
    const c1 = new Float32Array(N * 3), c2 = new Float32Array(N * 3), sd = new Float32Array(N);
    const por = (arr: Float32Array, i: number, a: number, b: number) => { arr[i * 2] = a; arr[i * 2 + 1] = b; };
    const cor = (arr: Float32Array, i: number, c: Cor) => arr.set(c, i * 3);

    const texto = amostrarTexto();

    // a mascara: oval, olhos e boca vazios; ambar (dito) a esquerda, azul (medido) a direita
    const ry = Math.min(PL.ph * 0.43, PL.pw * 0.6);
    const rx = ry * 0.68;
    const vazios = [
      [-0.36 * rx, -0.12 * ry, 0.2 * rx, 0.055 * ry],
      [0.36 * rx, -0.12 * ry, 0.2 * rx, 0.055 * ry],
      [0, 0.42 * ry, 0.26 * rx, 0.03 * ry],
    ];
    const noVazio = (dx: number, dy: number) =>
      vazios.some(([vx, vy, ax, ay]) => ((dx - vx) / ax) ** 2 + ((dy - vy) / ay) ** 2 < 1);
    const pontoDaMascara = (): [number, number] => {
      const r = Math.random();
      if (r < 0.2) {
        const t = Math.random() * Math.PI * 2;
        const k = 1 - Math.abs(gauss()) * 0.02;
        return [Math.cos(t) * rx * k, Math.sin(t) * ry * k];
      }
      if (r < 0.3) {
        const [vx, vy, ax, ay] = vazios[Math.floor(Math.random() * 3)];
        const t = Math.random() * Math.PI * 2;
        return [vx + Math.cos(t) * ax * 1.18, vy + Math.sin(t) * ay * 1.35];
      }
      for (let tentativa = 0; tentativa < 40; tentativa++) {
        const dx = (Math.random() * 2 - 1) * rx;
        const dy = (Math.random() * 2 - 1) * ry;
        if ((dx / rx) ** 2 + (dy / ry) ** 2 < 1 && !noVazio(dx, dy)) return [dx, dy];
      }
      return [0, 0];
    };

    // os nos: um por feature, agrupados na contagem REAL de cada familia
    const total = FAMILIAS_DO_VETOR.reduce((t, f) => t + f.qtd, 0);
    const raio = Math.min(PL.pw, PL.ph) * 0.36;
    const unidade = (Math.PI * 2) / (total + FAMILIAS_DO_VETOR.length * 1.8);
    const nos: Array<[number, number]> = [];
    const meios: Array<[string, number, number]> = [];
    let ang = -Math.PI / 2;
    for (const f of FAMILIAS_DO_VETOR) {
      const a0 = ang;
      for (let j = 0; j < f.qtd; j++) {
        const rr = raio * (j % 2 ? 1.06 : 0.95);
        nos.push([PL.cx + Math.cos(ang) * rr, PL.cy + Math.sin(ang) * rr * 0.92]);
        ang += unidade;
      }
      meios.push([f.rotulo.toLowerCase(), f.qtd, (a0 + ang - unidade) / 2]);
      ang += unidade * 1.8;
    }
    const rFusor = estados().fusor.r * Math.min(W, H) * 0.55;

    for (let i = 0; i < N; i++) {
      por(p0, i, Math.random() * W, Math.random() * H);
      const t = texto.length ? texto[Math.floor(Math.random() * texto.length)] : ([PL.pw / 2, PL.ph / 2, COR.dito] as const);
      por(p1, i, PL.px + t[0] + (Math.random() - 0.5) * 1.4, PL.py + t[1] + (Math.random() - 0.5) * 1.4);
      cor(c1, i, t[2] as Cor);
      const [mx, my] = pontoDaMascara();
      por(p2, i, PL.cx + mx, PL.cy + my);
      const k = grampear01((mx / rx + 0.12) / 0.24);
      cor(c2, i, [0, 1, 2].map((j) => COR.dito[j] + (COR.medido[j] - COR.dito[j]) * k) as Cor);
      const no = nos[i % nos.length];
      const espalho = Math.random() < 0.15 ? 13 : 4.5;
      por(p3, i, no[0] + gauss() * espalho, no[1] + gauss() * espalho);
      const ra = rFusor * Math.sqrt(Math.random());
      const th = Math.random() * Math.PI * 2;
      por(p4, i, PL.cx + Math.cos(th) * ra, PL.cy + Math.sin(th) * ra);
      sd[i] = Math.random();
    }
    carregar(B.p0, p0); carregar(B.p1, p1); carregar(B.p2, p2); carregar(B.p3, p3); carregar(B.p4, p4);
    carregar(B.c1, c1); carregar(B.c2, c2); carregar(B.seed, sd);
    nPontos = N;

    const fios = new Float32Array(nos.length * 4);
    nos.forEach(([x, y], i) => fios.set([x, y, PL.cx, PL.cy], i * 4));
    carregar(B.fios, fios);

    nVazio = estreito() ? 260 : 520;
    const a0 = new Float32Array(nVazio), rf = new Float32Array(nVazio), sv = new Float32Array(nVazio);
    for (let i = 0; i < nVazio; i++) {
      a0[i] = Math.random() * Math.PI * 2;
      rf[i] = 1.35 + Math.random() * 1.35;
      sv[i] = Math.random();
    }
    carregar(B.ang, a0); carregar(B.rf, rf); carregar(B.seedV, sv);

    // rotulos das familias em HTML, nas mesmas coordenadas dos nos
    rotulos.forEach((r) => r.remove());
    rotulos.length = 0;
    for (const [nome, qtd, a] of meios) {
      const el = document.createElement("span");
      el.className = "vt-familia";
      el.textContent = `${nome} · `;
      const b = document.createElement("b");
      b.textContent = String(qtd);
      el.append(b);
      const cs = Math.cos(a);
      el.style.left = `${PL.cx - PL.px + cs * (raio + 30)}px`;
      el.style.top = `${PL.cy - PL.py + Math.sin(a) * (raio + 30) * 0.92}px`;
      el.style.transform = `translate(${Math.abs(cs) < 0.3 ? "-50%" : cs > 0 ? "0" : "-100%"}, -50%)`;
      el.style.opacity = vivo ? "0" : "1";
      palco!.append(el);
      rotulos.push(el);
    }
  }

  function medirCanvas() {
    dpr = Math.min(devicePixelRatio || 1, 1.5);
    canvas.width = Math.round(innerWidth * dpr);
    canvas.height = Math.round(innerHeight * dpr);
    g.viewport(0, 0, canvas.width, canvas.height);
  }

  /* ---------------------------------------------------------- desenho */
  const O: EstadoDoOrbe = { ...estados().hero };
  const u = (prog: WebGLProgram, nome: string) => g.getUniformLocation(prog, nome);

  function desenhar(t: number, tOrbe: number) {
    const cw = canvas.width;
    const chh = canvas.height;
    g.disable(g.BLEND);
    g.useProgram(P.fundo);
    let ligados = ligar(g, P.fundo, [{ nome: "p", buffer: tela, tamanho: 2 }]);
    g.uniform2f(u(P.fundo, "R"), cw, chh);
    g.uniform2f(u(P.fundo, "C"), O.x * cw, (1 - O.y) * chh);
    g.uniform2f(u(P.fundo, "M"), S.mxA, S.myA);
    g.uniform1f(u(P.fundo, "T"), t);
    g.uniform1f(u(P.fundo, "TO"), tOrbe);
    g.uniform1f(u(P.fundo, "RAD"), Math.max(1, O.r * Math.min(cw, chh)));
    g.uniform1f(u(P.fundo, "SAT"), O.sat);
    g.uniform1f(u(P.fundo, "SP"), O.sp);
    g.uniform1f(u(P.fundo, "TR"), O.tr);
    g.uniform1f(u(P.fundo, "A"), O.A);
    g.uniform1f(u(P.fundo, "WD"), O.dito);
    g.uniform1f(u(P.fundo, "WM"), O.medido);
    g.uniform1f(u(P.fundo, "WH"), O.halo);
    g.drawArrays(g.TRIANGLES, 0, 3);
    ligados.forEach((l) => g.disableVertexAttribArray(l));

    const k = S.k;
    const rs = secao!.getBoundingClientRect();
    const ra = ancora!.getBoundingClientRect();
    const veConstelacao = rs.bottom > 0 && rs.top < H && k > 0.01 && k < 3.995;
    const veVazio = ra.bottom > -H * 0.2 && ra.top < H * 1.2;
    if (!veConstelacao && !veVazio) return;

    g.enable(g.BLEND);
    g.blendFunc(g.SRC_ALPHA, g.ONE);
    const topo = pin!.getBoundingClientRect().top;

    if (veConstelacao && nPontos) {
      const desl: [number, number] = [S.mxA * 6, topo + S.myA * 6];
      g.useProgram(P.pontos);
      ligados = ligar(g, P.pontos, [
        { nome: "p0", buffer: B.p0, tamanho: 2 }, { nome: "p1", buffer: B.p1, tamanho: 2 },
        { nome: "p2", buffer: B.p2, tamanho: 2 }, { nome: "p3", buffer: B.p3, tamanho: 2 },
        { nome: "p4", buffer: B.p4, tamanho: 2 }, { nome: "c1", buffer: B.c1, tamanho: 3 },
        { nome: "c2", buffer: B.c2, tamanho: 3 }, { nome: "seed", buffer: B.seed, tamanho: 1 },
      ]);
      g.uniform1f(u(P.pontos, "uK"), k);
      g.uniform1f(u(P.pontos, "uT"), t);
      g.uniform1f(u(P.pontos, "uPix"), dpr);
      g.uniform1f(u(P.pontos, "uTam"), estreito() ? 2.1 : 2.4);
      g.uniform1f(u(P.pontos, "uOp"), Math.min(1, k / 0.45) * (1 - grampear01((k - 3.82) / 0.17)));
      g.uniform3fv(u(P.pontos, "uC0"), COR.poeira);
      g.uniform3fv(u(P.pontos, "uC3"), COR.medido);
      g.uniform3fv(u(P.pontos, "uC4"), COR.fusor);
      g.uniform2f(u(P.pontos, "uRes"), W, H);
      g.uniform2f(u(P.pontos, "uDesl"), desl[0], desl[1]);
      g.drawArrays(g.POINTS, 0, nPontos);
      ligados.forEach((l) => g.disableVertexAttribArray(l));

      const opFios = grampear01((k - 2.55) / 0.45) * (1 - (vivo ? grampear01((k - 3.3) / 0.45) : 0)) * 0.32;
      if (opFios > 0.001) {
        g.useProgram(P.fios);
        ligados = ligar(g, P.fios, [{ nome: "p", buffer: B.fios, tamanho: 2 }]);
        g.uniform2f(u(P.fios, "uRes"), W, H);
        g.uniform2f(u(P.fios, "uDesl"), desl[0], desl[1]);
        g.uniform3fv(u(P.fios, "uCor"), COR.medido);
        g.uniform1f(u(P.fios, "uOp"), opFios);
        g.drawArrays(g.LINES, 0, FAMILIAS_DO_VETOR.reduce((s, f) => s + f.qtd, 0) * 2);
        ligados.forEach((l) => g.disableVertexAttribArray(l));
      }
    }

    if (veVazio && nVazio) {
      g.useProgram(P.vazio);
      ligados = ligar(g, P.vazio, [
        { nome: "ang", buffer: B.ang, tamanho: 1 },
        { nome: "rf", buffer: B.rf, tamanho: 1 },
        { nome: "seed", buffer: B.seedV, tamanho: 1 },
      ]);
      g.uniform1f(u(P.vazio, "uT"), t);
      g.uniform1f(u(P.vazio, "uR"), Math.max(20, O.r * Math.min(W, H)));
      g.uniform1f(u(P.vazio, "uPix"), dpr);
      g.uniform1f(u(P.vazio, "uOp"), 1 - O.sat * 0.85);
      g.uniform2f(u(P.vazio, "uCentro"), ra.left + ra.width / 2, ra.top + ra.height / 2);
      g.uniform2f(u(P.vazio, "uRes"), W, H);
      g.uniform3fv(u(P.vazio, "uCor"), COR.sem);
      g.drawArrays(g.POINTS, 0, nVazio);
      ligados.forEach((l) => g.disableVertexAttribArray(l));
    }
  }

  /* --------------------------------------------------------- interface */
  let passoAtual = -1;
  let opRotulos = -1;
  function atualizarInterface() {
    const p = grampear01(scrollY / Math.max(1, document.documentElement.scrollHeight - innerHeight));
    if (leitura) leitura.textContent = `${String(Math.round(p * 100)).padStart(3, "0")}%`;
    if (barra) barra.style.transform = `scaleX(${p})`;
    if (!vivo) return;

    const k = S.k;
    const n = k < 1.5 ? 0 : k < 2.5 ? 1 : k < 3.5 ? 2 : 3;
    if (n !== passoAtual) {
      passoAtual = n;
      passos.forEach((el, i) => el.toggleAttribute("data-ativo", i === n));
      notaFim?.toggleAttribute("data-ativo", n === 3);
    }
    const op = Math.round(grampear01((k - 2.6) / 0.4) * (1 - grampear01((k - 3.3) / 0.3)) * 100) / 100;
    if (op !== opRotulos) {
      opRotulos = op;
      rotulos.forEach((r) => (r.style.opacity = String(op)));
    }
    if (tituloHero) {
      const ph = grampear01(scrollY / Math.max(1, hero!.offsetHeight));
      tituloHero.style.transform = `translateY(${-18 * ph}%)`;
      tituloHero.style.opacity = String(1 - 0.75 * ph);
    }
  }

  /* -------------------------------------------------------------- laco */
  let tFundo = 3;
  let tOrbe = 3;
  let ultimo = performance.now();
  function quadro(agora: number) {
    const dt = Math.min(0.05, (agora - ultimo) / 1000);
    ultimo = agora;
    W = innerWidth;
    H = innerHeight;
    const alvoK = kDaRolagem();
    S.k += (alvoK - S.k) * (vivo ? 0.12 : 1);
    if (Math.abs(alvoK - S.k) < 0.0005) S.k = alvoK;
    S.mxA += (S.mx - S.mxA) * 0.05;
    S.myA += (S.my - S.myA) * 0.05;
    const alvo = orbeEntreQuadros(quadros, scrollY);
    for (const c of Object.keys(O) as (keyof EstadoDoOrbe)[]) O[c] += (alvo[c] - O[c]) * (vivo ? 0.12 : 1);
    if (vivo) {
      tFundo += dt;
      tOrbe += dt * O.vel;
    }
    desenhar(tFundo, tOrbe);
    atualizarInterface();
  }

  let lenis: Lenis | null = null;
  let raf = 0;
  let pendente = false;
  const pedirQuadro = () => {
    if (pendente) return;
    pendente = true;
    raf = requestAnimationFrame((t) => {
      pendente = false;
      quadro(t);
    });
  };

  function laco(t: number) {
    lenis?.raf(t);
    quadro(t);
    raf = requestAnimationFrame(laco);
  }

  const aoMover = (e: PointerEvent) => {
    S.mx = (e.clientX / innerWidth - 0.5) * 2;
    S.my = -(e.clientY / innerHeight - 0.5) * 2;
  };

  const aoClicar = (e: MouseEvent) => {
    const a = (e.target as Element | null)?.closest?.('a[href^="#"]');
    if (!a || !lenis) return;
    const alvo = raiz.querySelector<HTMLElement>(a.getAttribute("href")!);
    if (!alvo) return;
    e.preventDefault();
    lenis.scrollTo(alvo, { offset: DESLOCAMENTO_DO_TOPO });
  };

  let tempoResize = 0;
  let larguraConstruida = 0;
  let alturaDoPalco = 0;
  function remontar() {
    medirCanvas();
    montarQuadros();
    const ph = palco!.getBoundingClientRect().height;
    if (innerWidth !== larguraConstruida || Math.abs(ph - alturaDoPalco) > 2) {
      larguraConstruida = innerWidth;
      alturaDoPalco = ph;
      construirCeu();
    }
    if (!vivo) pedirQuadro();
  }
  const aoRedimensionar = () => {
    clearTimeout(tempoResize);
    tempoResize = window.setTimeout(remontar, 150);
  };
  const observador = new ResizeObserver(aoRedimensionar);

  let cancelado = false;
  async function comecar() {
    try {
      await Promise.race([document.fonts.ready, new Promise((r) => setTimeout(r, 2500))]);
    } catch {
      /* fonte que nao carrega so troca a amostragem pela fonte de sistema */
    }
    if (cancelado) return;
    remontar();
    observador.observe(raiz);
    addEventListener("resize", aoRedimensionar);
    if (vivo) {
      lenis = new Lenis({ lerp: 0.1, smoothWheel: true });
      addEventListener("pointermove", aoMover, { passive: true });
      raiz.addEventListener("click", aoClicar);
      raf = requestAnimationFrame(laco);
    } else {
      addEventListener("scroll", pedirQuadro, { passive: true });
      pedirQuadro();
    }
  }
  comecar();

  return () => {
    cancelado = true;
    cancelAnimationFrame(raf);
    clearTimeout(tempoResize);
    observador.disconnect();
    lenis?.destroy();
    removeEventListener("resize", aoRedimensionar);
    removeEventListener("scroll", pedirQuadro);
    removeEventListener("pointermove", aoMover);
    raiz.removeEventListener("click", aoClicar);
    rotulos.forEach((r) => r.remove());
    raiz.classList.remove("vt-vivo", "vt-estatico");
    g.getExtension("WEBGL_lose_context")?.loseContext();
  };
}
