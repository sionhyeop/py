# HANDOFF

AI 데이터사이언스 수업 자료 및 실습 저장소 인수인계 문서.

## 저장소 개요

- **Repository**: https://github.com/sionhyeop/py.git
- **현재 브랜치**: `aidata` (origin/aidata와 동기화됨)
- **주 브랜치**: `main`

## 디렉터리 구조

```
.
├── CLAUDE.md                      # ★ PDF→실습노트북 자동 구성 작업 규약 (다른 PC에서도 동일 동작)
├── tools/
│   └── build_chapter.py           # PDF→이미지 렌더링 + CSV 다운로드 + 이름규칙 자동화
├── 13장/                          # 13장 실습 폴더 (완성 예시)
│   ├── AI데이터사이언스13_실습.ipynb   # 실습 노트북
│   ├── baby.csv                   # 실습 데이터셋
│   ├── nba2013.csv
│   ├── san_francisco_2015.csv
│   ├── united_summer2015.csv
│   └── images/                    # 강의 자료 페이지 이미지 (page_XX.png)
│
├── 14장/                          # 14장 (예측 — 상관·회귀·최소제곱·진단)
│   ├── AI데이터사이언스14_실습.ipynb   # 실습 노트북 (77셀, md42/code35)
│   ├── family_heights.csv         # 부모-자녀 키 (Galton)
│   ├── hybrid.csv                 # 하이브리드 차량
│   ├── sat2014.csv                # 주별 SAT
│   ├── baby.csv                   # 산모 데이터
│   ├── little_women.csv           # Little Women (마침표/글자수)
│   ├── shotput.csv                # 포환던지기
│   ├── dugongs.csv                # 듀공 (나이/길이)
│   └── images/                    # AI데이터사이언스14.pdf 렌더링 이미지 (47p)
│
├── 15장/                          # 15장 (회귀를 위한 추론)
│   ├── AI데이터사이언스15_실습.ipynb   # 실습 노트북 (24셀, md14/code10)
│   ├── baby.csv                   # 산모-신생아 데이터
│   └── images/                    # AI데이터사이언스15.pdf 렌더링 이미지 (20p)
│
└── AI데이터사이언스(김대환)/          # 강의 자료(원본 PDF)
    ├── AI데이터사이언스01~15.pdf      # 챕터별 강의 PDF
    └── 중간고사.txt
```

## 새 챕터 추가 방법

`CLAUDE.md` 의 절차를 따른다. 핵심만:

```bash
python3 tools/build_chapter.py "AI데이터사이언스(김대환)/AI데이터사이언스14_1.pdf" --csv <필요한CSV...>
```

- 같은 챕터에 PDF 가 여러 개(`14_1`, `14_2`, `14_보충` …)면 **한 `14장/` 폴더**에 두되,
  노트북 파일명·이미지 하위폴더를 PDF 이름으로 구분해 **덮어쓰지 않는다.**
- 이후 슬라이드 이미지를 읽고 노트북 셀을 작성한다(`CLAUDE.md §3` 규약).

## 진행 상황

- 13장 실습 폴더 및 데이터셋(`baby.csv`, `nba2013.csv`, `san_francisco_2015.csv`, `united_summer2015.csv`) 구성 완료
- 13장 실습 노트북 완성
- **14장(예측) 실습 노트북 완성** — 상관 → 회귀직선 → 최소제곱법 → 최소제곱회귀 → 시각적/수치적 진단.
  데이터셋 7종 구성, `jupyter nbconvert --execute` 전체 실행 검증 완료(출력은 비운 상태로 배포).
  생성기는 `tools/build_nb14.py` (재현용).
- **15장(회귀를 위한 추론) 실습 노트북 완성** — 회귀 모형(신호+노이즈) → `draw_and_compare` 시뮬레이션
  → 산점도 부트스트랩으로 참 기울기 신뢰구간·가설검정 → 예측 구간(`bootstrap_prediction`).
  `baby.csv` 사용, 전체 실행 검증 완료(슬라이드 수치와 일치: 기울기 0.467, CI [0.385,0.556] 등).
  생성기는 `tools/build_nb15.py`.
- 1~15장 강의 PDF 자료 정리 (14_1.pdf → 14.pdf 단일본으로 교체, 15.pdf 추가됨)

## 다음 작업

- 필요 시 `aidata` 브랜치를 `main`으로 병합

## 참고

- 실습 데이터(CSV)는 `13장/` 폴더 내에 위치하므로 노트북 실행 시 경로 확인 필요
