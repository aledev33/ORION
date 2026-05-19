from datetime import datetime
from pydantic import BaseModel


class AliasRead(BaseModel):
    id: int
    alias: str

    class Config:
        from_attributes = True


class CommandCreate(BaseModel):
    raw_text: str
    cleaned_text: str | None = None
    intent: str | None = None
    payload: str | None = None
    confidence: float | None = None
    status: str = "success"
    response_message: str | None = None
    device_id: int | None = None


class CommandRead(CommandCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AppCreate(BaseModel):
    name: str
    exec_path: str
    enabled: bool = True


class AppRead(AppCreate):
    id: int

    class Config:
        from_attributes = True


class AppWithAliasesRead(AppRead):
    aliases: list[AliasRead] = []

    class Config:
        from_attributes = True


class AliasCreate(BaseModel):
    alias: str


class PreferenceCreate(BaseModel):
    pref_value: str