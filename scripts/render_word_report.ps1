# Render only the generated report through a new hidden Microsoft Word instance.
# This is the Windows fallback when bundled LibreOffice is unavailable.
$ErrorActionPreference = 'Stop'
$projectPath = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$reportPath = (Resolve-Path (Join-Path $projectPath 'reports\delivery\academic_report.vi.docx')).Path
$qaPath = Join-Path $projectPath '.qa\report'
New-Item -ItemType Directory -Path $qaPath -Force | Out-Null
$pdfPath = Join-Path $qaPath 'academic_report.vi.pdf'
$word = $null
$document = $null
$ownsEmptyInstance = $false
try {
    $word = New-Object -ComObject Word.Application
    if ($word.Documents.Count -ne 0) { throw 'Refuse to use an existing Word session containing documents.' }
    $ownsEmptyInstance = $true
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    $document = $word.Documents.Open($reportPath, $false, $true)
    $document.Repaginate()
    $document.ExportAsFixedFormat($pdfPath, 17)
    Write-Output ('Rendered pages: ' + $document.ComputeStatistics(2))
    Write-Output $pdfPath
}
finally {
    if ($null -ne $document) { $document.Close(0); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($document) }
    if ($null -ne $word) {
        if ($ownsEmptyInstance) { $word.Quit(0) }
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)
    }
}
