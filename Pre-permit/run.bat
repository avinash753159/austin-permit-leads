@echo off
echo.
echo  ============================================
echo   Brimstone Partner
echo   Pre-Construction Intelligence Engine
echo  ============================================
echo.
echo  [1] Run Full Scrape (all sources, regex analysis)
echo  [2] Run Full Scrape (with Claude API - more accurate)
echo  [3] Open Dashboard (browser)
echo  [4] Open Post-Permit Dashboard
echo  [5] View Report (markdown)
echo  [6] Open Leads CSV
echo  [7] Open Outreach Targets
echo  [8] View Pitch Report
echo  [9] Open PDFs Folder
echo  [0] Exit
echo.
set /p choice=Choose:

if "%choice%"=="1" goto opt1
if "%choice%"=="2" goto opt2
if "%choice%"=="3" goto opt3
if "%choice%"=="4" goto opt4
if "%choice%"=="5" goto opt5
if "%choice%"=="6" goto opt6
if "%choice%"=="7" goto opt7
if "%choice%"=="8" goto opt8
if "%choice%"=="9" goto opt9
if "%choice%"=="0" exit
goto end

:opt1
echo.
echo  Running full scrape with regex analysis (free)...
echo.
python "%~dp0scrape_all.py"
echo.
echo  Generating outreach targets...
python "%~dp0generate_outreach.py"
echo.
echo  Done! Opening dashboard...
start "" "%~dp0dashboard.html"
pause
goto end

:opt2
echo.
echo  Running full scrape with Claude API (requires ANTHROPIC_API_KEY)...
echo.
set /p apikey=Enter API key (or press Enter to skip):
if not "%apikey%"=="" set ANTHROPIC_API_KEY=%apikey%
python "%~dp0scrape_all.py" --use-api
echo.
echo  Generating outreach targets...
python "%~dp0generate_outreach.py"
echo.
echo  Done! Opening dashboard...
start "" "%~dp0dashboard.html"
pause
goto end

:opt3
start "" "%~dp0dashboard.html"
goto end

:opt4
start "" "%~dp0..\index-dashboard.html"
goto end

:opt5
if exist "%~dp0pre-construction-report.md" (
    start "" "%~dp0pre-construction-report.md"
) else (
    echo  No report found. Run a scrape first [option 1].
    pause
)
goto end

:opt6
if exist "%~dp0pre-construction-leads.csv" (
    start "" "%~dp0pre-construction-leads.csv"
) else (
    echo  No CSV found. Run a scrape first [option 1].
    pause
)
goto end

:opt7
if exist "%~dp0outreach-targets.csv" (
    start "" "%~dp0outreach-targets.csv"
) else (
    echo  No outreach targets found. Run a scrape first [option 1].
    pause
)
goto end

:opt8
if exist "%~dp0pitch-report.md" (
    start "" "%~dp0pitch-report.md"
) else (
    echo  No pitch report found. Run a scrape first [option 1].
    pause
)
goto end

:opt9
start "" "%~dp0PDFs"
goto end

:end
