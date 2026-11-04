# NeuroLab Enterprise

Plataforma modular basada en el Documento Maestro Semana 11. Incluye frontend React/TypeScript, API Python/FastAPI, persistencia SQLAlchemy compatible con PostgreSQL y worker separado para entrenamiento TensorFlow/Keras.

## Estructura

- `src/`: frontend React + Vite + TypeScript (se conserva el diseño y los diez módulos originales).
- `src/lib/api.ts`: cliente REST; `VITE_API_URL` define el servidor.
- `services/api/`: API versionada `/api/v1`, modelos, esquemas, persistencia y auditoría básica.
- `workers/training/`: worker independiente que procesa la cola y guarda el modelo entrenado.
- `docker-compose.yml`: PostgreSQL 16 para desarrollo.

## Requisitos

- Node.js 20+ y npm.
- Python 3.11 recomendado.
- Docker Desktop (opcional, para PostgreSQL).
- TensorFlow instalado en el entorno del worker para entrenamiento real. El worker puede requerir recursos considerables.

## 1. Base de datos

Desde la carpeta raíz:

```bash
docker compose up -d db
```

Copia `.env.example` como `.env` en la raíz del repositorio y configura la conexión. Para Docker Compose:

```env
DATABASE_URL=postgresql+psycopg://neurolab:neurolab_local_only@localhost:5432/neurolab
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
APP_ENV=development
```

Para SQLite local puedes dejar `DATABASE_URL=sqlite:///./neurolab.db`. La API crea las tablas al iniciar y añade registros de demostración si la base está vacía. Para producción reemplazar `create_all` por migraciones versionadas (Alembic).

## 2. API

Desde la raíz del repositorio:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Si PowerShell bloquea scripts, usa: .venv\Scripts\python.exe -m pip install -r services/api/requirements.txt
pip install -r services/api/requirements.txt
uvicorn services.api.app.main:app --reload --host 0.0.0.0 --port 8000
```

Documentación interactiva: `http://localhost:8000/docs`  
Salud: `http://localhost:8000/api/v1/health`

## 3. Worker TensorFlow/Keras

En otra terminal, desde la raíz:

```bash
pip install tensorflow
python workers/training/worker.py
```

El worker consulta la cola cada tres segundos, entrena MNIST usando una red Feedforward, registra métricas por época y guarda el artefacto `.keras` y su checksum en `storage/models/`. El worker es un proceso independiente de la API.

**Alcance real del entrenamiento incluido:** el worker implementa el MVP Feedforward para MNIST. RNN, CNN y GAN aparecen en el catálogo y en la interfaz, pero la API rechaza su entrenamiento hasta implementar y probar workers específicos por familia. No se debe interpretar la información precargada del dashboard como resultados científicos.

## 4. Frontend

Usa el `.env` de la raíz (copia `.env.example` si aún no existe):

```env
VITE_API_URL=http://localhost:8000
```

Luego:

```bash
npm install
npm run dev
```

Abre `http://localhost:5173`. El indicador de la barra superior muestra si la API está conectada. Al estar conectada, el frontend sincroniza proyectos, datasets y entrenamientos; crear proyectos/datasets y enviar trabajos usa la API. Si la API no está disponible, la interfaz mantiene el modo local de demostración con `localStorage`.

Para compilar:

```bash
npm run build
npm run preview
```

## Pruebas del backend

Desde la raíz, con las dependencias instaladas:

```bash
python -m pytest -q services/api/tests
```

## Endpoints implementados

- `GET /api/v1/health`
- `GET/POST /api/v1/projects`
- `GET /api/v1/projects/{id}`
- `GET/POST /api/v1/projects/{id}/architectures`
- `GET/POST /api/v1/datasets`
- `POST /api/v1/datasets/{id}/validate`
- `GET/POST /api/v1/training-jobs`
- `GET /api/v1/training-jobs/{id}`
- `POST /api/v1/training-jobs/{id}/cancel`
- `GET /api/v1/training-jobs/{id}/events` (SSE)
- `GET /api/v1/projects/{id}/models`
- `GET /api/v1/projects/{id}/audit-events`

## Importante: seguridad y producción

Este paquete es una base funcional de desarrollo/MVP, no un despliegue enterprise listo para producción. El backend aún requiere autenticación real, RBAC por usuario/proyecto, aislamiento multiusuario, límites de tasa y recursos, gestión segura de secretos, almacenamiento de objetos, migraciones Alembic, pruebas automatizadas y observabilidad. No expongas la API públicamente ni cargues datos sensibles hasta completar esos controles. El estado `Validado` de un dataset valida metadatos en esta versión; no certifica la calidad ni la licencia del contenido.

## Módulos conservados del frontend

Dashboard, Proyectos de IA, Fundamentos neuronales, Diseñador de arquitecturas, Datasets, Entrenamientos, Evaluación y métricas, Registro de modelos, Reportes y Administración y seguridad. Se mantienen el diseño visual, la navegación y la estructura de la aplicación entregada, corrigiendo el tipado de React y añadiendo la conexión API.
