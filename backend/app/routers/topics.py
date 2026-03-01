from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Topic
from app.schemas import TopicCreate, TopicOut

router = APIRouter(prefix="/topics", tags=["Topics"])


@router.post("/", response_model=TopicOut, status_code=201)
def create_topic(payload: TopicCreate, db: Session = Depends(get_db)):
    if db.query(Topic).filter(Topic.name == payload.name).first():
        raise HTTPException(status_code=409, detail="Topic name already exists")
    topic = Topic(name=payload.name, description=payload.description)
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


@router.get("/", response_model=list[TopicOut])
def list_topics(db: Session = Depends(get_db)):
    return db.query(Topic).all()


@router.get("/{topic_id}", response_model=TopicOut)
def get_topic(topic_id: int, db: Session = Depends(get_db)):
    t = db.query(Topic).filter(Topic.id == topic_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Topic not found")
    return t
