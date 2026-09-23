@echo off
REM ==============================================================================
REM Pre-Deployment Validation Script
REM ==============================================================================
REM Verifica que todo esté configurado correctamente antes del despliegue
REM ==============================================================================

echo ========================================
echo  Pre-Deployment Validation
echo ========================================
echo.

set ALL_OK=1

echo [1/6] Verificando AWS CLI...
echo ----------------------------------------
aws --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ✗ AWS CLI no está instalado o no está en el PATH
    set ALL_OK=0
) else (
    aws --version
    echo ✓ AWS CLI disponible
)
echo.

echo [2/6] Verificando Docker...
echo ----------------------------------------
docker --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ✗ Docker no está instalado o no está en el PATH
    set ALL_OK=0
) else (
    docker --version
    echo ✓ Docker disponible
)
echo.

echo [3/6] Verificando Docker daemon...
echo ----------------------------------------
docker ps >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ✗ Docker daemon no está corriendo
    echo   Por favor inicia Docker Desktop
    set ALL_OK=0
) else (
    echo ✓ Docker daemon corriendo
)
echo.

echo [4/6] Verificando credenciales AWS...
echo ----------------------------------------
aws sts get-caller-identity >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ✗ No se pudo obtener identidad AWS
    echo   Verifica tus credenciales: aws configure
    set ALL_OK=0
) else (
    aws sts get-caller-identity --query "Account" --output text
    echo ✓ Credenciales AWS válidas
)
echo.

echo [5/6] Verificando archivos necesarios...
echo ----------------------------------------
if not exist ".\antifraude-iac\Dockerfile" (
    echo ✗ No se encuentra: .\antifraude-iac\Dockerfile
    set ALL_OK=0
) else (
    echo ✓ Dockerfile encontrado
)

if not exist ".\requirements.txt" (
    echo ✗ No se encuentra: .\requirements.txt
    set ALL_OK=0
) else (
    echo ✓ requirements.txt encontrado
)

if not exist ".\setup.py" (
    echo ✗ No se encuentra: .\setup.py
    set ALL_OK=0
) else (
    echo ✓ setup.py encontrado
)

if not exist ".\dashboard" (
    echo ✗ No se encuentra directorio: .\dashboard
    set ALL_OK=0
) else (
    echo ✓ Directorio dashboard encontrado
)
echo.

echo [6/6] Verificando conectividad a ECR...
echo ----------------------------------------
aws ecr describe-repositories --repository-names fraud-detection-dev-app --region eu-north-1 >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ✗ No se pudo acceder al repositorio ECR
    echo   Verifica que Terraform se ejecutó correctamente
    set ALL_OK=0
) else (
    echo ✓ Repositorio ECR accesible
)
echo.

echo ========================================
if %ALL_OK%==1 (
    echo  ✓ TODO LISTO PARA DESPLIEGUE
    echo ========================================
    echo.
    echo Ejecuta: deploy-to-aws.bat
) else (
    echo  ✗ HAY PROBLEMAS QUE RESOLVER
    echo ========================================
    echo.
    echo Por favor corrige los errores antes de desplegar
)
echo.
pause
