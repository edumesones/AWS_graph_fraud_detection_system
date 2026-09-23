@echo off
REM ==============================================================================
REM Script de Build y Push a ECR - Version Windows
REM ==============================================================================

echo.
echo === Fraud Detection - Docker Build ^& Push ===
echo.

REM Verificar AWS CLI
where aws >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] AWS CLI no esta instalado
    echo Descargalo desde: https://aws.amazon.com/cli/
    exit /b 1
)

REM Verificar Docker
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker no esta instalado
    echo Descargalo desde: https://www.docker.com/products/docker-desktop
    exit /b 1
)

REM Obtener outputs de Terraform
cd terraform
echo [INFO] Obteniendo configuracion de Terraform...

for /f "delims=" %%i in ('terraform output -raw ecr_repository_url 2^>nul') do set ECR_URL=%%i
for /f "delims=" %%i in ('terraform output -raw aws_region 2^>nul') do set AWS_REGION=%%i

if "%ECR_URL%"=="" (
    echo [ERROR] No se pudo obtener ECR URL de Terraform
    echo Ejecuta primero: cd terraform ^&^& terraform apply
    cd ..
    exit /b 1
)

if "%AWS_REGION%"=="" (
    set AWS_REGION=us-east-1
)

cd ..

echo.
echo [INFO] ECR Repository: %ECR_URL%
echo [INFO] AWS Region: %AWS_REGION%
echo.

REM Autenticar con ECR
echo [PASO 1/5] Autenticando con ECR...
aws ecr get-login-password --region %AWS_REGION% | docker login --username AWS --password-stdin %ECR_URL%
if %errorlevel% neq 0 (
    echo [ERROR] Fallo la autenticacion con ECR
    exit /b 1
)
echo [OK] Autenticacion exitosa
echo.

REM Build
echo [PASO 2/5] Construyendo imagen Docker...
docker build -t fraud-detection:latest -f Dockerfile ..
if %errorlevel% neq 0 (
    echo [ERROR] Fallo el build de Docker
    exit /b 1
)
echo [OK] Imagen construida
echo.

REM Tag latest
echo [PASO 3/5] Tageando imagen (latest)...
docker tag fraud-detection:latest %ECR_URL%:latest
if %errorlevel% neq 0 (
    echo [ERROR] Fallo el tag de imagen
    exit /b 1
)
echo [OK] Tag latest aplicado
echo.

REM Tag con timestamp
echo [PASO 4/5] Tageando imagen (timestamp)...
for /f "tokens=1-6 delims=/-:. " %%a in ("%date% %time%") do (
    set TIMESTAMP=%%c%%b%%a-%%d%%e%%f
)
set TIMESTAMP=%TIMESTAMP: =0%
docker tag fraud-detection:latest %ECR_URL%:%TIMESTAMP%
echo [OK] Tag %TIMESTAMP% aplicado
echo.

REM Push
echo [PASO 5/5] Pushing imagenes a ECR...
docker push %ECR_URL%:latest
docker push %ECR_URL%:%TIMESTAMP%
if %errorlevel% neq 0 (
    echo [ERROR] Fallo el push a ECR
    exit /b 1
)
echo.
echo [SUCCESS] Build y push completados exitosamente!
echo.
echo Siguiente paso: Ejecuta deploy.bat para actualizar el servicio ECS
echo.
