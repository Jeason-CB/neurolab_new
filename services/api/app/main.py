from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .core.config import settings
from .core.database import Base, engine
from .models import entities  # noqa: F401
from .models.entities import Project, Dataset, Architecture
from .api.v1.routes import router

# Crea las tablas que todavía no existan. No elimina ni reemplaza datos.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NeuroLab Enterprise API",
    version="1.1.0",
    description="API REST para proyectos, arquitecturas y entrenamiento de redes neuronales.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


def default_layers(family: str) -> list[dict]:
    """Arquitectura inicial editable; no implica que todas las familias estén entrenables."""
    f = family.lower()
    if "cnn" in f or "convol" in f:
        return [
            {"id": 1, "type": "Entrada", "units": 784, "activation": "—"},
            {"id": 2, "type": "Convolucional", "units": 32, "activation": "ReLU"},
            {"id": 3, "type": "Pooling", "units": 2, "activation": "—"},
            {"id": 4, "type": "Salida", "units": 10, "activation": "Softmax"},
        ]
    if "rnn" in f or "recurrent" in f:
        return [
            {"id": 1, "type": "Entrada", "units": 128, "activation": "—"},
            {"id": 2, "type": "Recurrente", "units": 64, "activation": "Tanh"},
            {"id": 3, "type": "Salida", "units": 10, "activation": "Softmax"},
        ]
    if "gan" in f or "generativa" in f:
        return [
            {"id": 1, "type": "Entrada", "units": 100, "activation": "—"},
            {"id": 2, "type": "Densa", "units": 128, "activation": "ReLU"},
            {"id": 3, "type": "Salida", "units": 784, "activation": "Tanh"},
        ]
    return [
        {"id": 1, "type": "Entrada", "units": 784, "activation": "—"},
        {"id": 2, "type": "Densa", "units": 128, "activation": "ReLU"},
        {"id": 3, "type": "Densa", "units": 64, "activation": "ReLU"},
        {"id": 4, "type": "Salida", "units": 10, "activation": "Softmax"},
    ]


@app.on_event("startup")
def populate_database():
    """Carga datos de demostración sin duplicarlos y sin borrar datos existentes."""
    projects = [
        ("Reconocimiento de Dígitos MNIST", "Entrenamiento de una red neuronal para clasificar dígitos escritos a mano (0-9).", "Feedforward"),
        ("Análisis de Fraude Bancario", "Proyecto de clasificación de transacciones potencialmente fraudulentas.", "Feedforward"),
        ("Predicción de Demanda TRN-120", "Pronóstico de series temporales para optimizar inventarios.", "RNN"),
        ("Segmentación de Imágenes Médicas", "Proyecto de segmentación y clasificación de imágenes médicas.", "CNN"),
        ("Generación de Imágenes Artificiales", "Experimentación con redes generativas adversariales.", "GAN"),
        ("Clasificador de Sentimientos", "Análisis de sentimientos en textos y reseñas.", "RNN"),
        ("Detección de Objetos", "Reconocimiento de objetos en imágenes.", "CNN"),
        ("Filtro de Ruido Acústico", "Proyecto de reducción de ruido en señales de audio.", "Feedforward"),
    ]
    datasets = [
        ("MNIST · Dígitos Escritos", "Imágenes", "Dataset integrado de 70,000 imágenes en escala de grises de 28x28. Se descarga desde TensorFlow/Keras al entrenar.", "Validado", {"source": "tensorflow.keras.datasets.mnist", "builtin": True, "rows": 70000, "classes": 10, "image_size": "28x28"}),
        ("Credit Card Fraud · Metadatos", "CSV", "Registro de demostración. Debe cargarse el archivo real antes de entrenar.", "Pendiente", {"source": "external_upload_required", "builtin": False, "rows": 284807}),
        ("Stock Demand · Metadatos", "CSV", "Registro de demostración para series temporales. Requiere archivo real.", "Pendiente", {"source": "external_upload_required", "builtin": False, "rows": 45000}),
        ("Imágenes de Productos · Metadatos", "Imágenes", "Registro de demostración para clasificación visual. Requiere cargar imágenes.", "Pendiente", {"source": "external_upload_required", "builtin": False}),
    ]

    try:
        with Session(engine) as db:
            for name, description, family in projects:
                project = db.query(Project).filter(Project.name == name).first()
                if project is None:
                    project = Project(name=name, description=description, family=family, status="Activo")
                    db.add(project)
                    db.flush()

                # Cada proyecto recibe una arquitectura inicial solo si aún no tiene una.
                existing_arch = db.query(Architecture).filter(Architecture.project_id == project.id).first()
                if existing_arch is None:
                    db.add(Architecture(
                        project_id=project.id,
                        name=f"Arquitectura inicial · {project.name}",
                        family=family,
                        config_json={"layers": default_layers(family)},
                        version=1,
                    ))

            for name, fmt, description, status, metadata in datasets:
                dataset = db.query(Dataset).filter(Dataset.name == name).first()
                if dataset is None:
                    db.add(Dataset(
                        name=name,
                        format=fmt,
                        description=description,
                        status=status,
                        metadata_json=metadata,
                    ))

            db.commit()
            print("NeuroLab seed: proyectos, arquitecturas y datasets verificados correctamente.")
    except Exception as exc:
        # Se deja el detalle en los logs de Render para diagnosticar DATABASE_URL/permisos.
        print(f"ERROR al inicializar datos de NeuroLab: {type(exc).__name__}: {exc}")
        raise


@app.get("/")
def root():
    return {
        "name": "NeuroLab Enterprise API",
        "docs": "/docs",
        "health": "/api/v1/health",
        "seed": "startup idempotente",
    }
