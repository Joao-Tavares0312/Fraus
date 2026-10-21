/** Superfícies agora são opacas: o piso é a própria cor, sem cena a compor. */
import { css, temas } from "./cores.mjs";

for (const tema of temas) {
  console.log(`\n=== tema: ${tema.nome} ===`);
  console.table(["--background", "--card", "--popover", "--sidebar"].map((token) => {
    // Resolver a cor também recusa transparência ou token desconhecido.
    tema.cor(token);
    return { superficie: token, piso: tema.valores.get(token), opacidade: "100%" };
  }));
}
for (const [classe, token] of [["superficie", "card"], ["superficie-flutuante", "popover"]]) {
  const regra = css.match(new RegExp(`\\.${classe}\\s*\\{([^}]+)\\}`));
  if (!regra || !new RegExp(`background(?:-color)?:\\s*var\\(--${token}\\)`).test(regra[1]) || /opacity\s*:|backdrop-filter\s*:/.test(regra[1])) {
    throw new Error(`O piso de ${classe} deixou de ser a superfície opaca --${token}. Atualize o modelo de medição antes de liberar transparência.`);
  }
}
console.log("Pisos opacos: nenhum fundo cenográfico interfere na leitura da ferramenta.");
