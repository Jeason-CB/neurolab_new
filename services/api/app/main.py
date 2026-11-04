from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .core.database import Base, engine
from .models import entities  # noqa: F401
from .api.v1.routes import router

Base.metadata.create_all(bind=engine)
app=FastAPI(title='NeuroLab Enterprise API',version='1.0.0',description='API REST para proyectos, arquitecturas y entrenamiento de redes neuronales.')
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(',') if x.strip()],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
app.include_router(router,prefix='/api/v1')

# Registros iniciales solo para desarrollo local; se pueden borrar desde la BD.
from sqlalchemy.orm import Session
from .models.entities import Project, Dataset
with Session(engine) as db:
    if db.query(Project).count() == 0:
        db.add_all([
            Project(name='Clasificación de imágenes',description='Clasificación multiclase de imágenes.',family='CNN'),
            Project(name='Predicción de demanda',description='Pronóstico de series temporales.',family='RNN'),
            Project(name='Detección de anomalías',description='Identificación de patrones atípicos.',family='Feedforward'),
            Project(name='Generación de muestras',description='Experimentación generativa.',family='GAN')])
    if db.query(Dataset).count() == 0:
        db.add(Dataset(name='MNIST · Imágenes',format='Imágenes',description='Dataset MNIST integrado en Keras; se descarga al entrenar.',status='Validado',metadata_json={'source':'tensorflow.keras.datasets.mnist','builtin':True,'rows':70000}))
    db.commit()
@app.get('/')
def root(): return {'name':'NeuroLab Enterprise API','docs':'/docs','health':'/api/v1/health'}
