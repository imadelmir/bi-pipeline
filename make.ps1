<#
.SYNOPSIS
  Gli stessi comandi del Makefile, per Windows senza GNU Make.

.DESCRIPTION
  Il contratto del progetto è il Makefile: questo script espone gli stessi
  nomi e le stesse azioni, così il README resta uno solo.
  Se cambi un comando qui, cambialo anche nel Makefile.

.ESEMPI
  .\make.ps1            elenca i comandi
  .\make.ps1 up
  .\make.ps1 check
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Comando = 'help'
)

$ErrorActionPreference = 'Stop'

# Le azioni: stessa riga di comando del Makefile, stessa descrizione.
$comandi = [ordered]@{
    'up'     = @{ descrizione = 'Alza i servizi Docker e aspetta che il database risponda'
                  azione      = { docker compose up -d --wait } }
    'down'   = @{ descrizione = 'Ferma i servizi (il volume dei dati resta)'
                  azione      = { docker compose down } }
    'psql'   = @{ descrizione = 'Apre psql dentro il contenitore del database'
                  azione      = { docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' } }
    'check'  = @{ descrizione = 'Formattazione, lint e tipi - gli stessi controlli della CI'
                  azione      = {
                      uv run --frozen ruff format --check .
                      if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
                      uv run --frozen ruff check .
                      if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
                      uv run --frozen mypy
                  } }
    'format' = @{ descrizione = 'Formatta e corregge quello che si puo correggere da solo'
                  azione      = {
                      uv run --frozen ruff format .
                      uv run --frozen ruff check --fix .
                  } }
    'ingest' = @{ descrizione = 'Scarica, verifica il checksum e carica in raw con COPY'
                  azione      = { Write-Host 'Non ancora implementato: arriva con M2-T1 (scaricamento) e M2-T5 (COPY).'; exit 1 } }
    'build'  = @{ descrizione = 'dbt build: modelli e test insieme'
                  azione      = { Write-Host 'Non ancora implementato: arriva con M3-T1 (dbt init).'; exit 1 } }
    'test'   = @{ descrizione = 'Solo i test dbt, senza ricostruire i modelli'
                  azione      = { Write-Host 'Non ancora implementato: arriva con M5-T1.'; exit 1 } }
    'docs'   = @{ descrizione = 'Genera e apre la documentazione dbt con il lineage'
                  azione      = { Write-Host 'Non ancora implementato: arriva con M5-T9.'; exit 1 } }
    'flow'   = @{ descrizione = 'Il flusso Prefect completo, dall inizio alla fine'
                  azione      = { Write-Host 'Non ancora implementato: arriva con M6-T1.'; exit 1 } }
}

if ($Comando -eq 'help') {
    Write-Host 'Comandi disponibili:'
    foreach ($nome in $comandi.Keys) {
        Write-Host ('  {0,-10} {1}' -f $nome, $comandi[$nome].descrizione)
    }
    exit 0
}

if (-not $comandi.Contains($Comando)) {
    Write-Host "Comando sconosciuto: $Comando"
    Write-Host "Usa .\make.ps1 senza argomenti per l'elenco."
    exit 1
}

& $comandi[$Comando].azione
exit $LASTEXITCODE
