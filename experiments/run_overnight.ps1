# Corre a matriz final durante a noite, no Windows, e depois a análise.
#
#   powershell -ExecutionPolicy Bypass -File experiments\run_overnight.ps1
#
# A passagem 1 corre a matriz toda; as passagens 2 e 3 só repetem os runs que ficaram inválidos ou
# falharam (o run_matrix.py salta os runs válidos do mesmo commit). O registo fica em runs\overnight.log.
# A máquina tem de estar ligada à corrente e com a tampa aberta.
$ErrorActionPreference = 'Continue'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force runs | Out-Null
$log = 'runs\overnight.log'
function Log($message) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $message" | Tee-Object -FilePath $log -Append }
$python = '.venv\Scripts\python.exe'

$clean = $false
foreach ($pass in 1..3) {
    Log "pass $pass : run_matrix"
    & $python experiments/run_matrix.py --matrix main --seeds 1-10 --workers 4 *>> $log
    $code = $LASTEXITCODE
    Log "pass $pass exit=$code"
    if ($code -eq 0) { $clean = $true; break }
    if ($code -eq 2) { Log "uncommitted changes: stopping"; exit 2 }
}
Log "matrix clean=$clean ; running analyse.py"
& $python experiments/analyse.py *>> $log
Log "analyse exit=$LASTEXITCODE ; DONE"
