#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_chapter.py — 강의 PDF → 실습 폴더 자동 구성 도구 (기계적 단계 담당)

이 스크립트는 "정해진(결정적) 작업"만 합니다:
  1) PDF 페이지를 PNG 이미지로 렌더링  (PyMuPDF / fitz)
  2) 실습 데이터(CSV 등)를 URL에서 내려받기
  3) 폴더/파일 이름 규칙을 적용해 기존 파일을 덮어쓰지 않도록 보장

"노트북 내용(셀)"을 만드는 일은 사람이/Claude 가 슬라이드를 읽고 수행합니다.
자세한 전체 워크플로는 저장소 루트의 CLAUDE.md 를 보세요.

의존성(numpy/pandas 불필요): PyMuPDF, requests. 없으면 자동 설치를 시도합니다.

사용 예)
  # 13_1, 13_2 ... 처럼 같은 챕터에 PDF 가 여러 개여도 자동으로 구분됨
  python3 tools/build_chapter.py "AI데이터사이언스(김대환)/AI데이터사이언스14_1.pdf"

  # CSV 도 같이 받기 (Data 8 기본 저장소에서)
  python3 tools/build_chapter.py "...14_1.pdf" --csv baby.csv nba2013.csv

  # 렌더링 배율(기본 2.0) 높이기 — 작은 코드/글자가 안 보일 때
  python3 tools/build_chapter.py "...14_1.pdf" --zoom 3.5
"""
import argparse
import os
import re
import subprocess
import sys

DATA8_BASE = "https://raw.githubusercontent.com/data-8/materials-sp18/master/lec/"


def _ensure(mod, pip_name=None):
    """모듈이 없으면 pip 로 설치 시도 후 import."""
    try:
        return __import__(mod)
    except ImportError:
        pip_name = pip_name or mod
        print(f"[setup] '{pip_name}' 설치 중...", flush=True)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", pip_name])
        return __import__(mod)


def parse_chapter(pdf_path):
    """
    PDF 파일명에서 (챕터번호, 구분자) 를 추출.
      AI데이터사이언스14.pdf      -> ('14', '')        => 폴더 14장, 이미지 images/
      AI데이터사이언스14_1.pdf    -> ('14', '14_1')    => 폴더 14장, 이미지 images/14_1/
      AI데이터사이언스14_보충.pdf -> ('14', '14_보충') => 폴더 14장, 이미지 images/14_보충/
    구분자가 있으면 노트북/이미지 폴더 이름에 반영해 한 챕터 폴더 안에서
    PDF 별로 충돌하지 않게 한다.
    """
    stem = os.path.splitext(os.path.basename(pdf_path))[0]
    m = re.search(r"(\d+)(?:[_\-](.+))?$", stem)
    if not m:
        raise ValueError(f"PDF 이름에서 챕터 번호를 찾지 못했습니다: {stem}")
    chap = m.group(1)
    suffix = m.group(2)  # '1', '보충' ... 또는 None
    tag = f"{chap}_{suffix}" if suffix else chap
    return chap, tag, suffix


def render_pdf(pdf_path, img_dir, zoom=2.0):
    """PDF 모든 페이지를 img_dir/page_XX.png 로 렌더링. 이미 있으면 건너뜀."""
    fitz = _ensure("fitz", "PyMuPDF")
    os.makedirs(img_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    mat = fitz.Matrix(zoom, zoom)
    written = []
    for i, page in enumerate(doc, start=1):
        out = os.path.join(img_dir, f"page_{i:02d}.png")
        if os.path.exists(out):
            continue
        page.get_pixmap(matrix=mat).save(out)
        written.append(out)
    doc.close()
    print(f"[images] {len(written)} 페이지 렌더링 (총 {i} 페이지) -> {img_dir}")
    return i


def download_csv(names, dest_dir, base_url=DATA8_BASE):
    """CSV 파일들을 dest_dir 로 다운로드. 이미 있으면 건너뜀 (덮어쓰지 않음)."""
    if not names:
        return
    requests = _ensure("requests")
    os.makedirs(dest_dir, exist_ok=True)
    for name in names:
        dest = os.path.join(dest_dir, name)
        if os.path.exists(dest):
            print(f"[csv] 이미 존재 (건너뜀): {name}")
            continue
        url = name if name.startswith("http") else base_url + name
        print(f"[csv] 다운로드: {url}")
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        with open(dest, "wb") as f:
            f.write(r.content)


def main():
    ap = argparse.ArgumentParser(description="강의 PDF → 실습 폴더 구성 (이미지 렌더링 + CSV 다운로드)")
    ap.add_argument("pdf", help="강의 PDF 경로")
    ap.add_argument("--out-root", default=".", help="챕터 폴더를 만들 루트 (기본: 현재 폴더)")
    ap.add_argument("--csv", nargs="*", default=[], help="함께 받을 CSV 파일명 (Data 8 저장소 기준) 또는 전체 URL")
    ap.add_argument("--zoom", type=float, default=2.0, help="렌더링 배율 (기본 2.0)")
    ap.add_argument("--base-url", default=DATA8_BASE, help="CSV 기본 URL")
    args = ap.parse_args()

    if not os.path.exists(args.pdf):
        sys.exit(f"PDF 를 찾을 수 없습니다: {args.pdf}")

    chap, tag, suffix = parse_chapter(args.pdf)
    chap_dir = os.path.join(args.out_root, f"{chap}장")
    # 같은 챕터에 PDF 가 여러 개면 이미지를 PDF별 하위폴더로 분리해 충돌 방지
    img_dir = os.path.join(chap_dir, "images", tag) if suffix else os.path.join(chap_dir, "images")
    nb_name = f"AI데이터사이언스{tag}_실습.ipynb"
    nb_path = os.path.join(chap_dir, nb_name)

    os.makedirs(chap_dir, exist_ok=True)
    n_pages = render_pdf(args.pdf, img_dir, zoom=args.zoom)
    download_csv(args.csv, chap_dir, base_url=args.base_url)

    rel_img = os.path.relpath(img_dir, chap_dir).replace(os.sep, "/")
    print("\n=== 요약 ===")
    print(f"챕터 폴더 : {chap_dir}")
    print(f"이미지     : {img_dir}  (노트북 기준 상대경로: {rel_img}/page_XX.png)")
    print(f"노트북     : {nb_path}  {'(이미 존재 — 덮어쓰지 마세요)' if os.path.exists(nb_path) else '(아직 없음 — Claude 가 셀 작성)'}")
    print(f"페이지 수  : {n_pages}")
    print("\n다음 단계: CLAUDE.md 의 '노트북 작성' 절차에 따라 셀을 만들고")
    print(f"          이미지는 <img src=\"{rel_img}/page_XX.png\"> 형태로 삽입하세요.")


if __name__ == "__main__":
    main()
