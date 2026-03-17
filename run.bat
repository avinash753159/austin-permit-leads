@echo off
echo.
echo  ====================================
echo   Brimstone Partner
echo   Texas Construction Intelligence
echo  ====================================
echo.
echo  [1] Open Landing Page (local)
echo  [2] Open Live Site (GitHub Pages)
echo  [3] Open San Antonio Dashboard
echo  [4] Open Dallas Dashboard
echo  [5] Pull Contractor Leads (CSV)
echo  [6] Open Lead CSV File
echo  [7] Open Outreach Leads (with emails)
echo  [8] Open Email Templates
echo  [9] Send Outreach Emails (opens Gmail)
echo  [0] Exit
echo.
set /p choice=Choose:

if "%choice%"=="1" start "" "%~dp0index.html"
if "%choice%"=="2" start "" "https://avinash753159.github.io/austin-permit-leads/"
if "%choice%"=="3" start "" "https://avinash753159.github.io/austin-permit-leads/?city=sanantonio"
if "%choice%"=="4" start "" "https://avinash753159.github.io/austin-permit-leads/?city=dallas"
if "%choice%"=="5" (
    echo.
    echo Pulling leads from last 30 days...
    python "%~dp0pull_leads.py" 30
    echo.
    echo Done! CSV saved in %~dp0
    pause
)
if "%choice%"=="6" (
    for %%f in ("%~dp0austin-contractor-leads-*.csv") do start "" "%%f"
)
if "%choice%"=="7" start "" "%~dp0outreach-leads.csv"
if "%choice%"=="8" start "" "%~dp0outreach-email.md"
if "%choice%"=="9" (
    echo.
    echo How many emails to open? (Enter a number, or 'all')
    set /p num=Number:
    python "%~dp0send_outreach.py" %num%
    pause
)
if "%choice%"=="0" exit
