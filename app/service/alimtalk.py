import httpx
import logging

logger = logging.getLogger(__name__)

NOTIFICATION_TEMPLATE_MAP = {
    # 대법원 나의 사건 정보 이력 업데이트
    "CASE_NEW_HISTORY": {
        "template_code": "CASE_NEW_HISTORY",
        "required_parameters": [
            "사건명",
            "사건번호",
            "이력건수",
        ],
    },
    # 대법원 나의 사건 정보 변론기일 업데이트
    "CASE_NEW_TRIAL": {
        "template_code": "CASE_NEW_TRIAL",
        "required_parameters": [
            "사건명",
            "사건번호",
            "날짜",
            "장소",
            "기일구분",  # trial_type
        ],
    },
}


class AlimTalkService:
    def __init__(self, api_url, secret_key, app_key, sender_key):
        self.api_url = api_url
        self.secret_key = secret_key
        self.app_key = app_key
        self.sender_key = sender_key

    async def send_message(
        self, template_code: str, recipient_no: str, template_parameters: dict
    ):
        """
        알림톡 메시지를 보내는 공통 메소드
        """

        # 템플릿 코드가 존재하는가?
        if template_code not in NOTIFICATION_TEMPLATE_MAP:
            logger.error(f"템플릿 코드 {template_code}가 존재하지 않습니다.")
            return None

        # 템플릿 코드에 필요한 필수 파라미터가 존재하는가?
        required_parameters = NOTIFICATION_TEMPLATE_MAP[template_code][
            "required_parameters"
        ]
        for param in required_parameters:
            if param not in template_parameters:
                logger.error(
                    f"템플릿 코드 {template_code}에 필수 파라미터 {param}가 없습니다."
                )
                return None

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "X-Secret-Key": self.secret_key,
        }

        data = {
            "senderKey": self.sender_key,
            "templateCode": template_code,
            "recipientList": [
                {
                    "recipientNo": recipient_no,
                    "templateParameter": template_parameters,
                }
            ],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/appkeys/{self.app_key}/messages",
                headers=headers,
                json=data,
            )

            if response.status_code == 200:
                logger.info(f"알림톡 메시지 전송 성공: {response.json()}")
                return response.json()
            else:
                logger.error(f"알림톡 메시지 전송 실패: {response.json()}")
                return None
                # response.raise_for_status()
