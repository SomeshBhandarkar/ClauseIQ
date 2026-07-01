from fastapi import APIRouter
from services.database import list_contracts

router = APIRouter()


@router.get("/contracts")
def get_contracts():
    """GET /api/contracts — list all past analyses for the current user."""
    return list_contracts(None)
