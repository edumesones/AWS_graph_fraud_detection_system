# 📦 Herramientas AWS - Fraud Detection Project

## Tabla de Servicios AWS Utilizados

| # | Herramienta AWS | Contenido/Recursos | Funcionalidad en el Proyecto |
|---|-----------------|-------------------|------------------------------|
| 1 | **Amazon VPC** | • 1 VPC (10.0.0.0/16)<br>• 2 Subnets públicas<br>• 2 Subnets privadas<br>• 2 NAT Gateways<br>• 1 Internet Gateway<br>• Route Tables | **Red aislada y segura**<br>Proporciona aislamiento de red para toda la infraestructura. Las subnets privadas alojan los contenedores ECS (sin IP pública), mientras que las subnets públicas alojan el ALB para acceso externo. |
| 2 | **Amazon ECS Fargate** | • 1 ECS Cluster<br>• 1 Task Definition (4 vCPU, 8 GB RAM)<br>• 1 ECS Service<br>• 2-10 Tasks (auto-scaling) | **Plataforma de ejecución de contenedores**<br>Ejecuta la aplicación Gradio + NetworkX en contenedores serverless. Gestiona automáticamente la infraestructura subyacente sin necesidad de administrar servidores EC2. |
| 3 | **Amazon ECR** | • 1 Private Repository<br>• Image scanning<br>• Lifecycle policies | **Registro de imágenes Docker**<br>Almacena las imágenes Docker de la aplicación. Escanea automáticamente las imágenes en busca de vulnerabilidades y gestiona el ciclo de vida eliminando imágenes antiguas. |
| 4 | **Application Load Balancer** | • 1 ALB (público)<br>• 1 Target Group<br>• HTTP Listener (80)<br>• HTTPS Listener (443, opcional)<br>• Health checks | **Punto de entrada HTTPS**<br>Distribuye el tráfico entrante entre múltiples tasks de ECS en diferentes zonas de disponibilidad. Realiza health checks para asegurar que solo las tasks saludables reciben tráfico. |
| 5 | **Amazon EFS** | • 1 File System (encriptado)<br>• 2 Mount Targets (Multi-AZ)<br>• 1 Access Point<br>• Backup policy | **Almacenamiento persistente compartido**<br>Almacena logs, visualizaciones de grafos (exports/) y layouts de Pyvis. Montado en `/app/persistent` en todos los contenedores, permitiendo compartir datos entre tasks. |
| 6 | **AWS Auto Scaling** | • 2 Scaling Policies (CPU + Memoria)<br>• Target Tracking<br>• Capacidad: 2-10 tasks | **Escalado automático basado en métricas**<br>Ajusta dinámicamente el número de tasks según la carga de CPU (>70%) y memoria (>80%). Escala out rápido (60s) y scale in lento (300s) para optimizar costos y rendimiento. |
| 7 | **Amazon CloudWatch** | • Logs Groups<br>• Métricas ECS/ALB<br>• 2 Alarmas (CPU, Memoria)<br>• Container Insights | **Monitoreo y observabilidad**<br>Centraliza logs de todos los contenedores, métricas de rendimiento y alarmas. Permite debugging en tiempo real y análisis histórico de la aplicación. |
| 8 | **AWS IAM** | • 1 Task Execution Role<br>• 1 Task Role<br>• Policies (ECR, EFS, Logs) | **Seguridad y permisos**<br>Gestiona permisos con mínimo privilegio. El Task Execution Role permite pull de imágenes y escritura de logs. El Task Role permite acceso a EFS desde los contenedores. |
| 9 | **Security Groups** | • ALB Security Group<br>• ECS Tasks Security Group<br>• EFS Security Group | **Firewall de red**<br>Controla el tráfico entrante/saliente. ALB acepta 80/443 desde internet, ECS Tasks solo desde ALB en puerto 7860, EFS solo NFS desde ECS Tasks. |
| 10 | **Amazon S3** | • 1 Bucket (ALB logs)<br>• Lifecycle (90 días)<br>• Encriptación AES256 | **Almacenamiento de logs del ALB**<br>Guarda access logs del balanceador para auditoría y análisis de tráfico. Los logs se eliminan automáticamente después de 90 días. |
| 11 | **Elastic IP** | • 2 EIPs (NAT Gateways) | **IPs públicas estáticas**<br>Proporcionan IPs fijas para los NAT Gateways, permitiendo que las tasks en subnets privadas accedan a internet (ej: para pull de paquetes pip/apt). |

---

## 🎯 Flujo de Datos y Comunicación

```
Internet
  ↓ (HTTPS/HTTP)
Application Load Balancer (Público)
  ↓ (HTTP puerto 7860)
ECS Fargate Tasks (Privado - Multi-AZ)
  ├─→ Amazon ECR (Pull imágenes Docker)
  ├─→ Amazon EFS (Read/Write logs, exports)
  ├─→ CloudWatch Logs (Envío de logs)
  └─→ Internet via NAT Gateway (Paquetes Python/apt)
```

---

## 💡 Decisiones de Arquitectura

### ¿Por qué Fargate en lugar de EC2?

| Criterio | Fargate ✅ | EC2 |
|----------|-----------|-----|
| **Administración** | Sin servidores que gestionar | Patching, scaling de hosts |
| **Costos** | Pago por segundo de uso | Instancias siempre corriendo |
| **Escalado** | Automático e instantáneo | Requiere ASG y warm pools |
| **Seguridad** | Aislamiento por task | Compartido a nivel de host |

### ¿Por qué EFS en lugar de S3?

| Criterio | EFS ✅ | S3 |
|----------|-------|-----|
| **Tipo de acceso** | File system (POSIX) | Object storage (API) |
| **Latencia** | Baja (~1ms) | Media (~10-50ms) |
| **Uso compartido** | Múltiples tasks simultáneas | Requiere sincronización |
| **Caso de uso** | Logs, archivos temporales | Archivos estáticos finales |

### ¿Por qué ALB en lugar de NLB?

| Criterio | ALB ✅ | NLB |
|----------|-------|-----|
| **Capa OSI** | Layer 7 (HTTP/HTTPS) | Layer 4 (TCP/UDP) |
| **Health checks** | HTTP path-based | Solo puerto |
| **Sticky sessions** | Cookie-based | IP-based |
| **Caso de uso** | Aplicaciones web (Gradio) | Tráfico TCP de alto rendimiento |

---

## 📊 Flujo de Deployment

```
1. Developer
   ↓ (git push)
2. Build Docker Image
   ↓ (docker build)
3. Push to ECR
   ↓ (docker push)
4. ECS Task Definition
   ↓ (referencia a imagen ECR)
5. ECS Service
   ↓ (rolling deployment)
6. Running Tasks
   ├─→ Pull imagen desde ECR
   ├─→ Mount EFS
   ├─→ Register con ALB Target Group
   └─→ Start Gradio app
7. ALB Health Check
   ↓ (GET / → 200 OK)
8. Task HEALTHY
   ↓
9. Tráfico de usuarios
```

---

## 🔒 Seguridad Implementada

| Capa | Mecanismo | Implementación |
|------|-----------|----------------|
| **Red** | Private Subnets | Tasks sin IP pública |
| **Firewall** | Security Groups | Reglas restrictivas por servicio |
| **Acceso** | IAM Roles | Mínimos privilegios (least privilege) |
| **Datos en tránsito** | TLS/SSL | ALB HTTPS, EFS transit encryption |
| **Datos en reposo** | Encriptación | EFS, ECR, S3 (AES256) |
| **Contenedor** | Usuario no-root | UID 1001 (appuser) |
| **Imágenes** | Scanning | ECR escanea vulnerabilidades |

---

## 💰 Componentes de Costo

| Servicio | Factor de Costo | Optimización |
|----------|----------------|--------------|
| **ECS Fargate** | vCPU-hora + GB-hora | Usar Spot (70% ahorro), auto-scaling down |
| **NAT Gateway** | Horas + data transfer | VPC Endpoints para S3/ECR |
| **ALB** | Horas + LCU | Consolidar aplicaciones en 1 ALB |
| **EFS** | GB storage | Lifecycle to IA (92% ahorro) |
| **Data Transfer** | GB out to internet | CloudFront CDN para assets estáticos |

---

## 🚀 Escalabilidad

### Horizontal Scaling (Auto Scaling)
- **Métrica**: CPU > 70% o Memoria > 80%
- **Acción**: Lanzar nuevas tasks (max 10)
- **Tiempo**: Scale out en ~60s, scale in en ~300s

### Vertical Scaling (Manual)
- **Cambiar en `terraform.tfvars`**:
  ```hcl
  container_cpu    = 8192  # 8 vCPU
  container_memory = 16384 # 16 GB
  ```
- **Aplicar**: `terraform apply`
- **Efecto**: Nuevas tasks con más recursos

### Multi-Region (Futuro)
- Replicar stack en otra región
- Route53 con health checks
- Global Accelerator para baja latencia

---

## 📈 Métricas Clave a Monitorear

| Métrica | Umbral | Acción |
|---------|--------|--------|
| **CPU Utilization** | > 85% | Alarma + verificar auto-scaling |
| **Memory Utilization** | > 90% | Alarma + aumentar memoria |
| **Target Response Time** | > 2000ms | Investigar código/queries |
| **Unhealthy Host Count** | > 0 | Revisar logs de tasks |
| **4XX Errors** | > 5% | Problema en aplicación |
| **5XX Errors** | > 1% | Problema en backend/timeout |

---

## 🔄 Actualizaciones y Rollbacks

### Deployment Estrategias

**Rolling Update (actual)**:
- Max 200%, Min 100%
- Deploying: 4 tasks → 2 old + 2 new → 0 old + 2 new
- Rollback automático con Circuit Breaker

**Blue/Green (futuro)**:
- 2 Target Groups (blue, green)
- Traffic shifting 10% → 50% → 100%
- Rollback instantáneo

---

## 🎓 Recursos de Aprendizaje

| Servicio | Documentación AWS |
|----------|-------------------|
| ECS Fargate | https://docs.aws.amazon.com/ecs/latest/developerguide/AWS_Fargate.html |
| Auto Scaling | https://docs.aws.amazon.com/autoscaling/application/userguide/ |
| EFS | https://docs.aws.amazon.com/efs/latest/ug/ |
| ALB | https://docs.aws.amazon.com/elasticloadbalancing/latest/application/ |
| VPC | https://docs.aws.amazon.com/vpc/latest/userguide/ |

---

**Fecha de creación**: $(date)  
**Versión de Terraform**: >= 1.5.0  
**Región AWS recomendada**: us-east-1, us-west-2, eu-west-1
