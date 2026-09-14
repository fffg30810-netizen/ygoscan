@echo off
rem Pubblica (o aggiorna) YGO Scan su GitHub Pages: link pubblico HTTPS da mandare agli amici.
rem Prerequisito UNA volta: "gh auth login" (browser, account GitHub). Poi basta un doppio clic su questo file.
cd /d "%~dp0"
gh auth status >nul 2>&1 || gh auth login || exit /b 1
for /f %%u in ('gh api user --jq .login') do set U=%%u
if "%U%"=="" echo Login GitHub non riuscito. && exit /b 1
rem identita' git solo per questo repo (email no-reply di GitHub: niente email personale nei commit pubblici)
git config user.name >nul 2>&1 || git config user.name "%U%"
git config user.email >nul 2>&1 || git config user.email "%U%@users.noreply.github.com"
git add -A
git commit -m "YGO Scan: aggiornamento %date%" 2>nul
if not exist docs\db.json echo Manca docs\db.json: esegui prima "python build_db.py" && exit /b 1
gh repo view %U%/ygoscan >nul 2>&1 || gh repo create ygoscan --public --source=. --push --description "Scanner carte Yu-Gi-Oh: inquadri la carta, vedi il prezzo" || exit /b 1
git push -u origin HEAD || exit /b 1
gh api -X POST repos/%U%/ygoscan/pages -f "source[branch]=master" -f "source[path]=/docs" >nul 2>&1
echo.
echo   Link da mandare agli amici (attivo entro 1-2 minuti dalla prima pubblicazione):
echo   https://%U%.github.io/ygoscan/
echo.
echo   Per toglierla da internet: gh repo delete %U%/ygoscan --yes
pause
