# Windows execution

Use scripts/run_preflight.cmd to select `py -3` or `python` on PATH. Require
Python 3.9+ and only the CLI for EIAM plus the selected cloud provider. No Bash,
WSL, Unix executable bit, or administrator PowerShell is required for preflight.

Resolve executables using PATH/PATHEXT. Run from the installed skill directory;
quote paths containing spaces. Do not translate Unix shell escaping directly
into PowerShell. Prefer argument arrays and UTF-8 JSON files for policy inputs.

Use official CLI OAuth/device/SSO flows. Keep the initiating process alive for
callback or polling completion. Start-Process may open a verified one-time URL
if the user chose that browser flow. Never request browser callbacks or tokens
in chat. Recheck full target account identity after login.

The default state path is under LOCALAPPDATA (APPDATA/USERPROFILE fallback).
Store only sanitized non-secret discoveries. State is outside the installed
skill directory and must not enter the release package.

The launcher has offline coverage only; validate execution, official CLI login,
Unicode paths, and policy-file encoding on a real Windows host before claiming
Windows end-to-end certification.
