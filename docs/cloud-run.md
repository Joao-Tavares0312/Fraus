# API no Google Cloud Run

O deploy recomendado quando a Oracle Ampere não tem capacidade disponível é:

```text
dashboard (Vercel)
        ↓ proxy Next.js
API FastAPI (Cloud Run, ONNX, escala a zero)
        ├── pesos somente leitura (Cloud Storage)
        └── estado persistente (Postgres do Supabase)
```

Os modelos **não entram na imagem**. O Cloud Run monta o bucket como um volume
em `/artefatos`; o Supabase substitui o SQLite efêmero. Isso mantém a imagem
menor e separa código, artefato de treino e estado operacional.

## Pré-requisitos

1. Um projeto Google Cloud com faturamento habilitado.
2. [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) instalado.
3. `gcloud auth login` executado.
4. Os diretórios locais `modelos/` e `modelos-onnx/` completos.
5. A URL do **Transaction Pooler** do Supabase, preferencialmente na porta
   `6543`, terminando em `?sslmode=require`.

O projeto já aceita essa URL em `FRAUS_DATABASE_URL` e usa pool de conexões.
Não use a chave pública `anon` do Supabase: ela não é uma conexão Postgres.

## Publicar

No PowerShell, a partir da raiz do repositório:

```powershell
pwsh scripts/configurar_cloud_run.ps1 `
  -ProjectId SEU_PROJECT_ID `
  -DashboardUrl https://SEU-PROJETO.vercel.app
```

Na primeira execução, o script pede sem ecoar:

- a URL do pooler do Supabase;
- um código de convite para criar usuários.

A chave mestra e o segredo JWT são gerados criptograficamente. Os quatro
valores ficam no Secret Manager; não entram em argumentos, logs, imagem ou Git.
Execuções seguintes preservam os valores existentes.

O script também:

- cria um bucket regional em `us-central1` e envia os 939 MB de ONNX mais o
  fusor e as métricas;
- cria uma conta de serviço com leitura somente do bucket e dos quatro
  segredos;
- constrói a imagem com `BACKEND=onnx`;
- publica uma instância de 1 vCPU e 2 GiB de RAM;
- limita concorrência e máximo de instâncias a `1`;
- mantém mínimo `0`, permitindo escala a zero;
- expõe HTTPS público, com autenticação feita pelo próprio Fraus.

## Verificar

Pegue a URL mostrada ao final e confira:

```powershell
Invoke-RestMethod https://SUA-API.run.app/saude
```

O resultado precisa conter:

```json
{"status":"ok","motor":"real"}
```

Se aparecer `motor: duble`, pare: servir previsão sem os três modelos viola a
invariante 7. Se o primeiro acesso demorar, é o cold start carregando os três
grafos ONNX através do volume.

## Ligar a Vercel

Gere uma chave de acesso `fra_` usando a chave mestra guardada no Secret
Manager. Depois configure no projeto da dashboard:

```text
FRAUS_API_URL=https://SUA-API.run.app
FRAUS_CHAVE_ACESSO=fra_...
```

Faça um novo deploy da Vercel após salvar as variáveis.

## Limite de custo

A configuração foi desenhada para pouco tráfego dentro das franquias gratuitas,
mas franquia não é bloqueio de cobrança. O máximo de uma instância contém a
escala horizontal; ele não impede cobrança caso CPU, RAM, build, logs ou rede
ultrapassem os limites mensais. Crie um budget e alertas no Billing antes da
primeira publicação e mantenha o bucket em uma das regiões elegíveis ao Free
Tier (`us-central1` é o padrão do script).

Não configure `min-instances=1`: manter o modelo quente continuamente consome a
franquia mesmo sem usuários.
