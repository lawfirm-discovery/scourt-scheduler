from app.schema.base import SchemaBase
from pydantic import Field
from typing import Optional
from datetime import datetime
from typing import Dict, Any
from app.schema.base import SchemaBase
from enum import Enum


class CaseStatus(str, Enum):
    """사건 상태"""

    PENDING = "보류"
    OPEN = "진행중"
    CLOSE = "종결"


class CaseHistoryEventType(str, Enum):
    CASE = "사건"
    CONTRACT = "계약"
    SYSTEM = "시스템"
    COURT = "법원사건정보"


class CaseHistoryEventType2(str, Enum):
    # 사건 관련 이력
    CONSULT = "상담진행"
    SUBMISSION = "서류제출"
    TRIAL = "기일"
    ATTENDANCE = "기일출석"
    JUDGMENT = "판결선고"
    APPEAL = "항소/상고제기"
    SETTLEMENT = "조정/화해"
    CASE_END = "사건종결"

    # 계약 관련 이력
    CLIENT_CREATE = "의뢰인등록"
    CLIENT_UPDATE = "의뢰인변경"
    CONTRACT_CREATE = "위임계약체결"
    PAYMENT = "수임료납부"
    CONTRACT_END = "계약해지"
    LAWYER = "참여 변호사 수정"
    CONTRACT_UPDATE = "계약변경"

    # 시스템 이벤트
    CASE_CONTENT = "사건내용변경"
    CASE_STATUS = "사건상태변경"
    CASE_CLIENT_STATUS = "고객상태변경"
    SCHEDULE = "일정등록"

    ETC = "기타"


class ClientType(str, Enum):
    """고객 유형"""

    INDIVIDUAL = "개인"
    CORPORATION = "법인"


class ClientLitigantRole(str, Enum):
    """의뢰인의 소송 지위"""

    PLAINTIFF = "원고"
    DEFENDANT = "피고"
    SUSPECT = "피의자"
    ACCUSED = "피고인"
    COMPLAINANT = "고소인"
    ACCUSED_PARTY = "피고소인"
    APPLICANT = "신청인"
    APPELLANT = "피신청인"
    DEBTOR = "채권자"
    CREDITOR = "채무자"
    CLAIMANT = "청구인"
    DEFENDANT2 = "피청구인"
    DEFENDANT3 = "피고보조참가인"


class CaseHistoryBase(SchemaBase):
    """사건 이력 기본 스키마"""

    # id: Optional[int] = Field(None, description="사건 이력 ID")
    # created_at: Optional[datetime] = Field(None, description="생성 일자")

    case_id: int = Field(..., description="사건 ID")
    event_type: CaseHistoryEventType = Field(..., description="이벤트 타입")
    event_type2: CaseHistoryEventType2 = Field(..., description="이벤트 타입")
    prev_value: Optional[Dict[str, Any]] = Field(None, description="이전 값")
    curr_value: Optional[Dict[str, Any]] = Field(None, description="현재 값")

    details: Optional[str] = Field(None, description="이벤트 상세")
    result: Optional[str] = Field(None, description="결과")


class CaseHistoryResponse(CaseHistoryBase):
    """사건 이력 응답 스키마"""

    # 사건 이력 정보
    id: int = Field(..., description="사건 이력 ID")
    created_at: datetime = Field(..., description="사건 이력 생성 일자")


class TrialInfoBase(SchemaBase):
    """사건 변론기일 정보 기본 스키마"""

    case_id: Optional[int] = Field(None, description="사건 ID")
    attendee_id: Optional[int] = Field(None, description="참석자 ID")
    attendee_name: Optional[str] = Field(None, description="참석자 이름")
    trial_date: Optional[datetime] = Field(None, description="변론기일")
    trial_agency: Optional[str] = Field(None, description="관할 기관")
    trial_agency_address: Optional[str] = Field(None, description="관할 기관 주소")
    trial_agency_address_detail: Optional[str] = Field(
        None, description="관할 기관 상세 주소"
    )
    trial_agency_phone: Optional[str] = Field(None, description="관할 기관 전화번호")
    trial_agency_fax: Optional[str] = Field(None, description="관할 기관 팩스번호")
    trial_agency_email: Optional[str] = Field(None, description="관할 기관 이메일")
    trial_agency_manager: Optional[str] = Field(None, description="관할 기관 담당자")
    trial_agency_judge: Optional[str] = Field(None, description="관할 기관 판사")
    trial_result: Optional[str] = Field(None, description="판결 결과")
    trial_type: Optional[str] = Field(None, description="변론기일 종류")


class TrialInfoResponse(TrialInfoBase):
    """사건 변론기일 정보 응답 스키마"""

    id: int = Field(..., description="변론기일 ID")
    created_at: Optional[datetime] = Field(None, description="생성 일자")
    updated_at: Optional[datetime] = Field(None, description="수정 일자")


class CaseResponseForParser(SchemaBase):
    """나의 사건 정보 업데이트를 위한 사건 목록 응답 스키마"""

    case_id: int = Field(..., description="사건 ID")
    title: str = Field(..., description="사건 제목")
    case_number: str = Field(..., description="사건 번호")
    jurisdiction: str = Field(..., description="법원")
    status: CaseStatus = Field(..., description="사건 상태")
    author_id: int = Field(..., description="작성자 ID")
    firm_id: Optional[int] = Field(None, description="조직 ID")
    client_name: Optional[str] = Field(None, description="의뢰인 이름")


class CaseRelatedUsers(SchemaBase):
    """나의 사건 정보 업데이트를 위한 사건 관련 사용자 응답 스키마"""

    user_id: int = Field(..., description="사용자 ID")
    username: str = Field(..., description="사용자 이름")
    firm_id: Optional[int] = Field(None, description="소속 사무실 ID")
    dtype: Optional[str] = Field(None, description="사용자 타입")
    new_history: Optional[bool] = Field(None, description="새 이력 알림톡 수신 여부")
    new_trial: Optional[bool] = Field(None, description="새 일정 알림톡 수신 여부")

    phone: str = Field(..., description="사용자 전화번호")


class ClientBase(SchemaBase):
    """고객 기본 정보 스키마"""

    id: Optional[int] = Field(None, description="고객 ID")
    created_at: Optional[datetime] = Field(None, description="생성 일자")
    updated_at: Optional[datetime] = Field(None, description="수정 일자")
    deleted_at: Optional[datetime] = Field(None, description="삭제 일자")

    name: Optional[str] = Field(None, description="고객 이름")
    address: Optional[str] = Field(None, description="주소")
    detailed_address: Optional[str] = Field(None, description="상세 주소")
    postal_code: Optional[str] = Field(None, description="우편번호")

    referral_source: Optional[str] = Field(None, description="의뢰 출처")
    client_type: Optional[ClientType] = Field(None, description="고객 유형 (개인/법인)")

    # 개인 정보
    resident_registration_number: Optional[str] = Field(
        None, description="주민등록번호"
    )
    contact_number_1: Optional[str] = Field(None, description="연락처1")
    contact_number_2: Optional[str] = Field(None, description="연락처2")
    email: Optional[str] = Field(None, description="이메일")
    tax_invoice_email: Optional[str] = Field(None, description="세금계산서 이메일")

    # 법인 정보
    corporation_name: Optional[str] = Field(None, description="법인명")
    corporation_representative_name: Optional[str] = Field(
        None, description="법인 대표자명"
    )
    business_registration_number: Optional[str] = Field(
        None, description="사업자등록번호"
    )
    corporation_registration_number: Optional[str] = Field(
        None, description="법인등록번호"
    )
    manager_name: Optional[str] = Field(None, description="담당자명")

    lemon_user_id: Optional[int] = Field(None, description="레몬 사용자 ID")
    registering_firm_id: Optional[int] = Field(None, description="등록 조직 ID")

    litigant_role: Optional[ClientLitigantRole] = Field(
        None, description="의뢰인의 소송 지위"
    )


class ClientResponse(ClientBase):
    """고객 응답 스키마"""

    is_opponent: Optional[int] = Field(
        None, description="상대방 여부 (0: 의뢰인, 1: 상대방)"
    )
    litigant_role: Optional[ClientLitigantRole] = Field(
        None, description="의뢰인의 소송 지위"
    )
