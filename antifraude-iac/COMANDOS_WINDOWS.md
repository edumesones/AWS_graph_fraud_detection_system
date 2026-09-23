# 🪟 COMANDOS PARA WINDOWS

## ✅ Scripts Batch Disponibles

- `validate.bat` - Validación pre-deployment
- `build-and-push.bat` - Build Docker y push a ECR
- `deploy.bat` - Deploy a ECS Fargate

---

## 🚀 EJECUCIÓN EN WINDOWS

### Paso 1: Validar Pre-requisitos

```cmd
cd D:\graph_aml\fraud-detection-graphs\antifraude-iac
validate.bat
```

### Paso 2: Configurar Terraform

```cmd
cd terraform
copy terraform.tfvars.example terraform.tfvars
notepad terraform.tfvars
```

**Configurar estos valores mínimos:**
```hcl
project_name = "fraud-detection"
environment  = "production"
aws_region   = "us-east-1"

container_cpu    = 4096
container_memory = 8192

desired_count = 2
min_capacity  = 2
max_capacity  = 10
```

### Paso 3: Desplegar Infraestructura

```cmd
terraform init
terraform validate
terraform plan -out=tfplan
terraform apply tfplan
```

### Paso 4: Construir y Subir Docker

```cmd
cd ..
build-and-push.bat
```

**⏱️ Tiempo: ~3-5 minutos**

### Paso 5: Desplegar a ECS

```cmd
deploy.bat
```

**⏱️ Tiempo: ~3-5 minutos**

### Paso 6: Obtener URL

```cmd
cd terraform
terraform output application_url
```

---

## 🐛 Troubleshooting Windows

### Problema: "terraform no se reconoce como comando"

**Solución:**
1. Descargar Terraform: https://www.terraform.io/downloads
2. Agregar a PATH:
   ```cmd
   setx PATH "%PATH%;C:\terraform"
   ```
3. Reiniciar CMD

### Problema: "aws no se reconoce como comando"

**Solución:**
1. Descargar AWS CLI: https://aws.amazon.com/cli/
2. Instalar (agrega automáticamente a PATH)
3. Configurar:
   ```cmd
   aws configure
   ```

### Problema: "docker no se reconoce como comando"

**Solución:**
1. Instalar Docker Desktop: https://www.docker.com/products/docker-desktop
2. Reiniciar PC
3. Verificar:
   ```cmd
   docker --version
   ```

### Problema: Scripts .sh en lugar de .bat

Si ves errores con archivos `.sh`:
- Usa las versiones `.bat` en su lugar
- `./build-and-push.sh` → `build-and-push.bat`
- `./deploy.sh` → `deploy.bat`
- `./validate.sh` → `validate.bat`

---

## 📝 Comandos Terraform (Iguales en Windows/Linux)

```cmd
REM Ver estado actual
terraform show

REM Ver outputs
terraform output

REM Actualizar infraestructura
terraform plan
terraform apply

REM Destruir todo
terraform destroy

REM Ver recursos creados
terraform state list
```

---

## 🔍 Comandos AWS CLI (Iguales en Windows/Linux)

```cmd
REM Ver credenciales
aws sts get-caller-identity

REM Ver tareas ECS
aws ecs list-tasks --cluster fraud-detection-production-cluster --region us-east-1

REM Ver logs
aws logs tail /ecs/fraud-detection-production --follow --region us-east-1

REM Ver imágenes en ECR
aws ecr list-images --repository-name fraud-detection-production-app --region us-east-1
```

---

## ⚡ PowerShell (Alternativa)

Si prefieres PowerShell en lugar de CMD, los comandos Terraform y AWS CLI funcionan igual:

```powershell
# Mismos comandos
terraform init
terraform apply
aws sts get-caller-identity

# Los scripts .bat también funcionan
.\build-and-push.bat
.\deploy.bat
```

---

**Nota**: Para comandos de Linux en COMANDOS_EJECUTA.md, reemplaza:
- `./script.sh` → `script.bat`
- `chmod +x` → (no necesario en Windows)
- Usar CMD o PowerShell en lugar de bash
