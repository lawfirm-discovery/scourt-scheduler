# scourt-scheduler

대법원 나의 사건 검색에서 사건 정보를 파싱하는 스케줄러입니다.

업데이트 : 2025-08-19, ykchoi

## 주요 기능

1. 주기적으로 사건 정보를 불러와서 파싱하고 DB 에 업데이트 합니다.
2. 사건 관계자(전문가 및 조직 소송 구성원)에게 알림톡을 발송합니다.

스케줄 동작이 주된 기능이지만, 추후 api 기능을 위해 fastapi 를 추가 구성하였습니다.

\*\* 참고로 여기 사용되는 코드는 ERP 에서 작성하였던 코드를 거의 그대로 가져왔기 때문에  
약간의 불필요한 내용이 있을 수 있습니다.

## 서버 접속 정보

- 서버 : AWS EC2 (t3.micro, 2vCPU, 1GB RAM)
- IP : ec2-13-125-190-73.ap-northeast-2.compute.amazonaws.com (가변)
- SSH : 포트 2222, key 는 lawfirm-discovery.pem 파일을 사용

## 서비스 구성

이 서비스는 스케줄러만 동작하고, 실제 html 파싱하는 작업은 https://test.legalmonster.co.kr/parse_case 로 호출합니다.
테스트 서버에 GPU 가 있어 캡차 해결이 더 빠르기 때문에 ec2 에서 직접하지 않습니다.

또한 혹시 모를 ip 차단을 해결하기 위해 가변 IP 로 구성하였으므로,
IP 가 차단되는 경우 ec2 인스턴스를 재시작하여 새로운 ip 를 할당 받으시기 바랍니다.

## `.env` 구성요소

.env 파일은 다음의 구성요소를 포함해야 합니다.

```ini
ENV=development
DEBUG=true

DB_USER=
DB_PW=
DB_HOST=
DATABASE=

KAKAO_NOTI_API_URL=
KAKAO_NOTI_SECRET_KEY=
KAKAO_NOTI_APP_KEY=
KAKAO_NOTI_SENDER_KEY=
```
