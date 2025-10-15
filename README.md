
# GTestReport (NEW)

`gtest_report`는 Google Test, PC-Lint Plus 등 다양한 테스트/정적분석 XML 결과를
**가독성 높고 인터랙티브한 HTML 리포트**로 자동 변환해 주는 도구입니다.
Jenkins 등 CI 환경에서 브랜치, 커밋, 빌드, 릴리즈 정보를 자동 반영하여
품질 지표를 시각적으로 제공합니다.

---

## 주요 기능

- **UT/UIT 테스트 리포트**: UT, UIT 두 유형의 HTML 보고서 자동 생성
- **JUnit XML 지원**: JUnit 호환 XML(기존 gtest XML 포함) 파싱
- **개선 대시보드(UI)**: Overall Summary 카드 + Test Results by Stage + “View Report” 링크
- **상세 리포트(UI)**:
  - “Test Result XMLs” 섹션
  - Failed/Skipped 목록(사유 포함)
  - Test Case / Result 2열(고정폭 85%/15%) 상세표
- **Jenkins 친화 템플릿**: 외부 스크립트 없이도 표시되는 템플릿과 리소스 자동 복사
- **3자리 콤마 표기 · 병렬 처리 · Windows/Unix 지원**

---

## 요구 사항

- Python 3.7 이상
- pip (필수)
- Git (옵션, CI 통합시)

---

## 설치

```bash
# 프로젝트 루트에서
pip install --upgrade .         # 패키지 설치
# 개발/테스트 중에는 editable(-e) 설치 추천
pip install -e .
```

---

## CLI 사용법

```bash
gtest-report <ProjectName> <InputDir> <OutputDir>     --branch <Git Branch>     --tag <Release Tag>     --commit <Commit ID>     --build <Jenkins Build#>
```

- `<ProjectName>`: 보고서 헤더 표기 이름
- `<InputDir>`: `in/unit`(UT), `in/uit`(UIT) 폴더를 가진 상위 폴더
- `<OutputDir>`: 결과 HTML·정적리소스가 출력될 폴더
- `--branch`: Git 브랜치 (예: develop)
- `--tag`: 릴리즈 태그 (예: v1.2.3)
- `--commit`: 커밋 해시
- `--build`: Jenkins 빌드 번호  
(미입력시 해당 값 생략)

### 실행 예시

```bash
gtest-report PARA in out   --branch "$GIT_BRANCH"   --tag "$GIT_TAG"   --commit "$GIT_COMMIT"   --build "$BUILD_NUMBER"
```

실행 후 생성:

```
out/
├─ index.html                  # 개선 대시보드(메인)
├─ index_compact_external.html # Compact 외부 리소스 버전(같은 데이터)
├─ html_resources/             # CSS, 아이콘 등 정적 리소스
├─ UT_Report.html              # Unit Test 상세 리포트
└─ UIT_Report.html             # Unit Integration Test 상세 리포트
```

---

## in 디렉토리 구조 안내

`<InputDir>`(예: `in/`) 폴더는 다음과 같이 **테스트 유형별 하위 디렉토리**로 구성합니다.

```
in/
├─ unit/   # Unit Test (JUnit/gtest XML)
│   ├─ ...xml
└─ uit/    # Unit Integration Test
    ├─ ...xml
```

- 각 테스트 유형 폴더에는 **JUnit 호환 XML 결과 파일**을 위치하세요. (기존 gtest XML도 지원)

### 예시

```
in/
├─ unit/
│   ├─ MyUnitTest1.xml
│   └─ MyUnitTest2.xml
└─ uit/
    └─ IntegrationTest1.xml
```

- 각 폴더가 없어도 되고, 파일이 하나도 없는 폴더는 무시됩니다.

---

## 프로젝트 구조

```
gtest_report/
├─ cli.py                    # CLI 엔트리포인트 & 병렬 처리
├─ parser.py                 # XML 파싱(TestFileResult)
├─ builder/
│  ├─ utils.py               # HTML 조립, ID 생성, JSON 직렬화
│  ├─ chart_builder.py       # 차트 데이터 생성
│  └─ html_builder.py        # Jinja2 템플릿 렌더링 (index/report)
├─ templates/
│  ├─ index.html             # 종합 인덱스 템플릿(개선 UI)
│  ├─ index_compact.html     # Compact 외부 리소스 템플릿
│  ├─ report.html            # 개별 테스트 리포트 템플릿(클래식)
│  └─ report_jenkins.html    # 개별 테스트 리포트 템플릿(개선 UI)
├─ html_resources/           # CSS, JS, 아이콘
├─ setup.py                  # 패키징
└─ MANIFEST.in               # 리소스/템플릿 포함 설정
```

---

## 개발

- **코드 스타일**: `black .`
- **정적 분석**: `flake8`, `mypy`
- **테스트**: `pytest`
- **CI/CD**: GitHub Actions, Jenkins 등과 연동 가능

---

## 제거

```bash
pip uninstall gtest_report
```

---

### **(최신 변경점 반영: 2025-10)**
- **JUnit XML 지원 + UT/UIT만 유지** (기타 테스트/모듈/정적분석 요약 제거)
- **대시보드 개선**: index.html(개선 템플릿) + index_compact_external.html 동시 생성
- **상세 리포트 개선**: Test Result XMLs, Failed/Skipped(사유) 섹션, 2열 고정폭 상세표
- **“View Report” 링크/타임스탬프 파싱 안정화**

---


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
