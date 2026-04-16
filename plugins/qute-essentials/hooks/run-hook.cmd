@echo off
REM Portable Python hook runner for Windows.
REM Usage: run-hook.cmd script.py [args...]
REM Try order: uv run python, python3, python, py -3

where uv >nul 2>&1 && (uv run python %* & exit /b %ERRORLEVEL%)
where python3 >nul 2>&1 && (python3 %* & exit /b %ERRORLEVEL%)
where python >nul 2>&1 && (python %* & exit /b %ERRORLEVEL%)
where py >nul 2>&1 && (py -3 %* & exit /b %ERRORLEVEL%)
echo {"error":"No Python found. Install python3 or uv."} >&2
exit /b 1
