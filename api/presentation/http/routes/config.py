from typing import Annotated

from fastapi import APIRouter, Depends

from api.contract_models import Config
from api.presentation.http.dependencies import get_demo_login

router = APIRouter()


@router.get("/config", response_model=Config)
def read_config(demo_login: Annotated[bool, Depends(get_demo_login)]) -> Config:
    return Config(demo_login=demo_login)
