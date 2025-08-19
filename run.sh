#!/bin/bash

##########################################################################
# 파일 설명: run.sh
#   실제 서비스가 구동되는 ec2 에서 service 를 사용하여 실행할 때 호출하는 스크립트입니다.
#   여기서는 별도의 venv 를 구성하지 않았으므로 global 로 설정된 python 을 사용하면 됩니다.
#
# 서비스 실행 방법
#   $ sudo systemctl start scourt-scheduler
#   $ sudo systemctl stop scourt-scheduler
#   $ sudo systemctl restart scourt-scheduler
# 
# 서비스 관련 스크립트는 아래 경로 파일을 참고하세요.
#   /etc/systemd/system/scourt-scheduler.service
##########################################################################

# pyenv의 경로와 환경 변수를 설정합니다.
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH"

# uvicorn으로 FastAPI 앱을 실행합니다.
uvicorn app.main:app --host 0.0.0.0 --port 5001