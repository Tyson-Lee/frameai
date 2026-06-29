@echo off
REM Windows wrapper for the `frame` Python CLI.
REM Lets users invoke `.\frame add ...` on Windows the same way macOS/Linux
REM users invoke `./frame add ...`. The actual logic lives in the `frame`
REM Python script next to this file (no .py extension by convention).
python "%~dp0frame" %*
