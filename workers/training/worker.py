"""Worker separado. MVP didáctico: entrena MNIST con TensorFlow/Keras.
No ejecuta archivos ni código proporcionado por usuarios.
"""
import os, time, hashlib
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from services.api.app.core.config import settings
from services.api.app.models.entities import TrainingJob, TrainingMetric, ModelVersion
from services.api.app.models.entities import Architecture
from services.api.app.core.database import Base

URL=settings.database_url
args={'check_same_thread':False} if URL.startswith('sqlite') else {}
engine=create_engine(URL,pool_pre_ping=True,connect_args=args)
Session=sessionmaker(bind=engine)
Base.metadata.create_all(engine)

def process(job_id):
    db=Session()
    try:
        job=db.get(TrainingJob,job_id)
        if not job or job.status!='QUEUED': return
        job.status='PREPARING'; job.started_at=datetime.now(timezone.utc); db.commit()
        import tensorflow as tf
        import numpy as np
        (x_train,y_train),(x_test,y_test)=tf.keras.datasets.mnist.load_data()
        x_train=x_train.astype('float32').reshape(-1,784)/255.0
        x_test=x_test.astype('float32').reshape(-1,784)/255.0
        arch=db.get(Architecture,job.architecture_id)
        layer_specs=arch.config_json.get('layers',[])
        hidden=layer_specs[1:-1] or [{'units':128,'activation':'ReLU'},{'units':64,'activation':'ReLU'}]
        output_spec=layer_specs[-1] if layer_specs else {'units':10,'activation':'Softmax'}
        if int(output_spec.get('units',10)) != 10:
            raise ValueError('El worker MNIST requiere 10 unidades de salida.')
        keras_layers=[tf.keras.layers.Input((784,))]
        for spec in hidden:
            activation=str(spec.get('activation','ReLU')).lower()
            if activation in ('—','none',''): activation='relu'
            keras_layers.append(tf.keras.layers.Dense(int(spec.get('units',64)),activation=activation))
        keras_layers.append(tf.keras.layers.Dense(10,activation=str(output_spec.get('activation','Softmax')).lower()))
        model=tf.keras.Sequential(keras_layers)
        model.compile(optimizer=job.optimizer,loss='sparse_categorical_crossentropy',metrics=['accuracy'])
        job.status='RUNNING'; db.commit()
        for epoch in range(1,job.epochs+1):
            if db.get(TrainingJob,job_id).status=='CANCELLED': return
            h=model.fit(x_train,y_train,epochs=1,batch_size=job.batch_size,validation_split=.1,verbose=0)
            loss,acc=model.evaluate(x_test,y_test,verbose=0)
            job.progress=round(epoch/job.epochs*100); job.accuracy=float(acc); job.loss=float(loss)
            db.add_all([TrainingMetric(job_id=job_id,epoch=epoch,metric_name='accuracy',metric_value=float(acc)),TrainingMetric(job_id=job_id,epoch=epoch,metric_name='loss',metric_value=float(loss))]); db.commit()
        os.makedirs('storage/models',exist_ok=True)
        model_path=f'storage/models/job-{job.id}.keras'
        model.save(model_path)
        digest=hashlib.sha256(open(model_path,'rb').read()).hexdigest()
        job.status='COMPLETED'; job.ended_at=datetime.now(timezone.utc)
        db.add(ModelVersion(project_id=job.project_id,job_id=job.id,version=1,status='Borrador',storage_key=model_path,checksum=digest))
        db.commit()
    except Exception as exc:
        db.rollback(); job=db.get(TrainingJob,job_id)
        if job: job.status='FAILED'; job.error=str(exc)[:2000]; job.ended_at=datetime.now(timezone.utc); db.commit()
    finally: db.close()

def main():
    print('NeuroLab worker activo. Esperando trabajos...')
    while True:
        db=Session()
        job=db.query(TrainingJob).filter_by(status='QUEUED').order_by(TrainingJob.created_at).first()
        job_id=job.id if job else None; db.close()
        if job_id: process(job_id)
        else: time.sleep(3)

if __name__=='__main__': main()
