from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .core.config import settings
from .core.database import Base, engine
from .models import entities  # noqa: F401
from .models.entities import Project, Dataset
from .api.v1.routes import router

# Genera de forma automática las tablas en PostgreSQL si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title='NeuroLab Enterprise API',
    version='1.0.0',
    description='API REST para proyectos, arquitecturas y entrenamiento de redes neuronales.'
)

# Configuración del Middleware de CORS para conectar con Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(',') if x.strip()],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

app.include_router(router, prefix='/api/v1')

# Evento de inicialización optimizado para poblar la Base de Datos en Render de forma segura
@app.on_event("startup")
def populate_database():
    try:
        with Session(engine) as db:
            # 1. Población de Proyectos avanzados si la tabla está vacía
            if db.query(Project).count() == 0:
                db.add_all([
                    Project(name='Reconocimiento de Dígitos MNIST', description='Entrenamiento de una red Feedforward con el set clásico de números escritos a mano (0-9).', family='Feedforward'),
                    Project(name='Análisis de Fraude Bancario', description='Modelo inteligente encargado de auditar transacciones financieras en tiempo real.', family='Feedforward'),
                    Project(name='Predicción de Demanda TRN-120', description='Pronóstico avanzado de series temporales para optimización automática de stock e inventarios.', family='RNN'),
                    Project(name='Segmentación de Tumores Médicos', description='Clasificación multiclase píxel a píxel para la identificación de tejidos en tomografías.', family='CNN'),
                    Project(name='Generación de Rostros Artificiales', description='Experimentación generativa mediante redes GAN para el aumento de volumen en datasets de diseño.', family='GAN'),
                    Project(name='Clasificador de Sentimientos en Texto', description='Procesamiento de lenguaje natural mediante redes recurrentes para análisis de reseñas de usuarios.', family='RNN'),
                    Project(name='Detección de Objetos Autónomos', description='Red convolucional optimizada para el rastreo de vehículos y peatones en tiempo real.', family='CNN'),
                    Project(name='Filtro de Ruido Acústico Industrial', description='Autoencoder diseñado para la limpieza y restauración de señales de audio distorsionadas en fábricas.', family='Feedforward')
                ])
                print("✅ 8 Proyectos de Inteligencia Artificial agregados exitosamente a la base de datos.")
            
            # 2. Población de Datasets avanzados si la tabla está vacía
            if db.query(Dataset).count() == 0:
                db.add_all([
                    Dataset(name='MNIST · Dígitos Escritos', format='Imágenes', description='Set clásico integrado de 70,000 imágenes en escala de grises de 28x28 píxeles.', status='Validado', metadata_json={'source':'tensorflow.keras.datasets.mnist','builtin':True,'rows':70000}),
                    Dataset(name='CreditCard · Fraude 2024', format='CSV / Valores', description='Dataset anonimizado con registros estructurados de transacciones comerciales etiquetadas.', status='Validado', metadata_json={'source':'kaggle.creditcard','builtin':False,'rows':284807}),
                    Dataset(name='StockDemand · TimeSeries', format='JSON / Temporal', description='Muestras históricas de solicitudes de inventario estructuradas por intervalos horarios.', status='Pendiente', metadata_json={'source':'internal.warehouse.log','builtin':False,'rows':45000})
                ])
                print("✅ 3 Datasets estructurales agregados exitosamente a la base de datos.")
            
            db.commit()
    except Exception as e:
        print(f"⚠️ Alerta durante la inicialización de datos (Seeding): {e}")

@app.get('/')
def root(): 
    return {
        'name': 'NeuroLab Enterprise API',
        'docs': '/docs',
        'health': '/api/v1/health'
    }
