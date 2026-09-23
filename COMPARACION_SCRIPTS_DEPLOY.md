# 📊 Comparación de Scripts de Deployment

## 🎯 Resumen Ejecutivo

**RECOMENDACIÓN:** Usa los scripts de `antifraude-iac/` porque se sincronizan automáticamente con Terraform.

---

## 📝 Tres Scripts Disponibles

### 1️⃣ `deploy-to-aws.bat` (Raíz del Proyecto)
**Ubicación:** `D:\graph_aml\fraud-detection-graphs\deploy-to-aws.bat`

```batch
# VALORES HARDCODED (⚠️ PUEDEN QUEDAR DESACTUALIZADOS)
set AWS_REGION=eu-north-1
set ECR_REPO=<AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/fraud-detection-dev-app
set ECS_CLUSTER=fraud-detection-dev-cluster
set ECS_SERVICE=fraud-detection-dev-service
```

**¿Qué hace?**
1. ✅ Autentica con ECR
2. ✅ Build Docker
3. ✅ Tag como `:latest`
4. ✅ Push a ECR
5. ✅ Deploy a ECS
6. ❌ NO espera a que se estabilice

**Ventajas:**
- Todo en un solo comando
- Rápido de ejecutar

**Desventajas:**
- ⚠️ **Valores hardcoded pueden desincronizarse con Terraform**
- Solo crea tag `:latest` (no hay historial para rollback)
- No espera estabilización
- URL del ALB hardcoded

---

### 2️⃣ `build-and-push.bat` (Carpeta IAC)
**Ubicación:** `D:\graph_aml\fraud-detection-graphs\antifraude-iac\build-and-push.bat`

```batch
# VALORES DINÁMICOS (✅ SIEMPRE ACTUALIZADOS)
for /f "delims=" %%i in ('terraform output -raw ecr_repository_url') do set ECR_URL=%%i
for /f "delims=" %%i in ('terraform output -raw aws_region') do set AWS_REGION=%%i
```

**¿Qué hace?**
1. ✅ Lee configuración actual de Terraform
2. ✅ Autentica con ECR
3. ✅ Build Docker
4. ✅ Tag como `:latest` + tag con timestamp
5. ✅ Push ambos tags a ECR
6. ❌ NO hace deploy (solo build & push)

**Ventajas:**
- ✅ Siempre sincronizado con Terraform
- ✅ Crea tag con timestamp (ej: `20251029-143022`)
- ✅ Permite rollback a versiones anteriores
- ✅ Separación de responsabilidades

**Desventajas:**
- Necesita ejecutar `deploy.bat` después para desplegar

---

### 3️⃣ `deploy.bat` (Carpeta IAC)
**Ubicación:** `D:\graph_aml\fraud-detection-graphs\antifraude-iac\deploy.bat`

```batch
# VALORES DINÁMICOS (✅ SIEMPRE ACTUALIZADOS)
for /f "delims=" %%i in ('terraform output -raw ecs_cluster_name') do set CLUSTER_NAME=%%i
for /f "delims=" %%i in ('terraform output -raw ecs_service_name') do set SERVICE_NAME=%%i
```

**¿Qué hace?**
1. ✅ Lee configuración actual de Terraform
2. ✅ Fuerza nuevo deployment en ECS
3. ✅ **Espera hasta que el servicio esté estable** (3-5 min)
4. ✅ Reporta éxito o fallo

**Ventajas:**
- ✅ Siempre sincronizado con Terraform
- ✅ Espera a estabilización (sabes si funcionó)
- ✅ Usa `aws ecs wait services-stable`
- ✅ Muestra URL dinámica desde Terraform

**Desventajas:**
- No hace build ni push (necesitas ejecutar `build-and-push.bat` primero)

---

## 🔄 Flujos de Trabajo Completos

### **Opción A: Scripts IAC (RECOMENDADO ✅)**

```bash
cd D:\graph_aml\fraud-detection-graphs\antifraude-iac

# Paso 1: Build & Push
.\build-and-push.bat
# - Crea imagen Docker con requirements.txt actualizado
# - Sube a ECR con tags: latest + timestamp

# Paso 2: Deploy
.\deploy.bat
# - Despliega nueva versión
# - Espera hasta confirmar que funciona
```

**Cuándo usar:**
- ✅ Deployment normal (recomendado)
- ✅ Cuando cambiaste código o requirements
- ✅ Cuando quieres historial de versiones
- ✅ En CI/CD pipelines

---

### **Opción B: Script Raíz (RÁPIDO pero RIESGOSO ⚠️)**

```bash
cd D:\graph_aml\fraud-detection-graphs

# Todo en uno
.\deploy-to-aws.bat
```

**Cuándo usar:**
- ⚡ Deploy rápido de emergencia
- ⚠️ Solo si NO has cambiado nada en Terraform
- ⚠️ Solo si los valores hardcoded están actualizados

**NO usar si:**
- ❌ Cambiaste región de AWS
- ❌ Cambiaste nombres de recursos en Terraform
- ❌ Es tu primer deploy después de cambios en infra

---

## 🆚 Tabla Comparativa Detallada

| Característica | `deploy-to-aws.bat` | `build-and-push.bat` | `deploy.bat` |
|---------------|-------------------|---------------------|-------------|
| **Ubicación** | Raíz | IAC | IAC |
| **Configuración** | 🔴 Hardcoded | 🟢 Terraform | 🟢 Terraform |
| **Auth ECR** | ✅ | ✅ | ❌ |
| **Build Docker** | ✅ | ✅ | ❌ |
| **Tag latest** | ✅ | ✅ | - |
| **Tag timestamp** | ❌ | ✅ | - |
| **Push ECR** | ✅ | ✅ | ❌ |
| **Deploy ECS** | ✅ | ❌ | ✅ |
| **Wait stable** | ❌ | ❌ | ✅ |
| **Rollback capability** | ❌ | ✅ | - |
| **Sync con Terraform** | ❌ | ✅ | ✅ |

---

## 🎯 Para Tu Caso Específico

### Acabas de actualizar `requirements.txt` con `pydantic==2.10.6`

**Usa el flujo IAC:**

```bash
cd D:\graph_aml\fraud-detection-graphs\antifraude-iac

# 1. Build con nuevo pydantic
.\build-and-push.bat

# 2. Deploy y esperar
.\deploy.bat
```

**Ventajas para este caso:**
1. ✅ Build usa el nuevo `requirements.txt`
2. ✅ Tag con timestamp permite rollback si falla
3. ✅ `deploy.bat` espera y confirma éxito
4. ✅ Valores sincronizados con tu Terraform actual

---

## 🔍 ¿Cómo Verificar Qué Script Usar?

### Si NO estás seguro de tus valores hardcoded:

```bash
cd D:\graph_aml\fraud-detection-graphs\antifraude-iac\terraform

# Ver valores actuales de Terraform
terraform output ecr_repository_url
terraform output ecs_cluster_name
terraform output ecs_service_name
terraform output aws_region
```

Compara con los valores en `deploy-to-aws.bat`:
- ✅ Si coinciden → Puedes usar cualquier script
- ❌ Si NO coinciden → **SOLO usa scripts IAC**

---

## 🚨 Problemas Comunes

### Problema: "No se pudieron obtener los datos de Terraform"

**Solución:**
```bash
cd D:\graph_aml\fraud-detection-graphs\antifraude-iac\terraform
terraform init
terraform plan
terraform apply
```

### Problema: `deploy-to-aws.bat` falla con recursos no encontrados

**Causa:** Valores hardcoded desactualizados

**Solución:** Usa los scripts IAC en su lugar

---

## 💡 Recomendaciones Finales

1. **Para uso diario:** Usa scripts IAC (`build-and-push.bat` + `deploy.bat`)
2. **Para CI/CD:** Scripts IAC exclusivamente
3. **Actualiza o elimina** `deploy-to-aws.bat` para evitar confusión
4. **Siempre verifica** outputs de Terraform antes de deploy manual

---

## 📚 Comandos Útiles

```bash
# Ver última versión desplegada
aws ecs describe-services --cluster fraud-detection-dev-cluster --services fraud-detection-dev-service --region eu-north-1

# Ver logs en tiempo real
aws logs tail /ecs/fraud-detection-dev-app --follow --region eu-north-1

# Rollback a versión anterior (usando timestamp tag)
docker pull <ECR_URL>:20251029-143022
docker tag <ECR_URL>:20251029-143022 <ECR_URL>:latest
docker push <ECR_URL>:latest
aws ecs update-service --cluster ... --service ... --force-new-deployment
```
