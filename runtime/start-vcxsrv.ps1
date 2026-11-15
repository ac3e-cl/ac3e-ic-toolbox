param([Parameter(Mandatory = $true)][string]$AuthorityFile)
$ErrorActionPreference = 'Stop'

# Do not kill or silently reconfigure an X server owned by another session.
$servers = @(Get-CimInstance Win32_Process -Filter "Name = 'vcxsrv.exe'")
$escapedAuthority = [regex]::Escape($AuthorityFile)
$authorityArgument = '"' + $escapedAuthority + '"'
if ($AuthorityFile -notmatch '\s') { $authorityArgument += '|' + $escapedAuthority }
$authPattern = '(?:^|\s)-auth\s+(?:' + $authorityArgument + ')(?=\s|$)'
if ($servers.Count -gt 0) {
    $matching = @($servers | Where-Object {
        $_.CommandLine -match '(?:^|\s)-multiwindow(?:\s|$)' -and
        $_.CommandLine -match '(?:^|\s):0(?:\s|$)' -and
        $_.CommandLine -notmatch '(?:^|\s)-ac(?:\s|$)' -and
        $_.CommandLine -match $authPattern
    })
    if ($matching.Count -eq 0) {
        throw 'VcXsrv is already running with different settings. Close it explicitly, then rerun the launcher to enable multiwindow and matching Xauthority.'
    }
    exit 0
}

$command = Get-Command vcxsrv.exe -ErrorAction SilentlyContinue
if ($command) {
    $executable = $command.Source
} else {
    $executable = Join-Path $env:ProgramFiles 'VcXsrv\vcxsrv.exe'
}
if (-not (Test-Path -LiteralPath $executable)) {
    throw 'VcXsrv is not installed. Install VcXsrv or select AC3E_XSERVER=native for WSLg/an external X server.'
}
$arguments = @(':0', '-multiwindow', '-clipboard', '-primary', '-wgl',
               '-listen', 'tcp', '-auth', ('"' + $AuthorityFile + '"'))
$server = Start-Process -FilePath $executable -ArgumentList $arguments -PassThru
# Bound readiness waiting; fail instead of launching clients against a dead server.
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    if ($server.HasExited) { throw 'VcXsrv exited during startup.' }
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $connection = $client.ConnectAsync('127.0.0.1', 6000)
        if ($connection.Wait(200) -and $client.Connected) { exit 0 }
    } catch {
        # A refused connection is normal while the server starts.
    } finally {
        $client.Dispose()
    }
    Start-Sleep -Milliseconds 100
}
throw 'VcXsrv did not listen on display 0 within the startup deadline.'
