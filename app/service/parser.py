from datetime import datetime
import re
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from bs4 import BeautifulSoup

from app.service.mycase import MyCaseService

from app.schema.base import SchemaBase
from pydantic import Field
import logging

logger = logging.getLogger(__name__)


class SupremCourtHistoryParsedResult(SchemaBase):
    """대법원 사건 이력 파싱 결과 스키마"""

    date: str = Field(..., description="일자")
    content: str = Field(..., description="내용")
    result: Optional[str] = Field(None, description="결과")


class SupremCourtTrialInfoParsedResult(SchemaBase):
    """대법원 사건 변론기일 파싱 결과 스키마"""

    date: str = Field(..., description="일자")
    time: str = Field(..., description="시간")
    type: str = Field(..., description="종류")
    location: str = Field(..., description="장소")
    result: Optional[str] = Field(None, description="결과")


class ParserUpdateResult:
    def __init__(
        self,
        history: List[SupremCourtHistoryParsedResult],
        trial_info: List[SupremCourtTrialInfoParsedResult],
    ):
        self.history = history
        self.trial_info = trial_info


class ParseCaseService:
    def __init__(self, db: AsyncSession | None = None):
        self.db = db

        # 여기서 날짜 포맷을 정의해서 공통으로 사용합시다.
        self.date_fmt = "%Y.%m.%d"
        self.time_fmt = "%H:%M"

    async def get_html_from_capcha_server(
        self,
        sch_bub_nm: str,
        sel_sa_year: str,
        sa_gubun: str,
        sa_serial: str,
        ds_nm: str,
    ) -> str:
        """
        http client 를 사용하여 새로운 요청을 생성한 후 응답 값으로 부터
        사건 정보를 파싱합니다.

        endpoint url : https://test.legalmonster.co.kr/parse_case, POST
        """

        url = "https://test.legalmonster.co.kr/parse_case"
        form_data = {
            "sch_bub_nm": sch_bub_nm,
            "sel_sa_year": sel_sa_year,
            "sa_gubun": sa_gubun,
            "sa_serial": sa_serial,
            "ds_nm": ds_nm,
        }
        try:
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=httpx.Timeout(30.0)
            ) as client:
                response = await client.post(
                    url,
                    data=form_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                # 성공 케이스
                if 200 <= response.status_code < 300:
                    return response.text

                # 에러 케이스: 의도된(JSON) vs 비의도(plain string)를 구분
                status = response.status_code
                body_text = response.text
                try:
                    payload = response.json()
                except ValueError:
                    payload = None

                if (
                    isinstance(payload, dict)
                    and isinstance(payload.get("detail"), dict)
                    and "code" in payload["detail"]
                    and "message" in payload["detail"]
                ):
                    detail = payload["detail"]
                    logger.error(
                        f"사건 정보 조회중 에러가 발생했습니다. message={detail.get('message')}",
                    )
                    raise Exception(
                        f"{detail.get('message') or '상대 서버측의 알 수 없는 오류'}",
                    )
                else:
                    raise Exception("사건 정보 조회중 에러가 발생했습니다.")
        except httpx.RequestError as e:
            # 네트워크 계층 오류 (연결/타임아웃 등)
            logger.error(f"네트워크 요청이 실패했습니다.")
            raise Exception("네트워크 요청이 실패")

    async def parse_history_from_html(
        self, html: str
    ) -> List[SupremCourtHistoryParsedResult]:
        """
        ### beautifulsoup 를 사용하여 html로 부터 사건의 사건 이력을 파싱합니다.

        2025.05.27 기준
            대법원 나의 사건 정보에는 사건 이력이 표(table)로 제공됩니다.
            다수의 표에서 사건 이력이 표시되는 테이블을 찾기 위해
            테이블의 thead 내 span 텍스트를 확인하여
            '일자', '내용', '결과'가 포함된 테이블을 찾습니다.
            따라서 테이블 헤더의 내용이 변경된 경우 이 로직을 수정해야 합니다.

            클래스가 aglify-table인 것으로 추정되므로 클래스로 찾지 않습니다.
        """

        soup = BeautifulSoup(html, "html.parser")
        target_tables = []
        required_keywords = {"일자", "내용", "결과"}

        # 해당하는 테이블 찾기
        for table in soup.find_all("table"):
            thead = table.find("thead")
            if not thead:
                continue

            # thead 내 모든 span 텍스트 수집
            spans = thead.find_all("span")
            span_texts = [span.get_text(strip=True) for span in spans]

            matched_count = sum(
                1 for keyword in required_keywords if keyword in span_texts
            )

            if matched_count >= 3:
                target_tables.append(table)
                break

        if not target_tables:
            raise Exception("사건 진행 내용에 해당하는 테이블을 찾을 수 없습니다.")

        parsed_results = []
        # 테이블 바디(tbody)에서 각 tr > td를 찾고 문자열을 가져옵니다.
        # 지금 로직상 각 tr은 최소 3개의 td를 가지고 있어야 합니다.
        for table in target_tables:
            tbody = table.find("tbody")
            if not tbody:
                continue

            rows = tbody.find_all("tr")
            for row in rows:
                tds = row.find_all("td")
                if len(tds) >= 3:
                    date = tds[0].get_text(strip=True)
                    content = tds[1].get_text(strip=True)
                    result = tds[2].get_text(strip=True)
                    parsed_results.append(
                        SupremCourtHistoryParsedResult(
                            date=date, content=content, result=result
                        )
                    )

        logger.debug(f"[이력 파싱 완료] 사건 이력: {len(parsed_results)} 건")
        return parsed_results

    async def parse_trial_info_from_html(
        self, html: str
    ) -> List[SupremCourtTrialInfoParsedResult]:
        """
        html 에서 사건 변론기일(공판기일, 선고기일 등)을 파싱합니다.

        2025.05.27 기준
            사건 변론기일은 대법원 사건 정보 페이지에서
            '일자', '시각', '기일구분', '기일장소', '결과'가 포함된 테이블을 찾습니다.
        """

        soup = BeautifulSoup(html, "html.parser")
        target_tables = []
        required_keywords = {"일자", "시각", "기일구분", "기일장소", "결과"}

        # 해당하는 테이블 찾기
        for table in soup.find_all("table"):
            thead = table.find("thead")
            if not thead:
                continue

            # thead 내 모든 span 텍스트 수집
            spans = thead.find_all("span")
            span_texts = [span.get_text(strip=True) for span in spans]

            matched_count = sum(
                1 for keyword in required_keywords if keyword in span_texts
            )

            if matched_count >= 5:
                target_tables.append(table)
                break

        if not target_tables:
            # 대법원 사건의 경우 최근 기일 내용 테이블이 없음.
            logger.error("최근 기일 내용에 해당하는 테이블을 찾을 수 없습니다.")
            return []

        parsed_results = []
        # 테이블 바디(tbody)에서 각 tr > td를 찾고 문자열을 가져옵니다.
        # 지금 로직상 각 tr은 최소 5개의 td를 가지고 있어야 합니다.
        for table in target_tables:
            tbody = table.find("tbody")
            if not tbody:
                continue

            rows = tbody.find_all("tr")
            for row in rows:
                tds = row.find_all("td")
                if len(tds) >= 5:
                    date = tds[0].get_text(strip=True)
                    time = tds[1].get_text(strip=True)
                    type = tds[2].get_text(strip=True)
                    location = tds[3].get_text(strip=True)
                    result = tds[4].get_text(strip=True)
                    parsed_results.append(
                        SupremCourtTrialInfoParsedResult(
                            date=date,
                            time=time,
                            type=type,
                            location=location,
                            result=result,
                        )
                    )
                    logger.debug(
                        f"[변론기일 파싱] {date} {time} {type} {location} {result}"
                    )

        logger.debug(f"[이력 파싱 완료] 사건 변론기일: {len(parsed_results)} 건")
        return parsed_results

    async def filter_history_for_update(
        self,
        parsed_results: List[SupremCourtHistoryParsedResult],
        last_date: Optional[datetime] = None,
        last_content: Optional[str] = None,
    ) -> List[SupremCourtHistoryParsedResult]:
        """
        사건 이력 중 새로 받아온 사건 이력과
        기존 사건 이력 중 마지막 사건 이력을 비교하여
        새로 받아온 사건 이력 중 추가할 사건 이력을 필터링합니다.
        """

        if not last_date or not last_content:
            return parsed_results

        # 날짜와 내용이 같은 이력의 인덱스를 찾아냅니다.
        index = 0
        for parsed_result in parsed_results:
            if (
                parsed_result.date == last_date.strftime(self.date_fmt)
                and parsed_result.content == last_content
            ):
                break
            index += 1

        # 인덱스를 기준으로 리스트를 슬라이싱하여 새로 받아온 사건 이력 중 추가할 사건 이력을 필터링합니다.
        parsed_results = parsed_results[index:]

        if len(parsed_results) > 0:
            logger.debug(
                f"[이력 필터링 완료] (총 {len(parsed_results)}건 중 마지막 사건 이력: {parsed_results[-1].date}, {parsed_results[-1].content}"
            )

        return parsed_results

    async def filter_trial_info_for_update(
        self,
        parsed_results: List[SupremCourtTrialInfoParsedResult],
        last_date: Optional[datetime] = None,
        last_type: Optional[str] = None,
    ):
        """
        사건 변론기일 중 새로 받아온 사건 변론기일과
        기존 사건 변론기일 중 마지막 사건 변론기일을 비교하여
        새로 받아온 사건 변론기일 중 추가할 사건 변론기일이 있는지 판단합니다.
        """

        if not last_date or not last_type:
            return parsed_results

        index = 0
        for parsed_result in parsed_results:
            # 날짜와 시간, 변론기일 종류가 같은 변론기일의 인덱스를 찾아냅니다.
            if (
                parsed_result.date == last_date.strftime(self.date_fmt)
                and parsed_result.time == last_date.strftime(self.time_fmt)
                and parsed_result.type == last_type
            ):
                break
            index += 1

        parsed_results = parsed_results[index:]

        if len(parsed_results) > 0:
            logger.debug(
                f"[변론기일 필터링 완료] (총 {len(parsed_results)}건 중 마지막 변론기일: {parsed_results[-1].date}, {parsed_results[-1].time}, {parsed_results[-1].type}"
            )

        return parsed_results

    async def update_case_history(
        self,
        html: str,
        case_id: int,
    ) -> List[SupremCourtHistoryParsedResult]:
        """
        사건 이력 중 새로 받아온 사건 이력과
        기존 사건 이력 중 마지막 사건 이력을 비교하여
        새로 받아온 사건 이력 중 추가할 사건 이력을 필터링합니다.
        """

        logger.debug(
            f"[업데이트 시작] case_id: {case_id}에 대한 사건 이력을 DB 에 업데이트 합니다."
        )

        if not self.db:
            raise Exception("db is not initialized")

        # 사건 이력을 파싱합니다.
        parsed_results = await self.parse_history_from_html(html)

        # 대법원 사건 이력 중 마지막 사건 이력을 조회합니다.
        case_history_repository = MyCaseService(self.db)
        last_case_history = (
            await case_history_repository.get_last_supremCourt_history_by_case_id(
                case_id
            )
        )

        # 사건 이력 중 새로 받아온 사건 이력과 기존 사건 이력 중 마지막 사건 이력을 비교하여
        # 새로 받아온 사건 이력 중 추가할 사건 이력을 필터링합니다.
        filtered_results = await self.filter_history_for_update(
            parsed_results,
            last_date=last_case_history.created_at if last_case_history else None,
            last_content=last_case_history.details if last_case_history else None,
        )

        # TODO: 추가할 새로운 사건 이력이 있으면 관련 유저들에게 알림 보내기

        try:
            # 사건 이력 중 새로 받아온 사건 이력 중 추가할 사건 이력을 추가합니다.
            from datetime import timedelta

            for idx, parsed_result in enumerate(filtered_results):
                # 사건 이력의 날짜를 datetime으로 변환하고
                # seconds를 추가하여 사건 이력의 날짜를 구분합니다.(순서 보장)
                base_dt = datetime.strptime(parsed_result.date, self.date_fmt)
                dt_with_seconds = base_dt + timedelta(seconds=idx)
                await case_history_repository.create_case_history_from_supremCourt_history(
                    case_id=case_id,
                    date=dt_with_seconds,
                    content=parsed_result.content,
                    trial_result=parsed_result.result,
                )
            await self.db.commit()
            logger.debug(
                f"[업데이트 완료] case_id: {case_id}에 대한 사건 이력을 DB 에 업데이트 완료."
            )
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error occurred while updating case history: {str(e)}")

        return filtered_results

    async def update_case_trial_info(
        self,
        html: str,
        case_id: int,
        agency_name: Optional[str] = None,
    ) -> List[SupremCourtTrialInfoParsedResult]:
        """
        사건 변론기일 중 새로 받아온 사건 변론기일과
        기존 사건 변론기일 중 마지막 사건 변론기일을 비교하여
        새로 받아온 사건 변론기일 중 추가할 사건 변론기일이 있는지 판단합니다.
        """

        logger.debug(
            f"[업데이트 시작] case_id: {case_id}에 대한 사건 변론기일을 DB 에 업데이트 합니다."
        )

        if not self.db:
            raise Exception("db is not initialized")

        # 사건 변론기일을 파싱합니다.
        parsed_results = await self.parse_trial_info_from_html(html)

        # 사건 변론기일 중 마지막 사건 변론기일을 조회합니다.
        case_history_repository = MyCaseService(self.db)
        last_trial_info = await case_history_repository.get_last_trial_info_by_case_id(
            case_id
        )

        # 사건 변론기일 중 새로 받아온 사건 변론기일과 기존 사건 변론기일 중 마지막 사건 변론기일을 비교하여
        # 새로 받아온 사건 변론기일 중 추가할 사건 변론기일이 있는지 판단합니다.
        filtered_results = await self.filter_trial_info_for_update(
            parsed_results,
            last_date=last_trial_info.trial_date if last_trial_info else None,
            last_type=last_trial_info.trial_type if last_trial_info else None,
        )

        # TODO: 추가할 새로운 사건 변론기일이 있으면 관련 유저들에게 알림 보내기

        try:
            # 사건 변론기일 중 새로 받아온 사건 변론기일 중 추가할 사건 변론기일을 추가합니다.
            # parsed_result.date 와 parsed_result.time을 합쳐서 datetime으로 변환합니다.
            for parsed_result in filtered_results:
                await case_history_repository.create_trial_info_from_supremCourt_history(
                    case_id=case_id,
                    trial_date=datetime.strptime(
                        parsed_result.date + " " + parsed_result.time,
                        self.date_fmt + " " + self.time_fmt,
                    ),
                    trial_type=parsed_result.type,
                    trial_agency=agency_name,
                    trial_agency_address_detail=parsed_result.location,
                    trial_result=parsed_result.result,
                )
            await self.db.commit()
            logger.debug(
                f"[업데이트 완료] case_id: {case_id}에 대한 사건 변론기일을 DB 에 업데이트 완료."
            )
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error occurred while updating case trial info: {str(e)}")

        return filtered_results

    async def parse_agency_name(self, html: str) -> str:
        """
        대법원 사건 정보 html 응답 값에서 관할 기관명을 파싱합니다.

        2025.05.27 기준
            "기본 내용 (${관할법원명})" 형태로 응답됩니다.
        """

        # 기본 내용 (${관할법원명}) 형태의 문자열을 찾습니다.
        match = re.search(r"기본 내용 \((.*?)\)", html)
        if match:
            return match.group(1)

        return ""

    async def update(
        self, html: str, case_id: int, agency_name: Optional[str] = None
    ) -> ParserUpdateResult:
        """
        사건 이력과 사건 변론기일을 업데이트합니다.
        """

        new_history = await self.update_case_history(html, case_id)

        # TODO: html 에서 관할기관명을 가져올 수는 있지만, 안정성을 위해 나중에는 필수 파라미터롤 수정하는 것이 좋겠다.
        # 현재는 repository 에서도 optional 값으로 되어 있음
        if not agency_name:
            agency_name = await self.parse_agency_name(html)

        new_trial_info = await self.update_case_trial_info(html, case_id, agency_name)

        return ParserUpdateResult(history=new_history, trial_info=new_trial_info)  #
