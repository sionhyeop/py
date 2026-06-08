# -*- coding: utf-8 -*-
"""14장(예측) 실습 노트북 생성기. 슬라이드 흐름(개념 → 이미지 → 코드)을 그대로 따른다."""
import json, os

CELLS = []

def md(text):
    lines = text.split('\n')
    src = [l + '\n' for l in lines[:-1]] + [lines[-1]]
    CELLS.append({"cell_type": "markdown", "metadata": {}, "source": src})

def code(text):
    lines = text.split('\n')
    src = [l + '\n' for l in lines[:-1]] + [lines[-1]]
    CELLS.append({"cell_type": "code", "metadata": {}, "execution_count": None,
                  "outputs": [], "source": src})

def img(p, cap=None):
    cap = cap or f'강의 슬라이드 p.{p}'
    return (f'\n<div align="center">\n'
            f'<img src="images/page_{p:02d}.png" width="760" alt="강의 슬라이드 p.{p}"><br>\n'
            f'<sub>📑 {cap}</sub>\n'
            f'</div>')

# ───────────────────────── 0. 제목 & 준비 ─────────────────────────
md("""# AI데이터사이언스 14강 — 예측 (Prediction)

**2026-1학기 · ICT융합학부 컴퓨터공학트랙 · 김대환**

이 노트북은 강의자료 `AI데이터사이언스14.pdf` 의 흐름을 그대로 따라가는 **실습 파일**입니다.
원본 강의는 UC Berkeley *Data 8* 의 `datascience` 라이브러리를 사용하지만,
이 실습은 어디서나 바로 실행되도록 **numpy / pandas / matplotlib / scipy** 표준 라이브러리로 재구성했습니다.

## 목차
1. 개요 (Overview)
2. 상관 (Correlation)
3. 회귀 직선 (Regression Line)
4. 최소제곱법 (Method of Least Squares)
5. 최소제곱회귀 (Least Squares Regression)
6. 시각적 진단 (Visual Diagnostics)
7. 수치적 진단 (Numerical Diagnostics)
""" + img(1))

md("""## 0. 준비 — 라이브러리 & 헬퍼 함수

아래 셀을 **가장 먼저** 실행하세요.

데이터셋(`family_heights.csv`, `hybrid.csv`, `sat2014.csv`, `baby.csv`, `little_women.csv`, `shotput.csv`, `dugongs.csv`)은 **이 노트북과 같은 `14장` 폴더에 이미 들어 있습니다.** `load_data()` 는 ① 같은 폴더 → ② 현재 작업 폴더 → ③ (없을 때만) GitHub 다운로드 순으로 찾으므로 **인터넷 없이도 실행**됩니다.

이번 장의 핵심 헬퍼는 `standard_units`(표준단위 변환), `correlation`(상관계수 r), `slope`·`intercept`·`fit`·`residual`(회귀직선) 입니다. 모두 Data 8 강의의 정의와 동일하며, 표준편차는 `np.std`(모표준편차, ddof=0)를 사용합니다.""")

code('''import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from scipy.optimize import minimize

plt.rcParams['figure.figsize'] = (6, 4)
plt.rcParams['axes.grid'] = True
np.random.seed(14)  # 재현성 (챕터 번호로 고정)

# 이 노트북과 같은 폴더(14장)에 csv 파일들이 함께 들어 있습니다.
try:
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    DATA_DIR = os.getcwd()  # Jupyter/Colab 환경: 현재 작업 폴더
BASE_URL = 'https://raw.githubusercontent.com/data-8/materials-sp18/master/lec/'

def load_data(filename):
    """Data 8 강의 데이터셋 로드 (로컬 폴더 -> 원격 URL 순으로 시도)."""
    local_path = os.path.join(DATA_DIR, filename)
    if os.path.exists(local_path):              # ① 같은 폴더의 csv 우선 (오프라인 OK)
        return pd.read_csv(local_path)
    if os.path.exists(filename):                # ② 현재 작업 디렉터리
        return pd.read_csv(filename)
    try:
        return pd.read_csv(BASE_URL + filename)  # ③ 둘 다 없으면 GitHub에서 다운로드
    except Exception as e:
        raise RuntimeError(f'{filename} 를 불러올 수 없습니다: {e}')

def standard_units(arr):
    """표준 단위(z = (값 - 평균) / SD)로 변환. SD는 모표준편차(np.std)."""
    arr = np.asarray(arr, dtype=float)
    return (arr - np.mean(arr)) / np.std(arr)

def correlation(t, x, y):
    """표(DataFrame) t의 두 열 x, y의 상관계수 r = (표준단위 곱)의 평균."""
    return np.mean(standard_units(t[x]) * standard_units(t[y]))

def slope(t, x, y):
    """원래 단위에서 x로 y를 예측하는 회귀직선의 기울기 = r * (SD of y)/(SD of x)."""
    r = correlation(t, x, y)
    return r * np.std(t[y]) / np.std(t[x])

def intercept(t, x, y):
    """회귀직선의 절편 = (y 평균) - 기울기 * (x 평균)."""
    return np.mean(t[y]) - slope(t, x, y) * np.mean(t[x])

def fit(t, x, y):
    """각 x 값에서의 회귀직선 높이(적합 값, fitted values)를 반환."""
    a = slope(t, x, y)
    b = intercept(t, x, y)
    return a * np.asarray(t[x], dtype=float) + b

def residual(t, x, y):
    """잔차 = 관측값 y - 적합값(회귀직선 위의 예측값)."""
    return np.asarray(t[y], dtype=float) - fit(t, x, y)

print('준비 완료 ✔  (데이터 폴더:', DATA_DIR, ')')''')

# ───────────────────────── 1. 개요 ─────────────────────────
md("""---
# 1. 개요 (Overview)

**데이터로 미래를 예측한다.** 한 변수의 값으로 다른 변수의 값을 예측하는, 가장 일반적인 방법을 배웁니다.
""" + img(3))

md("""## 1.1 예제 — 부모 키로 자녀 키 예측 (934명)

영국 Galton 의 가족 키 데이터입니다. 부모의 **평균 키**(`MidParent`)로 다 자란 **자녀의 키**(`Child`)를 예측합니다.

- 원본: <https://github.com/data-8/textbook> (`family_heights.csv`)
""" + img(4))

code('''original = load_data('family_heights.csv')
# 강의와 동일하게 필요한 두 열만 골라 이름을 단순화
heights = pd.DataFrame({
    'MidParent': original['midparentHeight'],
    'Child':     original['childHeight'],
})
print('데이터 크기:', heights.shape)        # (934, 2)
heights.head()''')

code('''plt.scatter(heights['MidParent'], heights['Child'], s=8, alpha=0.4)
plt.xlabel('MidParent'); plt.ylabel('Child')
plt.title('부모 평균키 vs 자녀 키'); plt.show()''')

md("""## 1.2 수직 띠의 중심으로 예측하기

중간 부모 키가 `MidParent ± 0.5` 인치인 자녀들의 **평균 키**를 예측값으로 사용합니다.
이렇게 **수직 띠의 중심을 잇는 예측 방법**을 **회귀(Regression)** 라고 합니다.
""" + img(5))

code('''def predict_child(mp):
    """부모 평균키가 mp ± 0.5 인치인 자녀들의 평균 키를 예측값으로 반환."""
    close = heights[(heights['MidParent'] >= mp - 0.5) &
                    (heights['MidParent'] <= mp + 0.5)]
    return close['Child'].mean()

# 모든 부모 평균키에 적용
heights = heights.assign(Prediction=heights['MidParent'].apply(predict_child))

plt.scatter(heights['MidParent'], heights['Child'], s=8, alpha=0.3, label='Child')
plt.scatter(heights['MidParent'], heights['Prediction'], s=10, color='gold', label='Prediction')
plt.xlabel('MidParent'); plt.ylabel('Child'); plt.legend()
plt.title('수직 띠의 중심 = 회귀 예측'); plt.show()''')

# ───────────────────────── 2. 상관 ─────────────────────────
md("""---
# 2. 상관 (Correlation)

**선형 연관성(Linear association):** 산점도가 직선 주위에 얼마나 조밀하게 모여 있는지를 측정합니다.
""" + img(6))

md("""## 2.1 예제 — 하이브리드 차량 데이터 (1997~2013)

각 열의 의미
- `vehicle`: 모델명, `year`: 제조연도
- `msrp`: 2013년 기준 권장 소비자가(달러)
- `acceleration`: 가속 성능(km/h per second), `mpg`: 연비(miles per gallon)
- `class`: 차종
""" + img(7))

code('''hybrid = load_data('hybrid.csv')
print('데이터 크기:', hybrid.shape)
hybrid.head(10)''')

md("""## 2.2 산점도의 방향/모양으로 연관성 읽기

- **가속 vs 가격**: 양(positive)의 연관 (우상향)
- **연비 vs 가격**: 음(negative)의 연관 + 비선형(곡선)
- **SUV로 한정한 연비 vs 가격**: 음의 연관
""" + img(8))

code('''fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
axes[0].scatter(hybrid['acceleration'], hybrid['msrp'], s=10, alpha=0.5)
axes[0].set_xlabel('acceleration'); axes[0].set_ylabel('msrp'); axes[0].set_title('양(positive)의 연관')

axes[1].scatter(hybrid['mpg'], hybrid['msrp'], s=10, alpha=0.5)
axes[1].set_xlabel('mpg'); axes[1].set_ylabel('msrp'); axes[1].set_title('음(negative)+비선형')

suv = hybrid[hybrid['class'] == 'SUV']
axes[2].scatter(suv['mpg'], suv['msrp'], s=12, alpha=0.7)
axes[2].set_xlabel('mpg'); axes[2].set_ylabel('msrp'); axes[2].set_title('SUV 한정, 음의 연관')
plt.tight_layout(); plt.show()''')

md("""## 2.3 표준 단위로 변환

측정 단위에 신경 쓰지 않아도 되고, 동일한 축 척도에서 비교할 수 있습니다.
`standard_units` 로 두 축을 모두 표준단위(평균 0, SD 1)로 바꿔 봅니다.
""" + img(9))

code('''fig, axes = plt.subplots(1, 2, figsize=(10, 4))
axes[0].scatter(standard_units(suv['mpg']), standard_units(suv['msrp']), s=14)
axes[0].set_xlabel('mpg (standard units)'); axes[0].set_ylabel('msrp (standard units)')
axes[0].set_xlim(-3, 3); axes[0].set_ylim(-3, 3)

axes[1].scatter(standard_units(suv['acceleration']), standard_units(suv['msrp']), s=14)
axes[1].set_xlabel('acceleration (standard units)'); axes[1].set_ylabel('msrp (standard units)')
axes[1].set_xlim(-3, 3); axes[1].set_ylim(-3, 3)
plt.tight_layout(); plt.show()''')

md("""## 2.4 상관 계수 (Correlation coefficient)

- 두 변수 사이의 **선형** 관계의 강도를 측정, 기호 `r`
- `r` 은 항상 **-1 과 1 사이**의 값
- `r = 1`: 완벽한 우상향 직선, `r = -1`: 완벽한 우하향 직선, `r = 0`: 선형 관계 없음
""" + img(10))

md("""## 2.5 상관 계수 계산하기 (정의 따라가기)

**r 의 정의:** 두 변수를 모두 표준단위로 바꾼 뒤, **두 표준단위 곱의 평균**.

① 각 변수를 표준단위로 → ② 표준단위 쌍을 곱함 → ③ 그 곱들의 평균.
""" + img(11))

code('''x = np.arange(1, 7, 1)               # [1, 2, 3, 4, 5, 6]
y = np.array([2, 3, 1, 5, 2, 7])
t = pd.DataFrame({'x': x, 'y': y})

t_su = t.assign(**{
    'x (su)': standard_units(t['x']),
    'y (su)': standard_units(t['y']),
})
t_su = t_su.assign(**{'product of su': t_su['x (su)'] * t_su['y (su)']})
display(t_su)

r = np.mean(t_su['product of su'])   # ③ 곱들의 평균
print('r =', r)
print('correlation(t, "x", "y") =', correlation(t, 'x', 'y'))''')

md("""## 2.6 상관 계수의 성질

- `r` 은 **단위가 없는 순수한 수** (표준 단위 기반)
- 어느 축의 단위를 바꿔도 `r` 은 영향받지 않음
- **두 축을 서로 바꿔도 `r` 은 변하지 않음** — 표준단위의 곱은 어느 변수를 x/y 로 두든 동일하기 때문
""" + img(12))

code('''print('correlation(t, "x", "y") =', correlation(t, 'x', 'y'))
print('correlation(t, "y", "x") =', correlation(t, 'y', 'x'))  # 축을 바꿔도 동일''')

md("""## 2.7 `correlation` 함수와 인과의 함정

`correlation(t, x, y)` 는 표와 두 열 이름을 받아 **표준단위 곱의 평균(r)** 을 반환합니다.

- **연관은 인과가 아니다.** 상관은 오직 *연관* 만 측정하며 **인과관계를 의미하지 않습니다.**
- (예) 가격-연비는 음의 연관, 가격-가속은 양의 연관. 가격-가속의 선형 관계(약 0.5)가 가격-연비(약 -0.67)보다 조금 더 약합니다.
""" + img(13))

code('''print('가격-연비   correlation(suv, mpg, msrp)         =', correlation(suv, 'mpg', 'msrp'))
print('가격-가속   correlation(suv, acceleration, msrp) =', correlation(suv, 'acceleration', 'msrp'))''')

md("""## 2.8 상관은 **선형** 연관만 측정

강한 **비선형** 관계를 가진 변수들도 상관은 매우 낮을 수 있습니다.
아래는 완벽한 `y = x²` 관계지만 상관은 0 입니다.
""" + img(14))

code('''new_x = np.arange(-4, 4.1, 0.5)
nonlinear = pd.DataFrame({'x': new_x, 'y': new_x ** 2})
plt.scatter(nonlinear['x'], nonlinear['y'], s=30, color='r')
plt.xlabel('x'); plt.ylabel('y'); plt.title('완벽한 2차 관계'); plt.show()
print('correlation(nonlinear, "x", "y") =', round(correlation(nonlinear, 'x', 'y'), 10))''')

md("""## 2.9 상관은 **이상치(Outlier)** 에 민감

이상치 하나가 상관에 큰 영향을 줄 수 있습니다.
`r = 1` 이던 산점도에 단 하나의 이상점을 추가하자 `r = 0` 이 됩니다.
""" + img(15))

code('''line = pd.DataFrame({'x': [1, 2, 3, 4],    'y': [1, 2, 3, 4]})
outlier = pd.DataFrame({'x': [1, 2, 3, 4, 5], 'y': [1, 2, 3, 4, 0]})

fig, axes = plt.subplots(1, 2, figsize=(10, 4))
axes[0].scatter(line['x'], line['y'], s=40, color='r'); axes[0].set_title('r = %.1f' % correlation(line, 'x', 'y'))
axes[1].scatter(outlier['x'], outlier['y'], s=40, color='r'); axes[1].set_title('r = %.1f' % correlation(outlier, 'x', 'y'))
for ax in axes: ax.set_xlabel('x'); ax.set_ylabel('y')
plt.tight_layout(); plt.show()''')

md("""## 2.10 생태학적 상관은 신중히 해석

집계(aggregate)된 데이터에 기반한 상관은 오해를 부를 수 있습니다.

**예: 2014년 SAT** 의 비판적 읽기와 수학 점수 — 여기서는 **주별 평균** 데이터이므로,
실제 학생들의 데이터를 보면 상관이 낮아집니다.
""" + img(16))

code('''sat = load_data('sat2014.csv')
display(sat.head())
plt.scatter(sat['Critical Reading'], sat['Math'], s=18)
plt.xlabel('Critical Reading'); plt.ylabel('Math'); plt.title('주별 평균 SAT 점수'); plt.show()
print('correlation(sat, "Critical Reading", "Math") =', correlation(sat, 'Critical Reading', 'Math'))''')

md("""## 2.11 진지한 연구? 농담?

국가별 1인당 초콜릿 소비량과 인구 100만 명당 노벨상 수상자 수 사이의 상관(r=0.791).
**집계 데이터의 강한 상관**이 곧 인과(초콜릿을 먹으면 노벨상을 받는다)를 뜻하지 않는다는 유명한 사례입니다.
""" + img(17))

# ───────────────────────── 3. 회귀 직선 ─────────────────────────
md("""---
# 3. 회귀 직선 (Regression Line)

상관계수 `r` 은 점들이 직선 주위에 얼마나 모여 있는지를 측정할 뿐 아니라,
**점들이 모여 있는 그 직선 자체**를 찾는 데에도 쓰입니다.
""" + img(19))

md("""## 3.1 표준 단위에서 본 회귀

두 변수를 모두 **표준단위**로 측정하면, x 로 y 를 예측하는 회귀직선은 **기울기가 `r` 이고 원점을 지납니다.**
""" + img(20))

code('''heights_su = pd.DataFrame({
    'MidParent SU': standard_units(heights['MidParent']),
    'Child SU':     standard_units(heights['Child']),
})
r_heights = correlation(heights, 'MidParent', 'Child')
print('r (MidParent, Child) =', r_heights)
print('표준단위에서 회귀직선의 기울기 = r =', r_heights)
# 0.5 인치는 표준단위로 환산하면
print('0.5 인치 ≈', 0.5 / np.std(heights['MidParent']), '표준단위')''')

md("""## 3.2 표준 단위에서 직선 선별하기

표준단위 산점도 위에 세 직선을 겹쳐 봅니다.
- **45도 직선**(빨강, 기울기 1)
- **회귀직선**(초록, 기울기 r): 각 수직 띠의 중심(평균)을 지나는 직선
- `r` 은 0보다 크고 1보다 작으므로 회귀직선은 45도선보다 완만합니다.
""" + img(21))

code('''xs = np.array([-3, 3])
plt.scatter(heights_su['MidParent SU'], heights_su['Child SU'], s=8, alpha=0.3)
plt.plot(xs, xs, color='red', label='45도 직선 (기울기 1)')
plt.plot(xs, r_heights * xs, color='green', lw=2, label='회귀직선 (기울기 r)')
plt.xlabel('MidParent (SU)'); plt.ylabel('Child (SU)'); plt.legend()
plt.title('표준 단위에서의 회귀직선'); plt.show()''')

md("""## 3.3 회귀직선의 모양과 `r`

- `r` 이 1 에 가까우면 산점도·45도선·회귀직선이 모두 거의 일치
- `r` 이 중간 정도면 회귀직선이 눈에 띄게 더 완만

`r` 을 바꿔가며 (이변량 정규) 데이터를 생성해 회귀직선을 그려 봅니다.
""" + img(22))

code('''def regression_line(r, n=800):
    """상관이 r 인 이변량 정규 표본을 만들어 표준단위 산점도와 두 직선을 그림."""
    cov = [[1, r], [r, 1]]
    z = np.random.multivariate_normal([0, 0], cov, size=n)
    xs = np.array([-4, 4])
    plt.scatter(z[:, 0], z[:, 1], s=6, alpha=0.3)
    plt.plot(xs, xs, color='red', label='45도')
    plt.plot(xs, r * xs, color='green', lw=2, label='회귀직선 (기울기 r=%.2f)' % r)
    plt.xlim(-4, 4); plt.ylim(-4, 4); plt.legend(); plt.title('regression_line(%.2f)' % r); plt.show()

regression_line(0.95)
regression_line(0.60)''')

md("""## 3.4 회귀 효과 (Regression effect)

한 변수에서 평균으로부터 멀리 떨어진 개체는, 다른 변수에서는 그만큼 멀지 않을 것으로 기대됩니다.

- 주의: 회귀 효과는 **평균에 대한 진술**입니다. 부모 평균키가 1.5 표준단위인 자녀들 **전체의 평균 키**가 1.5보다 조금 작다는 뜻이지, 그 자녀들이 *모두* 1.5보다 작다는 뜻은 아닙니다.
- 자녀가 부모보다 평균에 조금 더 가까울 것으로 예측 → **평균으로의 회귀**.
""" + img(23))

md("""## 3.5 회귀직선의 방정식

x 와 y 를 표준단위로 측정하면 추정값은 `r · x` 입니다. 이를 원래 단위로 풀면:

$$\\text{기울기} = r \\cdot \\frac{\\text{SD of }y}{\\text{SD of }x}, \\qquad \\text{절편} = (\\text{y 평균}) - \\text{기울기}\\cdot(\\text{x 평균})$$

앞서 정의한 `slope`, `intercept` 함수가 바로 이 공식입니다.
""" + img(24))

code('''print('slope(heights, MidParent, Child)     =', slope(heights, 'MidParent', 'Child'))
print('intercept(heights, MidParent, Child) =', intercept(heights, 'MidParent', 'Child'))''')

md("""## 3.6 회귀직선의 단위로 본 예측

데이터의 원래 단위(인치)로 본 회귀직선:

$$\\text{자녀 키 추정값} = 0.64 \\times \\text{부모 평균키} + 22.64$$

부모 평균키가 70.48 인치이면 자녀 키는 약 67.56 인치로 예측됩니다.
""" + img(25))

code('''family_slope = slope(heights, 'MidParent', 'Child')
family_intercept = intercept(heights, 'MidParent', 'Child')
print('추정식: 자녀키 = %.2f * 부모평균키 + %.2f' % (family_slope, family_intercept))

pred_70_48 = family_slope * 70.48 + family_intercept
print('부모 평균키 70.48 → 자녀 키 예측 =', round(pred_70_48, 2))''')

md("""## 3.7 적합 값 (Fitted values)

회귀직선 위에 놓인 예측 값들을 **적합 값(fitted values)** 이라 합니다.
`fit` 함수가 각 x 에서의 회귀직선 높이를 돌려줍니다.
""" + img(26))

code('''fitted = fit(heights, 'MidParent', 'Child')
plt.scatter(heights['MidParent'], heights['Child'], s=8, alpha=0.3, label='Child')
plt.scatter(heights['MidParent'], fitted, s=8, color='gold', label='Fitted')
plt.xlabel('MidParent'); plt.ylabel('Child'); plt.legend()
plt.title('적합 값(회귀직선)'); plt.show()''')

md("""## 3.8 기울기의 측정 단위 (예제: 산모 데이터)

병원에서 출산한 산모 데이터로, **키(인치)로 임신 체중(파운드)** 을 예측합니다.

기울기는 **3.57 파운드/인치** — 키가 1인치 더 큰 두 여성의 임신 체중 예측값은 약 3.57파운드 차이가 납니다.
""" + img(27))

code('''baby = load_data('baby.csv')
a = slope(baby, 'Maternal Height', 'Maternal Pregnancy Weight')
b = intercept(baby, 'Maternal Height', 'Maternal Pregnancy Weight')
print('기울기 =', a, '파운드/인치')

xs = np.array([baby['Maternal Height'].min(), baby['Maternal Height'].max()])
plt.scatter(baby['Maternal Height'], baby['Maternal Pregnancy Weight'], s=8, alpha=0.3)
plt.plot(xs, a * xs + b, color='navy', lw=2)
plt.xlabel('Maternal Height'); plt.ylabel('Maternal Pregnancy Weight')
plt.title('키로 임신 체중 예측'); plt.show()''')

md("""## 3.9 (예제) 바셋 하운드 — 요약 통계만으로 회귀

원자료 없이 **평균·SD·상관** 만 알아도 회귀직선을 세울 수 있습니다. 관측된 `r = 0.5`.

| | average | SD |
|---|---|---|
| height | 14 inches | 2 inches |
| weight | 50 pounds | 5 pounds |

$$\\text{slope} = r\\cdot\\frac{\\text{SD of }y}{\\text{SD of }x} = \\frac{0.5\\cdot 2}{5} = 0.2,\\quad \\text{intercept} = 14 - 0.2\\cdot 50 = 4$$
""" + img(28))

code('''r_bh, sd_h, sd_w, avg_h, avg_w = 0.5, 2, 5, 14, 50
bh_slope = r_bh * sd_h / sd_w           # x=weight, y=height
bh_intercept = avg_h - bh_slope * avg_w
print('slope     =', bh_slope, 'inches per pound')
print('intercept =', bh_intercept, 'inches')
print('추정 키 = %.1f * 주어진 체중 + %.0f' % (bh_slope, bh_intercept))''')

# ───────────────────────── 4. 최소제곱법 ─────────────────────────
md("""---
# 4. 최소제곱법 (Method of Least Squares)

**최선의 직선** = 모든 직선 중 전체 오차가 가장 작은 직선.

**(예제) Little Women** — 마침표(period) 개수로 글자 수(characters)를 추정합니다.
""" + img(30))

code('''little_women = load_data('little_women.csv')
display(little_women.head(3))
plt.scatter(little_women['Periods'], little_women['Characters'], s=20, alpha=0.6)
plt.xlabel('Periods'); plt.ylabel('Characters'); plt.show()
print('correlation =', correlation(little_women, 'Periods', 'Characters'))''')

md("""## 4.1 추정의 오차 (Error in estimation)

**오차 = 실제값 - 예측값.** 점이 직선 *아래*에 있으면 오차가 음수입니다.
회귀직선으로 예측했을 때 각 점의 오차(잔차)를 살펴봅니다.
""" + img(31))

code('''lw_fitted = fit(little_women, 'Periods', 'Characters')
lw_error = little_women['Characters'].values - lw_fitted

xs = np.array([little_women['Periods'].min(), little_women['Periods'].max()])
a = slope(little_women, 'Periods', 'Characters'); b = intercept(little_women, 'Periods', 'Characters')
plt.scatter(little_women['Periods'], little_women['Characters'], s=20, alpha=0.6)
plt.plot(xs, a * xs + b, color='gold', lw=2)
plt.xlabel('Periods'); plt.ylabel('Characters'); plt.title('회귀 예측과 오차'); plt.show()

out = little_women.copy()
out['Linear Prediction'] = lw_fitted
out['Error'] = lw_error
out.head()''')

md("""## 4.2 평균 제곱 오차 (MSE) 와 RMSE

오차의 부호를 없애기 위해 **제곱**한 뒤 평균낸 것이 MSE, 그 제곱근이 RMSE 입니다.

$$\\text{MSE} = \\frac{1}{n}\\sum (y_i - \\hat{y}_i)^2, \\qquad \\text{RMSE} = \\sqrt{\\text{MSE}}$$

`RMSE` 를 최소화하는 직선이 **최선의 직선**이며, 그 직선은 유일하게 존재합니다.
""" + img(32))

code('''def lw_linear_mse(any_slope, any_intercept):
    x = little_women['Periods'].values
    y = little_women['Characters'].values
    fitted = any_slope * x + any_intercept
    return np.mean((y - fitted) ** 2)

# 회귀공식으로 구한 직선의 MSE / RMSE
mse_reg = lw_linear_mse(a, b)
print('회귀직선의 MSE  =', mse_reg)
print('회귀직선의 RMSE =', np.sqrt(mse_reg))''')

md("""## 4.3 수치적 최적화 (Numerical optimization)

`scipy.optimize.minimize` 로 MSE 를 최소화하는 (기울기, 절편) 을 **직접 탐색**합니다.
그 결과가 회귀 공식 `slope`/`intercept` 와 일치하는지 확인합니다 → **최소제곱직선 = 회귀직선**.
""" + img(33))

code('''res = minimize(lambda params: lw_linear_mse(params[0], params[1]), x0=[0, 0])
best_slope, best_intercept = res.x
print('수치 최적화: 기울기 = %.5f, 절편 = %.5f' % (best_slope, best_intercept))
print('회귀 공식:   기울기 = %.5f, 절편 = %.5f' % (a, b))''')

# ───────────────────────── 5. 최소제곱회귀 ─────────────────────────
md("""---
# 5. 최소제곱회귀 (Least Squares Regression)

산점도의 모양과 무관하게, **최소제곱직선의 기울기·절편은 §3 에서 유도한 공식과 동일**합니다.

**(예제) 포환 던지기** — 여자 대학 육상 선수 28명의 근력(Weight Lifted)과 포환던지기 거리(Shot Put Distance).
""" + img(35))

code('''shotput = load_data('shotput.csv')
display(shotput.head())
plt.scatter(shotput['Weight Lifted'], shotput['Shot Put Distance'], s=25)
plt.xlabel('Weight Lifted'); plt.ylabel('Shot Put Distance'); plt.show()
print('slope     =', slope(shotput, 'Weight Lifted', 'Shot Put Distance'))
print('intercept =', intercept(shotput, 'Weight Lifted', 'Shot Put Distance'))''')

md("""## 5.1 수치 최적화도 같은 직선을 준다

선형 MSE 를 최소화해 보면, 공식으로 구한 기울기·절편과 동일한 값이 나옵니다.
→ **산점도가 어떤 모양이든, 추정의 평균제곱오차를 최소화하는 유일한 직선이 존재합니다.**
""" + img(36))

code('''def shotput_linear_mse(any_slope, any_intercept):
    x = shotput['Weight Lifted'].values
    y = shotput['Shot Put Distance'].values
    fitted = any_slope * x + any_intercept
    return np.mean((y - fitted) ** 2)

res = minimize(lambda p: shotput_linear_mse(p[0], p[1]), x0=[0, 0])
print('수치 최적화 (기울기, 절편) =', res.x)

a = slope(shotput, 'Weight Lifted', 'Shot Put Distance')
b = intercept(shotput, 'Weight Lifted', 'Shot Put Distance')
xs = np.array([shotput['Weight Lifted'].min(), shotput['Weight Lifted'].max()])
plt.scatter(shotput['Weight Lifted'], shotput['Shot Put Distance'], s=25, label='Shot Put Distance')
plt.plot(xs, a * xs + b, color='gold', lw=2, label='Best Straight Line')
plt.xlabel('Weight Lifted'); plt.legend(); plt.show()''')

md("""## 5.2 비선형 회귀 (Nonlinear regression)

산점도가 휘어 있으면 직선보다 곡선이 더 적합합니다. 근력과 거리 사이에 **이차(quadratic)** 관계를 가정하고,
**모든 이차함수 중 최선**을 찾습니다.

$$f(x) = ax^2 + bx + c$$
""" + img(37))

code('''def shotput_quadratic_mse(a2, b2, c2):
    x = shotput['Weight Lifted'].values
    y = shotput['Shot Put Distance'].values
    fitted = a2 * x ** 2 + b2 * x + c2
    return np.mean((y - fitted) ** 2)

best = minimize(lambda p: shotput_quadratic_mse(p[0], p[1], p[2]), x0=[0, 0, 0])
print('best (a, b, c) =', best.x)

xs = np.linspace(shotput['Weight Lifted'].min(), shotput['Weight Lifted'].max(), 100)
fit_curve = best.x[0] * xs ** 2 + best.x[1] * xs + best.x[2]
plt.scatter(shotput['Weight Lifted'], shotput['Shot Put Distance'], s=25, label='Shot Put Distance')
plt.plot(xs, fit_curve, color='gold', lw=2, label='Best Quadratic Curve')
plt.xlabel('Weight Lifted'); plt.legend(); plt.show()''')

# ───────────────────────── 6. 시각적 진단 ─────────────────────────
md("""---
# 6. 시각적 진단 (Visual Diagnostics)

**잔차(Residuals) = 관측값 - 적합값 = y - (회귀직선 위의 예측값).**
점에서 회귀직선까지의 수직 거리이며, 점마다 하나씩 존재합니다.
""" + img(39))

code('''heights_res = residual(heights, 'MidParent', 'Child')
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
a = slope(heights, 'MidParent', 'Child'); b = intercept(heights, 'MidParent', 'Child')
xs = np.array([heights['MidParent'].min(), heights['MidParent'].max()])
axes[0].scatter(heights['MidParent'], heights['Child'], s=8, alpha=0.3)
axes[0].plot(xs, a * xs + b, color='gold', lw=2)
axes[0].set_xlabel('MidParent'); axes[0].set_ylabel('Child'); axes[0].set_title('회귀직선')

axes[1].scatter(heights['MidParent'], heights_res, s=8, alpha=0.3, color='r')
axes[1].axhline(0, color='navy', lw=2)
axes[1].set_xlabel('MidParent'); axes[1].set_ylabel('residual'); axes[1].set_title('Residual Plot')
plt.tight_layout(); plt.show()''')

md("""## 6.1 잔차 그림의 성질 & 비선형성 탐지

- **0을 중심으로 분포**(잔차=0 수평선 주위), **상승·하강 추세가 없음** — 모든 회귀에서 참.
- 좋은 회귀의 잔차 그림에는 **패턴이 없습니다.** 곡선 패턴이 보이면 **비선형** 신호.

**(예제) 듀공 데이터** — 나이(년)와 길이(m).
""" + img(40))

code('''dugong = load_data('dugongs.csv')
display(dugong.head())
print('correlation(dugong, Length, Age) =', correlation(dugong, 'Length', 'Age'))''')

md("""## 6.2 듀공 — 회귀 진단 그림

상관은 0.83 으로 높지만, **잔차 그림에 뚜렷한 곡선 패턴**이 나타납니다.
(길이가 작은 쪽: 잔차 양수 → 중간: 음수 → 큰 쪽: 다시 양수) → 두 변수 사이에 **비선형** 관계.
""" + img(41))

code('''def regression_diagnostic_plots(t, x, y):
    """좌: 산점도+회귀직선, 우: 잔차 그림."""
    a = slope(t, x, y); b = intercept(t, x, y)
    res = residual(t, x, y)
    xs = np.array([t[x].min(), t[x].max()])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].scatter(t[x], t[y], s=18)
    axes[0].plot(xs, a * xs + b, color='gold', lw=2)
    axes[0].set_xlabel(x); axes[0].set_ylabel(y)
    axes[1].scatter(t[x], res, s=18, color='r')
    axes[1].axhline(0, color='navy', lw=2)
    axes[1].set_xlabel(x); axes[1].set_ylabel('residuals'); axes[1].set_title('Residual Plot')
    plt.tight_layout(); plt.show()

regression_diagnostic_plots(dugong, 'Length', 'Age')''')

md("""## 6.3 이분산성 탐지 (Detecting heteroscedasticity)

**불균등한 퍼짐(uneven spread).** 하이브리드 자동차에서 연비(mpg)를 가속(acceleration)으로 회귀하면,
잔차 그림이 **가속이 낮은 쪽으로 부채꼴로 벌어집니다.** (가속이 낮을 때 오차 변동이 크고, 높을 때 작음)
""" + img(42))

code('''regression_diagnostic_plots(hybrid, 'acceleration', 'mpg')''')

# ───────────────────────── 7. 수치적 진단 ─────────────────────────
md("""---
# 7. 수치적 진단 (Numerical Diagnostics)

## 7.1 잔차엔 추세가 없고, 평균은 0

- 좋든 나쁘든 **모든 선형회귀**에서 잔차 그림은 추세가 없음 → **잔차와 예측변수는 무상관**.
- 산점도 모양과 무관하게 **잔차의 평균 = 0**.
""" + img(44))

code('''heights = heights.assign(Fitted=fit(heights, 'MidParent', 'Child'),
                         Residual=residual(heights, 'MidParent', 'Child'))
print('corr(MidParent, Residual) =', round(correlation(heights, 'MidParent', 'Residual'), 10))
print('mean(Residual)            =', round(np.mean(heights['Residual']), 10))

dugong = dugong.assign(Fitted=fit(dugong, 'Length', 'Age'),
                       Residual=residual(dugong, 'Length', 'Age'))
print('corr(Length, Residual)    =', round(correlation(dugong, 'Length', 'Residual'), 10))
print('mean(Residual)            =', round(np.mean(dugong['Residual']), 10))''')

md("""## 7.2 잔차의 표준편차

산점도 모양과 무관하게, **잔차의 SD = 반응변수 SD 의 일정 비율** $\\sqrt{1-r^2}$:

$$\\text{SD of residuals} = \\sqrt{1 - r^2}\\;\\cdot\\;\\text{SD of }y$$

| r | √(1-r²) | 잔차 SD | 의미 |
|---|---|---|---|
| ±1 | 0 | 0 | 모든 잔차 = 0, 완벽한 추정 |
| 중간값 | 진분수 | 0 ~ SD of y | 잔차 SD < y 의 SD (회귀가 도움됨) |
| 0 | 1 | SD of y | 선형회귀의 이득 없음 |
""" + img(45))

code('''r = correlation(heights, 'MidParent', 'Child')
print('np.std(Residual)              =', np.std(heights['Residual']))
print('sqrt(1 - r**2) * np.std(Child) =', np.sqrt(1 - r ** 2) * np.std(heights['Child']))

r2 = correlation(hybrid, 'acceleration', 'mpg')
hyb = hybrid.assign(Residual=residual(hybrid, 'acceleration', 'mpg'))
print()
print('np.std(Residual)               =', np.std(hyb['Residual']))
print('sqrt(1 - r**2) * np.std(mpg)    =', np.sqrt(1 - r2 ** 2) * np.std(hybrid['mpg']))''')

md("""## 7.3 `r` 의 또 다른 해석

적합 값(fitted values)의 SD 도 `y` 의 SD 의 일정 비율이며, 그 비율은 `|r|` 입니다.

$$\\frac{\\text{SD of fitted values}}{\\text{SD of }y} = |r|, \\qquad \\frac{\\text{variance of fitted values}}{\\text{variance of }y} = r^2$$
""" + img(46))

code('''r = correlation(heights, 'MidParent', 'Child')
print('|r|                                =', abs(r))
print('SD(Fitted) / SD(Child)             =', np.std(heights['Fitted']) / np.std(heights['Child']))
print()
print('r**2                               =', r ** 2)
print('Var(Fitted) / Var(Child)           =', np.var(heights['Fitted']) / np.var(heights['Child']))''')

# ───────────────────────── Q&A ─────────────────────────
md("""---
# Q & A

수고하셨습니다! 이번 장에서 다룬 내용:
1. **상관 `r`** — 두 변수의 선형 연관 강도 (표준단위 곱의 평균, -1~1, 인과 아님, 선형만, 이상치에 민감)
2. **회귀직선** — 표준단위에서 기울기 r, 원래 단위에서 `slope = r·SDy/SDx`, `intercept`
3. **최소제곱법** — MSE/RMSE 를 최소화하는 직선 = 회귀직선 (수치 최적화로 확인)
4. **진단** — 잔차 그림(비선형성·이분산성), 잔차 평균 0, 잔차 SD = √(1-r²)·SDy
""" + img(47))

# ───────────────────────── 저장 ─────────────────────────
nb = {
    "cells": CELLS,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        '14장', 'AI데이터사이언스14_실습.ipynb')
if os.path.exists(out_path):
    raise SystemExit('이미 존재: ' + out_path + ' (덮어쓰기 방지)')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print('생성 완료:', out_path)
print('셀 수:', len(CELLS),
      '(markdown', sum(c['cell_type'] == 'markdown' for c in CELLS),
      '/ code', sum(c['cell_type'] == 'code' for c in CELLS), ')')
