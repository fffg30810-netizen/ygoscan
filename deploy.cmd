@echo off
rem Pubblica (o aggiorna) YGO Scan su GitHub Pages: link pubblico HTTPS da mandare agli amici.
rem Prerequisito UNA volta: "gh auth login" (browser, account GitHub). Poi basta un doppio clic su questo file.
cd /d "%~dp0"
gh auth status >nul 2>&1 || gh auth login || exit /b 1
git add -A
git commit -m "YGO Scan: aggiornamento %date% %time%" >nul 2>&1
gh repo view ygoscan >nul 2>&1 || gh repo create ygoscan --public --source=. --push --description "Scanner carte Yu-Gi-Oh: inquadri la carta, vedi il prezzo" || exit /b 1
git push -u origin HEAD >nul 2>&1
gh api -X POST repos/{owner}/ygoscan/pages -f "source[branch]=master" -f "source[path]=/docs" >nul 2>&1
for /f %%u in ('gh api user --jq .login') do set U=%%u
echo.
echo   Link da mandare agli amici (attivo entro 1-2 minuti dalla prima pubblicazione):
echo   https://%U%.github.io/ygoscan/
echo.
echo   Per toglierla da internet: gh repo delete ygoscan --yes
pause
