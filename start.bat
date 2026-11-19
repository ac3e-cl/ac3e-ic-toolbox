@echo off
setlocal DisableDelayedExpansion
REM WSL2 with Docker integration; VcXsrv is started with secure defaults.
REM Convert the script directory, not the caller's current directory.
for /f "usebackq delims=" %%I in (`wsl.exe --exec wslpath -u "%~dp0."`) do set "LAUNCH_ROOT=%%I"
if not defined LAUNCH_ROOT exit /b 1
if defined AC3E_XSERVER (
    wsl.exe --exec env AC3E_XSERVER=%AC3E_XSERVER% bash "%LAUNCH_ROOT%/start_x.sh" %*
) else (
    wsl.exe --exec bash "%LAUNCH_ROOT%/start_x.sh" %*
)
exit /b %errorlevel%
