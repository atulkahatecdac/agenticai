# Renders every slide of a deck to PNG through PowerPoint, for visual QA after a build.
#   powershell -ExecutionPolicy Bypass -File tools\deck_builder\tools\render.ps1 -Deck 16_PGP-Agentic\PGP_Agentic_AI.pptx -OutDir out_png
param(
  [Parameter(Mandatory = $true)][string]$Deck,
  [Parameter(Mandatory = $true)][string]$OutDir,
  [int]$Width = 1280
)
$ErrorActionPreference = "Stop"
$Deck = (Resolve-Path $Deck).Path
New-Item -ItemType Directory -Force $OutDir | Out-Null
$OutDir = (Resolve-Path $OutDir).Path
Get-ChildItem $OutDir -Filter "*.png" | Remove-Item
$ppt = New-Object -ComObject PowerPoint.Application
$p = $ppt.Presentations.Open($Deck, $true, $false, $false)
try {
  foreach ($i in 1..$p.Slides.Count) {
    $p.Slides($i).Export(("{0}\{1:D3}.png" -f $OutDir, $i), "PNG", $Width, [int]($Width * 9 / 16))
  }
  "Rendered $($p.Slides.Count) slides to $OutDir"
} finally {
  $p.Close(); $ppt.Quit()
}
