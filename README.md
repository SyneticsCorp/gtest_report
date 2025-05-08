# GTestReport (NEW)

이 가이드에서는 `gtest_report` 저장소를 처음 받아 설치하고 실행하는 방법을 설명합니다.

## Prerequisites

- Python 3.7 이상
- Git (옵션)
- `pip` (Python 패키지 관리자)

## 1. 저장소 복제(Clone)

GitHub 등에 호스팅된 저장소인 경우:

```bash
git clone <REPO_URL>
cd gtest_report
```

로컬에 압축 등으로 제공된 경우, 압축 해제 후 해당 디렉터리로 이동합니다.

## 2. 의존성 설치(Install Dependencies)

### 방법 A: 패키지로 설치

```bash
pip install --upgrade .
```

### 방법 B: requirements.txt 사용

```bash
pip install -r requirements.txt
```

이 명령은 다음 패키지를 자동으로 설치합니다:

- Jinja2 (템플릿 렌더링)
- matplotlib (차트 생성)

## 3. CLI 실행(Usage)

설치 후 `gtest-report` 명령을 사용해 보고서를 생성합니다:

```bash
gtest-report <프로젝트명> <in 폴더 경로> <out 폴더 경로>
```

- `<프로젝트명>`: 보고서에 표시할 프로젝트 이름
- `<in 폴더 경로>`: XML 파일들이 들어 있는 상위 디렉터리 (UT, UIT, CT, CIT, SRT 하위 폴더 포함)
- `<out 폴더 경로>`: 생성된 HTML 보고서 및 리소스를 저장할 디렉터리

### 예제

```bash
gtest-report PARA in out
```

위 명령을 실행하면:

- `out/index.html`: 종합 인덱스 페이지
- `out/UT_Report.html`, `out/UIT_Report.html` 등: 각 테스트 유형별 보고서
- `out/html_resources/`: 아이콘, CSS, JS, 차트 이미지 등 정적 리소스

## 4. 저장소 구조(Repository Structure)

```
gtest_report/
├── gtest_report/            # 패키지 모듈
│   ├── cli.py               # CLI 엔트리포인트
│   ├── generator.py         # HTML 보고서 생성 로직
│   ├── parser.py            # XML 파싱 로직
│   ├── templates/           # Jinja2 템플릿 파일 (report.html, index.html)
│   └── html_resources/      # 아이콘, CSS, JS 파일
├── requirements.txt         # 의존성 목록
├── setup.py                 # 패키징 설정
├── MANIFEST.in              # 패키지 포함 파일 설정
└── README.md                # 프로젝트 소개 및 참고 문서
```

## 5. 제거(Uninstall)

```bash
pip uninstall gtest_report
```

---
# 기존 설명
Pyton 2.* script which generate rather simple HTML output in "out/"directory based on xml gtests repors from "in/" directory.
Clone it and use "generate.(sh|bat)" as startup script. Script was tested with xml output format from gtest-1.7.0.

* Shows in html format status of different tests (failed, succeeded, disabled)
* Shows outline info per each report
* If you give >2 google test xml report then it highlight min and max execution time per test
* If you append custom things into your xml gtest output via "::testing::Test::RecordProperty(key, value);" then this custom fields can be observed in generated report

Screenshot of html report is "screenshot_of_html_report.png"

// Copyright (c) 2016, Konstantin Burlachenko (burlachenkok@gmail.com).  All rights reserved.
