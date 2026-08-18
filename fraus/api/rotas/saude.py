"""GET /saude -- a rota que responde antes de qualquer dependencia."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/saude")
def saude() -> dict:
    return {"status": "ok"}
