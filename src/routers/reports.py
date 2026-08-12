from fastapi import APIRouter, Body, Request
from src.schemas.reports_schemas import ReportGenerateSchema
from src.schemas.organizations_schema import OrganizationCreateSchema
from src.service.reports_service import ReportsService
from src.routers.dependencies import DBDep, RMQDep, AuthUserDep


router = APIRouter(prefix="/reports", tags=["Отчеты"])


@router.get("/get-organizations/")
async def get_organizations(request: Request, db: DBDep):
    organs = await db.organizations.get_origins()
    return organs


@router.post("/post-organizations/")
async def get_organizations(request: Request, db: DBDep, body: OrganizationCreateSchema):
    organ = await db.organizations.post_origin(body)
    await db.save()
    return organ


@router.post("/get-ai-answer/")
async def get_answer_for_log(request: Request, db: DBDep, rmq: RMQDep, body: str = Body(embed=True)):
    answer = await ReportsService(db, rabbit_mq=rmq).get_answer_from_ai(body)
    return {"result": answer}


@router.post("/create-report/")
async def create_report(request: Request,
                        db: DBDep,
                        rmq: RMQDep,
                        user_id: AuthUserDep,
                        body: ReportGenerateSchema):
    result = await ReportsService(db, rabbit_mq=rmq).create_report(body, user_id)
    return result

@router.get("/get-reports/")
async def get_reports(request: Request, db: DBDep, rmq: RMQDep):
    answer = await ReportsService(db, rabbit_mq=rmq).get_reports()
    return answer