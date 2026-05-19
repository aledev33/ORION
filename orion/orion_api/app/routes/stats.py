from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db import get_db
from ..models import CommandHistory, ErrorLog, App

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def get_stats(db: Session = Depends(get_db)):
    total_commands = db.query(func.count(CommandHistory.id)).scalar() or 0
    total_errors = db.query(func.count(ErrorLog.id)).scalar() or 0
    total_apps = db.query(func.count(App.id)).scalar() or 0

    return {
        "total_commands": total_commands,
        "total_errors": total_errors,
        "total_apps": total_apps,
    }