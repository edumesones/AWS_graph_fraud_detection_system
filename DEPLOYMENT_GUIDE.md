# 🚀 Guía de Despliegue a AWS

## Estado Actual

✅ **Infraestructura desplegada exitosamente con Terraform**
- VPC, subnets, security groups configurados
- Application Load Balancer activo
- ECS Cluster y Service creados
- ECR Repository listo
- EFS para persistencia configurado

⏳ **Falta**: Desplegar la aplicación containerizada

## URL de la Aplicación

```
http://fraud-detection-dev-alb-1935014707.eu-north-1.elb.amazonaws.com
```

## 📋 Pasos para Desplegar

### 1️⃣ Pre-requisitos

Asegúrate de tener instalado:
- ✅ AWS CLI configurado (`aws configure`)
- ✅ Docker Desktop corriendo
- ✅ Credenciales AWS válidas

### 2️⃣ Validación Pre-Despliegue

Ejecuta el script de validación:

```cmd
pre-deploy-check.bat
```

Este script verifica:
- AWS CLI instalado y configurado
- Docker corriendo
- Credenciales AWS válidas
- Archivos necesarios presentes
- Conectividad a ECR

### 3️⃣ Despliegue Automatizado

Si todo está OK, ejecuta:

```cmd
deploy-to-aws.bat
```

Este script hace todo automáticamente:
1. Autentica con AWS ECR
2. Construye la imagen Docker
3. Tagea la imagen para ECR
4. Sube la imagen a ECR
5. Fuerza nuevo despliegue en ECS

⏱️ **Tiempo estimado**: 5-10 minutos (dependiendo de tu conexión)

### 4️⃣ Monitoreo del Despliegue

Puedes monitorear el progreso en:

**AWS Console**:
```
ECS → Clusters → fraud-detection-dev-cluster → Services → fraud-detection-dev-service
```

**Desde CLI**:
```cmd
aws ecs describe-services ^
  --cluster fraud-detection-dev-cluster ^
  --services fraud-detection-dev-service ^
  --region eu-north-1
```

**Ver logs en tiempo real**:
```cmd
aws logs tail /ecs/fraud-detection-dev --follow --region eu-north-1
```

### 5️⃣ Verificación

Una vez completado el despliegue (2-3 minutos después de subir la imagen):

1. Abre tu navegador en: `http://fraud-detection-dev-alb-1935014707.eu-north-1.elb.amazonaws.com`
2. Deberías ver tu aplicación Gradio funcionando

## 🔍 Troubleshooting

### Error: "Cannot connect to the Docker daemon"
**Solución**: Inicia Docker Desktop

### Error: "Unable to locate credentials"
**Solución**: 
```cmd
aws configure
```
Ingresa tus credenciales AWS

### Error: "denied: Your authorization token has expired"
**Solución**: Re-autentica con ECR:
```cmd
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/fraud-detection-dev-app
```

### La URL no responde después de 5 minutos
**Diagnóstico**:
1. Verifica el estado del servicio ECS:
```cmd
aws ecs describe-services --cluster fraud-detection-dev-cluster --services fraud-detection-dev-service --region eu-north-1
```

2. Revisa los logs:
```cmd
aws logs tail /ecs/fraud-detection-dev --follow --region eu-north-1
```

3. Verifica el health check del target group:
```cmd
aws elbv2 describe-target-health --target-group-arn <ARN> --region eu-north-1
```

## 📊 Recursos Desplegados

| Recurso | Nombre | Región |
|---------|--------|--------|
| VPC | fraud-detection-dev-vpc | eu-north-1 |
| ALB | fraud-detection-dev-alb | eu-north-1 |
| ECS Cluster | fraud-detection-dev-cluster | eu-north-1 |
| ECS Service | fraud-detection-dev-service | eu-north-1 |
| ECR Repo | fraud-detection-dev-app | eu-north-1 |
| CloudWatch Logs | /ecs/fraud-detection-dev | eu-north-1 |

## 🔄 Redespliegues

Para actualizar la aplicación en el futuro:

1. Haz cambios en tu código
2. Ejecuta `deploy-to-aws.bat`
3. ECS automáticamente hará rolling update sin downtime

## 🗑️ Limpieza (cuando termines)

Para destruir toda la infraestructura:

```cmd
cd antifraude-iac\terraform
terraform destroy
```

**⚠️ Cuidado**: Esto eliminará TODOS los recursos AWS creados.
