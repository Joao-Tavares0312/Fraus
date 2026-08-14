# Treinar no Colab pelo terminal

A máquina de desenvolvimento não tem GPU CUDA, então o fine-tuning do BERTimbau
e dos sinais de emoção e ironia roda no Google Colab. Este documento descreve as
duas ferramentas instaladas para isso e por que cada uma vive onde vive.

São ferramentas diferentes, com propósitos diferentes:

- **`colab` (CLI)** — provisiona uma VM com GPU, roda um script local nela,
  baixa os pesos e desliga a VM. É o caminho para treinar.
- **`colab-mcp`** — liga o agente a um notebook aberto no navegador. É o caminho
  para inspecionar uma sessão que já está rodando.

## A CLI vive no WSL, não no Windows

A CLI **não suporta Windows** — só Linux e macOS, conforme o README do projeto.
Por isso ela foi instalada dentro da distro `AzureLinux-4` do WSL, e não no
Windows diretamente. Não adianta tentar `pip install` no PowerShell.

Instalação feita (não precisa repetir):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install google-colab-cli
```

O `uv tool update-shell` já colocou `~/.local/bin` no PATH do shell de login,
então `colab` responde em qualquer `wsl -d AzureLinux-4 -- bash -lc "..."`.

### Autenticação

> Os comandos abaixo aparecem com o prefixo `wsl -d AzureLinux-4 -- bash -lc`
> porque são escritos para quem chama **do PowerShell**, de fora. Se você já
> estiver dentro do WSL (prompt `dell08@...:~$`), use só a parte entre aspas —
> `wsl` é comando do Windows e não existe lá dentro.

Passo manual e único, porque exige uma conta Google e um navegador:

```bash
wsl -d AzureLinux-4 -- bash -lc "colab sessions"
```

A CLI imprime uma URL. Abra no navegador, aprove com a conta que tem o Colab, e
cole de volta o código que o Google mostrar. O token fica salvo; as execuções
seguintes não perguntam mais.

Se preferir OAuth em vez do fluxo padrão (ADC), use `--auth oauth2`.

### Treinar

O `colab run` faz o ciclo inteiro numa linha: sobe uma VM nova, roda o script,
e derruba a VM ao terminar — o que importa quando a cobrança é por unidade de
computação.

```bash
wsl -d AzureLinux-4 -- bash -lc "cd /mnt/c/Users/dell08/Documents/GitHub/Fraus && colab run --gpu T4 scripts/treinar.py"
```

O repositório é visível dentro do WSL em `/mnt/c/...`, então não é preciso
clonar de novo lá dentro.

Para uma sessão que sobrevive entre comandos, o fluxo é `colab new --gpu T4`,
depois `colab exec`/`colab upload`/`colab download`, e `colab stop` no fim.
**A VM não desliga sozinha** nesse modo — a CLI mantém um daemon de keep-alive
justamente para impedir a expiração por ociosidade. Esqueça o `colab stop` e a
VM segue consumindo.

Os notebooks em `notebooks/` continuam válidos para o fluxo pelo navegador; a
CLI é uma alternativa, não uma substituição.

## O MCP vive no Windows

O `colab-mcp` não tem a restrição de plataforma da CLI — roda por `uvx` no
Windows mesmo. Ele é uma ponte para uma sessão de Colab **aberta no navegador**,
não um provisionador de VM.

Registro em `.mcp.json` na raiz do repositório:

```json
{
  "mcpServers": {
    "colab-mcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/googlecolab/colab-mcp", "colab-mcp"],
      "timeout": 30000
    }
  }
}
```

O servidor é buscado do git a cada partida, sem versão fixada — é o que a
documentação oficial recomenda. Em troca, uma mudança no repositório do Google
chega sem aviso. Se algum dia isso quebrar o ambiente, fixe o commit trocando a
URL por `git+https://github.com/googlecolab/colab-mcp@<sha>`.
