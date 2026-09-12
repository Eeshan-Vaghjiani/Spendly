param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string] $PlantUmlJar
)

$ErrorActionPreference = 'Stop'
$diagramSource = Join-Path $PSScriptRoot '*.puml'

& java '-DPLANTUML_LIMIT_SIZE=16384' -jar $PlantUmlJar -charset UTF-8 -tsvg $diagramSource
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& java '-DPLANTUML_LIMIT_SIZE=16384' -jar $PlantUmlJar -charset UTF-8 -tpng $diagramSource
exit $LASTEXITCODE

