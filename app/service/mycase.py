from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime

from app.schema.case_schema import (
    CaseHistoryResponse,
    CaseHistoryEventType,
    CaseHistoryEventType2,
    CaseRelatedUsers,
    CaseResponseForParser,
    CaseStatus,
    ClientResponse,
    TrialInfoResponse,
)
from app.schema.notification_schema import (
    NotificationAction,
    NotificationPriority,
    NotificationType,
)


class MyCaseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_supremCourt_history_by_case_id(
        self, case_id: int
    ) -> List[CaseHistoryResponse]:
        """
        대법원 나의 사건 정보를 통해 입력된 사건 이력 중 마지막 이력을 조회합니다.
        마지막 이력은 새로 받아온 정보 중에서 추가할 이력이 있는지 판단하기 위해 사용됩니다.

        날짜는 같은 날짜(동일 시간)가 있으므로, id 기준으로 정렬하여 마지막 이력을 조회합니다.
        """

        result = await self.db.execute(
            text(
                """
            SELECT
                his.id
                , his.case_id
                , his.event_type
                , his.event_type2
                , his.details
                , his.created_at
                , his.result
            FROM erp_case_histories his
            WHERE 
                his.case_id = :case_id
                AND his.event_type = :event_type
            ORDER BY his.id DESC
            """
            ),
            {"case_id": case_id, "event_type": CaseHistoryEventType.COURT.value},
        )
        rows = result.fetchall()

        if not rows:
            return []

        return [CaseHistoryResponse.model_validate(row) for row in rows]

    async def create_case_history_from_supremCourt_history(
        self,
        case_id: int,
        date: datetime,
        # date_fmt: str,
        content: str,
        trial_result: Optional[str] = None,
    ) -> int:
        """
        대법원 나의 사건 정보에서 가져온 사건 이력을 테이블에 저장합니다.

        date: 사건 이력의 날짜
        date_fmt: 사건 이력의 날짜 형식(현재 "%Y.%m.%d")
        content: 사건 이력의 내용
        trial_result: 사건 이력의 결과
        """

        result = await self.db.execute(
            text(
                """
            INSERT INTO erp_case_histories (
                case_id
                , event_type
                , event_type2
                , prev_value
                , curr_value
                , details
                , created_at
                , result
            )
            VALUES (
                :case_id
                , :event_type
                , :event_type2
                , :prev_value
                , :curr_value
                , :details
                , :created_at
                , :result
            )
            RETURNING id
            """
            ),
            {
                "case_id": case_id,
                "event_type": CaseHistoryEventType.COURT.value,
                "event_type2": CaseHistoryEventType2.ETC.value,
                "prev_value": None,
                "curr_value": None,
                "details": content,
                "created_at": date,
                "result": trial_result,
            },
        )
        row = result.fetchone()

        return row.id if row else 0

    async def create_trial_info_from_supremCourt_history(
        self,
        case_id: int,
        trial_date: datetime,
        trial_type: Optional[str] = None,
        trial_agency: Optional[str] = None,
        trial_agency_address_detail: Optional[str] = None,
        trial_result: Optional[str] = None,
    ) -> int:
        """
        사건 변론기일 중 새로 받아온 사건 변론기일을 테이블에 저장합니다.

        date: 사건 변론기일의 날짜
        content: 사건 변론기일의 내용
        trial_result: 사건 변론기일의 결과
        """

        result = await self.db.execute(
            text(
                """
            INSERT INTO erp_case_trial_info (
                case_id
                , trial_date
                , trial_agency
                , trial_agency_address_detail
                , trial_result
                , trial_type
                , source
            )
            VALUES (
                :case_id
                , :trial_date
                , :trial_agency
                , :trial_agency_address_detail
                , :trial_result
                , :trial_type
                , :source
            )
            RETURNING id
            """
            ),
            {
                "case_id": case_id,
                "trial_date": trial_date,
                "trial_agency": trial_agency,
                "trial_agency_address_detail": trial_agency_address_detail,
                "trial_result": trial_result,
                "trial_type": trial_type,
                "source": CaseHistoryEventType.COURT.value,
            },
        )
        row = result.fetchone()

        return row.id if row else 0

    async def get_trial_info_by_case_id(self, case_id: int) -> List[TrialInfoResponse]:
        """
        ### 사건 변론기일 정보 중 마지막 변론기일을 조회합니다.
        마지막 변론기일은 새로 받아온 정보 중에서 추가할 변론기일이 있는지 판단하기 위해 사용됩니다.

        날짜는 같은 날짜(동일 시간)가 있으므로, trial_date 기준으로 정렬하여 마지막 변론기일을 조회합니다.
        """

        result = await self.db.execute(
            text(
                """
            SELECT
                trial.id
                , trial.case_id
                , trial.trial_date
                , trial.trial_type
                , trial.trial_agency_address_detail
                , trial.trial_result
            FROM erp_case_trial_info trial
            WHERE 
                trial.case_id = :case_id
                AND trial.source = :source
            ORDER BY trial.trial_date DESC
            """
            ),
            {"case_id": case_id, "source": CaseHistoryEventType.COURT.value},
        )
        rows = result.fetchall()

        if not rows:
            return []

        return [TrialInfoResponse.model_validate(row) for row in rows]

    async def get_case_list_for_scheduler(
        self, skip: int, limit: int
    ) -> List[CaseResponseForParser]:
        """
        나의 사건 정보 업데이를 위한 사건 목록 조회입니다.
        모든 사건을 조회하기 때문에 유저의 요청이 아닌 스케줄러에서만 사용하기 바랍니다.
        """

        results = await self.db.execute(
            text(
                f"""
        SELECT 
            ec.id AS case_id
            , ec.title
            , ec.status
            , ec.case_number
            , ec.jurisdiction
            , ec.author_id
            , ec.firm_id
            , (
                SELECT 
                    c.name
                FROM 
                    erp_case_clients cc
                INNER JOIN erp_clients c 
                    ON cc.client_id = c.id
                WHERE 
                    cc.case_id = ec.id
                ORDER BY
                    -- 형사사건의 경우 피고인/피의자로 조회해야 함.
                    -- 일단 간단하게 사건 ec.case_type1 = '형사' 같은 조건 처리 없이
                    -- 정렬 순서를 수정하는 방법으로 처리하였음.
                    CASE 
                        WHEN cc.litigant_role = '피고인' THEN 1
                        WHEN cc.litigant_role = '피의자' THEN 2
                        ELSE 3
                    END
                LIMIT 1
            ) AS client_name
        FROM 
            erp_cases ec
        WHERE 
            ec.case_number IS NOT NULL
            AND ec.jurisdiction IS NOT NULL
            AND ec.status != :status
        ORDER BY 
            ec.id ASC
        LIMIT :limit
        OFFSET :skip
        """
            ),
            {"skip": skip, "limit": limit, "status": CaseStatus.CLOSE.value},
        )
        rows = results.fetchall()

        if not rows:
            return []

        cases = []
        for row in rows:
            cases.append(CaseResponseForParser.model_validate(row))

        return cases

    async def get_related_users(
        self, author_id: int, firm_id: Optional[int] = None
    ) -> List[CaseRelatedUsers]:
        """
        사건 관련 유저를 조회합니다.
        알림톡 발송이 목적이므로 phone 이 있는 유저만 검색합니다.
        """

        results = await self.db.execute(
            text(
                f"""
        SELECT 
            u.id AS user_id
            , u.username
            , u.firm_id
            , u.dtype
            , u.phone
            , us.new_history
            , us.new_trial
        FROM 
            users u
        LEFT JOIN erp_user_notification_setting us
            ON u.id = us.user_id
        WHERE 
            u.phone IS NOT NULL
            AND (
                u.id = :author_id
                {"OR u.firm_id = :firm_id" if firm_id else ""}
            )
        """
            ),
            {"author_id": author_id, "firm_id": firm_id},
        )
        rows = results.fetchall()

        if not rows:
            return []

        users = []
        for row in rows:
            users.append(CaseRelatedUsers.model_validate(row))

        return users

    async def get_related_clients_by_case_id(
        self, case_id: int
    ) -> List[CaseRelatedUsers]:
        """
        사건 관련 의뢰인을 조회합니다.
        알림톡 발송이 목적이므로 contact_number_1 이 있는 유저만 검색합니다.
        """

        results = await self.get_clients_by_case_id(case_id)

        if not results:
            return []

        users = []
        for result in results:
            if not result.name or not result.contact_number_1:
                continue

            users.append(
                CaseRelatedUsers(
                    user_id=-1,  # 레몬 유저가 아니라 의뢰인은 id 가 없다.
                    username=result.name,
                    firm_id=None,
                    dtype=None,
                    phone=result.contact_number_1,
                    new_history=None,
                    new_trial=None,
                )
            )

        return users

    async def get_clients_by_case_id(
        self, case_id: int, firm_id: Optional[int] = None
    ) -> List[ClientResponse]:
        """
        사건 ID로 관련된 클라이언트 정보를 조회합니다.

        Args:
            case_id (int): 사건 ID
            firm_id (Optional[int]): 조직 ID, 조직 소속 클라이언트만 조회

        Returns:
            List[ClientResponse]: 클라이언트 정보 목록
        """

        result = await self.db.execute(
            text(
                f"""
            SELECT
                c.id
                , c.name
                , c.client_type 
                , c.address
                , c.detailed_address
                , c.postal_code
                , c.referral_source
                , c.resident_registration_number
                , c.contact_number_1
                , c.contact_number_2
                , c.email
                , c.tax_invoice_email
                , c.corporation_name
                , c.corporation_representative_name
                , c.business_registration_number
                , c.corporation_registration_number
                , c.manager_name
                , cc.is_opponent
                , cc.litigant_role
            FROM 
                erp_clients c
            INNER JOIN erp_case_clients cc 
                ON c.id = cc.client_id
                AND cc.case_id = :case_id
            WHERE 1=1
                {f"AND c.registering_firm_id = :firm_id" if firm_id else ""}
            """
            ),
            {"case_id": case_id, "firm_id": firm_id},
        )
        results = result.fetchall()

        if not results:
            return []

        clients: List[ClientResponse] = []
        for row in results:
            clients.append(ClientResponse.model_validate(row))

        return clients

    async def create_supremecourt_parse_history(
        self, case_id: int, method: str | None, result: str | None
    ) -> None:
        """
        캡차 크래커를 이용해서 나의사건정보를 파싱한 이력을 기록
        """

        await self.db.execute(
            text(
                """
            INSERT INTO erp_supremecourt_parse_history (
                case_id
                , method
                , result
            ) VALUES (
                :case_id
                , :method
                , :result
            )
            """
            ),
            {"case_id": case_id, "method": method, "result": result},
        )

        return None

    async def create_system_notification(
        self, title: str, content: str, case_id: int, user_id: int
    ):
        """
        시스템 알림을 생성합니다.
        """

        result = await self.db.execute(
            text(
                f"""
        INSERT INTO erp_notifications (
            type
            , action
            , title
            , content
            , priority
            , source
            , source_id
            , target_url
            , extra_data
            , user_id
            , firm_id
            , sender_id
            , for_everyone
        ) VALUES (
            :type
            , :action
            , :title
            , :content
            , :priority
            , :source
            , :source_id
            , :target_url
            , :extra_data
            , :user_id
            , :firm_id
            , :sender_id
            , :for_everyone
        ) RETURNING id
        """
            ),
            {
                "type": NotificationType.CASE,
                "action": NotificationAction.CASE_HISTORY_ADDED,
                "title": title,
                "content": content,
                "priority": NotificationPriority.MEDIUM,
                "source": "case",
                "source_id": case_id,
                "target_url": None,
                "extra_data": None,
                "user_id": user_id,
                "firm_id": None,
                "sender_id": None,
                "for_everyone": False,
            },
        )

        row = result.fetchone()

        if not row:
            return None

        return row.id
