from enum import Enum

################################################################
# 여기서 정의하는 알림 스키마는, 시스템에서 SSE 를 통해 사용자의 브라우저로 보내는 알림에 대한 정의이다.
################################################################


class NotificationType(str, Enum):
    """알림 유형"""

    SYSTEM = "system"  # 시스템 알림
    TODO = "todo"  # 할 일 관련 알림
    SCHEDULE = "schedule"  # 일정 관련 알림
    CASE = "case"  # 사건 관련 알림
    CONTRACT = "contract"  # 계약 관련 알림


class NotificationPriority(str, Enum):
    """알림 우선순위"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class NotificationAction(str, Enum):
    """알림 액션 유형"""

    # 시스템 관리자가 보내는 알림
    SYSTEM_INFO = "system_info"
    SYSTEM_WARNING = "system_warning"

    # 할일 관련 알림
    TODO_SHARED = "todo_shared"

    # 일정 관련 알림
    SCHEDULE_SHARED = "schedule_shared"

    # 사건 관련 알림
    CASE_CREATED = "case_created"
    CASE_ASSIGNED = "case_assigned"
    CASE_UPDATED = "case_updated"
    CASE_TRIAL_ADDED = "case_trial_added"
    CASE_TRIAL_UPDATED = "case_trial_updated"
    CASE_TRIAL_DELETED = "case_trial_deleted"

    CASE_HISTORY_ADDED = "case_history_added"

    # 사건 계약 관련 알림
    CASE_CONTRACT_ADDED = "case_contract_added"
    CASE_CONTRACT_UPDATED = "case_contract_updated"
    CASE_CONTRACT_DELETED = "case_contract_deleted"
