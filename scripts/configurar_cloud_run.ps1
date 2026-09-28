<#
.SYNOPSIS
Configura e publica a API real do Fraus no Cloud Run.

.DESCRIPTION
Idempotente: recursos existentes e versoes de segredo existentes sao
preservados. Os modelos ONNX e o fusor vao para Cloud Storage e entram no
container por volume somente leitura. O banco e o Supabase, via Secret Manager.

Requer Google Cloud CLI autenticado e um projeto com faturamento habilitado.
O desenho foi limitado para uso pequeno: escala a zero e no maximo uma
instancia. Isso reduz o risco de custo, mas franquia gratuita nao e trava de
cobranca; crie tambem um budget no Console.

.EXAMPLE
pwsh scripts/configurar_cloud_run.ps1 `
  -ProjectId meu-projeto `
  -DashboardUrl https://fraus-one.vercel.app
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z][a-z0-9-]{4,28}[a-z0-9]$')]
    [string]$ProjectId,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^https://')]
    [string]$DashboardUrl,

    [string]$Region = 'us-central1',
    [string]$Service = 'fraus-api',
    [string]$Repository = 'fraus',
    [string]$Bucket = "$ProjectId-fraus-modelos"
)

$ErrorActionPreference = 'Stop'
$Raiz = Split-Path -Parent $PSScriptRoot
$ContaServico = "fraus-api@$ProjectId.iam.gserviceaccount.com"
$Imagem = "$Region-docker.pkg.dev/$ProjectId/$Repository/api:latest"
$Segredos = @(
    'fraus-database-url',
    'fraus-chave-mestra',
    'fraus-jwt-segredo',
    'fraus-codigo-convite'
)

function Passo([string]$Mensagem) {
    Write-Host "`n== $Mensagem" -ForegroundColor Cyan
}

function Exigir-UltimoExitCode([string]$Mensagem) {
    if ($LASTEXITCODE -ne 0) { throw $Mensagem }
}

function Novo-HexSeguro {
    $bytes = [byte[]]::new(32)
    [Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    return [Convert]::ToHexString($bytes).ToLowerInvariant()
}

function Adicionar-Segredo([string]$Nome, [string]$Valor) {
    $temporario = [IO.Path]::GetTempFileName()
    try {
        [IO.File]::WriteAllText($temporario, $Valor)
        & gcloud secrets versions add $Nome --data-file=$temporario --project=$ProjectId --quiet
        Exigir-UltimoExitCode "nao foi possivel gravar o segredo $Nome"
    }
    finally {
        Remove-Item -LiteralPath $temporario -Force -ErrorAction SilentlyContinue
    }
}

function Garantir-Segredo([string]$Nome) {
    & gcloud secrets describe $Nome --project=$ProjectId --quiet 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   $Nome ja existe; valor preservado"
        return
    }

    & gcloud secrets create $Nome --replication-policy=automatic --project=$ProjectId --quiet | Out-Null
    Exigir-UltimoExitCode "nao foi possivel criar o segredo $Nome"

    switch ($Nome) {
        'fraus-chave-mestra' { $valor = Novo-HexSeguro }
        'fraus-jwt-segredo' { $valor = Novo-HexSeguro }
        'fraus-database-url' {
            $seguro = Read-Host 'Cole a URL do pooler Supabase (postgresql://..., porta 6543, sslmode=require)' -AsSecureString
            $ponteiro = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($seguro)
            try { $valor = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ponteiro) }
            finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ponteiro) }
        }
        'fraus-codigo-convite' {
            $seguro = Read-Host 'Defina o codigo de convite para cadastro' -AsSecureString
            $ponteiro = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($seguro)
            try { $valor = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ponteiro) }
            finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ponteiro) }
        }
    }
    if ([string]::IsNullOrWhiteSpace($valor)) { throw "$Nome nao pode ser vazio" }
    Adicionar-Segredo $Nome $valor
    $valor = $null
}

Set-Location $Raiz

Passo 'Pre-requisitos locais'
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw 'Google Cloud CLI nao encontrado. Instale em https://cloud.google.com/sdk/docs/install e rode gcloud auth login.'
}
foreach ($caminho in @('modelos-onnx', 'modelos/fusor.joblib')) {
    if (-not (Test-Path -LiteralPath (Join-Path $Raiz $caminho))) {
        throw "artefato ausente: $caminho. A API real nao pode subir sem modelo."
    }
}

& gcloud config set project $ProjectId | Out-Null
Exigir-UltimoExitCode 'projeto invalido ou sem acesso'

Passo 'APIs do Google Cloud'
& gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com storage.googleapis.com iam.googleapis.com --project=$ProjectId --quiet
Exigir-UltimoExitCode 'nao foi possivel habilitar as APIs; confira faturamento e permissoes'

Passo 'Bucket regional dos modelos'
& gcloud storage buckets describe "gs://$Bucket" --project=$ProjectId 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    & gcloud storage buckets create "gs://$Bucket" --project=$ProjectId --location=$Region --uniform-bucket-level-access
    Exigir-UltimoExitCode 'nao foi possivel criar o bucket'
}
& gcloud storage rsync (Join-Path $Raiz 'modelos-onnx') "gs://$Bucket/modelos-onnx" --recursive --delete-unmatched-destination-objects
Exigir-UltimoExitCode 'falha ao enviar os modelos ONNX'
& gcloud storage cp (Join-Path $Raiz 'modelos/fusor.joblib') "gs://$Bucket/modelos/fusor.joblib"
Exigir-UltimoExitCode 'falha ao enviar o fusor'
foreach ($arquivo in @(
    'modelos/bertimbau-satisfacao/metricas.json',
    'modelos/metricas_emocao.json',
    'modelos/metricas_ironia.json'
)) {
    $local = Join-Path $Raiz $arquivo
    if (Test-Path -LiteralPath $local) {
        & gcloud storage cp $local "gs://$Bucket/$($arquivo.Replace('\', '/'))"
        Exigir-UltimoExitCode "falha ao enviar $arquivo"
    }
}

Passo 'Conta de servico e permissoes minimas'
& gcloud iam service-accounts describe $ContaServico --project=$ProjectId 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    & gcloud iam service-accounts create fraus-api --display-name='Fraus API no Cloud Run' --project=$ProjectId
    Exigir-UltimoExitCode 'nao foi possivel criar a conta de servico'
}
& gcloud storage buckets add-iam-policy-binding "gs://$Bucket" --member="serviceAccount:$ContaServico" --role=roles/storage.objectViewer --project=$ProjectId --quiet | Out-Null
Exigir-UltimoExitCode 'nao foi possivel liberar leitura do bucket'

Passo 'Segredos (valores existentes nunca sao sobrescritos)'
foreach ($segredo in $Segredos) { Garantir-Segredo $segredo }
foreach ($segredo in $Segredos) {
    & gcloud secrets add-iam-policy-binding $segredo --member="serviceAccount:$ContaServico" --role=roles/secretmanager.secretAccessor --project=$ProjectId --quiet | Out-Null
    Exigir-UltimoExitCode "nao foi possivel liberar o segredo $segredo"
}

Passo 'Repositorio e build da imagem ONNX'
& gcloud artifacts repositories describe $Repository --location=$Region --project=$ProjectId 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    & gcloud artifacts repositories create $Repository --repository-format=docker --location=$Region --description='Imagens do Fraus' --project=$ProjectId
    Exigir-UltimoExitCode 'nao foi possivel criar o Artifact Registry'
}
$ContaBuild = & gcloud builds get-default-service-account --project=$ProjectId
Exigir-UltimoExitCode 'nao foi possivel descobrir a conta usada pelo Cloud Build'
& gcloud artifacts repositories add-iam-policy-binding $Repository --location=$Region --member="serviceAccount:$ContaBuild" --role=roles/artifactregistry.writer --project=$ProjectId --quiet | Out-Null
Exigir-UltimoExitCode 'nao foi possivel liberar o push da imagem pelo Cloud Build'
& gcloud builds submit --config=cloudbuild.yaml --substitutions="_IMAGE=$Imagem" --project=$ProjectId .
Exigir-UltimoExitCode 'o build da imagem falhou'

Passo 'Deploy no Cloud Run'
$Variaveis = @(
    'FRAUS_BACKEND=onnx',
    'FRAUS_CAMINHO_ONNX_TEXTO=/artefatos/modelos-onnx/bertimbau-satisfacao',
    'FRAUS_CAMINHO_ONNX_EMOCAO=/artefatos/modelos-onnx/bertimbau-emocao',
    'FRAUS_CAMINHO_ONNX_IRONIA=/artefatos/modelos-onnx/bertimbau-ironia',
    'FRAUS_CAMINHO_FUSOR=/artefatos/modelos/fusor.joblib',
    'FRAUS_CAMINHO_METRICAS=/artefatos/modelos/bertimbau-satisfacao/metricas.json',
    'FRAUS_CAMINHO_METRICAS_EMOCAO=/artefatos/modelos/metricas_emocao.json',
    'FRAUS_CAMINHO_METRICAS_IRONIA=/artefatos/modelos/metricas_ironia.json',
    "FRAUS_ORIGENS=$DashboardUrl"
) -join ','

& gcloud run deploy $Service `
    --image=$Imagem `
    --region=$Region `
    --project=$ProjectId `
    --service-account=$ContaServico `
    --execution-environment=gen2 `
    --cpu=1 `
    --memory=2Gi `
    --concurrency=1 `
    --max-instances=1 `
    --min-instances=0 `
    --timeout=300 `
    --cpu-boost `
    --allow-unauthenticated `
    --set-env-vars=$Variaveis `
    --set-secrets='FRAUS_DATABASE_URL=fraus-database-url:latest,FRAUS_CHAVE_MESTRA=fraus-chave-mestra:latest,FRAUS_JWT_SEGREDO=fraus-jwt-segredo:latest,FRAUS_CODIGO_CONVITE=fraus-codigo-convite:latest' `
    --add-volume="mount-path=/artefatos,type=cloud-storage,bucket=$Bucket,readonly=true"
Exigir-UltimoExitCode 'o deploy no Cloud Run falhou'

$Url = & gcloud run services describe $Service --region=$Region --project=$ProjectId --format='value(status.url)'
Exigir-UltimoExitCode 'nao foi possivel ler a URL publicada'

Passo 'Pronto'
Write-Host "API: $Url"
Write-Host 'Proximos passos:'
Write-Host "  1. confira GET $Url/saude (motor precisa ser real);"
Write-Host '  2. gere uma chave fra_ usando a mestra do Secret Manager;'
Write-Host '  3. configure FRAUS_API_URL e FRAUS_CHAVE_ACESSO na Vercel;'
Write-Host '  4. crie um budget/alerta no Google Cloud.'
