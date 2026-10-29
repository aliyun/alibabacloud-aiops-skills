@echo off
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 "%~dp0role_tools.py" %*
exit /b %errorlevel%
:use_python
python "%~dp0role_tools.py" %*
exit /b %errorlevel%
