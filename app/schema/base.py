from pydantic import BaseModel


def snake_to_camel(s: str) -> str:
    """스네이크 케이스를 카멜 케이스로 변환"""
    parts = s.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class SchemaBase(BaseModel):
    """ERP 스키마 기본 클래스"""

    """
    SqlAlchemy 모델을 pydantic 모델로 변환할 때 사용하는 공통 설정 정의

    Pydantic 의 BaseModel 을 커스텀해서 사용할 수 있지만,
    기존 사용방법과 동일하게 사용할 수 있도록 하기 위해 별도 클래스로 정의하고
    필요한 모델에서 BaseModel 과 다중 상속 받으면 됨.

    "from_attributes" : SQLAlchemy 모델을 Pydantic 모델로 변환할 때 사용.
        Pydantic 모델에 정의되지 않은 속성을 필터링 하여 적용하지 않게 함.
        그리고 dict() 로 변환후 **kwargs 로 전달하지 않고, model_validate() 로 직접 변환할 수 있음.
        이전 버전의 orm_mode 와 동일한 기능을 함.

    "populate_by_name" : 전달 받은 데이터 속성명칭과 필드 명칭이 정확히 일치하지 않아도 매핑할 수 있도록 함.

    "alias_generator" : alias 생성을 위한 함수. 입력 뿐 아니라 출력에도 적용된다.
        프론트엔드에서는 camelCase 를 사용하고 있고, fastapi 에서는 snake_case 를 사용하고 있는데
        이걸 사용하면 각 필드에 대해서 별도로 alias 를 지정할 필요가 없어진다.
    """

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "alias_generator": snake_to_camel,
        "extra": "ignore",
    }
