from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...core.database import get_db
from ...models.entities import Project, Architecture, Dataset, TrainingJob, TrainingMetric, AuditEvent, ModelVersion
from ...schemas.dto import ProjectCreate, ProjectOut, ArchitectureCreate, DatasetCreate, TrainingCreate

router = APIRouter()

@router.get('/health')
def health(): return {'status':'ok','service':'neurolab-api','api_version':'v1'}

@router.get('/projects', response_model=list[ProjectOut])
def list_projects(db: Session=Depends(get_db)):
    return db.query(Project).order_by(Project.id.desc()).all()

@router.post('/projects', response_model=ProjectOut, status_code=201)
def create_project(data: ProjectCreate, db: Session=Depends(get_db)):
    item=Project(**data.model_dump()); db.add(item); db.flush()
    # Crear también una arquitectura inicial para que el proyecto no quede vacío.
    default_layers = [
        {'id': 1, 'type': 'Entrada', 'units': 784, 'activation': '—'},
        {'id': 2, 'type': 'Densa', 'units': 128, 'activation': 'ReLU'},
        {'id': 3, 'type': 'Densa', 'units': 64, 'activation': 'ReLU'},
        {'id': 4, 'type': 'Salida', 'units': 10, 'activation': 'Softmax'},
    ]
    db.add(Architecture(project_id=item.id, name=f'Arquitectura inicial · {item.name}', family=item.family, config_json={'layers': default_layers}, version=1))
    db.add(AuditEvent(project_id=item.id, action='project.created', metadata_json={'name':item.name}))
    db.commit(); db.refresh(item); return item

@router.get('/projects/{project_id}', response_model=ProjectOut)
def get_project(project_id: int, db: Session=Depends(get_db)):
    item=db.get(Project, project_id)
    if not item: raise HTTPException(404,'Proyecto no encontrado')
    return item

@router.post('/projects/{project_id}/architectures', status_code=201)
def create_architecture(project_id: int, data: ArchitectureCreate, db: Session=Depends(get_db)):
    if not db.get(Project,project_id): raise HTTPException(404,'Proyecto no encontrado')
    cfg=data.config_json; layers=cfg.get('layers',[])
    allowed_families = ('Feedforward', 'FFN', 'Convolucional (CNN)', 'CNN', 'Recurrente (RNN)', 'RNN', 'Generativa (GAN)', 'GAN')
    if data.family not in allowed_families:
        raise HTTPException(422, 'Familia de red no reconocida.')
    if len(layers)<2: raise HTTPException(422,'La arquitectura debe contener al menos entrada y salida')
    for layer in layers:
        if int(layer.get('units',0))<1: raise HTTPException(422,'Todas las capas deben tener unidades positivas')
        activation=str(layer.get('activation','ReLU')).lower()
        if activation not in ('relu','softmax','sigmoid','tanh','linear','elu','selu','—','none',''):
            raise HTTPException(422,f'Función de activación no admitida: {activation}')
    latest_version = db.query(Architecture).filter_by(project_id=project_id).count() + 1
    item=Architecture(project_id=project_id, name=data.name, family=data.family, config_json=data.config_json, version=latest_version); db.add(item); db.commit(); db.refresh(item)
    db.add(AuditEvent(project_id=project_id, action='architecture.created', metadata_json={'architecture_id':item.id, 'version':item.version})); db.commit()
    return {'id':item.id,'project_id':project_id,'name':item.name,'family':item.family,'config_json':item.config_json,'version':item.version}

@router.get('/projects/{project_id}/architectures')
def list_architectures(project_id:int, db:Session=Depends(get_db)):
    if not db.get(Project, project_id): raise HTTPException(404, 'Proyecto no encontrado')
    return db.query(Architecture).filter_by(project_id=project_id).order_by(Architecture.id.desc()).all()

@router.get('/datasets')
def list_datasets(db:Session=Depends(get_db)):
    return db.query(Dataset).order_by(Dataset.id.desc()).all()

@router.post('/datasets',status_code=201)
def create_dataset(data:DatasetCreate,db:Session=Depends(get_db)):
    item=Dataset(**data.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

@router.post('/datasets/{dataset_id}/validate')
def validate_dataset(dataset_id:int,db:Session=Depends(get_db)):
    item=db.get(Dataset,dataset_id)
    if not item: raise HTTPException(404,'Dataset no encontrado')
    # Validación de metadatos; no certifica que exista un archivo de entrenamiento.
    item.status='Validado'; db.commit(); return {'id':item.id,'status':item.status,'note':'Metadatos validados. Verifica la disponibilidad del archivo antes de entrenar.'}

@router.post('/projects/{project_id}/training-jobs',status_code=202)
def create_training(project_id:int,data:TrainingCreate,db:Session=Depends(get_db)):
    project=db.get(Project,project_id); arch=db.get(Architecture,data.architecture_id); dataset=db.get(Dataset,data.dataset_id)
    if not project: raise HTTPException(404,'Proyecto no encontrado')
    if not arch or arch.project_id!=project_id: raise HTTPException(422,'Arquitectura no válida para este proyecto')
    if not dataset or dataset.status!='Validado': raise HTTPException(422,'Se requiere un dataset validado')
    if arch.family not in ('Feedforward', 'FFN'):
        raise HTTPException(422, 'En esta versión solo está habilitado el entrenamiento Feedforward con MNIST. La arquitectura puede guardarse, pero CNN, RNN y GAN aún no tienen worker de entrenamiento.')
    job=TrainingJob(project_id=project_id,architecture_id=arch.id,dataset_id=dataset.id,epochs=data.epochs,batch_size=data.batch_size,optimizer=data.optimizer)
    db.add(job); db.flush(); db.add(AuditEvent(project_id=project_id,action='training.queued',metadata_json={'job_id':job.id})); db.commit(); db.refresh(job)
    return {'id':job.id,'project_id':project_id,'status':job.status,'progress':job.progress,'epochs':job.epochs,'message':'Trabajo agregado a la cola. Inicia el worker para procesarlo.'}

@router.get('/training-jobs/{job_id}')
def get_job(job_id:int,db:Session=Depends(get_db)):
    j=db.get(TrainingJob,job_id)
    if not j: raise HTTPException(404,'Entrenamiento no encontrado')
    return {'id':j.id,'project_id':j.project_id,'status':j.status,'progress':j.progress,'epoch':len({m.epoch for m in j.metrics}),'epochs':j.epochs,'accuracy':j.accuracy,'loss':j.loss,'error':j.error,'metrics':[{'epoch':m.epoch,'name':m.metric_name,'value':m.metric_value} for m in j.metrics]}

@router.post('/training-jobs/{job_id}/cancel')
def cancel_job(job_id:int,db:Session=Depends(get_db)):
    j=db.get(TrainingJob,job_id)
    if not j: raise HTTPException(404,'Entrenamiento no encontrado')
    if j.status not in ('QUEUED','PREPARING','RUNNING'): raise HTTPException(409,'El trabajo ya finalizó')
    j.status='CANCELLED'; j.ended_at=datetime.now(timezone.utc); db.commit()
    return {'id':j.id,'status':j.status,'message':'Cancelación registrada'}

@router.get('/projects/{project_id}/models')
def list_models(project_id:int,db:Session=Depends(get_db)):
    return db.query(ModelVersion).filter_by(project_id=project_id).order_by(ModelVersion.version.desc()).all()

@router.get('/projects/{project_id}/audit-events')
def audit(project_id:int,db:Session=Depends(get_db)):
    return db.query(AuditEvent).filter_by(project_id=project_id).order_by(AuditEvent.created_at.desc()).all()

@router.get('/training-jobs')
def list_jobs(db:Session=Depends(get_db)):
    rows=db.query(TrainingJob).order_by(TrainingJob.id.desc()).limit(100).all()
    return [{'id':j.id,'project_id':j.project_id,'project':j.project.name,'family':j.project.family,'status':j.status,'progress':j.progress,'epoch':len({m.epoch for m in j.metrics}),'epochs':j.epochs,'accuracy':j.accuracy,'loss':j.loss,'duration':'—'} for j in rows]

from fastapi.responses import StreamingResponse
from ...core.database import SessionLocal
import asyncio, json

@router.get('/training-jobs/{job_id}/events')
async def job_events(job_id:int):
    async def stream():
        last=None
        for _ in range(300):
            with SessionLocal() as db:
                j=db.get(TrainingJob,job_id)
                if not j:
                    yield 'event: error\ndata: {"detail":"Entrenamiento no encontrado"}\n\n'; return
                payload={'id':j.id,'status':j.status,'progress':j.progress,'accuracy':j.accuracy,'loss':j.loss}
                encoded=json.dumps(payload)
                if encoded!=last:
                    yield f'event: progress\ndata: {encoded}\n\n'; last=encoded
                if j.status in ('COMPLETED','FAILED','CANCELLED'): return
            await asyncio.sleep(1)
    return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})
