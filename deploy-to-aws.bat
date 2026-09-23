@echo off
REM ==============================================================================
REM Script de Despliegue Automatizado - Fraud Detection Graph Analytics
REM ==============================================================================
REM Este script construye, tagea y sube la imagen Docker a AWS ECR,
REM luego fuerza un nuevo despliegue en ECS
REM ==============================================================================

echo ========================================
echo  Fraud Detection - AWS Deployment
echo ========================================
echo.

REM ------------------------------------------------------------------------------
REM Variables de configuración (obtenidas de Terraform outputs)
REM ------------------------------------------------------------------------------
set AWS_REGION=eu-north-1
set ECR_REPO=<AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/fraud-detection-dev-app
set IMAGE_NAME=fraud-detection-dev-app
set ECS_CLUSTER=fraud-detection-dev-cluster
set ECS_SERVICE=fraud-detection-dev-service

echo [1/5] Autenticando con AWS ECR...
echo ----------------------------------------
aws ecr get-login-password --region %AWS_REGION% | docker login --username AWS --password-stdin %ECR_REPO%
if %ERRORLEVEL% neq 0 (
    echo ERROR: Fallo al autenticar con ECR
    echo Verifica que tienes AWS CLI configurado y credenciales válidas
    pause
    exit /b 1
)
echo ✓ Autenticación exitosa
echo.

echo [2/5] Construyendo imagen Docker...
echo ----------------------------------------
echo Usando Dockerfile: .\antifraude-iac\Dockerfile
echo Contexto: directorio actual (raíz del proyecto)
docker build -f .\antifraude-iac\Dockerfile -t %IMAGE_NAME%:latest .
if %ERRORLEVEL% neq 0 (
    echo ERROR: Fallo al construir la imagen Docker
    pause
    exit /b 1
)
echo ✓ Imagen construida exitosamente
echo.

echo [3/5] Tageando imagen para ECR...
echo ----------------------------------------
docker tag %IMAGE_NAME%:latest %ECR_REPO%:latest
if %ERRORLEVEL% neq 0 (
    echo ERROR: Fallo al tagear la imagen
    pause
    exit /b 1
)
echo ✓ Imagen tageada exitosamente
echo.

echo [4/5] Subiendo imagen a ECR...
echo ----------------------------------------
docker push %ECR_REPO%:latest
if %ERRORLEVEL% neq 0 (
    echo ERROR: Fallo al subir la imagen a ECR
    pause
    exit /b 1
)
echo ✓ Imagen subida exitosamente
echo.

echo [5/5] Desplegando nueva versión en ECS...
echo ----------------------------------------
aws ecs update-service --cluster %ECS_CLUSTER% --service %ECS_SERVICE% --force-new-deployment --region %AWS_REGION%
if %ERRORLEVEL% neq 0 (
    echo ERROR: Fallo al desplegar en ECS
    pause
    exit /b 1
)
echo ✓ Despliegue iniciado exitosamente
echo.

echo ========================================
echo  ✓ DESPLIEGUE COMPLETADO
echo ========================================
echo.
echo URL de la aplicación:
echo http://fraud-detection-dev-alb-1935014707.eu-north-1.elb.amazonaws.com
echo.
echo El despliegue puede tardar 2-3 minutos en completarse.
echo Monitorea el progreso en la consola de AWS ECS.
echo.
pause
