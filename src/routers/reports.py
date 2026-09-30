from fastapi import APIRouter, Body, Request

from src.routers.dependencies import DBDep, RMQDep
from src.schemas.organizations_schema import OrganizationCreateSchema
from src.schemas.reports_schemas import ReportGenerateSchema
from src.service.reports_service import ReportsService

router = APIRouter(prefix="/reports", tags=["Отчеты"])


@router.get("/get-organizations/")
def get_organizations(request: Request, db: DBDep):
    organ = db.organizations.get_origins()
    return organ


@router.post("/post-organizations/")
def post_organization(request: Request, db: DBDep, body: OrganizationCreateSchema):
    organ = db.organizations.post_origin(body)
    db.save()
    return organ


@router.post("/get-ai-answer/")
def get_answer_for_log(
    request: Request,
    db: DBDep,
    rmq: RMQDep,
    body: str = Body(embed=True),
):
    answer = ReportsService(db, rabbit_mq=rmq).get_answer_from_ai(body)
    return {"result": answer}


@router.post("/create-report/")
def create_report(
    request: Request,
    db: DBDep,
    rmq: RMQDep,
    body: ReportGenerateSchema,
):
    result = ReportsService(db, rabbit_mq=rmq).create_report(body)
    return result


@router.get("/get-reports/")
def get_reports(request: Request, db: DBDep, rmq: RMQDep):
    answer = ReportsService(db, rabbit_mq=rmq).get_reports()
    return answer