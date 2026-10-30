# 졸업시험 문제은행

원문 PDF의 12개 주제를 바탕으로 핵심 문항 12개와 응용 문항 12개를 구성한 오프라인 파이썬 프로그램입니다. 원문에 출처가 없는 게임 산업 수치는 검증형 문항으로 처리했습니다.

## 실행

Python 3.10 이상이 필요합니다. 추가 패키지는 필요하지 않습니다. 이 폴더에서 다음 명령을 실행하세요.

```powershell
python web_app.py --port 8080
```

브라우저에서 `http://127.0.0.1:8080/`을 여세요. 먼저 권한 페이지에서 비밀번호를 입력합니다. 전체 권한은 모든 목차와 문제은행 응시 기능을, 제한 권한은 10번까지의 해설집만 볼 수 있습니다. 화면의 `권한 변경`을 누르면 로그아웃됩니다.

전체 권한(기본 비밀번호·권한값 `1014`)에서는 영역·유형·학습 상태·검색어로 문항을 찾을 수 있습니다. `5문항 빠른 연습`이나 `무작위 출제`를 누르면 선택한 조건에서 중복 없이 문제를 뽑습니다. 답안 초안은 현재 브라우저 탭에 임시 저장됩니다. `정답 보기`로 모범답안을 확인한 뒤 0·1·2점으로 자가 채점하세요. 최근 평가가 0점 또는 1점인 문항은 상단의 `오답노트`에 자동으로 모이며, 2점으로 다시 채점하면 목록에서 빠집니다. 점수는 같은 폴더의 `progress.json`에 저장됩니다. 서버 종료는 실행한 터미널에서 `Ctrl+C`를 누르세요.

별도의 해설집은 `http://127.0.0.1:8080/explanations`에서 볼 수 있습니다. 주제별 핵심 개념, A·B 문항의 모범답안과 풀이 설명, 주의할 점을 제공하며 현재 주제를 인쇄할 수 있습니다.

기존 데스크톱 창 버전은 `python question_bank.py`로 실행할 수 있습니다.

## 터미널 사용

```powershell
python question_bank.py check
python question_bank.py list --kind 핵심
python question_bank.py list --search 파이썬
python question_bank.py quiz --count 5
python question_bank.py stats
```

`quiz`에서 `--section "V. 파이썬 실행 구조"`, `--kind 응용`, `--seed 42` 같은 조건도 사용할 수 있습니다. 데이터 파일 경로는 `--bank`, 진도 파일 경로는 `--progress`로 바꿀 수 있습니다.

## 파일

- `question_bank.py`: GUI 및 터미널 프로그램
- `web_app.py`, `web/index.html`: 로컬 웹 서버 및 브라우저 화면
- `web/login.html`: 권한 입력 화면
- `web/explanations.html`, `explanations.json`: 별도 해설집 화면과 해설 데이터
- `question_bank.json`: 편집 가능한 24개 문항과 모범답안
- `build_bank_data.py`: 기존 PDF 제작 원고(`make_workbook.py`)에서 JSON을 다시 생성하는 도구
- `progress.json`: 처음 채점할 때 자동 생성되는 학습 기록

문항을 고치려면 `question_bank.json`의 `question`과 `answer`를 수정하세요. `id`는 중복되지 않게 유지해야 합니다.

## Vercel

Vercel 배포는 `api/index.py`와 `vercel.json`으로 구성됩니다. 프로젝트 환경 변수 `QB_FULL_PASSWORD`는 `1014`로, `QB_LIMITED_PASSWORD`, `QB_SESSION_SECRET`도 먼저 설정하세요. `QB_SESSION_SECRET`은 길고 임의적인 문자열을 사용합니다. 배포 환경의 채점 현황은 브라우저 쿠키에 저장되므로 다른 기기와 동기화되지 않으며 로그아웃하면 사라집니다.
