@echo off
REM ==============================================================================
REM Script de Deployment a ECS Fargate - Version Windows
REM ==============================================================================

echo.
echo === Fraud Detection - ECS Deployment ===
echo.

REM Verificar AWS CLI
where aws >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] AWS CLI no esta instalado
    exit /b 1
)

REM Obtener outputs de Terraform
cd terraform
echo [INFO] Obteniendo configuracion de Terraform...

for /f "delims=" %%i in ('terraform output -raw ecs_cluster_name 2^>nul') do set CLUSTER_NAME=%%i
for /f "delims=" %%i in ('terraform output -raw ecs_service_name 2^>nul') do set SERVICE_NAME=%%i
for /f "delims=" %%i in ('terraform output -raw aws_region 2^>nul') do set AWS_REGION=%%i

if "%CLUSTER_NAME%"=="" (
    echo [ERROR] No se pudieron obtener los datos de Terraform
    echo Ejecuta primero: cd terraform ^&^& terraform apply
    cd ..
    exit /b 1
)

if "%AWS_REGION%"=="" (
    set AWS_REGION=us-east-1
)

cd ..

echo.
echo [INFO] Cluster: %CLUSTER_NAME%
echo [INFO] Service: %SERVICE_NAME%
echo [INFO] Region: %AWS_REGION%
echo.

REM Forzar nuevo deployment
echo [PASO 1/2] Forzando nuevo deployment en ECS...
aws ecs update-service --cluster %CLUSTER_NAME% --service %SERVICE_NAME% --force-new-deployment --region %AWS_REGION%
if %errorlevel% neq 0 (
    echo [ERROR] Fallo el comando de deployment
    exit /b 1
)
echo [OK] Deployment iniciado
echo.

REM Esperar a que se estabilice
echo [PASO 2/2] Esperando a que el servicio se estabilice...
echo [INFO] Esto puede tomar 3-5 minutos...
echo.
aws ecs wait services-stable --cluster %CLUSTER_NAME% --services %SERVICE_NAME% --region %AWS_REGION%

if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] Deployment completado exitosamente!
    echo.
    echo Para ver la URL de la aplicacion:
    echo   cd terraform
    echo   terraform output application_url
    echo.
) else (
    echo.
    echo [WARNING] Timeout o fallo en la estabilizacion
    echo.
    echo Para verificar el estado manualmente:
    echo   aws ecs describe-services --cluster %CLUSTER_NAME% --services %SERVICE_NAME% --region %AWS_REGION%
    echo.
)
