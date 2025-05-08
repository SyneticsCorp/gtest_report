# GTestReport (NEW)

`gtest_report`는 Google Test XML 결과를 시각적이고 인터랙티브한 HTML 보고서로 변환해 주는 도구입니다.

## 주요 기능

- **UT, UIT, CT, CIT, SRT** 테스트 유형별 개별 보고서 생성  
- **종합 Index** (`index.html`) 생성 및 각 보고서 링크 제공  
- **병렬 처리** (`ProcessPoolExecutor`)로 빠른 보고서 생성  
- **Overall Summary**에 총 테스트 수, 실행 수, 성공/실패/스킵 비율 및 타임스탬프 제공  
- **인터랙티브 차트** (Chart.js)로 실행률, 성공률 파이 차트 시각화  
- **검색 & 필터** 기능 (실패만 보기, 테스트 이름 검색)  
- **클릭 네비게이션**: Failed Tests 목록 및 상세 섹션 간 앵커 링크  
- **유니코드/Windows 호환**: XML `timestamp` 속성 또는 파일 수정 시간 폴백  

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

## 사용방법

```bash
gtest-report <프로젝트명> <in 폴더 경로> <out 폴더 경로>
```

- `<프로젝트명>`: 보고서 헤더에 표시할 이름  
- `<in 폴더 경로>`: UT, UIT, CT, CIT, SRT 하위 폴더의 XML 파일들을 담은 디렉터리  
- `<out 폴더 경로>`: HTML 보고서 및 리소스가 생성될 디렉터리  

### 예시

```bash
gtest-report PARA in out
```

실행 후 생성:

```
out/
├─ index.html
├─ html_resources/
│  ├─ *.css, .js, .png
├─ UT_Report.html
├─ UIT_Report.html
├─ CT_Report.html
├─ CIT_Report.html
└─ SRT_Report.html
```

## 프로젝트 구조

```
gtest_report/                # 패키지 루트
├─ cli.py                    # CLI 엔트리포인트 & 병렬 제어
├─ parser.py                 # XML 파싱(TestFileResult)
├─ builder/                  # 보고서 빌드 모듈
│  ├─ utils.py               # HTML 조립, ID 생성, JSON 직렬화
│  ├─ chart_builder.py       # Chart.js 데이터 생성
│  └─ html_builder.py        # Jinja2 템플릿 렌더링
├─ templates/                # Jinja2 템플릿 파일
│  ├─ report.html            # 개별 리포트 템플릿
│  └─ index.html             # 종합 인덱스 템플릿
├─ html_resources/           # CSS, JS, 아이콘 파일
├─ setup.py                  # 패키징 설정
└─ MANIFEST.in               # 패키지 데이터 포함 설정
```

## 개발

- **코드 포맷**: `black .`  


## 제거

```bash
pip uninstall gtest_report
```

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
