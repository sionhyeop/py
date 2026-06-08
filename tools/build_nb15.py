# -*- coding: utf-8 -*-
"""15장(회귀를 위한 추론) 실습 노트북 생성기. 슬라이드 흐름(개념→이미지→코드)을 따른다."""
import json, os

CELLS = []

def md(text):
    lines = text.split('\n')
    CELLS.append({"cell_type": "markdown", "metadata": {},
                  "source": [l + '\n' for l in lines[:-1]] + [lines[-1]]})

def code(text):
    lines = text.split('\n')
    CELLS.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                  "source": [l + '\n' for l in lines[:-1]] + [lines[-1]]})

def img(p, cap=None):
    cap = cap or f'강의 슬라이드 p.{p}'
    return (f'\n<div align="center">\n'
            f'<img src="images/page_{p:02d}.png" width="760" alt="강의 슬라이드 p.{p}"><br>\n'
            f'<sub>📑 {cap}</sub>\n'
            f'</div>')

# ───────────────────────── 0. 제목 & 준비 ─────────────────────────
md("""# AI데이터사이언스 15강 — 회귀를 위한 추론 (Inference for Regression)

**2026-1학기 · ICT융합학부 컴퓨터공학트랙 · 김대환**

이 노트북은 강의자료 `AI데이터사이언스15.pdf` 의 흐름을 그대로 따라가는 **실습 파일**입니다.
원본 강의는 UC Berkeley *Data 8* 의 `datascience` 라이브러리를 사용하지만,
이 실습은 어디서나 바로 실행되도록 **numpy / pandas / matplotlib / scipy** 표준 라이브러리로 재구성했습니다.

14강(예측)에서 배운 **회귀직선**을, 이번에는 **추론(inference)** 의 관점에서 다룹니다.
표본으로 그린 회귀선이 보이지 않는 **참 직선(true line)** 을 얼마나 잘 추정하는지,
그리고 **부트스트랩(bootstrap)** 으로 참 기울기의 신뢰구간과 예측구간을 어떻게 구하는지 배웁니다.

## 목차
1. 개요 (Overview)
2. 회귀 모형 (Regression Model)
3. 참 기울기를 위한 추론 (Inference for the True Slope)
4. 예측 구간 (Prediction Intervals)
""" + img(1))

md("""## 0. 준비 — 라이브러리 & 헬퍼 함수

아래 셀을 **가장 먼저** 실행하세요. 데이터셋 `baby.csv` 는 **이 노트북과 같은 `15장` 폴더에 들어 있습니다**(오프라인 실행 가능).

이번 장의 헬퍼:
- 14강과 동일한 `standard_units`, `correlation`, `slope`, `intercept`, `fit`
- 새 함수 `fitted_value`(특정 x 에서의 예측값), `bootstrap_slope`(기울기 부트스트랩 분포), `bootstrap_prediction`(예측값 부트스트랩 분포)""")

code('''import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams['figure.figsize'] = (6, 4)
plt.rcParams['axes.grid'] = True
np.random.seed(15)  # 재현성 (챕터 번호로 고정)

try:
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    DATA_DIR = os.getcwd()  # Jupyter/Colab: 현재 작업 폴더
BASE_URL = 'https://raw.githubusercontent.com/data-8/materials-sp18/master/lec/'

def load_data(filename):
    """Data 8 강의 데이터셋 로드 (로컬 폴더 -> 원격 URL 순으로 시도)."""
    local_path = os.path.join(DATA_DIR, filename)
    if os.path.exists(local_path):
        return pd.read_csv(local_path)
    if os.path.exists(filename):
        return pd.read_csv(filename)
    try:
        return pd.read_csv(BASE_URL + filename)
    except Exception as e:
        raise RuntimeError(f'{filename} 를 불러올 수 없습니다: {e}')

def standard_units(arr):
    arr = np.asarray(arr, dtype=float)
    return (arr - np.mean(arr)) / np.std(arr)

def correlation(t, x, y):
    return np.mean(standard_units(t[x]) * standard_units(t[y]))

def slope(t, x, y):
    return correlation(t, x, y) * np.std(t[y]) / np.std(t[x])

def intercept(t, x, y):
    return np.mean(t[y]) - slope(t, x, y) * np.mean(t[x])

def fit(t, x, y):
    return slope(t, x, y) * np.asarray(t[x], dtype=float) + intercept(t, x, y)

def fitted_value(t, x, y, given_x):
    """회귀직선 위에서 x = given_x 일 때의 예측값(적합값)."""
    return slope(t, x, y) * given_x + intercept(t, x, y)

print('준비 완료 ✔  (데이터 폴더:', DATA_DIR, ')')''')

# ───────────────────────── 1. 개요 ─────────────────────────
md("""---
# 1. 개요 (Overview)

## 회귀 모델(Regression Model)이란?

추론적 사고는 항상 **데이터에 대한 가정(모델)** 을 먼저 검토하는 데서 시작합니다.
선형적으로 보이는 산점도의 **무작위성에 대한 가정들의 집합**이 곧 **회귀 모델**입니다.

- **진짜 선(True Line):** 실제로는 볼 수 없는 모집단의 숨겨진 선형 관계
- **오차(Error):** 평균 0, 정규분포를 따르는 무작위 노이즈 → 점들이 선에서 위아래로 흩어짐

## 회귀선은 진짜 선의 추정값

- 우리가 실제로 보는 것은 **표본 데이터뿐** → 회귀선으로 진짜 선을 추정
- 표본 크기가 클수록 회귀선이 진짜 선에 더 가까워짐

## 진짜 기울기 추정: 부트스트랩(Bootstrap)

- 원래 표본에서 **복원 추출**을 반복 → 각 부트스트랩 표본마다 회귀선 기울기 계산
- 기울기들의 분포로 **95% 신뢰구간** 계산 → 진짜 기울기가 0인지(관계 없음) 검정 가능
""" + img(4))

# ───────────────────────── 2. 회귀 모형 ─────────────────────────
md("""---
# 2. 회귀 모형 (Regression Model)

## 2.1 회귀 모델의 핵심 아이디어

- 두 변수 사이의 **진짜 관계는 완벽한 직선(신호, Signal)** → 우리 눈에는 보이지 않음
- 직선 주변에 흩어진 점들 → 각 점은 (직선 위의 값) + **무작위 노이즈(Noise)** 로 오염
- **(추론 목표) 노이즈 속에서 신호(진짜 선)를 분리해 내는 것**

**산점도 데이터의 무작위 생성 과정 (모델 가정)**
1. 각 x 에 대해 진짜 직선 위의 점을 찾음
2. **오차(Error)** 를 더함 → 평균 0 인 정규분포에서 무작위로 추출
3. 실제 데이터 포인트 = (x, 진짜 선의 y값 + 오차) → 선의 위아래로 흩어짐
4. 진짜 선은 지움 → 우리가 관측하는 것은 **점들뿐!**
""" + img(6))

md("""## 2.2 시뮬레이션 — 회귀선 vs 진짜 선

`draw_and_compare(참기울기, 참절편, 표본크기)` 로 모델의 데이터 생성 과정을 재현합니다.
1. **진짜 선** 생성 → 2. 오차를 더해 **점** 생성 → 3. 점만 남기고 진짜 선은 숨김 → 4. 점으로 **회귀선**을 구해 진짜 선과 비교.

**표본 크기가 클수록** 회귀선(초록)이 진짜 선(파랑)의 좋은 근삿값이 됩니다.
""" + img(7))

code('''def draw_and_compare(true_slope, true_int, sample_size):
    # 1) 진짜 선 위의 점들을 만들고, 평균 0 정규 오차를 더해 데이터 생성
    x = np.random.normal(50, 5, sample_size)
    xlims = np.array([x.min(), x.max()])
    errors = np.random.normal(0, 6, sample_size)
    y = true_slope * x + true_int + errors
    sample = pd.DataFrame({'x': x, 'y': y})

    # 표본으로 구한 회귀선
    a = slope(sample, 'x', 'y'); b = intercept(sample, 'x', 'y')

    fig, axes = plt.subplots(1, 4, figsize=(16, 3.6))
    # ① 진짜 선 + 점
    axes[0].scatter(x, y, s=10, alpha=0.5)
    axes[0].plot(xlims, true_slope * xlims + true_int, color='blue', lw=2)
    axes[0].set_title('True Line, and Points Created')
    # ② 우리가 보는 것 (점만)
    axes[1].scatter(x, y, s=10, alpha=0.5)
    axes[1].set_title('What We Get to See')
    # ③ 회귀선 추정
    axes[2].scatter(x, y, s=10, alpha=0.5)
    axes[2].plot(xlims, a * xlims + b, color='green', lw=2)
    axes[2].set_title('Regression Line: Estimate of True Line')
    # ④ 두 선 비교
    axes[3].plot(xlims, true_slope * xlims + true_int, color='blue', lw=2, label='True')
    axes[3].plot(xlims, a * xlims + b, color='green', lw=2, label='Regression')
    axes[3].legend(); axes[3].set_title('Regression Line and True Line')
    plt.tight_layout(); plt.show()
    print('참 기울기 = %.2f / 회귀 추정 기울기 = %.3f' % (true_slope, a))

draw_and_compare(2, -5, 25)    # 작은 표본
draw_and_compare(2, -5, 200)   # 큰 표본 → 회귀선이 진짜 선에 더 가까움''')

# ───────────────────────── 3. 참 기울기 추론 ─────────────────────────
md("""---
# 3. 참 기울기를 위한 추론 (Inference for the True Slope)

## 3.1 진짜 기울기(True Slope) 추정

회귀 모델 성립시 큰 n 에서 **회귀선 ≈ 진짜 선** → 진짜 기울기를 추정할 수 있습니다.

**(예제) 산모와 신생아 표본** — 출생체중(`Birth Weight`) vs 임신기간(`Gestational Days`).
직선 주변에 점들이 비교적 고르게 분포 → 회귀 모델이 타당해 보입니다.
""" + img(9))

code('''baby = load_data('baby.csv')
print('데이터 크기:', baby.shape)

a = slope(baby, 'Gestational Days', 'Birth Weight')
b = intercept(baby, 'Gestational Days', 'Birth Weight')
print('상관계수 r =', correlation(baby, 'Gestational Days', 'Birth Weight'))
print('회귀선 기울기 = %.3f 온스/일' % a)

xs = np.array([baby['Gestational Days'].min(), baby['Gestational Days'].max()])
plt.scatter(baby['Gestational Days'], baby['Birth Weight'], s=6, alpha=0.3)
plt.plot(xs, a * xs + b, color='gold', lw=2)
plt.xlabel('Gestational Days'); plt.ylabel('Birth Weight')
plt.title('임신기간 vs 출생체중'); plt.show()''')

md("""## 3.2 산점도 부트스트랩 (Bootstrapping the Scatter Plot)

- 원래 표본에서 **복원 추출(with replacement)** 로 같은 크기의 새 표본 생성 → **부트스트랩 표본**
- 표본이 점들의 분포를 대표하므로, 부트스트랩 표본도 비슷한 산점도를 가짐(다만 일부 점은 중복/누락)
- 왜? 현실에서는 모집단(추가 표본)을 구할 수 없으니, **원래 표본 하나로** 표본추출의 변동성을 시뮬레이션.
""" + img(10))

code('''n = len(baby)
fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
axes[0].scatter(baby['Gestational Days'], baby['Birth Weight'], s=6, alpha=0.3)
axes[0].set_title('Original sample')
for k in (1, 2):
    bs = baby.sample(n, replace=True)   # 복원 추출
    axes[k].scatter(bs['Gestational Days'], bs['Birth Weight'], s=6, alpha=0.3)
    axes[k].set_title('Bootstrap sample %d' % k)
for ax in axes:
    ax.set_xlabel('Gestational Days'); ax.set_ylabel('Birth Weight')
plt.tight_layout(); plt.show()''')

md("""## 3.3 진짜 기울기 추정 방법

1. 원래 표본에서 N 번 부트스트랩
2. 각 부트스트랩 표본마다 회귀선 기울기 계산 → **기울기 수집**
3. 기울기들의 히스토그램을 그려 분포 확인 → **95% 신뢰구간**(백분위수 방법: 2.5번째 ~ 97.5번째 백분위수)

아래 `bootstrap_slope` 함수가 ① 부트스트랩 기울기 히스토그램 ② 95% 신뢰구간 노란 막대 ③ 수치 출력을 한 번에 처리합니다.
""" + img(11) + img(12))

code('''def bootstrap_slope(t, x, y, repetitions):
    """t 를 repetitions 번 부트스트랩해 회귀 기울기 분포를 구하고, 95% 신뢰구간을 표시."""
    n = len(t)
    slopes = np.array([slope(t.sample(n, replace=True), x, y) for _ in range(repetitions)])
    left, right = np.percentile(slopes, [2.5, 97.5])

    plt.hist(slopes, bins=25, density=True, edgecolor='white', color='#3b5d78')
    plt.plot([left, right], [0, 0], color='gold', lw=8, label='95% 신뢰구간')
    plt.xlabel('Bootstrap Slopes'); plt.ylabel('Percent per unit'); plt.legend()
    plt.title('기울기 부트스트랩 분포'); plt.show()
    print('진짜 기울기의 95%% 신뢰구간 ≈ [%.3f, %.3f]' % (left, right))
    return slopes

# repetitions: 강의자료는 5000회. 여기서는 실행 속도를 위해 2000회 사용(원하면 늘려도 됨).
slopes_gd = bootstrap_slope(baby, 'Gestational Days', 'Birth Weight', 2000)''')

md("""## 3.4 가설 검정 — 진짜 기울기가 0일 수 있는가?

회귀선이 완전히 평평하지 않더라도, 그것이 우연일 수 있습니다(진짜 기울기 = 0).

- **귀무가설 $H_0$:** 진짜 선의 기울기는 0 (선형 관계 없음)
- **대립가설 $H_1$:** 진짜 선의 기울기는 0 이 아님 (선형 관계 있음)
- **판단 기준:** 95% 신뢰구간에 **0이 포함되는지** 확인 → 포함되면 $H_0$ 기각 불가.

임신기간-출생체중은 신뢰구간이 양수 구간(약 0.38~0.56)으로 **0을 포함하지 않음** → 관계 있음.
""" + img(13))

code('''left, right = np.percentile(slopes_gd, [2.5, 97.5])
print('임신기간→출생체중 95%% 신뢰구간: [%.3f, %.3f]' % (left, right))
print('0 포함 여부:', left <= 0 <= right, '→', '관계 없음(H0 기각 불가)' if left <= 0 <= right else '관계 있음(H0 기각)')''')

md("""## 3.5 적용 예 — 출생체중 vs 산모 나이

이번엔 출생체중을 **산모 나이(`Maternal Age`)** 로 회귀해 봅니다.

- 관측 기울기: 약 0.085 온스/년 (매우 작고 거의 평평)
- 95% 신뢰구간: 약 **-0.10 ~ +0.28 온스/년 → 0 을 포함!**
- 결론: 귀무가설 기각 불가 → **산모 나이로 출생체중을 예측하는 것은 부적절**
""" + img(14))

code('''a_age = slope(baby, 'Maternal Age', 'Birth Weight')
b_age = intercept(baby, 'Maternal Age', 'Birth Weight')
print('관측 기울기 = %.4f 온스/년' % a_age)

xs = np.array([baby['Maternal Age'].min(), baby['Maternal Age'].max()])
plt.scatter(baby['Maternal Age'], baby['Birth Weight'], s=6, alpha=0.3)
plt.plot(xs, a_age * xs + b_age, color='gold', lw=2)
plt.xlabel('Maternal Age'); plt.ylabel('Birth Weight'); plt.title('산모 나이 vs 출생체중'); plt.show()

slopes_age = bootstrap_slope(baby, 'Maternal Age', 'Birth Weight', 2000)
left, right = np.percentile(slopes_age, [2.5, 97.5])
print('0 포함 여부:', left <= 0 <= right, '→ 산모 나이는 출생체중 예측에', '부적절' if left <= 0 <= right else '유효')''')

# ───────────────────────── 4. 예측 구간 ─────────────────────────
md("""---
# 4. 예측 구간 (Prediction Intervals)

## 4.1 예측 구간이란?

- (회귀의 목적) 원래 표본에 없던 **새 개체의 y 값**을 예측
- 이상적으로는 진짜 선의 높이를 알고 싶지만 → 회귀선(표본)을 사용
- 예측에는 불확실성이 있다 → 단일 값 대신 **구간(interval)** 으로 표현

**적합값(Fitted Value):** 주어진 x 에서 회귀선의 높이. `fitted_value(t, x, y, given_x)` = 기울기·given_x + 절편.
""" + img(16))

code('''pred_300 = fitted_value(baby, 'Gestational Days', 'Birth Weight', 300)
print('임신기간 300일인 아기의 예측 출생체중 = %.1f 온스' % pred_300)''')

md("""## 4.2 예측의 변동성 (Variability)

표본이 달라지면 회귀선도 달라지고 → **예측값도 달라집니다.** 예측이 얼마나 달라질 수 있는지 알면 신뢰도를 알 수 있습니다.

**부트스트랩으로 변동성 확보:** ① 부트스트랩 표본을 반복 재표집 → ② 각 부트스트랩 표본의 회귀선으로 같은 x(예: 300)에서 예측 → ③ 예측값 분포 확인.
""" + img(17))

code('''def bootstrap_prediction(t, x, y, given_x, repetitions):
    """x = given_x 에서의 예측값을 부트스트랩으로 반복 계산해 분포와 95% 예측구간을 표시."""
    n = len(t)
    preds = np.array([fitted_value(t.sample(n, replace=True), x, y, given_x)
                      for _ in range(repetitions)])
    left, right = np.percentile(preds, [2.5, 97.5])

    plt.hist(preds, bins=25, density=True, edgecolor='white', color='#3b5d78')
    plt.plot([left, right], [0, 0], color='gold', lw=8, label='95% 예측구간')
    plt.xlabel('predictions at x=%g' % given_x); plt.ylabel('Percent per unit'); plt.legend()
    plt.title('x=%g 에서의 예측값 분포' % given_x); plt.show()
    print('x=%g 예측값 점추정 = %.1f' % (given_x, fitted_value(t, x, y, given_x)))
    print('95%% 예측구간 ≈ [%.1f, %.1f]' % (left, right))
    return preds

preds_300 = bootstrap_prediction(baby, 'Gestational Days', 'Birth Weight', 300, 2000)''')

md("""## 4.3 예측변수 값에 따른 구간 폭 변화

x 값의 위치에 따라 예측 구간의 폭이 달라집니다.
- `x = 285` (평균에 가까움): 예측 약 122 온스, 구간이 **좁음**
- `x = 300` (평균에서 떨어짐): 예측 약 129 온스, 구간이 **더 넓음**

**왜 평균 근처에서 구간이 더 좁은가?** 부트스트랩 회귀선들은 분포의 중심(평균 x, 평균 y) 근처에서 모임 →
**중심 가까운 x 의 예측 변동은 작고**, 멀어질수록(데이터가 적은 양 끝) 변동이 커집니다.
""" + img(18) + img(19))

code('''gd_mean = baby['Gestational Days'].mean()
print('임신기간 평균 = %.1f 일 (이 근처에서 예측 구간이 가장 좁음)' % gd_mean)

preds_285 = bootstrap_prediction(baby, 'Gestational Days', 'Birth Weight', 285, 2000)  # 평균 근처 → 좁음
preds_300b = bootstrap_prediction(baby, 'Gestational Days', 'Birth Weight', 300, 2000)  # 평균에서 멈 → 넓음

w285 = np.diff(np.percentile(preds_285, [2.5, 97.5]))[0]
w300 = np.diff(np.percentile(preds_300b, [2.5, 97.5]))[0]
print('\\n구간 폭 비교 → x=285: %.2f 온스  vs  x=300: %.2f 온스' % (w285, w300))''')

# ───────────────────────── Q&A ─────────────────────────
md("""---
# Q & A

수고하셨습니다! 이번 장에서 다룬 내용:
1. **회귀 모형** — 진짜 선(신호) + 평균 0 정규오차(노이즈). 관측되는 것은 점들뿐.
2. **회귀선 = 진짜 선의 추정** — 표본이 클수록 정확 (`draw_and_compare` 시뮬레이션).
3. **참 기울기 추론** — 산점도 부트스트랩으로 기울기 분포 → 95% 신뢰구간 → 기울기 0 검정.
4. **예측 구간** — 특정 x 의 예측값을 부트스트랩 → 예측구간. 평균에서 멀수록 구간이 넓어짐.
""" + img(20))

# ───────────────────────── 저장 ─────────────────────────
nb = {
    "cells": CELLS,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3"},
    },
    "nbformat": 4, "nbformat_minor": 5,
}
out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        '15장', 'AI데이터사이언스15_실습.ipynb')
if os.path.exists(out_path):
    raise SystemExit('이미 존재: ' + out_path + ' (덮어쓰기 방지)')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print('생성 완료:', out_path)
print('셀 수:', len(CELLS),
      '(markdown', sum(c['cell_type'] == 'markdown' for c in CELLS),
      '/ code', sum(c['cell_type'] == 'code' for c in CELLS), ')')
