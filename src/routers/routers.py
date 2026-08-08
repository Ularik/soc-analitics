from fastapi import APIRouter, Body, Request
from src.schemas.reports_schemas import ReportCreateSchema
from src.service.reports_service import ReportsService
from src.routers.dependencies import DBDep


router = APIRouter()


@router.get("/get-organizations/")
async def get_organizations(request: Request, db: DBDep):
    organs = await db.organizations.get_origins()
    return organs


@router.post("/get-ai-answer/")
async def get_answer_for_log(request: Request, body: str = Body(embed=True)):
    answer = await ReportsService().get_answer_from_ai(body)
    return {"result": answer}


@router.post("/create-report/")
async def create_report(request, Request,
                        db: DBDep,
                        body: ReportCreateSchema):
    pass
