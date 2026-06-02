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
├── 14장/                          # 14장 (예측 — 개요·상관)
│   ├── AI데이터사이언스14_1_실습.ipynb  # 14_1 실습 노트북 (33셀)
│   ├── family_heights.csv         # 부모-자녀 키 (Galton)
│   ├── hybrid.csv                 # 하이브리드 차량
│   ├── sat2014.csv                # 주별 SAT
│   └── images/14_1/               # AI데이터사이언스14_1.pdf 렌더링 이미지 (18p)
│
└── AI데이터사이언스(김대환)/          # 강의 자료(원본 PDF)
    ├── AI데이터사이언스01~14_1.pdf    # 챕터별 강의 PDF (14_1 등 구분자 형태 존재)
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
- 1~13장 강의 PDF 자료 정리 완료
- 13장 실습 노트북 작업 진행 중

## 다음 작업

- 13장 실습 노트북(`13장/AI데이터사이언스13_실습.ipynb`) 마무리
- 필요 시 `aidata` 브랜치를 `main`으로 병합

## 참고

- 실습 데이터(CSV)는 `13장/` 폴더 내에 위치하므로 노트북 실행 시 경로 확인 필요
