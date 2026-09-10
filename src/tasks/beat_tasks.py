import logging
from celery import shared_task
from src.tasks.telegram_tasks import send_telegram_attack_task
from src.tasks.utils import is_request_new, is_request_danger
from src.spidertm.client_session import siem_client
from src.tasks.llm_tasks import analyze_attack_task
from src.schemas.detection_events_schemas import DetectionNoticeResponse, DetectionEventSchema


logger = logging.getLogger(__name__)


@shared_task(name="src.tasks.beat_tasks.process_siem_events_task")
def process_siem_events_task():
    try:
        detection_schema: DetectionNoticeResponse = siem_client.fetch_events()
    except Exception as e:
        logger.error(f"Не удалось получить данные из SIEM: {e}")
        return

    new_events = is_request_new(detection_schema)

    if not new_events:
        logger.info("Новых событий не найдено.")
        return

    for event_wrapper in new_events:
        status: str = event_wrapper["status"]
        event: DetectionEventSchema = event_wrapper["data"]

        # Используем вспомогательный метод схемы для парсинга json-строки
        event_log = event.parse_line()

        is_danger = is_request_danger(event_log)

        if is_danger:
            src_ip_str = event_log.get("s_ip")
            logger.warning(
                f"[!] ОБНАРУЖЕНА ВНЕШНЯЯ АТАКА [{status}] с IP: {src_ip_str} | "
                f"Правило: {event.rulename.strip()} | "
                f"Узел: {event.d_info} | Попыток: {event.cnt}"
            )

            # Для Celery дампим объект Pydantic в dict для корректной JSON-сериализации
            serializable_wrapper = {
                "status": status,
                "data": event.model_dump(),
            }

            send_telegram_attack_task.delay(
                event_wrapper=serializable_wrapper,
            )
            analyze_attack_task.delay(event_wrapper=serializable_wrapper)

# {
#     "data": {
#         "seeNotice": "true",
#         "noticeList": {
#             "result": [
#                 {
#                     "current_level": 1,
#                     "expired_time": 60,
#                     "rulename": "[S12_IPS_TMS_KG] Apache Struts URLValidator Denial of Service-2\t",
#                     "line_status": "101",
#                     "type": "simple",
#                     "userid": "igloosec",
#                     "notice_sound": 0,
#                     "s_addr": "00000000000000000000ffffc0a80e05",
#                     "samefield_hash": "45701d8c7e2be04adae2e94884e7550a9305b5e1fb9a2c22d8dfbd2e97d295f7c77ee7bc8cc866bb9b50af4c7ccf0150336e328a10ad6a72f18e0f029379318e",
#                     "set_id": 8020400,
#                     "inst_id": "-",
#                     "credibility": 1,
#                     "rulegroup_id": "groupid10",
#                     "origin_name": "FINACE_01.TMS Sensor(IPS)",
#                     "prediction_nm": null,
#                     "method": "Apache Struts URLValidator Denial of Service-2\t",
#                     "ruleset": false,
#                     "s_country": "null",
#                     "d_info": "10.200.22.120",
#                     "techniques_id": null,
#                     "rulegroup": "S12 IPS-TMS Event",
#                     "status": null,
#                     "distance": 5187,
#                     "ruleset_id": null,
#                     "line": "{\"duser_team\":\"null\",\"s_mac\":\"00:50:56:bf:b8:17\",\"logcompress\":\"Lvl1\",\"suser_team\":\"null\",\"RAW\":\"LEEF:2.0|AhnLab|AIPS|1.0|event||stime=20260910T024736.403\\tetime=20260910T024738.571\\tsid=6698\\tdevice_id=b668d8\\tvulnerability_id=4462\\tcve=CVE-2016-4465\\tattackname=Apache Struts URLValidator Denial of Service-2\\thost_name=SCNS_FIN_IPS01\\thost_alias=AhnLab_AIPS_2000B\\tcateid=Predefined Signature\\tscateid=Server Side Application\\tmodule=IPS\\tpriority=HIGH\\tether_type=IPv4\\tsrc_ip=192.168.14.5\\tsrc_country=\\tsrc_mac=00:50:56:bf:b8:17\\tdst_ip=10.200.22.120\\tdst_country=\\tsrc_port=44228\\tdst_port=8382\\tproto=TCP\\tsrc_asset_os=\\tsrc_asset_app=\\tdst_asset_os=\\tdst_asset_app=\\tsuser_id=\\tsuser_name=\\tsuser_team=\\tduser_id=\\tduser_name=\\tduser_team=\\ticmp_type=0\\ticmp_code=0\\tattack_try_cnt=1\\tdetect_pkts=1\\tdetect_bytes=1117\\tblock=ALLOW\\tblock_action=PACKET\\tblock_time=1\\treaction=NONE\\tszone=Internal_Security\\tszone_id=1\\tszone_group=defaultGroup\\tinterface=eth2\\tsegment=SEG/0\\tsessionid=3938801404567088958\\tpktid=3938801406746423267\\tdetour=NONE\\tssl_decrypt=NONE\\tpkt_dir=IE\\tsession_dir=IE\\tlogcompress=Lvl1\\torigin_filename=\\tfile_reference=\\tv_data=0,\\toffset=684\\tpatternsize=45\\tsrc_service=212.241.18.105\\tdst_service=10.200.22.120:8382\\tmax_latency=\\tavg_latency=\\toversig_hits=\\toversig_detects=\\toversig_rate=\\tpayload=1MOyoQIABAAAAAAAAAAAAP//AAABAAAAShqiavD5CABdBAAAXQQAAGQA8SPBxgBQVr+4FwgARQAET2igQABABt4bwKgOBQrIFnisxCC+DVoPi1CtJkOAGAAVOCkAAAEBCAoGukKuedTB3URRc0MzUWtkQ3cwTHZSZ3RDd0lOQyUyRjBMNGcwWUxRdGRDOTBMVFF0ZEdBMFlNZzRvU1dJREkyTURReE56VTFPVGt5TURjd05pRFF2dEdDSURFM0xqQTBMakl3TWpiUXN5QXNJTkMwMEw3UXM5QyUyQjBMTFF2dEdBSU9LRWxqUXpJTkMlMkIwWUlnTWpJdU1EUXVNakF5TnRDeklOQzMwTEFnMEwlMkZSZ05DJTJCMExUUmc5QzYwWUxSaTNOeEFINEFEQVdyQ0VsMEFBTTNPREowQUFneU1qRTRNVEV3TUhRQU90Q2YwWURRdU5DJTJCMExIUmdOQzEwWUxRdGRDOTBMalF0U0RRdjlHQTBMN1F0TkdEMExyUmd0QyUyQjBMSWcwTCUyRlF1TkdDMExEUXZkQzQwWTl3Y0hOeEFINEFEQUFSN1d4emNnQVVhbUYyWVM1dFlYUm9Ma0pwWjBSbFkybHRZV3hVeHhWWCUyQllFb1R3TUFBa2tBQlhOallXeGxUQUFHYVc1MFZtRnNkQUFXVEdwaGRtRXZiV0YwYUM5Q2FXZEpiblJsWjJWeU8zaHhBSDRBRFFBQUFBSnpjZ0FVYW1GMllTNXRZWFJvTGtKcFowbHVkR1ZuWlhLTSUyRko4ZnFUdjdIUU1BQmtrQUNHSnBkRU52ZFc1MFNRQUpZbWwwVEdWdVozUm9TUUFUWm1seWMzUk9iMjU2WlhKdlFubDBaVTUxYlVrQURHeHZkMlZ6ZEZObGRFSnBkRWtBQm5OcFoyNTFiVnNBQ1cxaFoyNXBkSFZrWlhRQUFsdENlSEVBZmdBTiUyRiUyRiUyRiUyRiUyRiUyRiUyRiUyRiUyRiUyRiUyRiUyRiUyRiUyRiUyRiUyQiUyRiUyRiUyRiUyRiUyRmdBQUFBRjFjZ0FDVzBLczh4ZjRCZ2hVNEFJQUFIaHdBQUFBQkFHVCUyQmZoNGVIUUFKZENmMEx2UXNOR0MwTFhRdHRDOTBMN1F0U0RRdjlDJTJCMFlEUmc5R0gwTFhRdmRDNDBMVnpjUUIlMkJBQXdBQUFBQ2NIQjBBQkF4TWprd01UQXpNelV3TURBME5qSTVkQUFHTVRJNU1ERXdkQUFPTVRBNU1EVXhPVGcyTURFM016QjBBRG5RbU5DZklDMGcwS1BSZ2RDMTBMM1F2dEN5MExBZzBKelFzTkdGMExEUXNkQ3cwWUlnMEpEUmo5R0IwTEhRdGRDNjBMN1FzdEM5MExCMEFBelFsTkMlMkIwWVhRdnRDMDBZdHpjUUIlMkJBQXdBQUFBamNBJTNEJTNEJmphdmF4LmZhY2VzLlZpZXdTdGF0ZT03OTAxOTIxOTAyNTk4NzE0ODEzJTNBLTY2MDE1OTg0MzQ5NjEwMjAwOTc=\\tlocalstime=20260910T084736.403\\tlocaletime=20260910T084738.571\",\"sessionid\":\"3938801404567088958\",\"dst_asset_app\":\"null\",\"block_time\":\"1\",\"szone\":\"Internal_Security\",\"protocol\":6,\"logtype\":\"IPS\",\"origin_filename\":\"null\",\"_esper_time\":1789008426136,\"payload\":\"�ò�\\u0002\\u0000\\u0004\\u0000\\u0000\\u0000\\u0000\\u0000\\u0000\\u0000\\u0000\\u0000��\\u0000\\u0000\\u0001\\u0000\\u0000\\u0000J\\u001A�j��\\b\\u0000]\\u0004\\u0000\\u0000]\\u0004\\u0000\\u0000d\\u0000�#��\\u0000PV��\\u0017\\b\\u0000E\\u0000\\u0004Oh�@\\u0000@\\u0006�\\u001B��\\u000E\\u0005\\n�\\u0016x�� �\\rZ\\u000F�P�&C�\\u0018\\u0000\\u00158)\\u0000\\u0000\\u0001\\u0001\\b\\n\\u0006�B�y���DQsC3QkdCw0LvRgtCwINC%2F0L4g0YLQtdC90LTQtdGA0YMg4oSWIDI2MDQxNzU1OTkyMDcwNiDQvtGCIDE3LjA0LjIwMjbQsyAsINC00L7Qs9C%2B0LLQvtGAIOKEljQzINC%2B0YIgMjIuMDQuMjAyNtCzINC30LAg0L%2FRgNC%2B0LTRg9C60YLRi3NxAH4ADAWrCEl0AAM3ODJ0AAgyMjE4MTEwMHQAOtCf0YDQuNC%2B0LHRgNC10YLQtdC90LjQtSDQv9GA0L7QtNGD0LrRgtC%2B0LIg0L%2FQuNGC0LDQvdC40Y9wcHNxAH4ADAAR7WxzcgAUamF2YS5tYXRoLkJpZ0RlY2ltYWxUxxVX%2BYEoTwMAAkkABXNjYWxlTAAGaW50VmFsdAAWTGphdmEvbWF0aC9CaWdJbnRlZ2VyO3hxAH4ADQAAAAJzcgAUamF2YS5tYXRoLkJpZ0ludGVnZXKM%2FJ8fqTv7HQMABkkACGJpdENvdW50SQAJYml0TGVuZ3RoSQATZmlyc3ROb256ZXJvQnl0ZU51bUkADGxvd2VzdFNldEJpdEkABnNpZ251bVsACW1hZ25pdHVkZXQAAltCeHEAfgAN%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F%2B%2F%2F%2F%2F%2FgAAAAF1cgACW0Ks8xf4BghU4AIAAHhwAAAABAGT%2Bfh4eHQAJdCf0LvQsNGC0LXQttC90L7QtSDQv9C%2B0YDRg9GH0LXQvdC40LVzcQB%2BAAwAAAACcHB0ABAxMjkwMTAzMzUwMDA0NjI5dAAGMTI5MDEwdAAOMTA5MDUxOTg2MDE3MzB0ADnQmNCfIC0g0KPRgdC10L3QvtCy0LAg0JzQsNGF0LDQsdCw0YIg0JDRj9GB0LHQtdC60L7QstC90LB0AAzQlNC%2B0YXQvtC00YtzcQB%2BAAwAAAAjcA%3D%3D&javax.faces.ViewState=7901921902598714813%3A-6601598434961020097\",\"ether_type\":\"IPv4\",\"v_data\":\"0\",\"segment\":\"SEG/0\",\"oversig_detects\":\"null\",\"icmp_code\":\"0\",\"block\":\"ALLOW\",\"duser_id\":\"null\",\"id\":\"20260910084704610_0000000000000209447_2026091008.log_LEEF-AHNLAB-AIPS-EVENT-21171\",\"origin_name\":\"FINACE_01.TMS Sensor(IPS)\",\"patternsize\":\"45\",\"block_action\":\"PACKET\",\"src_asset_app\":\"null\",\"szone_group\":\"defaultGroup\",\"device_id\":\"b668d8\",\"vulnerability_id\":\"4462\",\"offset\":\"684\\t\",\"method\":\"Apache Struts URLValidator Denial of Service-2\\t\",\"module\":\"IPS\",\"mprotocol\":\"TCP\",\"cate_id\":\"Predefined Signature\\t\",\"priority\":\"HIGH\",\"file_reference\":\"null\",\"s_country\":\"null\",\"start_time\":\"20260910T024736.403\",\"detour\":\"NONE\",\"max_latency\":\"null\",\"d_info\":\"10.200.22.120\",\"src_asset_os\":\"null\",\"szone_id\":\"1\",\"attack_try_cnt\":\"1\",\"status\":101,\"icmp_type\":\"0\",\"avg_latency\":\"null\",\"dst_asset_os\":\"null\",\"ssl_decrypt\":\"NONE\",\"detect_pkts\":\"1\",\"log\":\"ips\",\"s_ip\":\"192.168.14.5\",\"origin\":\"10.10.30.101\",\"detect_bytes\":\"1117\",\"session_dir\":\"IE\",\"origin_id\":\"21171\",\"d_ip\":\"10.200.22.120\",\"interface\":\"eth2\",\"oversig_rate\":\"null\",\"mgr_ip\":\"192.168.30.101\",\"s_id\":\"6698\",\"cve\":\"CVE-2016-4465\",\"s_info\":\"192.168.14.5\",\"d_service\":\"10.200.22.120:8382\",\"pcap\":\"1MOyoQIABAAAAAAAAAAAAP//AAABAAAAShqiavD5CABdBAAAXQQAAGQA8SPBxgBQVr+4FwgARQAET2igQABABt4bwKgOBQrIFnisxCC+DVoPi1CtJkOAGAAVOCkAAAEBCAoGukKuedTB3URRc0MzUWtkQ3cwTHZSZ3RDd0lOQyUyRjBMNGcwWUxRdGRDOTBMVFF0ZEdBMFlNZzRvU1dJREkyTURReE56VTFPVGt5TURjd05pRFF2dEdDSURFM0xqQTBMakl3TWpiUXN5QXNJTkMwMEw3UXM5QyUyQjBMTFF2dEdBSU9LRWxqUXpJTkMlMkIwWUlnTWpJdU1EUXVNakF5TnRDeklOQzMwTEFnMEwlMkZSZ05DJTJCMExUUmc5QzYwWUxSaTNOeEFINEFEQVdyQ0VsMEFBTTNPREowQUFneU1qRTRNVEV3TUhRQU90Q2YwWURRdU5DJTJCMExIUmdOQzEwWUxRdGRDOTBMalF0U0RRdjlHQTBMN1F0TkdEMExyUmd0QyUyQjBMSWcwTCUyRlF1TkdDMExEUXZkQzQwWTl3Y0hOeEFINEFEQUFSN1d4emNnQVVhbUYyWVM1dFlYUm9Ma0pwWjBSbFkybHRZV3hVeHhWWCUyQllFb1R3TUFBa2tBQlhOallXeGxUQUFHYVc1MFZtRnNkQUFXVEdwaGRtRXZiV0YwYUM5Q2FXZEpiblJsWjJWeU8zaHhBSDRBRFFBQUFBSnpjZ0FVYW1GMllTNXRZWFJvTGtKcFowbHVkR1ZuWlhLTSUyRko4ZnFUdjdIUU1BQmtrQUNHSnBkRU52ZFc1MFNRQUpZbWwwVEdWdVozUm9TUUFUWm1seWMzUk9iMjU2WlhKdlFubDBaVTUxYlVrQURHeHZkMlZ6ZEZObGRFSnBkRWtBQm5OcFoyNTFiVnNBQ1cxaFoyNXBkSFZrWlhRQUFsdENlSEVBZmdBTiUyRiUyRiUyRiUyRiUyRiUyRiUyRiUyRiUyRiUyRiUyRiUyRiUyRiUyRiUyRiUyQiUyRiUyRiUyRiUyRiUyRmdBQUFBRjFjZ0FDVzBLczh4ZjRCZ2hVNEFJQUFIaHdBQUFBQkFHVCUyQmZoNGVIUUFKZENmMEx2UXNOR0MwTFhRdHRDOTBMN1F0U0RRdjlDJTJCMFlEUmc5R0gwTFhRdmRDNDBMVnpjUUIlMkJBQXdBQUFBQ2NIQjBBQkF4TWprd01UQXpNelV3TURBME5qSTVkQUFHTVRJNU1ERXdkQUFPTVRBNU1EVXhPVGcyTURFM016QjBBRG5RbU5DZklDMGcwS1BSZ2RDMTBMM1F2dEN5MExBZzBKelFzTkdGMExEUXNkQ3cwWUlnMEpEUmo5R0IwTEhRdGRDNjBMN1FzdEM5MExCMEFBelFsTkMlMkIwWVhRdnRDMDBZdHpjUUIlMkJBQXdBQUFBamNBJTNEJTNEJmphdmF4LmZhY2VzLlZpZXdTdGF0ZT03OTAxOTIxOTAyNTk4NzE0ODEzJTNBLTY2MDE1OTg0MzQ5NjEwMjAwOTc=\\tlocalstime=20260910T084736.403\\tlocaletime=20260910T084738.571\",\"sublog\":\"event\",\"d_country\":\"null\",\"host_alias\":\"AhnLab_AIPS_2000B\",\"suser_name\":\"null\",\"suser_id\":\"null\",\"s_port\":44228,\"reaction\":\"NONE\",\"end_time\":\"20260910T024738.571\",\"pktid\":\"3938801406746423267\",\"oversig_hits\":\"null\",\"d_port\":8382,\"mgr_time\":20260910084704619,\"scate_id\":\"Server Side Application\\t\",\"duser_name\":\"null\",\"attack_name\":\"Apache Struts URLValidator Denial of Service-2\\t\",\"pkt_dir\":\"IE\",\"s_service\":\"212.241.18.105\",\"category\":\"E002\",\"host_name\":\"SCNS_FIN_IPS01\",\"event_time\":20260910084704620}",
#                     "origin": "10.10.30.101",
#                     "stime": "2026/09/10 08:47:13",
#                     "origin_id": 21171,
#                     "sub_data": [
#                         {
#                             "rule_id": 49017,
#                             "etime": "2026/09/10 10:13:40",
#                             "cnt": 1332,
#                             "rulename": "[S12_IPS_TMS_KG] Apache Struts URLValidator Denial of Service-2\t",
#                             "credibility": "1",
#                             "risk": 2,
#                             "set_id": 8020400,
#                             "stime": "2026/09/10 08:47:13",
#                             "risk_weight": 0,
#                             "rule_level": 1
#                         }
#                     ],
#                     "access_right": "R",
#                     "s_info": "192.168.14.5",
#                     "d_country": "null",
#                     "ruleset_set_id": null,
#                     "incident_hash": "14867e372d24b3ea35e4b0a0d2a6f05c63b0c03fd936982b553f2153e9f6eab0fd1123fa3456e32487624f27b97406392118c3662de2bf3c7a6ae2f570e05440",
#                     "hitcount": "{\"count(*)\":23}",
#                     "direction": "-",
#                     "prediction_cd": null,
#                     "d_addr": "00000000000000000000ffff0ac81678",
#                     "s_port": "44228",
#                     "ai_score": null,
#                     "display": 1,
#                     "cnt": 1332,
#                     "tactics_id": null,
#                     "display_level": 1,
#                     "d_port": "8382",
#                     "rule_id": 49017,
#                     "max_level": 1,
#                     "etime": "2026/09/10 10:13:40",
#                     "risk": 2,
#                     "risk_weight": 0
#                 }
#             ]
#         },
#         "soundList": [
#             "Alarm1.mp3"
#         ],
#         "alarmList": []
#     }
# }