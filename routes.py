from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile,Query, Form
from sqlalchemy.orm import Session
from typing import List,Annotated
import service, models, schemas
from fastapi import Query
from database import SessionLocal, engine
from middleware.application_middleware import default_dependency
models.Base.metadata.create_all(bind=engine)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get('/')
async def get_(request: Request, db: Session = Depends(get_db), protected_deps_1: dict = Depends(default_dependency)):
    try:
        return await service.get_(request, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

