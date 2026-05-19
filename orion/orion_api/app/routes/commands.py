from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..db import get_db
from ..models import CommandHistory
from ..schemas import CommandCreate, CommandRead

router = APIRouter(prefix="/commands", tags=["commands"])


@router.post("", response_model=CommandRead)
def create_command(payload: CommandCreate, db: Session = Depends(get_db)):
    command = CommandHistory(**payload.model_dump())
    db.add(command)
    db.commit()
    db.refresh(command)
    return command


@router.get("/recent", response_model=list[CommandRead])
def get_recent_commands(limit: int = 10, db: Session = Depends(get_db)):
    stmt = select(CommandHistory).order_by(CommandHistory.created_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())