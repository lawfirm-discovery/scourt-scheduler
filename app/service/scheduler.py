from datetime import datetime, timedelta
import logging
from math import e
from typing import List
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.session import AsyncSessionLocal
from app.schema.case_schema import CaseRelatedUsers, CaseResponseForParser
from app.service.parser import (
    ParseCaseService,
    SupremCourtHistoryParsedResult,
    SupremCourtTrialInfoParsedResult,
)
import re
from app.core.config import settings
from app.service.alimtalk import AlimTalkService
from app.service.mycase import MyCaseService


logger = logging.getLogger(__name__)


class SupremeCourtScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
        self.alimtalk = AlimTalkService(
            api_url=settings.KAKAO_NOTI_API_URL,
            secret_key=settings.KAKAO_NOTI_SECRET_KEY,
            app_key=settings.KAKAO_NOTI_APP_KEY,
            sender_key=settings.KAKAO_NOTI_SENDER_KEY,
        )

    async def start(self):
        # 디버깅용
        # self.scheduler.add_job(
        #     self._runner, "date", run_date=datetime.now() + timedelta(seconds=10)
        # )

        # 매일 10시 0분, 17시 0분에 실행
        self.scheduler.add_job(self._runner, "cron", hour=10, minute=0)
        # self.scheduler.add_job(self._runner, "cron", hour=17, minute=0)

        self.scheduler.start()
        logger.info("나의사건정보 스케줄러 시작")

    async def shutdown(self):
        self.scheduler.shutdown()
        logger.info("나의사건정보 스케줄러 종료")

    async def _runner(self):
        logger.info("나의사건정보 스케줄러 실행")

        # 작업 단위로 비동기 세션 생성/종료
        async with AsyncSessionLocal() as session:
            parser = ParseCaseService(session)
            repo = MyCaseService(session)

            skip = 0
            LIMIT = 10

            # 업데이트할 사건 목록 조회
            logger.info(f"스케줄러 작업 시작")
            while True:
                cases = await repo.get_case_list_for_scheduler(skip=skip, limit=LIMIT)
                if not cases:
                    break

                for case in cases:
                    # 테스트용
                    # if case.case_id != 189:
                    #     continue

                    logger.info(
                        f"스케줄러 작업 대상 사건: {case.title}, 사건번호: {case.case_number}"
                    )
                    if not case.client_name:
                        logger.info(
                            f"의뢰인 이름이 없어 사건 정보를 파싱하지 않습니다. 사건번호: {case.case_number}"
                        )
                        continue

                    if not case.jurisdiction:
                        logger.info(
                            f"관할법원 정보가 없어 사건 정보를 파싱하지 않습니다. 사건번호: {case.case_number}"
                        )
                        continue

                    # 사건 번호 파싱
                    parsed_case_number = self._parse_case_number(case.case_number)
                    if not parsed_case_number:
                        logger.info(
                            f"사건번호가 형식에 맞지 않아서 사건 정보를 파싱하지 않습니다. 사건번호: {case.case_number}"
                        )
                        continue
                    year, gubun, serial = parsed_case_number

                    try:
                        parsed_html = await parser.get_html_from_capcha_server(
                            sch_bub_nm=case.jurisdiction,
                            sel_sa_year=year,
                            sa_gubun=gubun,
                            sa_serial=serial,
                            ds_nm=case.client_name,
                        )

                        result = await parser.update(
                            html=parsed_html,
                            case_id=case.case_id,
                            agency_name=case.jurisdiction,
                        )

                        # 스케줄러 동작 이력을 기록합니다.
                        await repo.create_supremecourt_parse_history(
                            case_id=case.case_id,
                            method="scheduler",
                            result="success",
                        )
                        await session.commit()
                    except Exception as e:
                        logger.error(
                            f"사건 정보를 파싱하는 중 오류가 발생했습니다. 사건번호: {case.case_number}, 오류: {str(e)}"
                        )
                        await session.rollback()
                        await repo.create_supremecourt_parse_history(
                            case_id=case.case_id,
                            method="scheduler",
                            result=str(e),
                        )
                        await session.commit()
                        continue

                    if not result.history and not result.trial_info:
                        continue

                    logger.info(
                        f"대상사건: {case.title}({case.case_number}), 이력업데이트 {len(result.history) if result.history else 0}건, 기일업데이트 {len(result.trial_info) if result.trial_info else 0}건"
                    )

                    # 변호사 및 소속 조직구성원
                    if (
                        case.firm_id == 1
                    ):  # 테스트를 위해 일단 디스커버리 사건만 알림톡을 보낸다.
                        target_users = await repo.get_related_users(
                            author_id=case.author_id,
                            firm_id=case.firm_id,
                            # author_id=72,
                            # firm_id=None,
                        )

                        # 테스트(테스트대표변호사, 테스트로펌)
                        # target_users = await repo.get_related_users(
                        #     author_id=72, firm_id=14
                        # )

                        # 사건 의뢰인(의뢰인에게 까지 보내야 하면 주석 해제)
                        # target_users.extend(
                        #     await repo.get_related_clients_by_case_id(
                        #         case_id=case.case_id
                        #     )
                        # )

                        # 알림톡 보내기
                        await self._send_alimtalk(
                            target_users=target_users,
                            case=case,
                            history=result.history,
                            trial_info=result.trial_info,
                        )

                skip += LIMIT

            logger.info("스케줄러 작업 종료")

    def _parse_case_number(self, case_number: str) -> tuple[str, str, str] | None:
        """
        사건번호를 파싱합니다.
        정규표현식을 사용해서 2025가단123456 형식을 year, gubun, serial로 분리합니다.
        [수정] gubun 에 해당하는 글자가 최대 4자까지 있음
        [수정] serial 에 해당하는 숫자가 최대 7자까지 있음
        [수정] serial 뒤에 숫자가 아닌 추가표기(예: "(본소)")가 올 수 있으므로 이를 무시
        """
        m = re.fullmatch(r"(\d{2,4})([가-힣]{1,4})(\d{1,7})(?:\D.*)?", case_number)
        if not m:
            return None
        year, gubun, serial = m.groups()
        return (year, gubun, serial)

    async def _send_alimtalk(
        self,
        target_users: List[CaseRelatedUsers],
        case: CaseResponseForParser,
        history: List[SupremCourtHistoryParsedResult],
        trial_info: List[SupremCourtTrialInfoParsedResult],
    ):
        if not history and not trial_info:
            return

        if history:
            for user in target_users:
                if (
                    user.new_history == False
                ):  # 명시적으로 거부한 경우(False)에는 보내지 않음. 즉 None 일때는 보냄
                    continue

                try:
                    # 알림톡 기본 1000자 제한이 있다. 그래서 템플릿 기본 글자 약 230자를 제외하고 700자까지만 보냄
                    await self.alimtalk.send_message(
                        template_code="CASE_NEW_HISTORY",
                        recipient_no=user.phone,
                        template_parameters={
                            "사건명": case.title,
                            "사건번호": case.case_number,
                            "등록건수": len(history),
                            "진행내용": "\n".join(
                                ["\n"]  # 첫줄에 개행문자 추가하기 위한 용도
                                + [
                                    f"{i+1}. {h.date} - {h.content}"
                                    for i, h in enumerate(history)
                                ]
                            )[:700],
                        },
                    )
                except Exception as e:
                    logger.error(
                        f"알림톡 전송 중 오류가 발생했습니다. 대상: {user.username}({user.phone}), 오류: {str(e)}"
                    )
                    continue

        if trial_info:
            for user in target_users:
                if (
                    user.new_trial == False
                ):  # 명시적으로 거부한 경우(False)에는 보내지 않음. 즉 None 일때는 보냄
                    continue

                # 마지막 기일만 알림톡 보낸다.
                index = len(trial_info) - 1
                try:
                    await self.alimtalk.send_message(
                        template_code="CASE_NEW_TRIAL",
                        recipient_no=user.phone,
                        template_parameters={
                            "사건명": case.title,
                            "사건번호": case.case_number,
                            "날짜": trial_info[index].date,
                            "장소": trial_info[index].location,
                            "기일구분": trial_info[index].type,
                        },
                    )
                except Exception as e:
                    logger.error(
                        f"알림톡 전송 중 오류가 발생했습니다. 대상: {user.username}({user.phone}), 오류: {str(e)}"
                    )
                    continue
