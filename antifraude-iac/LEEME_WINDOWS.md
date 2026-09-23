# ✅ RESUMEN - Todo Listo para Windows
Terraform gestiona la infraestructura (Task Definition con variables de entorno). El script de deploy gestiona el código (imagen Docker). Cambios en infraestructura → terraform apply. Cambios en código → deploy-to-aws.bat
## 📦 Archivos Creados para Windows

```
antifraude-iac/
├── ✅ build-and-push.bat          Script Windows: Build Docker + Push ECR
├── ✅ deploy.bat                  Script Windows: Deploy a ECS
├── ✅ validate.bat                Script Windows: Validación pre-deployment
├── 📄 COMANDOS_WINDOWS.md         ⭐ GUÍA PARA WINDOWS - LEER PRIMERO
│
├── 📄 COMANDOS_EJECUTA.md         Guía completa (para Linux/Mac)
├── 📄 HERRAMIENTAS_AWS.md         Lista de servicios AWS
├── 📄 README.md                   Documentación arquitectura
├── 📄 arquitectura-aws.excalidraw.json  Diagrama importable
│
├── Dockerfile                     Multi-stage optimizado
├── .dockerignore                  Exclusiones Docker
│
├── build-and-push.sh              Script Linux (no usar en Windows)
├── deploy.sh                      Script Linux (no usar en Windows)
├── validate.sh                    Script Linux (no usar en Windows)
│
└── terraform/                     Infraestructura AWS
    ├── main.tf
    ├── variables.tf
    ├── terraform.tfvars.example   ⭐ COPIAR Y CONFIGURAR
    ├── outputs.tf
    ├── vpc.tf
    ├── security_groups.tf
    ├── iam.tf
    ├── ecr.tf
    ├── ecs_fargate.tf             Con auto-scaling
    ├── load_balancing.tf
    └── storage.tf
```

---

## 🪟 COMANDOS PARA WINDOWS (Quick Start)

### 1️⃣ Validar
```cmd
cd D:\graph_aml\fraud-detection-graphs\antifraude-iac
validate.bat
```

### 2️⃣ Configurar Terraform
```cmd
cd terraform
copy terraform.tfvars.example terraform.tfvars
notepad terraform.tfvars
```

### 3️⃣ Crear Infraestructura
```cmd
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### 4️⃣ Build y Push Docker
```cmd
cd ..
build-and-push.bat
```

### 5️⃣ Deploy
```cmd
deploy.bat
```

### 6️⃣ Obtener URL
```cmd
cd terraform
terraform output application_url
```

---

## ⚠️ IMPORTANTE PARA WINDOWS

### ✅ USA ESTOS:
- `build-and-push.bat`
- `deploy.bat`
- `validate.bat`
- `COMANDOS_WINDOWS.md`

### ❌ NO USES ESTOS (son para Linux):
- `build-and-push.sh`
- `deploy.sh`
- `validate.sh`

---

## 📍 ¿Dónde van tus datos?

### Datos Persistentes (EFS):
- `/app/persistent/logs/` → Logs
- `/app/persistent/exports/` → Visualizaciones HTML
- `/app/persistent/layouts/` → Layouts guardados

### Datos en Memoria (se pierden al reiniciar):
- Grafos NetworkX → RAM del contenedor
- Uploads temporales

### ¿Puedes añadir más datos?
✅ **SÍ**, de 3 formas:
1. **Via Gradio UI** - subir CSVs desde navegador
2. **Via EFS** - montar desde EC2 y copiar archivos
3. **Via S3** - modificar código para leer de S3 (recomendado para datasets grandes)

---

## 🎯 Próximos Pasos

1. **Ahora**: Lee `COMANDOS_WINDOWS.md`
2. **Luego**: Ejecuta los 6 pasos de arriba
3. **Después**: Abre la URL de tu aplicación
4. **Opcional**: Importa `arquitectura-aws.excalidraw.json` en https://excalidraw.com

---

## 💡 Ayuda Rápida

**Si algo falla:**
- Revisa `COMANDOS_WINDOWS.md` sección Troubleshooting
- Los logs de errores están en la salida del script
- Todos los comandos de AWS CLI funcionan igual en Windows

**Costos estimados:**
- Config base: ~$454/mes
- Con optimizaciones: ~$213-256/mes
- Ver detalles en `HERRAMIENTAS_AWS.md`

**Tiempo total deployment:**
- ~15-20 minutos desde cero
- ~5 minutos para actualizaciones

---

✅ **Todo listo para Windows!**
