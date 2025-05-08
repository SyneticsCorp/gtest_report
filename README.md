# GTestReport (NEW)

`gtest_report`는 Google Test XML 결과를 시각적이고 인터랙티브한 HTML 보고서로 변환해 주는 도구입니다. Jenkins CI 환경에서 브랜치, 커밋, 빌드 번호, 릴리즈 태그를 파라미터로 받아 인덱스와 리포트 상단에 표 형태로 표시합니다.

## 주요 기능

- **UT, UIT, CT, CIT, SRT** 테스트 유형별 개별 보고서 생성  
- **종합 Index** (`index.html`) 생성 및 각 리포트 링크 제공  
- **Jenkins 통합**: 브랜치, 릴리즈 태그, 커밋 ID, 빌드 번호, 생성 일시 표시  
- **Test Stage Summary**: 각 단계(Test Stage)의 총 테스트, 실행/통과/실패/Skip(사유 유·무) 수치 표출  
- **Coverage Summary**: Execution Rate (%), Execution Rate (without Skipped) (%), Pass Rate (%) 계산 및 표출  
- **Metrics Explained**: 지표별 설명과 계산 공식을 인덱스 하단에 제공  
- **Parallel Processing** (`ProcessPoolExecutor`)으로 빠른 리포트 생성  
- **Detailed Test Summary**: 각 테스트 파일별 통계와 실패 테스트 상세 내비게이션  
- **Interactive Charts** (Chart.js): 메트릭별 파이 차트 시각화  
- **Search & Filter**: 테스트 이름 검색, 실패만 보기 토글  
- **Cross-platform**: Windows/Unix 환경 모두 지원, XML `timestamp` 또는 파일 수정시간 폴백

## 요구 사항

- Python 3.7 이상  
- `pip` 및 Git (선택)

## 설치

```bash
# 프로젝트 루트에서
pip install --upgrade .        # 패키지 설치
# 개발 중에는 editable 설치 추천
pip install -e .
```

## CLI 사용법

```bash
gtest-report <ProjectName> <InputDir> <OutputDir> \
    --branch <Git Branch> \
    --tag <Release Tag> \
    --commit <Commit ID> \
    --build <Jenkins Build#>
```

- `<ProjectName>`: 보고서 헤더에 표시할 프로젝트 이름  
- `<InputDir>`: UT, UIT, CT, CIT, SRT 하위 폴더에 위치한 XML 파일이 있는 상위 디렉터리  
- `<OutputDir>`: 생성된 HTML 보고서 및 정적 리소스가 출력될 디렉터리  
- `--branch`: Git 브랜치명 (예: develop)  
- `--tag`: Release 태그 (예: v1.2.3)  
- `--commit`: 커밋 해시  
- `--build`: Jenkins 빌드 번호

입력하지 않은 -- 옵션은 표시되지 않습니다.

### 예시

```bash
gtest-report PARA in out \
  --branch "$GIT_BRANCH" \
  --tag "$GIT_TAG" \
  --commit "$GIT_COMMIT" \
  --build "$BUILD_NUMBER"
```

실행 후 생성:

```
out/
├─ index.html             # 종합 인덱스 (Jenkins 정보, Overall Summary, Test Stage Summary, Coverage Summary, Metrics Explained)
├─ html_resources/        # CSS, JS, 아이콘
├─ UT_Report.html         # Unit Test 상세 리포트
├─ UIT_Report.html        # Unit Integration Test 리포트
├─ CT_Report.html         # Component Test 리포트
├─ CIT_Report.html        # Component Integration Test 리포트
└─ SRT_Report.html        # SW Requirement Test 리포트
```

## 프로젝트 구조

```
gtest_report/                # 패키지 모듈
├─ cli.py                    # CLI 엔트리포인트 & 병렬 제어
├─ parser.py                 # XML 파싱(TestFileResult)
├─ builder/                  # 보고서 빌드 모듈
│  ├─ utils.py               # HTML 조립, ID 생성, JSON 직렬화
│  ├─ chart_builder.py       # Coverage 데이터 준비
│  └─ html_builder.py        # Jinja2 템플릿 렌더링 (index+report)
├─ templates/                # Jinja2 템플릿
│  ├─ report.html            # 세부 리포트 템플릿
│  └─ index.html             # 종합 인덱스 템플릿
├─ html_resources/           # CSS, JS, 아이콘 파일
├─ setup.py                  # 패키징 설정
└─ MANIFEST.in               # 패키지 데이터 포함 설정
```

## 개발

- **코드 포맷**: `black .`  
- **정적 분석**: `flake8`, `mypy`  
- **테스트**: `pytest` 권장  
- **CI/CD**: GitHub Actions, Jenkins 연동 예제 스크립트 작성 가능

## 제거

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
