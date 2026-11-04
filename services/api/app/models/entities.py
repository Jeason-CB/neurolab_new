from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..core.database import Base

def now(): return datetime.now(timezone.utc)

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    family: Mapped[str] = mapped_column(String(40), default="Feedforward")
    status: Mapped[str] = mapped_column(String(30), default="Activo")
    owner: Mapped[str] = mapped_column(String(120), default="Usuario local")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    architectures = relationship("Architecture", back_populates="project", cascade="all, delete-orphan")
    jobs = relationship("TrainingJob", back_populates="project", cascade="all, delete-orphan")

class Architecture(Base):
    __tablename__ = "architectures"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(160))
    family: Mapped[str] = mapped_column(String(40))
    config_json: Mapped[dict] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    project = relationship("Project", back_populates="architectures")

class Dataset(Base):
    __tablename__ = "datasets"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    format: Mapped[str] = mapped_column(String(30), default="CSV")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="Borrador")
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class TrainingJob(Base):
    __tablename__ = "training_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    architecture_id: Mapped[int] = mapped_column(ForeignKey("architectures.id"))
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    status: Mapped[str] = mapped_column(String(20), default="QUEUED")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    epochs: Mapped[int] = mapped_column(Integer, default=5)
    batch_size: Mapped[int] = mapped_column(Integer, default=32)
    optimizer: Mapped[str] = mapped_column(String(30), default="adam")
    accuracy: Mapped[float] = mapped_column(Float, default=0)
    loss: Mapped[float] = mapped_column(Float, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    project = relationship("Project", back_populates="jobs")
    metrics = relationship("TrainingMetric", back_populates="job", cascade="all, delete-orphan")

class TrainingMetric(Base):
    __tablename__ = "training_metrics"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("training_jobs.id", ondelete="CASCADE"))
    epoch: Mapped[int] = mapped_column(Integer)
    metric_name: Mapped[str] = mapped_column(String(40))
    metric_value: Mapped[float] = mapped_column(Float)
    job = relationship("TrainingJob", back_populates="metrics")

class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    job_id: Mapped[int] = mapped_column(ForeignKey("training_jobs.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="Borrador")
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(120), default="local-user")
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
