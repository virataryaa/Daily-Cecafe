@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  Cecafe Daily data publish
echo ============================================
echo.

echo Pulling entries saved from the dashboard ...
git pull --rebase --autostash
if errorlevel 1 (
    echo Pull failed - see error above.
    pause
    exit /b 1
)

echo Step 1/3: Validating Database\cecafe_daily.csv and Database\Cecafe Monthly.xlsx ...
python validate_csv.py
if errorlevel 1 (
    echo.
    echo ============================================
    echo  VALIDATION FAILED - nothing was pushed.
    echo  Fix the issues above in "Database\cecafe_daily.csv", then run this again.
    echo ============================================
    pause
    exit /b 1
)
python validate_destinations.py
if errorlevel 1 (
    echo.
    echo ============================================
    echo  VALIDATION FAILED - nothing was pushed.
    echo  Fix the issues above in "Database\Cecafe Monthly.xlsx", then run this again.
    echo ============================================
    pause
    exit /b 1
)
echo Converting Cecafe Monthly.xlsx to Database\cecafe_destinations.csv ...
python Automator\build_destinations.py
if errorlevel 1 (
    echo Conversion failed - see error above. Is the Excel file open and locked?
    pause
    exit /b 1
)

echo.
echo Step 2/3: Checking for changes ...
git diff --quiet -- "Database\cecafe_daily.csv" "Database\cecafe_exports.csv" "Database\cecafe_settings.json" "Database\cecafe_destinations.csv"
if not errorlevel 1 (
    echo No changes detected in the data files - nothing to push.
    pause
    exit /b 0
)

echo.
echo Step 3/3: Committing and pushing to GitHub ...
git add "Database\cecafe_daily.csv" "Database\cecafe_exports.csv" "Database\cecafe_settings.json" "Database\cecafe_destinations.csv"
for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm\""') do set STAMP=%%i
git commit -m "Data update %STAMP%"
if errorlevel 1 (
    echo.
    echo Commit failed - see error above.
    pause
    exit /b 1
)

git push
if errorlevel 1 (
    echo.
    echo Push failed - see error above. Your commit is still saved locally.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Done. Streamlit Cloud will redeploy within
echo  about a minute.
echo ============================================
pause
