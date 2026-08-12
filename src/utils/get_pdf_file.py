from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from src.schemas.reports_schemas import ReportGenerateSchema


def generate_report_pdf(report: ReportGenerateSchema) -> BytesIO:
    buffer = BytesIO()
    # 2. Документ и стили
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=40, leftMargin=40,
        topMargin=60, bottomMargin=40
    )
    styles = getSampleStyleSheet()
    styles['Title'].fontName = 'TimesNewRoman'
    styles['Normal'].fontName = 'TimesNewRoman'
    cell = ParagraphStyle('CellStyle', fontName='TimesNewRoman', fontSize=10, leading=12, wordWrap='LTR')

    # 3. Заголовок + таблица с данными
    elems = [Paragraph("Отчет по выявлению аномалий средствами SOC", styles['Title']), Spacer(1, 12)]

    host_or_cve = ''
    if report.host:
        host_or_cve = [Paragraph("Host", cell), Paragraph(report.host, cell)]
    if report.cve:
        host_or_cve = [Paragraph("CVE", cell), Paragraph(report.cve, cell)]
    data = [
        [Paragraph("Поле", cell), Paragraph("Значение", cell)],
        [Paragraph("Дата и время", cell), Paragraph(report.detection_date.strftime("%Y-%m-%d"), cell)],
        [Paragraph("Тип угрозы", cell), Paragraph(report.attack_type, cell)],
        [Paragraph("Источник угрозы", cell), Paragraph(report.source_ip, cell)],
        [Paragraph("Адрес назначения", cell), Paragraph(report.destination_ip, cell)],
        host_or_cve,
        [Paragraph("Средство обнаружения", cell), Paragraph(report.detection_tool, cell)],
        [Paragraph("Краткое описание", cell), Paragraph(report.short_description, cell)],
        [Paragraph("Методы атаки", cell), Paragraph(report.methods, cell)],
        [Paragraph("Протоколы и порты", cell), Paragraph(report.protocols_ports, cell)],
        [Paragraph("Критичность", cell), Paragraph(report.risk_assessment, cell)],
        [Paragraph("Потенциальные последствия", cell), Paragraph(report.potential_impact, cell)],
        [Paragraph(["Payload", "Data"][bool(report.host)], cell), Paragraph(report.data_or_payload, cell)],
        [Paragraph("Реагирование на инцидент", cell),
         Paragraph(report.response_actions.replace('\n', '<br/>'), cell)],
    ]

    # 5. Стилизация таблицы
    table = Table(data, colWidths=[150, 330])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elems.append(table)

    # 6. Сборка PDF
    doc.build(elems)
    buffer.seek(0)

    return buffer