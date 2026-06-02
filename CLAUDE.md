# CLAUDE.md — AI 데이터사이언스 실습 자동 구성 가이드

이 저장소는 **강의 PDF → 실습용 Jupyter 노트북(.ipynb)** 변환 작업을 반복한다.
이 문서는 *어느 컴퓨터에서든* Claude Code 가 동일한 결과를 만들도록 하는 **작업 규약**이다.
새 챕터를 요청받으면 아래 절차와 규칙을 그대로 따른다.

---

## 0. 한 줄 요약

> "강의 PDF 를 주면 → 페이지를 이미지로 떠서 읽고 → 표준 라이브러리 기반 실습 노트북을 만들고
> → 필요한 데이터(CSV)와 슬라이드 이미지를 **자동으로 내려받아 폴더에 함께 첨부**한다.
> 같은 챕터에 PDF 가 여러 개여도 **서로 덮어쓰지 않게** 이름으로 구분한다."

---

## 1. 폴더 · 파일 이름 규칙 (가장 중요 — 덮어쓰기 방지)

PDF 파일명은 `AI데이터사이언스<챕터><구분>.pdf` 형식이다. 예: `AI데이터사이언스14_1.pdf`.

| PDF 이름 | 챕터 폴더 | 노트북 파일 | 이미지 폴더 |
|---|---|---|---|
| `AI데이터사이언스13.pdf` | `13장/` | `AI데이터사이언스13_실습.ipynb` | `13장/images/` |
| `AI데이터사이언스14_1.pdf` | `14장/` | `AI데이터사이언스14_1_실습.ipynb` | `14장/images/14_1/` |
| `AI데이터사이언스14_2.pdf` | `14장/` | `AI데이터사이언스14_2_실습.ipynb` | `14장/images/14_2/` |
| `AI데이터사이언스14_보충.pdf` | `14장/` | `AI데이터사이언스14_보충_실습.ipynb` | `14장/images/14_보충/` |

규칙 요약:
1. **챕터 폴더는 번호로 공유**한다. `14_1`, `14_2`, `14_보충` 은 모두 `14장/` 안에 들어간다.
2. PDF 에 구분자(`_1`, `_2`, `_보충` …)가 있으면 **노트북 파일명과 이미지 하위폴더 이름에 그대로 반영**해 충돌을 막는다.
3. 구분자가 없는 단일 PDF(예: 13장)는 이미지를 `images/` 바로 아래(`page_XX.png`)에 둔다.
4. **기존 파일은 절대 덮어쓰지 않는다.** 노트북/이미지/CSV 가 이미 있으면 건너뛰고, 같은 이름이 필요하면 멈추고 사용자에게 확인한다.
5. CSV 같은 **데이터셋은 챕터 폴더에서 공유**한다(여러 PDF가 같은 데이터를 쓰면 중복 다운로드하지 않음).

이 규칙은 `tools/build_chapter.py` 의 `parse_chapter()` 에 코드로 구현되어 있다.

---

## 2. 작업 절차 (체크리스트)

### 단계 A — 기계적 준비 (스크립트가 자동 처리)

```bash
# 이미지 렌더링 + (선택) CSV 다운로드 + 이름 규칙 적용을 한 번에
python3 tools/build_chapter.py "AI데이터사이언스(김대환)/AI데이터사이언스14_1.pdf" \
        --csv baby.csv nba2013.csv          # 데이터셋명을 알면 같이 지정
```

- `tools/build_chapter.py` 는 **PyMuPDF / requests 가 없으면 자동 설치**를 시도하므로 다른 컴퓨터에서도 동작한다.
- 출력에 챕터 폴더 / 이미지 상대경로 / 노트북 경로 / 페이지 수가 요약된다.
- 작은 글자·코드가 안 보이면 `--zoom 3.5` 처럼 배율을 올려 다시 렌더링한다(기존 이미지는 보존되므로 필요한 페이지만 지우고 재실행).

> 환경 메모: 이 저장소의 빌드 환경에는 `pdftoppm`(poppler)이 **없다.** PDF→이미지는 반드시 **PyMuPDF(fitz)** 로 한다. 또한 빌드 셸에는 numpy/pandas 가 없을 수 있다 — 그건 *학생이 노트북을 실행할 때* 쓰는 것이지 빌드 단계에선 불필요하다.

### 단계 B — 슬라이드 읽기

- 렌더된 `page_XX.png` 들을 Read 도구로 **순서대로** 읽어 강의 흐름·코드·수식을 파악한다.
- 제목/구분용 빈 슬라이드는 노트북 셀에 넣지 않아도 되지만, 사용자가 원하면 추가한다.

### 단계 C — 노트북 작성

`tools/build_chapter.py` 는 셀 내용을 만들지 않는다. **셀은 Claude 가 슬라이드를 읽고 직접 작성**한다. 아래 §3 규약을 지킨다.

- `.ipynb` 편집은 **NotebookEdit 도구**로만 한다(일반 Edit 도구는 .ipynb 를 거부함). 편집 전 반드시 Read 를 먼저 한다.
- 셀을 직접 JSON 으로 생성할 때는 `nbformat 4.5`, `source` 는 줄 단위 리스트로 만든다.

### 단계 D — 이미지 삽입

각 섹션 설명(markdown 셀) **끝에** 해당 슬라이드 이미지를 상대경로로 붙인다. §4 의 HTML 블록을 그대로 쓴다.

### 단계 E — 검증

- 노트북 JSON 유효성(셀 수, 파싱) 확인.
- 참조한 모든 `page_XX.png` 가 실제로 존재하는지 확인(누락 0건).
- CSV 가 노트북이 기대하는 컬럼을 갖는지 간단히 확인.
- `HANDOFF.md` 의 진행 상황/구조를 갱신한다.

---

## 3. 노트북 작성 규약

원본 강의는 UC Berkeley **Data 8** 의 `datascience` 라이브러리를 쓰지만, 실습 노트북은
**어디서나 실행되도록 `numpy / pandas / matplotlib / scipy` 표준 라이브러리로 재구성**한다.

### 첫 markdown 셀 (제목)
- 제목 `# AI데이터사이언스 N강 — <주제>`, 학기/학부/교수명, 출처 PDF 파일명, 목차.

### 두 번째 셀 묶음 (준비 — 라이브러리 & 헬퍼)
아래 **로컬 우선 → 원격 폴백** 데이터 로더를 표준으로 사용한다(오프라인에서도 실행됨).
`DATA_DIR` 덕분에 노트북 위치(챕터 폴더)에서 CSV 를 먼저 찾고, 없으면 GitHub 에서 받는다.

```python
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

plt.rcParams['figure.figsize'] = (6, 4)
plt.rcParams['axes.grid'] = True
np.random.seed(13)  # 재현성 (챕터 번호 등으로 고정)

try:
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    DATA_DIR = os.getcwd()  # Jupyter/Colab: 현재 작업 폴더
BASE_URL = 'https://raw.githubusercontent.com/data-8/materials-sp18/master/lec/'

def load_data(filename):
    """Data 8 데이터셋 로드 (① 같은 폴더 → ② 작업 폴더 → ③ GitHub 다운로드)."""
    local_path = os.path.join(DATA_DIR, filename)
    if os.path.exists(local_path):
        return pd.read_csv(local_path)
    if os.path.exists(filename):
        return pd.read_csv(filename)
    try:
        return pd.read_csv(BASE_URL + filename)
    except Exception as e:
        raise RuntimeError(f'{filename} 를 불러올 수 없습니다: {e}')
```

- 통계 실습에 자주 쓰는 헬퍼(`percentile`, `standard_units`, `hist_percent` 등)는
  `13장/AI데이터사이언스13_실습.ipynb` 의 준비 셀을 참고해 동일 스타일로 둔다.
- 본문은 **(개념 설명 markdown → 슬라이드 이미지 → 실행 코드)** 흐름을 섹션마다 반복한다.

---

## 4. 이미지 삽입 형식 (폴더 분리 방식)

base64 임베드 대신 **상대경로 참조**를 쓴다(노트북 용량↓, 폴더째 옮기면 그대로 보임).
markdown 셀 끝에 아래 블록을 붙인다. `<상대경로>` 는 노트북 기준 이미지 폴더 경로다.

- 단일 PDF(13장): `images/page_01.png`
- 다중 PDF(14_1): `images/14_1/page_01.png`

```html
<div align="center">
<img src="<상대경로>/page_XX.png" width="760" alt="강의 슬라이드 p.X"><br>
<sub>📑 강의 슬라이드 p.X</sub>
</div>
```

⚠️ 상대경로이므로 **챕터 폴더(`14장/`)를 통째로 옮겨야** 이미지가 깨지지 않는다.

---

## 5. 데이터셋 (CSV)

- 출처: `https://raw.githubusercontent.com/data-8/materials-sp18/master/lec/<파일명>`
- 다운로드는 `tools/build_chapter.py --csv <파일들>` 로 하거나, 노트북 실행 시 `load_data()` 가 자동 처리.
- 자주 쓰는 파일: `san_francisco_2015.csv`, `nba2013.csv`, `baby.csv`, `united_summer2015.csv`.
- **이미 받은 CSV 는 다시 받지 않는다**(스크립트가 존재 시 건너뜀).

---

## 6. 참고 — 기존 산출물(따라 만들 표준)

- `13장/` : 완성 예시. `AI데이터사이언스13_실습.ipynb`(50셀) + `images/page_XX.png`(25장) + CSV 4종.
- `HANDOFF.md` : 저장소 개요·진행 상황. 작업 후 갱신.
- `tools/build_chapter.py` : 이미지 렌더링 / CSV 다운로드 / 이름 규칙 자동화 스크립트.

## 7. 커밋 규칙

- 기존 커밋 스타일을 따른다: `feat : ...`, `docs : ...` (예: `feat : 14장 실습폴더 생성`).
- 작업 브랜치는 `aidata`. 사용자가 요청할 때만 커밋/푸시한다.
