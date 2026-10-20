@echo off
setlocal EnableExtensions EnableDelayedExpansion

where py >nul 2>&1
if !ERRORLEVEL! EQU 0 (
  py -3 "%~dp0cloud_identity_preflight.py" %*
  exit /b !ERRORLEVEL!
)

where python >nul 2>&1
if !ERRORLEVEL! EQU 0 (
  python "%~dp0cloud_identity_preflight.py" %*
  exit /b !ERRORLEVEL!
)

echo Python 3 was not found. Install Python 3 or enable the Windows py launcher. 1>&2
exit /b 127
