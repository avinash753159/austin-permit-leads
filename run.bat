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
echo  [7] Generate All 61 PDFs
echo  [8] Create Gmail Drafts - OLD 41 (already sent)
echo  [9] View Collected Emails (admin)
echo  [10] Create Gmail Drafts - NEW 20 ONLY
echo  [11] Open New PDFs Folder
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
if "%choice%"=="10" goto opt10
if "%choice%"=="11" goto opt11
if "%choice%"=="0" exit
goto end

:opt1
start "" "%~dp0index.html"
goto end

:opt2
start "" "https://brimstone-permits-production.up.railway.app"
goto end

:opt3
start "" "%~dp0index.html"
timeout /t 2 >nul
echo Opening San Antonio...
goto end

:opt4
echo.
echo Pulling leads from last 30 days...
python "%~dp0pull_leads.py" 30
echo.
echo Done! CSV saved in %~dp0
pause
goto end

:opt5
start "" "%~dp0outreach-leads.csv"
goto end

:opt6
start "" "%~dp0PDFs"
goto end

:opt7
echo.
echo Generating 61 personalized PDFs...
python "%~dp0generate_pdfs.py"
echo.
pause
goto end

:opt8
echo.
echo WARNING: These are the OLD 41 leads you already sent.
set /p confirm=Are you sure? (y/n):
if /i not "%confirm%"=="y" goto end
set /p num=How many drafts? (number or 'all'):
python "%~dp0send_emails.py" %num%
pause
goto end

:opt9
start "" "https://brimstone-permits-production.up.railway.app/api/leads"
goto end

:opt10
echo.
echo  Creating Gmail drafts for 20 NEW leads only...
echo  (PDFs from PDFs-New folder, no duplicates with old 41)
echo.
python "%~dp0send_emails.py" --new all
pause
goto end

:opt11
start "" "%~dp0PDFs-New"
goto end

:end
