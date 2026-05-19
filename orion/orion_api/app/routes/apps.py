from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from ..db import get_db
from ..models import App, AppAlias
from ..schemas import AppCreate, AppRead, AliasCreate, AppWithAliasesRead

router = APIRouter(prefix="/apps", tags=["apps"])


@router.post("", response_model=AppRead)
def create_app(payload: AppCreate, db: Session = Depends(get_db)):
    exists = db.scalar(select(App).where(App.name == payload.name))
    if exists:
        raise HTTPException(status_code=400, detail="La app ya existe")

    app = App(**payload.model_dump())
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@router.get("", response_model=list[AppWithAliasesRead])
def list_apps(db: Session = Depends(get_db)):
    stmt = select(App).options(selectinload(App.aliases)).order_by(App.name)
    return list(db.scalars(stmt).all())


@router.post("/{app_id}/aliases")
def add_alias(app_id: int, payload: AliasCreate, db: Session = Depends(get_db)):
    app = db.get(App, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App no encontrada")

    alias = AppAlias(app_id=app_id, alias=payload.alias)
    db.add(alias)
    db.commit()
    db.refresh(alias)
    return {"message": "Alias agregado", "alias_id": alias.id}