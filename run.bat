@echo off
echo.
echo  ====================================
echo   Brimstone Partner
echo   Texas Construction Intelligence
echo  ====================================
echo.
echo  [1] Open Landing Page (local)
echo  [2] Open Live Site (Railway)
echo  [3] Open San Antonio Dashboard
echo  [4] Pull Contractor Leads (CSV)
echo  [5] Open Outreach Leads (with emails)
echo  [6] Open PDFs Folder
echo  [7] Generate All 41 PDFs
echo  [8] Create Gmail Drafts (with PDFs attached)
echo  [9] View Collected Emails (admin)
echo  [0] Exit
echo.
set /p choice=Choose:

if "%choice%"=="1" start "" "%~dp0index.html"
if "%choice%"=="2" start "" "https://brimstone-permits-production.up.railway.app"
if "%choice%"=="3" (
    start "" "%~dp0index.html"
    timeout /t 2 >nul
    echo Opening San Antonio...
)
if "%choice%"=="4" (
    echo.
    echo Pulling leads from last 30 days...
    python "%~dp0pull_leads.py" 30
    echo.
    echo Done! CSV saved in %~dp0
    pause
)
if "%choice%"=="5" start "" "%~dp0outreach-leads.csv"
if "%choice%"=="6" start "" "%~dp0PDFs"
if "%choice%"=="7" (
    echo.
    echo Generating 41 personalized PDFs...
    python "%~dp0generate_pdfs.py"
    echo.
    pause
)
if "%choice%"=="8" (
    echo.
    echo How many drafts to create? (Enter a number, or 'all')
    set /p num=Number:
    python "%~dp0send_emails.py" %num%
    pause
)
if "%choice%"=="9" start "" "https://brimstone-permits-production.up.railway.app/api/leads"
if "%choice%"=="0" exit
