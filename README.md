
# GTestReport (NEW)

`gtest_report`는 Google Test, PC-Lint Plus 등 다양한 테스트/정적분석 XML 결과를
**가독성 높고 인터랙티브한 HTML 리포트**로 자동 변환해 주는 도구입니다.
Jenkins 등 CI 환경에서 브랜치, 커밋, 빌드, 릴리즈 정보를 자동 반영하여
품질 지표를 시각적으로 제공합니다.

---

## 주요 기능

- **단위/통합/시스템/요구사항 테스트 리포트**:  
  UT, UIT, CT, CIT, SRT 테스트 유형별 HTML 보고서 자동 생성
- **정적 분석 리포트**:  
  PC-Lint Plus XML(report.xml) 기반 **Static Analysis Report(SA_Report.html)** 및  
  컴포넌트별 상세 리포트 **SA_Report_*.html** 자동 생성
- **3자리 콤마(,) 표기**:  
  모든 리포트·인덱스의 주요 수치에 자릿수 구분 적용
- **Jenkins 연동**:  
  브랜치, 릴리즈 태그, 커밋, 빌드번호, 생성일시 자동 표기
- **Overall/Stage Summary**:  
  단계별 총 테스트, 실행/통과/실패/Skip(사유별) 수치 표출,  
  Execution Rate, Pass Rate 등 품질 지표 표시
- **정적분석 상세 통계**:  
  컴포넌트/Severity/Rule ID별 건수 + 컴포넌트별 상세 보고서 자동 생성
- **차트 시각화**:  
  Chart.js 기반의 파이/바 차트(테스트 메트릭, 정적분석 컴포넌트·룰ID·Severity)
- **테스트명 검색·실패만 필터**:  
  대규모 테스트에서 효율적 탐색
- **병렬 처리**:  
  대용량 결과도 빠르게 처리  
- **Windows/Unix** 양쪽 지원

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
- `<InputDir>`: UT, UIT, SCT, SCIT, SRT, SA(정적분석) 폴더를 가진 상위 폴더
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
├─ index.html              # 종합 인덱스 (Jenkins 정보, Test Stage Summary, Static Analysis Summary 등)
├─ html_resources/         # CSS, JS, 아이콘
├─ UT_Report.html          # Unit Test 상세 리포트
├─ UIT_Report.html         # Unit Integration Test 리포트
├─ CT_Report.html          # Component Test 리포트
├─ CIT_Report.html         # Component Integration Test 리포트
├─ SRT_Report.html         # SW Requirement Test 리포트
├─ SA_Report.html          # 전체 정적분석 리포트 (PC Lint Plus)
└─ SA_Report_<component>.html # 컴포넌트별 상세 리포트
```

---

## in 디렉토리 구조 안내

`<InputDir>`(예: `in/`) 폴더는 다음과 같이 **테스트 유형별 하위 디렉토리**와  
정적분석(PC-Lint Plus)의 경우 **SA 폴더 하위에 반드시 `report.xml` 파일**이 위치해야 합니다.

```
in/
├─ UT/           # Unit Test       (예: gtest xml)
│   ├─ ...xml
├─ UIT/          # Unit Integration Test
│   ├─ ...xml
├─ SCT/          # Component Test
│   ├─ ...xml
├─ SCIT/         # Component Integration Test
│   ├─ ...xml
├─ SRT/          # SW Requirement Test
│   ├─ ...xml
└─ SA/           # Static Analysis (PC-Lint Plus)
    └─ report.xml   # 반드시 SA 폴더 하위에 위치해야 함!
```

- 각 테스트 유형 폴더(UT, UIT, SCT, SCIT, SRT)에는  
  **Google Test 등에서 생성된 XML 결과 파일**이 위치해야 합니다.  
- **정적분석 리포트 생성을 위해서는 `SA/report.xml` 파일이 반드시 필요합니다.**

### 예시

```
in/
├─ UT/
│   ├─ MyUnitTest1.xml
│   └─ MyUnitTest2.xml
├─ UIT/
│   └─ IntegrationTest1.xml
├─ SCT/
│   └─ ComponentTest.xml
├─ SCIT/
│   └─ ComponentIntegrationTest.xml
├─ SRT/
│   └─ RequirementTest.xml
└─ SA/
    └─ report.xml
```

- 각 폴더가 없어도 되고, 파일이 하나도 없는 폴더는 무시됩니다.
- **SA/report.xml** 파일이 없으면 정적 분석 리포트가 생성되지 않습니다.

---

## 프로젝트 구조

```
gtest_report/
├─ cli.py                    # CLI 엔트리포인트 & 병렬 처리
├─ parser.py                 # XML 파싱(TestFileResult)
├─ builder/
│  ├─ utils.py               # HTML 조립, ID 생성, JSON 직렬화
│  ├─ chart_builder.py       # 차트 데이터 생성
│  └─ html_builder.py        # Jinja2 템플릿 렌더링 (index/report/SA)
├─ sa_component_report_generator.py # 정적분석 컴포넌트별 리포트 생성
├─ templates/
│  ├─ index.html             # 종합 인덱스 템플릿
│  ├─ report.html            # 개별 테스트 리포트 템플릿
│  └─ sa_report.html         # 전체 정적분석 템플릿
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

### **(최신 변경점 반영: 2025-05)**
- **정적분석(PC Lint Plus) 지원/SA 보고서 자동생성**
- **모든 리포트/통계 숫자 3자리 콤마 표기**
- **템플릿 및 차트 구조 최신화**

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
