// Tipo minimo do pngjs (vem com o vgpu, sem @types): so o que os posteres usam.
declare module "pngjs" {
  export class PNG {
    constructor(opcoes: { width: number; height: number });
    data: Uint8Array;
    static sync: { write(png: PNG): Buffer };
  }
}
