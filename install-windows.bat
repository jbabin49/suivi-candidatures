@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ====================================
echo  Installation - Suivi Candidatures
echo ====================================
echo.

REM Vérifier si Node.js est installé
echo Vérification de Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js n'est pas installé
    echo.
    echo Téléchargez et installez Node.js depuis: https://nodejs.org/
    echo Recommandé: Version LTS (20.x ou supérieur)
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo ✓ Node.js %NODE_VERSION% détecté

REM Vérifier npm
echo Vérification de npm...
npm --version >nul 2>&1
if errorlevel 1 (
    echo ❌ npm n'est pas installé
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('npm --version') do set NPM_VERSION=%%i
echo ✓ npm %NPM_VERSION% détecté

REM Installation des dépendances
echo.
echo Installation des dépendances...
call npm install
if errorlevel 1 (
    echo ❌ Erreur lors de l'installation des dépendances
    pause
    exit /b 1
)
echo ✓ Dépendances installées

REM Créer le fichier .env
echo.
echo Configuration du fichier .env...
if exist .env (
    echo Le fichier .env existe déjà. Passage...
) else (
    if exist .env.example (
        copy .env.example .env >nul
        echo ✓ Fichier .env créé à partir de .env.example
    ) else (
        echo ❌ Le fichier .env.example est manquant
        pause
        exit /b 1
    )
)

REM Générer un secret NextAuth
echo.
echo Génération du secret NextAuth...
for /f "tokens=*" %%i in ('powershell -Command "[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((New-Guid).ToString() + (New-Guid).ToString())) | Select-Object -First 1"') do set NEXTAUTH_SECRET=%%i

REM Mettre à jour le fichier .env
powershell -Command "(Get-Content .env) -replace 'your-secret-here-replace-me', '%NEXTAUTH_SECRET%' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace 'NODE_ENV=\"development\"', 'NODE_ENV=\"development\"' | Set-Content .env"

echo ✓ Fichier .env configuré

REM Initialiser la base de données
echo.
echo Configuration de la base de données...
call npx prisma migrate dev --name init
if errorlevel 1 (
    echo ❌ Erreur lors de la migration
    pause
    exit /b 1
)
echo ✓ Base de données configurée

REM Afficher les instructions finales
echo.
echo ====================================
echo  Installation terminée! ✓
echo ====================================
echo.
echo Pour démarrer l'application:
echo   npm run dev
echo.
echo L'application sera disponible à:
echo   http://localhost:3000
echo.
echo Credentials par défaut:
echo   Utilisateur: admin
echo   Mot de passe: admin123
echo.
pause
