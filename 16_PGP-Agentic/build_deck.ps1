# Builds 16_PGP-Agentic\PGP_Agentic_AI.pptx from Session_Plan.md.
# Every slide referenced in the plan's tables is copied (in plan order) from the original
# course decks, which are only read, never modified. Each copied slide gets a white
# background and a DEMO bar holding that row's "Code example" cell.
# Re-run after editing Session_Plan.md:
#   powershell -ExecutionPolicy Bypass -File 16_PGP-Agentic\build_deck.ps1
# Close the output deck in PowerPoint first.
$ErrorActionPreference = "Stop"
$ROOT = "C:\code\agenticai"
$HERE = "$ROOT\16_PGP-Agentic"
$PLAN = "$HERE\Session_Plan.md"
$OUT  = "$HERE\PGP_Agentic_AI.pptx"
$decks = @{
  MAIN = @{ path = "$ROOT\0_slides\Agentic AI.pptx";                          label = "0_slides\Agentic AI.pptx" }
  ADV  = @{ path = "$ROOT\14_advanced\Agentic AI - Advanced Engineering.pptx"; label = "14_advanced\Agentic AI - Advanced Engineering.pptx" }
  REAL = @{ path = "$ROOT\15_real\Agentic AI - Real.pptx";                     label = "15_real\Agentic AI - Real.pptx" }
}
$ND = [char]0x2013   # en dash
$EM = [char]0x2014   # em dash
$CONCEPT = "Concept slide - no code; discuss"
$schedule = @{
  1 = "Sat 24-Oct"; 2 = "Sat 25-Oct"; 3 = "Sun 31-Oct"; 4 = "Sat 1-Nov"; 5 = "Sun 7-Nov"
  6 = "Sat 8-Nov";  7 = "Sun 14-Nov"; 8 = "Sat 15-Nov"; 9 = "Sun 21-Nov"
}

# ---------------------------------------------------------------- parse the plan
$sessions = New-Object System.Collections.ArrayList
$cur = $null; $topic = ""; $inTopics = $false
foreach ($line in (Get-Content $PLAN -Encoding UTF8)) {
  if ($line -match "^## Session (\d+)\s+\S\s+(.+)$") {
    $cur = @{ num = [int]$matches[1]; title = $matches[2].Trim(); topics = @(); items = New-Object System.Collections.ArrayList; seen = @{} }
    [void]$sessions.Add($cur); $inTopics = $false; continue
  }
  if (-not $cur) { continue }
  if ($line -match "^\*\*Topics\*\*") { $inTopics = $true; continue }
  if ($inTopics -and $line -match "^\d+\.\s+(.+)$") { $cur.topics += $matches[1].Trim().Replace('`', ''); continue }
  if ($line -match "^### (.+)$") { $inTopics = $false; $topic = $matches[1].Trim(); continue }
  if ($line -match "^\|\s*(MAIN|ADV|REAL)\s*\|") {
    $cells = $line.Trim().Trim("|").Split("|") | ForEach-Object { $_.Trim() }
    $rowDeck = $cells[0]; $slides = $cells[1]; $code = $cells[3].Replace('`', '').Replace('\|', '|')
    if ($code -eq "" -or $code.StartsWith([string]$EM)) { $code = $CONCEPT }
    $slides = [regex]::Replace($slides, "\(=[^)]*\)", "")
    foreach ($part in $slides.Split(";")) {
      $part = $part.Trim(); if ($part -eq "") { continue }
      $dk = $rowDeck
      if ($part -match "^(MAIN|ADV|REAL)\s+(.+)$") { $dk = $matches[1]; $part = $matches[2] }
      foreach ($m in [regex]::Matches($part, "(\d+)(?:\s*[-$ND]\s*(\d+))?")) {
        $a = [int]$m.Groups[1].Value
        $b = if ($m.Groups[2].Success) { [int]$m.Groups[2].Value } else { $a }
        for ($n = $a; $n -le $b; $n++) {
          $key = "$dk-$n"
          if ($cur.seen.ContainsKey($key)) { continue }   # same slide twice in one session
          $cur.seen[$key] = 1
          [void]$cur.items.Add(@{ deck = $dk; n = $n; demo = $code; topic = $topic })
        }
      }
    }
  }
}
$total = ($sessions | ForEach-Object { $_.items.Count } | Measure-Object -Sum).Sum
"Parsed $($sessions.Count) sessions, $total source slides"

# ---------------------------------------------------------------- helpers
function Set-White($sl) {
  $sl.FollowMasterBackground = 0
  $sl.Background.Fill.Solid()
  $sl.Background.Fill.ForeColor.RGB = 16777215
}
# Bar geometry depends on text length: 1 line at 12pt, 1 line at 10.5pt, or 2 lines.
function Demo-Geometry([string]$text) {
  $len = $text.Length + 7
  if ($len -le 150) { return @{ size = 12;   h = 26; top = 506 } }
  if ($len -le 180) { return @{ size = 10.5; h = 26; top = 506 } }
  return @{ size = 10.5; h = 40; top = 492 }
}
function Add-Demo($sl, [string]$text, $g) {
  $box = $sl.Shapes.AddShape(5, 20, [single]$g.top, 920, [single]$g.h)   # rounded rectangle
  $box.Name = "DemoCallout"
  $box.Adjustments.Item(1) = 0.25
  $box.Fill.ForeColor.RGB = 0xF7F1EB    # BGR -> #EBF1F7
  $box.Line.ForeColor.RGB = 0xC89E5B    # BGR -> #5B9EC8
  $box.Line.Weight = 0.75
  $tf = $box.TextFrame
  $tf.MarginLeft = 8; $tf.MarginRight = 8; $tf.MarginTop = 2; $tf.MarginBottom = 2
  $tf.WordWrap = -1
  $tf.AutoSize = 0
  $tf.VerticalAnchor = 3
  $tf.TextRange.Text = "DEMO:  " + $text
  $tf.TextRange.ParagraphFormat.Alignment = 1
  $tr = $tf.TextRange
  $tr.Font.Name = "Calibri"; $tr.Font.Size = [single]$g.size; $tr.Font.Color.RGB = 0x333333
  $tr.Font.Bold = 0; $tr.Font.Italic = 0
  $tr.Characters(1, 5).Font.Bold = -1
  $tr.Characters(1, 5).Font.Color.RGB = 0x7A4A1F   # BGR -> #1F4A7A
}
function Scale-Fonts($shp, [double]$f) {
  if ($shp.HasTable) {
    $t = $shp.Table
    for ($r = 1; $r -le $t.Rows.Count; $r++) { for ($c = 1; $c -le $t.Columns.Count; $c++) {
      $tr = $t.Cell($r, $c).Shape.TextFrame.TextRange
      # table cell fonts snap to whole points, so round down or small shrinks round back up
      for ($i = 1; $i -le $tr.Runs().Count; $i++) { $run = $tr.Runs($i); $run.Font.Size = [single][math]::Max(6, [math]::Floor($run.Font.Size * $f)) }
    } }
  } elseif ($shp.Type -eq 6) {
    foreach ($gi in $shp.GroupItems) { Scale-Fonts $gi $f }
  } elseif ($shp.HasTextFrame -and $shp.TextFrame.HasText) {
    $tr = $shp.TextFrame.TextRange
    for ($i = 1; $i -le $tr.Runs().Count; $i++) { $run = $tr.Runs($i); $run.Font.Size = [math]::Max(6, $run.Font.Size * $f) }
  }
}
function Content-Bottom($sl) {
  $b = 0
  foreach ($shp in $sl.Shapes) {
    if ($shp.Top -ge 530) { continue }   # off-slide leftovers (e.g. photo credits)
    if ($shp.HasTextFrame -and -not $shp.HasTable -and $shp.Type -ne 6 -and $shp.Type -ne 13) {
      if (-not $shp.TextFrame.HasText) { continue }
      $tr = $shp.TextFrame.TextRange
      $bb = [math]::Max($tr.BoundTop + $tr.BoundHeight, 0)
      if ($shp.Fill.Visible -or $shp.Line.Visible) { $bb = [math]::Max($bb, $shp.Top + $shp.Height) }
    } else { $bb = $shp.Top + $shp.Height }
    if ($bb -gt $b) { $b = $bb }
  }
  return $b
}
# Shrink everything proportionally (about top-centre) so content ends above the demo bar.
# Re-measures after each pass (tables/autofit text don't always shrink by the full factor).
# Slides that would need more than a 40% shrink are left as-is and reported.
function Fit-Content($sl, [double]$limit, [string]$label) {
  for ($pass = 1; $pass -le 3; $pass++) {
    $b = Content-Bottom $sl
    if ($b -le $limit) { return }
    $f = $limit / $b
    if ($f -lt 0.6) { Write-Output "  WARN: $label needs $([math]::Round($f, 2)) shrink - left unchanged (check source slide)"; return }
    Scale-Slide $sl $f
  }
}
function Scale-Slide($sl, [double]$f) {
  $cx = 480
  foreach ($shp in @($sl.Shapes)) {
    $l = $shp.Left; $t = $shp.Top; $w = $shp.Width; $h = $shp.Height
    Scale-Fonts $shp $f
    if ($shp.HasTable) {
      $tb = $shp.Table
      for ($c = 1; $c -le $tb.Columns.Count; $c++) { $tb.Columns.Item($c).Width = $tb.Columns.Item($c).Width * $f }
      for ($r = 1; $r -le $tb.Rows.Count; $r++) { $tb.Rows.Item($r).Height = $tb.Rows.Item($r).Height * $f }
    } else {
      $shp.LockAspectRatio = 0
      $shp.Width = $w * $f; $shp.Height = $h * $f
    }
    $shp.Left = $cx + ($l - $cx) * $f
    $shp.Top = $t * $f
  }
}
function Add-Note($sl, [string]$text) {
  $ph = $sl.NotesPage.Shapes.Placeholders.Item(2)
  $old = $ph.TextFrame.TextRange.Text
  if ($old.Trim().Length -gt 0) { $ph.TextFrame.TextRange.Text = $text + "`r`r" + $old }
  else { $ph.TextFrame.TextRange.Text = $text }
}
function Layout($p, [string]$name) {
  foreach ($l in $p.SlideMaster.CustomLayouts) { if ($l.Name -eq $name) { return $l } }
  throw "layout $name not found"
}

# ---------------------------------------------------------------- build
$pp = New-Object -ComObject PowerPoint.Application
$base = "$env:TEMP\pgp_base.pptx"
$src = $pp.Presentations.Open($decks.REAL.path, $true, $true, $false)   # read-only, no window
$src.SaveCopyAs($base); $src.Close()
$p = $pp.Presentations.Open($base, $false, $false, $false)
while ($p.Slides.Count -gt 0) { $p.Slides.Item(1).Delete() }

# Title slide
$sl = $p.Slides.AddSlide(1, (Layout $p "Title Slide")); Set-White $sl
$sl.Shapes.Placeholders.Item(1).TextFrame.TextRange.Text = "PGP $ND Agentic AI"
$sl.Shapes.Placeholders.Item(2).TextFrame.TextRange.Text = "Sessions 1 $ND 9  |  08:00 $ND 11:00 AM`rAtul Kahate"
Add-Note $sl "Demo paths on every slide are relative to the repo root c:\code\agenticai."

# Contents slide
$sl = $p.Slides.AddSlide(2, (Layout $p "Title Only")); Set-White $sl
$sl.Shapes.Placeholders.Item(1).TextFrame.TextRange.Text = "Sessions"
$t = $sl.Shapes.AddTable($sessions.Count + 1, 3, 40, 125, 880, 360).Table
$t.Columns.Item(1).Width = 110; $t.Columns.Item(2).Width = 130; $t.Columns.Item(3).Width = 640
$rows = @(,@("Session", "Date", "Topic"))
foreach ($s in $sessions) { $rows += ,@("Session $($s.num)", $schedule[$s.num], $s.title) }
for ($r = 1; $r -le $rows.Count; $r++) { for ($c = 1; $c -le 3; $c++) {
  $cell = $t.Cell($r, $c).Shape.TextFrame
  $cell.TextRange.Text = $rows[$r-1][$c-1]; $cell.TextRange.Font.Size = 16; $cell.TextRange.Font.Name = "Calibri"
} }

foreach ($s in $sessions) {
  # Session separator
  $idx = $p.Slides.Count + 1
  $sl = $p.Slides.AddSlide($idx, (Layout $p "Title Slide")); Set-White $sl
  $sl.Shapes.Placeholders.Item(1).TextFrame.TextRange.Text = "Session $($s.num)"
  $sl.Shapes.Placeholders.Item(1).TextFrame.TextRange.Font.Size = 60
  $sl.Shapes.Placeholders.Item(1).TextFrame.TextRange.Font.Bold = -1
  $sl.Shapes.Placeholders.Item(2).TextFrame.TextRange.Text = "$($s.title)`r$($schedule[$s.num])  |  08:00 $ND 11:00 AM"
  $sl.Shapes.Placeholders.Item(2).TextFrame.TextRange.Font.Size = 24
  Add-Note $sl ("Start of Session $($s.num)")

  # Topics slide for the session
  $idx = $p.Slides.Count + 1
  $sl = $p.Slides.AddSlide($idx, (Layout $p "Title and Content")); Set-White $sl
  $sl.Shapes.Placeholders.Item(1).TextFrame.TextRange.Text = "Session $($s.num) Topics"
  $body = $sl.Shapes.Placeholders.Item(2)
  $body.TextFrame.TextRange.Text = ($s.topics -join "`r")
  $body.TextFrame.TextRange.ParagraphFormat.Bullet.Type = 2          # numbered
  $body.TextFrame.TextRange.Font.Size = $(if ($s.topics.Count -le 10) { 20 } elseif ($s.topics.Count -le 12) { 18 } else { 15 })
  $body.TextFrame2.AutoSize = 2                                      # shrink text on overflow
  Add-Note $sl ("Session $($s.num) $ND " + $schedule[$s.num])

  # Group consecutive slides from the same deck into one InsertFromFile call
  $i = 0
  while ($i -lt $s.items.Count) {
    $j = $i
    while ($j + 1 -lt $s.items.Count -and $s.items[$j+1].deck -eq $s.items[$i].deck -and $s.items[$j+1].n -eq $s.items[$j].n + 1) { $j++ }
    $first = $p.Slides.Count + 1
    [void]$p.Slides.InsertFromFile($decks[$s.items[$i].deck].path, $p.Slides.Count, $s.items[$i].n, $s.items[$j].n)
    for ($k = $i; $k -le $j; $k++) {
      $it = $s.items[$k]
      $sl = $p.Slides.Item($first + ($k - $i))
      $g = Demo-Geometry $it.demo
      Set-White $sl
      Fit-Content $sl ($g.top - 6) "$($it.deck) slide $($it.n) (deck slide $($first + $k - $i))"
      Add-Demo $sl $it.demo $g
      Add-Note $sl ("Session $($s.num) | Topic: $($it.topic)`rSource: $($decks[$it.deck].label), slide $($it.n)`rDemo: $($it.demo)")
    }
    $i = $j + 1
  }
  "Session $($s.num): $($s.items.Count) slides (deck now $($p.Slides.Count))"
}

$p.SaveAs($OUT)
$n = $p.Slides.Count
$p.Close()
Remove-Item $base -ErrorAction SilentlyContinue
"Saved $OUT with $n slides"
