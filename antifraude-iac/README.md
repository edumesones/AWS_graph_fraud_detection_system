# 🏗️ Fraud Detection - AWS ECS Fargate Infrastructure

Infraestructura como Código (IaC) con Terraform para desplegar una aplicación de detección de fraude basada en Gradio + NetworkX en AWS ECS Fargate con alta disponibilidad y auto-scaling.

## 📋 Tabla de Contenidos

- [Arquitectura](#-arquitectura)
- [Componentes](#-componentes)
- [Estrategia de Escalado](#-estrategia-de-escalado-target-tracking)
- [Pre-requisitos](#-pre-requisitos)
- [Despliegue](#-despliegue)
- [Persistencia de Datos](#-persistencia-de-datos-efs)
- [Monitoring](#-monitoring)
- [Costos Estimados](#-costos-estimados)
- [Evaluación TRIAGE](#-evaluación-triage)

---

## 🏛️ Arquitectura

```
                              Internet
                                 |
                                 |
                        [Application Load Balancer]
                         (HTTPS/HTTP - Multi-AZ)
                                 |
                    ┌────────────┴────────────┐
                    |                         |
            [Subnet Pública 1a]      [Subnet Pública 1b]
                    |                         |
            [NAT Gateway 1a]         [NAT Gateway 1b]
                    |                         |
                    └────────────┬────────────┘
                                 |
                    ┌────────────┴────────────┐
                    |                         |
           [Subnet Privada 1a]      [Subnet Privada 1b]
                    |                         |
           [ECS Fargate Tasks]      [ECS Fargate Tasks]
           (Gradio + NetworkX)      (Gradio + NetworkX)
                    |                         |
                    └────────────┬────────────┘
                                 |
                         [Amazon EFS]
                    (logs, exports, layouts)
```

### Características Clave

✅ **Alta Disponibilidad**: Multi-AZ con 2+ zonas de disponibilidad  
✅ **Seguridad**: Subnets privadas, Security Groups restrictivos, IAM con mínimos privilegios  
✅ **Escalabilidad**: Auto-scaling basado en CPU y Memoria con Target Tracking  
✅ **Persistencia**: Amazon EFS para logs y visualizaciones generadas  
✅ **Observabilidad**: CloudWatch Logs, métricas y alarmas integradas  
✅ **Cost-Optimized**: Fargate Spot opcional, lifecycle policies en S3/ECR

---

## 🧩 Componentes

### 1. **VPC y Networking** (`vpc.tf`)
- VPC dedicada con CIDR `/16`
- 2 Subnets Públicas (para ALB) en diferentes AZs
- 2 Subnets Privadas (para ECS y EFS) en diferentes AZs
- NAT Gateways redundantes (uno por AZ) para HA
- Internet Gateway para conectividad pública

### 2. **Application Load Balancer** (`load_balancing.tf`)
- ALB público en subnets públicas
- Target Group para ECS tasks (tipo IP)
- Health checks configurados (`/` cada 30s)
- Sticky sessions habilitadas (24h)
- Listeners HTTP (80) y HTTPS (443) - con redirect automático
- Access logs en S3 con lifecycle de 90 días

### 3. **ECS Fargate** (`ecs_fargate.tf`)
- **Cluster ECS** con Container Insights habilitado
- **Task Definition**:
  - CPU: 4 vCPU (4096 units) - configurable
  - Memoria: 8 GB (8192 MB) - configurable
  - Imagen: ECR Repository
  - Volumen EFS montado en `/app/persistent`
  - Health check interno
  - Logs a CloudWatch
- **Service**:
  - Launch Type: FARGATE
  - Desired Count: 2 (configurable)
  - Rolling deployment (max 200%, min 100%)
  - Circuit breaker con rollback automático
  - Integración con ALB Target Group

### 4. **Auto Scaling** (`ecs_fargate.tf`)
- **Target Tracking en CPU**: Escala cuando CPU promedio > 70%
- **Target Tracking en Memoria**: Escala cuando memoria promedio > 80%
- Cooldown periods configurables:
  - Scale out: 60 segundos
  - Scale in: 300 segundos (5 minutos)
- Capacidad: min=2, max=10 (configurable)

### 5. **Storage - Amazon EFS** (`storage.tf`)
- File System encriptado
- Performance mode: `generalPurpose` (o `maxIO` para cargas pesadas)
- Throughput mode: `bursting`
- Access Point con UID/GID 1001 (matching Dockerfile)
- Mount targets en subnets privadas (Multi-AZ)
- Backup policy habilitado
- Lifecycle: transición a IA después de 30 días

### 6. **Container Registry - ECR** (`ecr.tf`)
- Repositorio privado con encriptación AES256
- Image scanning automático en push
- Lifecycle policy:
  - Mantener últimas 10 imágenes tageadas
  - Eliminar imágenes sin tag después de 7 días

### 7. **Security** (`security_groups.tf`, `iam.tf`)
- **Security Groups**:
  - ALB: 80/443 desde internet, egress a ECS tasks
  - ECS Tasks: Solo desde ALB en puerto 7860, egress completo
  - EFS: Solo NFS (2049) desde ECS tasks
- **IAM Roles**:
  - Task Execution Role: Pull images, write logs
  - Task Role: Acceso a EFS con scope limitado a Access Point

### 8. **Monitoring** (`ecs_fargate.tf`)
- CloudWatch Log Group con retención de 30 días
- Alarmas:
  - CPU > 85% durante 2 períodos
  - Memoria > 90% durante 2 períodos

---

## 🎯 Estrategia de Escalado (Target Tracking)

### Métricas de Auto Scaling

La plataforma utiliza **Target Tracking Scaling** de AWS, que ajusta automáticamente la capacidad para mantener las métricas objetivo.

#### 1. **CPU Utilization Target**
```hcl
cpu_target_value = 70  # 70% CPU promedio
```

**Comportamiento**:
- Cuando **CPU promedio del servicio > 70%** durante 60 segundos → **Scale Out**
- Cuando **CPU promedio del servicio < 70%** durante 300 segundos → **Scale In**

**Ejemplo**: Si tienes 2 tasks corriendo al 85% CPU cada una:
1. ECS lanza una tercera task
2. La carga se redistribuye: ~57% CPU por task
3. El sistema se estabiliza bajo el target del 70%

#### 2. **Memory Utilization Target**
```hcl
memory_target_value = 80  # 80% memoria promedio
```

**Comportamiento**:
- Cuando **memoria promedio del servicio > 80%** durante 60 segundos → **Scale Out**
- Cuando **memoria promedio del servicio < 80%** durante 300 segundos → **Scale In**

**Crítico para NetworkX**: Los grafos se cargan en memoria. Si un análisis requiere 6 GB:
- Con 8 GB por task → 75% utilización (OK)
- Con grafos crecientes, puede superar 80% → auto-scaling preventivo

### Cooldown Periods

```hcl
scale_out_cooldown = 60   # 1 minuto
scale_in_cooldown  = 300  # 5 minutos
```

**Razón**:
- **Scale Out rápido** (1 min): Responder rápidamente a picos de carga
- **Scale In lento** (5 min): Evitar "flapping" - no reducir capacidad prematuramente

### Límites de Capacidad

```hcl
min_capacity = 2   # Siempre ≥2 tasks para HA
max_capacity = 10  # Máximo 10 tasks
```

**Cálculo de capacidad máxima**:
- 10 tasks × 4 vCPU = 40 vCPUs
- 10 tasks × 8 GB = 80 GB RAM total
- Suficiente para ~50-100 usuarios concurrentes analizando grafos medianos

### Políticas Duales (CPU + Memoria)

Ambas políticas operan **simultáneamente**:
- Si **cualquiera** supera su target → Scale Out
- Solo hace Scale In cuando **ambas** están bajo target

**Ventaja**: Protege contra cuellos de botella tanto en CPU (cálculos de grafos) como en memoria (tamaño de grafos).

### Ejemplo de Escenario Real

**Estado inicial**: 2 tasks al 50% CPU, 60% memoria

**Evento**: 10 usuarios ejecutan análisis de comunidades simultáneamente

1. **T+0s**: CPU sube a 85%, memoria a 75%
2. **T+60s**: Target de CPU superado → Scale Out a 3 tasks
3. **T+90s**: Carga redistribuida → 57% CPU, 50% memoria por task
4. **T+600s**: Usuarios terminan → 30% CPU, 40% memoria
5. **T+900s**: Ambos targets bajo umbral por >300s → Scale In a 2 tasks

---

## 📦 Pre-requisitos

### Software Requerido

- [Terraform](https://www.terraform.io/downloads) >= 1.5.0
- [AWS CLI](https://aws.amazon.com/cli/) >= 2.0
- [Docker](https://www.docker.com/get-started) >= 20.10
- Bash shell (para scripts de deployment)

### Credenciales AWS

Configurar AWS CLI con credenciales que tengan permisos para:
- VPC, Subnets, Security Groups, NAT Gateway, Internet Gateway
- ECS, ECR, CloudWatch Logs
- IAM Roles y Policies
- EFS
- Application Load Balancer
- S3 (para logs)

```bash
aws configure
```

### (Opcional) Dominio y Certificado SSL

Para HTTPS en producción:
1. Registrar un dominio en Route53 o cualquier registrar
2. Crear certificado en AWS Certificate Manager (ACM)
3. Configurar en `terraform.tfvars`:
   ```hcl
   domain_name     = "fraud-detection.tu-dominio.com"
   certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/..."
   ```

---

## 🚀 Despliegue

### 1. Clonar y Configurar

```bash
cd antifraude-iac/terraform
cp terraform.tfvars.example terraform.tfvars
```

Editar `terraform.tfvars` con tus valores:

```hcl
project_name = "fraud-detection"
environment  = "production"
aws_region   = "us-east-1"

# Ajustar recursos según carga esperada
container_cpu    = 4096  # 4 vCPU
container_memory = 8192  # 8 GB

desired_count = 2
min_capacity  = 2
max_capacity  = 10

# Opcional: HTTPS
# domain_name     = "fraud-detection.example.com"
# certificate_arn = "arn:aws:acm:..."
```

### 2. Inicializar Terraform

```bash
terraform init
```

### 3. Planificar Cambios

```bash
terraform plan -out=tfplan
```

Revisar los recursos que se crearán (~40-50 recursos).

### 4. Aplicar Infraestructura

```bash
terraform apply tfplan
```

⏱️ Tiempo estimado: 5-7 minutos

### 5. Construir y Subir Imagen Docker

```bash
cd ..  # Volver a antifraude-iac/
chmod +x build-and-push.sh
./build-and-push.sh
```

Este script:
- Autentica con ECR
- Construye la imagen Docker (multi-stage)
- Tagea con `latest` y timestamp
- Sube a ECR

### 6. Desplegar a ECS

```bash
chmod +x deploy.sh
./deploy.sh
```

Este script:
- Fuerza un nuevo deployment en ECS
- Espera a que el servicio se estabilice
- Muestra el estado del deployment

### 7. Verificar Deployment

```bash
terraform output application_url
```

Abrir la URL en el navegador. Deberías ver la aplicación Gradio.

---

## 💾 Persistencia de Datos (EFS)

### Arquitectura de Storage

```
ECS Task Container
├── /app/logs/              → Montado desde EFS
├── /app/exports/           → Montado desde EFS
│   └── layouts/            → Montado desde EFS
└── /app/persistent/        → EFS Mount Point (raíz)
```

### Configuración EFS

El volumen EFS se monta en `/app/persistent` dentro del contenedor. Los subdirectorios `logs`, `exports` y `layouts` se crean automáticamente.

**Task Definition** (extracto):
```hcl
volume {
  name = "efs-storage"
  efs_volume_configuration {
    file_system_id          = aws_efs_file_system.main.id
    transit_encryption      = "ENABLED"
    authorization_config {
      access_point_id = aws_efs_access_point.main.id
      iam             = "ENABLED"
    }
  }
}

mountPoints = [{
  sourceVolume  = "efs-storage"
  containerPath = "/app/persistent"
  readOnly      = false
}]
```

### Ventajas de EFS

✅ **Multi-AZ**: Acceso compartido desde todas las tasks  
✅ **Persistencia**: Datos sobreviven a reinicios/deployments  
✅ **Escalabilidad**: Crece automáticamente según demanda  
✅ **Backup**: Backups automáticos habilitados  
✅ **Cost-Optimization**: Lifecycle a IA después de 30 días

### Acceso a los Datos

#### Desde AWS Console:
1. EFS → File Systems → Seleccionar el filesystem
2. Usar EFS File Browser o montar en EC2

#### Desde CLI:
```bash
# Obtener EFS ID
terraform output efs_id

# Montar en EC2 (requiere security group con acceso NFS)
sudo mount -t efs -o tls fs-xxxxx:/ /mnt/efs
```

---

## 📊 Monitoring

### CloudWatch Logs

**Log Group**: `/ecs/fraud-detection-production`  
**Retention**: 30 días  
**Streams**: Uno por task (automático)

Ver logs:
```bash
aws logs tail /ecs/fraud-detection-production --follow
```

### Métricas Clave

Acceder en CloudWatch → Metrics → ECS:

- **CPUUtilization**: % de CPU utilizado por el servicio
- **MemoryUtilization**: % de memoria utilizada
- **TargetResponseTime**: Tiempo de respuesta del ALB
- **HealthyHostCount**: Número de tasks saludables
- **UnHealthyHostCount**: Tasks con health checks fallidos

### Alarmas Configuradas

1. **CPU High**: Alerta cuando CPU > 85% durante 2 minutos
2. **Memory High**: Alerta cuando memoria > 90% durante 2 minutos

Configurar SNS Topics para notificaciones:
```hcl
# En terraform/main.tf
resource "aws_sns_topic" "alerts" {
  name = "${local.name_prefix}-alerts"
}

# Añadir a las alarmas
alarm_actions = [aws_sns_topic.alerts.arn]
```

### Dashboard Recomendado

Crear un dashboard en CloudWatch con:
- CPU y Memoria del servicio ECS
- Conteo de tasks (running, pending, stopped)
- Request count y latencia del ALB
- 5XX y 4XX errors del ALB
- EFS throughput y IOPS

---

## 💰 Costos Estimados

Estimación mensual para configuración base (US East 1):

### Configuración Base
- 2 tasks × 4 vCPU × 8 GB RAM en Fargate
- 100 GB en EFS
- 1 Application Load Balancer
- 100 GB de logs en CloudWatch
- 50 GB de transferencia de datos

| Servicio | Configuración | Costo Mensual (USD) |
|----------|---------------|---------------------|
| **ECS Fargate** | 2 tasks × 4 vCPU × 8 GB × 730h | ~$283 |
| **NAT Gateway** | 2 NAT × 730h + 50 GB data | ~$100 |
| **ALB** | 1 ALB × 730h + LCU | ~$25 |
| **EFS** | 100 GB Standard + lifecycle | ~$30 |
| **CloudWatch** | 100 GB logs + métricas | ~$10 |
| **ECR** | 10 GB storage | ~$1 |
| **Data Transfer** | 50 GB out | ~$5 |
| **TOTAL** | | **~$454/mes** |

### Opciones de Optimización

#### 1. Usar Fargate Spot (hasta 70% descuento)
```hcl
# En ecs_fargate.tf
capacity_provider_strategy {
  capacity_provider = "FARGATE_SPOT"
  weight           = 100
  base             = 0
}
```
**Ahorro**: ~$198/mes → **Total: ~$256/mes**

#### 2. Usar un solo NAT Gateway
- Configurar solo 1 NAT Gateway (pierde HA)
- **Ahorro**: ~$45/mes → **Total: ~$409/mes**

#### 3. Reducir tasks en horario no productivo
- Usar AWS Instance Scheduler o Lambda
- Reducir a 1 task durante 16h/día
- **Ahorro**: ~$94/mes → **Total: ~$360/mes**

#### 4. EFS Infrequent Access
- Ya configurado: automático después de 30 días
- **Ahorro**: Variable según uso, hasta 92% en datos old

### Configuración Optimizada (Prod)
**Spot + 1 NAT + Scheduling**: **~$213/mes**

### Configuración Dev (bajo costo)
- 1 task × 2 vCPU × 4 GB
- 1 NAT Gateway
- Sin HA
**Costo**: **~$95/mes**

---

## 🔍 Evaluación TRIAGE

### T - Task (Asignación Central) ✅

**Objetivo**: Desplegar aplicación Gradio + NetworkX en AWS ECS Fargate con HA y auto-scaling.

**Entregable**: Repositorio IaC completo con:
- ✅ Terraform modules para todos los componentes AWS
- ✅ Dockerfile multi-stage optimizado
- ✅ Scripts de deployment automatizados
- ✅ Documentación completa de arquitectura y escalado

### C - Context (Información Esencial) ✅

**Audience**: Ingeniería de Plataforma  
**Platform**: AWS ECS Fargate (serverless containers)  
**Stack**: Python 3.11, Pandas, NetworkX, Pyvis, Gradio 4.15  

**Requisitos Cumplidos**:
- ✅ HTTPS via ALB (con certificado ACM opcional)
- ✅ CPU/Memoria suficiente (4 vCPU / 8 GB configurable)
- ✅ Alta Disponibilidad Multi-AZ
- ✅ VPC con subnets privadas/públicas

### G - Goal (Criterios de Éxito) ✅

**Dockerfile**:
- ✅ Multi-stage build para optimizar tamaño
- ✅ Dependencias: pandas, NetworkX, Gradio, Pyvis
- ✅ Manejo de archivos estáticos (exports/, logs/)
- ✅ Usuario no-root (UID 1001)
- ✅ Health check integrado

**Servicio ECS Fargate**:
- ✅ Task Definition con recursos configurables
- ✅ Service con ALB integration
- ✅ Rolling deployment + circuit breaker
- ✅ Auto-scaling Target Tracking (CPU + Memoria)

**Persistencia**:
- ✅ EFS con Access Point
- ✅ Montaje en `/app/persistent`
- ✅ Backups habilitados
- ✅ Lifecycle policies

### R - References (Estructura) ✅

```
/antifraude-iac
├── terraform/
│   ├── main.tf                    ✅
│   ├── vpc.tf                     ✅
│   ├── ecr.tf                     ✅
│   ├── ecs_fargate.tf             ✅ (NUEVO - auto-scaling)
│   ├── load_balancing.tf          ✅
│   ├── storage.tf                 ✅
│   ├── iam.tf                     ✅
│   ├── security_groups.tf         ✅
│   ├── variables.tf               ✅
│   ├── outputs.tf                 ✅ (NUEVO)
│   └── terraform.tfvars.example   ✅ (NUEVO)
├── Dockerfile                     ✅ (OPTIMIZADO)
├── .dockerignore                  ✅ (NUEVO)
├── build-and-push.sh              ✅ (NUEVO)
├── deploy.sh                      ✅ (NUEVO)
└── README.md                      ✅ (COMPLETO)
```

### E - Evaluate (Calidad) 📊

#### Seguridad (IAM y Red): **9/10**

**Fortalezas**:
- ✅ Subnets privadas para ECS (no IPs públicas)
- ✅ Security Groups con reglas mínimas necesarias
- ✅ IAM roles con permisos scoped (EFS Access Point)
- ✅ Encriptación en tránsito (EFS, ALB HTTPS)
- ✅ Encriptación en reposo (EFS, ECR)
- ✅ Usuario no-root en contenedor

**Mejoras posibles** (-1 punto):
- WAF en ALB para protección DDoS/SQL injection
- Secrets Manager para credenciales (si hubiera DB)

#### Eficiencia de Costes (Fargate/EFS): **8.5/10**

**Fortalezas**:
- ✅ Fargate (no EC2 idle): pago solo por uso
- ✅ EFS lifecycle to IA (ahorro 92% en datos old)
- ✅ ECR lifecycle policy (gestión de imágenes)
- ✅ S3 lifecycle para logs ALB (90 días)
- ✅ Auto-scaling down durante baja carga
- ✅ NAT Gateway redundante (necesario para HA)

**Mejoras posibles** (-1.5 puntos):
- Fargate Spot (hasta 70% descuento) - fácil de añadir
- Considerar VPC Endpoints para S3/ECR (reduce NAT Gateway data)
- Reserved Capacity para workloads predecibles

### I - Iterate (Refinamiento) ✅

**Score propio**: 8.75/10

**Mejoras implementadas en este iteration**:
1. ✅ Dockerfile multi-stage completo con optimizaciones
2. ✅ Auto-scaling Target Tracking dual (CPU + Memoria)
3. ✅ Scripts de deployment automatizados
4. ✅ Documentación exhaustiva de estrategia de escalado
5. ✅ Outputs.tf con comandos de deployment
6. ✅ Alarmas CloudWatch
7. ✅ Circuit breaker en ECS Service

---

## 🛠️ Troubleshooting

### Task no arranca

**Síntoma**: ECS service muestra tasks en estado `STOPPED`

**Diagnóstico**:
```bash
# Ver logs de la última task stopped
aws ecs describe-tasks \
  --cluster fraud-detection-production-cluster \
  --tasks $(aws ecs list-tasks \
    --cluster fraud-detection-production-cluster \
    --service-name fraud-detection-production-service \
    --desired-status STOPPED \
    --max-items 1 \
    --query 'taskArns[0]' \
    --output text)
```

**Causas comunes**:
- ❌ Imagen no existe en ECR → Verificar `terraform output ecr_repository_url`
- ❌ Health check falla → Verificar logs de la aplicación
- ❌ EFS no accesible → Verificar Security Group `efs`

### ALB retorna 503

**Síntoma**: `curl http://alb-url` retorna 503 Service Unavailable

**Diagnóstico**:
```bash
# Ver targets unhealthy
aws elbv2 describe-target-health \
  --target-group-arn $(terraform output -raw target_group_arn)
```

**Causas comunes**:
- ❌ Health check path incorrecto → Verificar que Gradio responda en `/`
- ❌ Tasks no registradas → Esperar 2-3 minutos después del deploy
- ❌ Security Group bloquea tráfico → Verificar regla ALB → ECS tasks

### EFS Permission Denied

**Síntoma**: Task logs muestran `Permission denied` al escribir en EFS

**Solución**:
```bash
# Verificar que UID/GID del Dockerfile (1001) match con EFS Access Point
terraform state show aws_efs_access_point.main | grep -A5 posix_user
```

Debe mostrar:
```
posix_user {
  uid = 1001
  gid = 1001
}
```

### Auto-scaling no funciona

**Síntoma**: CPU > 70% pero no escala

**Diagnóstico**:
```bash
# Ver políticas de scaling
aws application-autoscaling describe-scaling-policies \
  --service-namespace ecs \
  --resource-id service/fraud-detection-production-cluster/fraud-detection-production-service
```

**Causas comunes**:
- ❌ Max capacity alcanzado → Aumentar `max_capacity` en variables.tf
- ❌ Cooldown period activo → Esperar que termine el cooldown
- ❌ Métricas no se publican → Verificar CloudWatch métricas ECS

---

## 📚 Recursos Adicionales

- [AWS ECS Fargate Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/intro.html)
- [Target Tracking Scaling](https://docs.aws.amazon.com/autoscaling/application/userguide/application-auto-scaling-target-tracking.html)
- [EFS Performance](https://docs.aws.amazon.com/efs/latest/ug/performance.html)
- [Gradio Documentation](https://www.gradio.app/docs/)
- [NetworkX Documentation](https://networkx.org/documentation/stable/)

---

## 🤝 Contribuir

Para mejoras o issues, abrir un PR o issue en el repositorio.

---

## 📄 Licencia

Este proyecto está bajo licencia MIT.

---

## 👥 Equipo

Desarrollado por el equipo de Data Science para análisis de fraude con grafos.

**Contacto**: data-science@empresa.com

---

**¡Deployment exitoso! 🚀**
