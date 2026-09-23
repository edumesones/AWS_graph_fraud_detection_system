@echo off
REM ==============================================================================
REM Script de Validacion Pre-Deployment - Version Windows
REM ==============================================================================

echo.
echo === Pre-Deployment Validation ===
echo.

set ERRORS=0
set WARNINGS=0

REM Verificar Terraform
C:\terraform\terraform.exe version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Terraform no esta instalado
    set /a ERRORS+=1
) else (
    echo [OK] Terraform instalado
    C:\terraform\terraform.exe version | findstr /C:"Terraform"
)

REM Verificar AWS CLI
where aws >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] AWS CLI no esta instalado
    set /a ERRORS+=1
) else (
    echo [OK] AWS CLI instalado
    aws --version
)

REM Verificar Docker
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Docker no esta instalado
    set /a ERRORS+=1
) else (
    echo [OK] Docker instalado
    docker --version
)

REM Verificar credenciales AWS
echo.
echo [INFO] Verificando credenciales AWS...
aws sts get-caller-identity >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Credenciales AWS no configuradas o invalidas
    echo     Ejecuta: aws configure
    set /a ERRORS+=1
) else (
    echo [OK] Credenciales AWS validas
    aws sts get-caller-identity
)

REM Verificar terraform.tfvars
echo.
echo [INFO] Verificando configuracion Terraform...
if not exist "terraform\terraform.tfvars" (
    echo [!] terraform.tfvars no existe
    echo     Copia terraform.tfvars.example y configura tus valores
    set /a WARNINGS+=1
) else (
    echo [OK] terraform.tfvars existe
)

REM Verificar requirements.txt
echo.
echo [INFO] Verificando dependencias Python...
if not exist "..\requirements.txt" (
    echo [X] requirements.txt no encontrado en directorio padre
    set /a ERRORS+=1
) else (
    echo [OK] requirements.txt encontrado
    echo     Dependencias principales:
    findstr /C:"gradio" /C:"networkx" /C:"pandas" /C:"pyvis" ..\requirements.txt
)

REM Verificar estructura de directorios
echo.
echo [INFO] Verificando estructura del proyecto...
if not exist "..\dashboard" (
    echo [X] Directorio no encontrado: ..\dashboard
    set /a ERRORS+=1
) else (
    echo [OK] ..\dashboard
)

if not exist "..\analysis" (
    echo [X] Directorio no encontrado: ..\analysis
    set /a ERRORS+=1
) else (
    echo [OK] ..\analysis
)

if not exist "..\data" (
    echo [X] Directorio no encontrado: ..\data
    set /a ERRORS+=1
) else (
    echo [OK] ..\data
)

if not exist "..\visualization" (
    echo [X] Directorio no encontrado: ..\visualization
    set /a ERRORS+=1
) else (
    echo [OK] ..\visualization
)

REM Verificar Dockerfile
echo.
echo [INFO] Verificando Dockerfile...
if not exist "Dockerfile" (
    echo [X] Dockerfile no encontrado
    set /a ERRORS+=1
) else (
    echo [OK] Dockerfile existe
    
    findstr /C:"FROM.*as builder" Dockerfile >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Multi-stage build detectado
    ) else (
        echo [!] No se detecto multi-stage build
        set /a WARNINGS+=1
    )
    
    findstr /C:"USER appuser" Dockerfile >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Usuario no-root configurado
    ) else (
        echo [X] No se detecto usuario no-root
        set /a ERRORS+=1
    )
)

REM Resumen
echo.
echo ================================
if %ERRORS% equ 0 (
    if %WARNINGS% equ 0 (
        echo [SUCCESS] Todos los checks pasaron!
        echo Puedes proceder con el deployment
        exit /b 0
    ) else (
        echo [WARNING] %WARNINGS% warnings encontrados
        echo Revisa los warnings y continua si es apropiado
        exit /b 0
    )
) else (
    echo [ERROR] %ERRORS% errores encontrados
    if %WARNINGS% gtr 0 (
        echo [WARNING] %WARNINGS% warnings encontrados
    )
    echo Corrige los errores antes de continuar
    exit /b 1
)
