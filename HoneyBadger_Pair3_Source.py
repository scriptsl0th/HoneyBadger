#!/usr/bin/env python3
"""
HoneyBadger — Pair 03
Profiling Network Attack Behaviors Through Unsupervised Learning

Generates a 17-slide, 16:9, fully editable research deck from the actual
Pair 3 artifacts in this repository.

Usage:
    python HoneyBadger_Pair3_Source.py
    python HoneyBadger_Pair3_Source.py --force     # recompute analysis + assets
    python HoneyBadger_Pair3_Source.py --render    # also build PDF + contact sheet

Data sources (in evidence order):
    data/kaggle/Train_data.csv
    ml/pair3/run_pair3.py
    ml/pair3/pair3_cluster_profiles.csv
    ml/pair3/pair3_cluster_assignments.csv
    ml/pair3/pair3_mitre_mapping.json
    backend/{schemas,mitre,pipeline,storage}.py
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt
from lxml import etree

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "kaggle" / "Train_data.csv"
PAIR3 = ROOT / "ml" / "pair3"
ASSETS = PAIR3 / "assets"
CACHE = PAIR3 / "analysis_cache.json"
OUT_PPTX = ROOT / "HoneyBadger_Pair3_Clustering_Professional.pptx"
OUT_PDF = ROOT / "HoneyBadger_Pair3_Preview.pdf"
OUT_SHEET = ROOT / "HoneyBadger_Pair3_Contact_Sheet.png"

# ── Palette ──────────────────────────────────────────────────────────────────
BG      = RGBColor(0x09, 0x0D, 0x14)
BG2     = RGBColor(0x11, 0x18, 0x27)
CARD    = RGBColor(0x18, 0x22, 0x35)
CARD_HI = RGBColor(0x1E, 0x29, 0x3B)
ACCENT  = RGBColor(0x22, 0xD3, 0xEE)
BLUE    = RGBColor(0x3B, 0x82, 0xF6)
THREAT  = RGBColor(0xF4, 0x3F, 0x5E)
WARN    = RGBColor(0xFB, 0xBF, 0x24)
GOOD    = RGBColor(0x34, 0xD3, 0x99)
TEXT    = RGBColor(0xF1, 0xF5, 0xF9)
MUTED   = RGBColor(0x94, 0xA3, 0xB8)
DIM     = RGBColor(0x64, 0x74, 0x8B)
LINE    = RGBColor(0x24, 0x30, 0x44)
WHITE   = RGBColor(0xFF, 0xFF, 0xFF)

C0 = ACCENT
C1 = THREAT
C2 = BLUE
C3 = WARN

TITLE_FONT = "Space Grotesk"
BODY_FONT = "Inter"
MONO_FONT = "JetBrains Mono"

SW, SH = 13.333, 7.5
ML, MR = 0.75, 0.75
CW = SW - ML - MR
TOTAL_SLIDES = 17

# ── Small utilities ──────────────────────────────────────────────────────────
def hx(c: RGBColor) -> str:
    return str(c)


def _set_run(run, size, color, font, bold=False, italic=False, spc=None):
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.name = font
    run.font.bold = bold
    run.font.italic = italic
    if spc is not None:
        run._r.get_or_add_rPr().set("spc", str(int(spc * 100)))


def bg(slide, color=BG):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def tx(slide, x, y, w, h, text, size=12, color=TEXT, font=BODY_FONT,
       bold=False, italic=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
       line=1.0, spc=None, wrap=True):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    tf.auto_size = None
    for i, line_text in enumerate(str(text).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line
        p.space_before = Pt(0)
        p.space_after = Pt(0)
        r = p.add_run()
        r.text = line_text
        _set_run(r, size, color, font, bold, italic, spc)
    return tb


def rich(slide, x, y, w, h, parts, size=12, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, line=1.0, gap=0):
    """One paragraph made of (text, {color, font, bold, size}) runs."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    tf.auto_size = None
    p = tf.paragraphs[0]
    p.alignment = align
    p.line_spacing = line
    p.space_before = Pt(0)
    p.space_after = Pt(gap)
    for text, opts in parts:
        r = p.add_run()
        r.text = text
        _set_run(r, opts.get("size", size), opts.get("color", TEXT),
                 opts.get("font", BODY_FONT), opts.get("bold", False),
                 opts.get("italic", False), opts.get("spc"))
    return tb


def bullets(slide, x, y, w, h, items, size=11, color=MUTED, gap=8,
            line=1.18, prefix_color=ACCENT, prefix="—  "):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.auto_size = None
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = line
        p.space_before = Pt(0)
        p.space_after = Pt(gap)
        r0 = p.add_run()
        r0.text = prefix
        _set_run(r0, size, prefix_color, MONO_FONT, bold=True)
        if isinstance(item, tuple):
            lead, rest = item
            r1 = p.add_run(); r1.text = lead
            _set_run(r1, size, TEXT, BODY_FONT, bold=True)
            r2 = p.add_run(); r2.text = rest
            _set_run(r2, size, color, BODY_FONT)
        else:
            r1 = p.add_run(); r1.text = item
            _set_run(r1, size, color, BODY_FONT)
    return tb


def _fill_alpha(shape, color, alpha):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    solid = shape.fill._xPr.find(qn("a:solidFill"))
    if solid is not None:
        srgb = solid.find(qn("a:srgbClr"))
        if srgb is not None:
            a = etree.SubElement(srgb, qn("a:alpha"))
            a.set("val", str(int(alpha * 100000)))


def rect(slide, x, y, w, h, fill=CARD, line=None, lw=0.75, radius=0.04):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        shape.adjustments[0] = radius
    if fill is None:
        shape.fill.background()
    else:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(lw)
    shape.shadow.inherit = False
    return shape


def tinted_rect(slide, x, y, w, h, color, alpha=0.12, line=None, lw=0.75, radius=0.04):
    shape = rect(slide, x, y, w, h, fill=color, line=line, lw=lw, radius=radius)
    _fill_alpha(shape, color, alpha)
    return shape


def hline(slide, x, y, w, color=LINE, lw=0.75, dash=None):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                   Inches(x), Inches(y), Inches(x + w), Inches(y))
    c.line.color.rgb = color
    c.line.width = Pt(lw)
    if dash:
        c.line.dash_style = dash
    c.shadow.inherit = False
    return c


def vline(slide, x, y, h, color=LINE, lw=0.75, dash=None):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                   Inches(x), Inches(y), Inches(x), Inches(y + h))
    c.line.color.rgb = color
    c.line.width = Pt(lw)
    if dash:
        c.line.dash_style = dash
    c.shadow.inherit = False
    return c


def arrow(slide, x1, y1, x2, y2, color=MUTED, lw=1.0, dash=None, head=True):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                   Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(lw)
    if dash:
        c.line.dash_style = dash
    if head:
        ln = c.line._get_or_add_ln()
        tail = etree.SubElement(ln, qn("a:tailEnd"))
        tail.set("type", "triangle")
        tail.set("w", "sm")
        tail.set("len", "sm")
    c.shadow.inherit = False
    return c


def circle(slide, cx, cy, r, fill, line=None, lw=1.0):
    s = slide.shapes.add_shape(MSO_SHAPE.OVAL,
                               Inches(cx - r), Inches(cy - r),
                               Inches(2 * r), Inches(2 * r))
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(lw)
    s.shadow.inherit = False
    return s


def pill(slide, x, y, w, h, text, color=ACCENT, size=8.5, fill_alpha=0.10):
    s = tinted_rect(slide, x, y, w, h, color, alpha=fill_alpha, line=color, lw=0.75, radius=0.5)
    tf = s.text_frame
    tf.word_wrap = False
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    _set_run(r, size, color, MONO_FONT, bold=True, spc=0.6)
    return s


def kicker(slide, text):
    rect(slide, ML, 0.58, 0.035, 0.16, fill=ACCENT, radius=0)
    tx(slide, ML + 0.13, 0.55, 9.5, 0.22, text.upper(), size=9,
       color=ACCENT, font=MONO_FONT, bold=True, spc=1.4)


def title(slide, text, size=34, y=0.84, w=11.8, color=TEXT):
    tx(slide, ML, y, w, 0.72, text, size=size, color=color,
       font=TITLE_FONT, bold=True, line=1.0, spc=-0.4)


def subtitle(slide, text, y=1.46, w=10.6, color=MUTED, size=12.5):
    tx(slide, ML, y, w, 0.4, text, size=size, color=color, font=BODY_FONT, line=1.15)


def header(slide, kick, ttl, sub=None, tsize=34):
    kicker(slide, kick)
    title(slide, ttl, size=tsize)
    if sub:
        subtitle(slide, sub)


def footer(slide, n, section="ATTACK TYPE PROFILING"):
    hline(slide, ML, 7.02, CW, color=LINE, lw=0.6)
    tx(slide, ML, 7.10, 4.2, 0.18, "HONEYBADGER  ·  PAIR 03", size=7.2,
       color=DIM, font=MONO_FONT, spc=0.6)
    tx(slide, 5.2, 7.10, 3.0, 0.18, section, size=7.2, color=DIM,
       font=MONO_FONT, align=PP_ALIGN.CENTER, spc=0.6)
    tx(slide, 11.35, 7.10, 1.23, 0.18, f"{n:02d} / {TOTAL_SLIDES:02d}", size=7.2,
       color=MUTED, font=MONO_FONT, align=PP_ALIGN.RIGHT, spc=0.6)


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def _cell_border(cell, color=LINE, width=0.6, edges="LRTB"):
    tcPr = cell._tc.get_or_add_tcPr()
    tags = {"L": "a:lnL", "R": "a:lnR", "T": "a:lnT", "B": "a:lnB"}
    for e in reversed(edges):
        tag = tags[e]
        for old in tcPr.findall(qn(tag)):
            tcPr.remove(old)
        ln = etree.Element(qn(tag))
        ln.set("w", str(int(width * 12700)))
        ln.set("cap", "flat")
        ln.set("cmpd", "sng")
        ln.set("algn", "ctr")
        sf = etree.SubElement(ln, qn("a:solidFill"))
        srgb = etree.SubElement(sf, qn("a:srgbClr"))
        srgb.set("val", hx(color))
        pd = etree.SubElement(ln, qn("a:prstDash"))
        pd.set("val", "solid")
        tcPr.insert(0, ln)


def chart_bg(chart, color=CARD):
    """Set the chart-area fill without relying on python-pptx's missing Chart.format."""
    cs = chart._chartSpace
    chart_el = cs.find(qn("c:chart"))
    for old in cs.findall(qn("c:spPr")):
        cs.remove(old)
    spPr = etree.Element(qn("c:spPr"))
    sf = etree.SubElement(spPr, qn("a:solidFill"))
    srgb = etree.SubElement(sf, qn("a:srgbClr"))
    srgb.set("val", hx(color))
    ln = etree.SubElement(spPr, qn("a:ln"))
    etree.SubElement(ln, qn("a:noFill"))
    if chart_el is not None:
        chart_el.addnext(spPr)
    else:
        cs.append(spPr)


def table(slide, x, y, w, h, rows, widths, header_row=True, size=10,
          row_h=None, header_color=ACCENT, mono_cols=(), align_right=()):
    shape = slide.shapes.add_table(len(rows), len(widths), Inches(x), Inches(y),
                                   Inches(w), Inches(h))
    tbl = shape.table
    tbl.first_row = False
    tbl.horz_banding = False
    tbl.vert_banding = False
    for i, cw in enumerate(widths):
        tbl.columns[i].width = Inches(cw)
    if row_h:
        for r in range(len(rows)):
            tbl.rows[r].height = Inches(row_h)
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            cell = tbl.cell(r, c)
            cell.margin_left = Inches(0.09)
            cell.margin_right = Inches(0.09)
            cell.margin_top = Inches(0.02)
            cell.margin_bottom = Inches(0.02)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = BG2 if (header_row and r == 0) else (
                CARD if r % 2 == 0 else BG2)
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.RIGHT if c in align_right else PP_ALIGN.LEFT
            run = p.add_run()
            run.text = str(value)
            is_header = header_row and r == 0
            _set_run(run, size if not is_header else size - 0.5,
                     header_color if is_header else TEXT,
                     MONO_FONT if (c in mono_cols or is_header) else BODY_FONT,
                     bold=is_header or c in mono_cols)
            _cell_border(cell, LINE, 0.55, "B")
    return tbl


def metric(slide, x, y, w, h, value, label, sub="", color=TEXT, vsize=34):
    rect(slide, x, y, w, h, fill=CARD, line=LINE, lw=0.6, radius=0.05)
    tx(slide, x + 0.18, y + 0.16, w - 0.36, 0.16, label.upper(), size=7.8,
       color=MUTED, font=MONO_FONT, bold=True, spc=0.9)
    tx(slide, x + 0.18, y + 0.38, w - 0.36, 0.52, value, size=vsize,
       color=color, font=TITLE_FONT, bold=True, spc=-0.8)
    if sub:
        tx(slide, x + 0.18, y + h - 0.34, w - 0.36, 0.24, sub, size=8.4,
           color=DIM, font=BODY_FONT, line=1.0)


def section_number(slide, x, y, number, color, size=92):
    """Large ghost number."""
    dark = {hx(C0): RGBColor(0x0B, 0x3B, 0x45),
            hx(C1): RGBColor(0x3B, 0x15, 0x20),
            hx(C2): RGBColor(0x12, 0x26, 0x4A),
            hx(C3): RGBColor(0x3B, 0x2E, 0x0B)}.get(hx(color), CARD_HI)
    tx(slide, x, y, 2.2, 1.3, number, size=size, color=dark,
       font=TITLE_FONT, bold=True, spc=-2)

# ── Analysis: run the actual Pair 3 pipeline once, then cache ────────────────
def _f(x):
    return float(x)


def _i(x):
    return int(x)


def ensure_analysis(force=False):
    coords = PAIR3 / "pca_coords.npy"
    labels = PAIR3 / "cluster_labels.npy"
    if CACHE.exists() and coords.exists() and labels.exists() and not force:
        return json.loads(CACHE.read_text())

    if not DATA.exists():
        raise SystemExit(f"Dataset not found: {DATA}")

    from sklearn.cluster import DBSCAN, KMeans
    from sklearn.compose import ColumnTransformer
    from sklearn.decomposition import PCA
    from sklearn.metrics import (adjusted_rand_score, calinski_harabasz_score,
                                 davies_bouldin_score, silhouette_score)
    from sklearn.mixture import GaussianMixture
    from sklearn.neighbors import NearestNeighbors
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import (FunctionTransformer, OneHotEncoder,
                                       StandardScaler)

    seed = 42
    np.random.seed(seed)
    print("[analysis] loading data", flush=True)
    train = pd.read_csv(DATA)
    test_path = DATA.parent / "Test_data.csv"
    test_rows = len(pd.read_csv(test_path)) if test_path.exists() else 0
    anomalies = train[train["class"] == "anomaly"].copy()

    constant_cols = ["num_outbound_cmds", "is_host_login"]
    features = [c for c in anomalies.columns if c not in ["class"] + constant_cols]
    X = anomalies[features].copy()

    categorical = ["protocol_type", "service", "flag"]
    numeric = [c for c in features if c not in categorical]
    service_counts = X["service"].value_counts()
    rare = service_counts[service_counts < 100].index.tolist()
    X["service_grouped"] = X["service"].replace(rare, "other")

    skewed = ["duration", "src_bytes", "dst_bytes"]
    numeric_regular = [c for c in numeric if c not in skewed]
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False),
         ["protocol_type", "service_grouped", "flag"]),
        ("num_skewed", Pipeline([
            ("log", FunctionTransformer(np.log1p, validate=False)),
            ("scale", StandardScaler())]), skewed),
        ("num_regular", StandardScaler(), numeric_regular),
    ], remainder="drop")
    Xp = pre.fit_transform(X)

    pca2 = PCA(n_components=2, random_state=seed)
    X2 = pca2.fit_transform(Xp)
    pca95 = PCA(n_components=0.95, random_state=seed)
    Z = pca95.fit_transform(Xp)

    k_range = list(range(2, 16))
    inertias, silhouettes = [], []
    np.random.seed(seed)
    sample_idx = np.random.choice(len(Z), min(5000, len(Z)), replace=False)
    Zs = Z[sample_idx]
    print("[analysis] K-Means selection", flush=True)
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=seed, n_init=10)
        lab = km.fit_predict(Z)
        inertias.append(_f(km.inertia_))
        silhouettes.append(_f(silhouette_score(Zs, lab[sample_idx])))

    diff2 = np.diff(inertias, 2)
    elbow_k = k_range[int(np.argmax(diff2)) + 2] if len(diff2) else 6
    best_sil_k = k_range[int(np.argmax(silhouettes))]

    bics, aics = [], []
    print("[analysis] GMM BIC/AIC selection", flush=True)
    for k in k_range:
        g = GaussianMixture(n_components=k, random_state=seed, n_init=5).fit(Z)
        bics.append(_f(g.bic(Z)))
        aics.append(_f(g.aic(Z)))
    best_bic_k = k_range[int(np.argmin(bics))]
    best_aic_k = k_range[int(np.argmin(aics))]

    k_neighbors = pca95.n_components_ + 1
    nn = NearestNeighbors(n_neighbors=k_neighbors).fit(Z)
    dist, _ = nn.kneighbors(Z)
    dist = np.sort(dist[:, -1])
    eps = _f(np.percentile(dist, 90))
    min_samples = k_neighbors

    chosen_k = elbow_k
    km = KMeans(n_clusters=chosen_k, random_state=seed, n_init=10)
    km_labels = km.fit_predict(Z)
    gmm = GaussianMixture(n_components=chosen_k, random_state=seed, n_init=5).fit(Z)
    gmm_labels = gmm.predict(Z)
    db = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(Z)
    db_clusters = len(set(db)) - (1 if -1 in db else 0)
    db_outliers = int((db == -1).sum())
    print("[analysis] final models fitted; computing metrics", flush=True)

    def metrics(Xv, lab, name):
        valid = lab >= 0
        Xv, lv = Xv[valid], lab[valid]
        idx = np.random.choice(len(Xv), min(5000, len(Xv)), replace=False)
        return {
            "method": name,
            "n_clusters": _i(len(np.unique(lv))),
            "silhouette": _f(silhouette_score(Xv[idx], lv[idx])),
            "davies_bouldin": _f(davies_bouldin_score(Xv, lv)),
            "calinski_harabasz": _f(calinski_harabasz_score(Xv, lv)),
        }

    km_m = metrics(Z, km_labels, "K-Means")
    gmm_m = metrics(Z, gmm_labels, "GMM")
    db_m = metrics(Z, db, "DBSCAN")

    def stability(cls, params):
        base = cls(**params, random_state=seed).fit_predict(Z)
        aris = [adjusted_rand_score(base, cls(**params, random_state=s).fit_predict(Z))
                for s in range(10)]
        return _f(np.mean(aris)), _f(np.std(aris))

    print("[analysis] stability analysis", flush=True)
    km_ari, km_std = stability(KMeans, {"n_clusters": chosen_k, "n_init": 10})
    gmm_ari, gmm_std = stability(GaussianMixture, {"n_components": chosen_k, "n_init": 5})
    # Profiles come from the archived assignment artifacts: the CSV matches the
    # 4-component GMM partition exactly (3,189 / 6,181 / 988 / 1,385).
    prof_df = anomalies.copy()
    prof_df["cluster"] = gmm_labels
    profile_features = [
        "duration", "src_bytes", "dst_bytes", "count", "srv_count",
        "serror_rate", "rerror_rate", "same_srv_rate", "diff_srv_rate",
        "dst_host_count", "dst_host_srv_count", "dst_host_same_srv_rate",
        "dst_host_diff_srv_rate", "num_failed_logins", "logged_in",
        "is_guest_login", "num_compromised", "root_shell", "su_attempted",
        "num_root", "num_file_creations", "num_shells", "num_access_files", "hot",
    ]
    numeric_profile = [c for c in profile_features
                       if c in prof_df.select_dtypes(include="number").columns]
    med = prof_df.groupby("cluster")[numeric_profile].median()
    modes = prof_df.groupby("cluster").agg({
        "protocol_type": lambda x: x.mode().iloc[0],
        "service": lambda x: x.mode().iloc[0],
        "flag": lambda x: x.mode().iloc[0],
    })
    sizes = prof_df["cluster"].value_counts().sort_index()
    profiles = {}
    for c in sorted(sizes.index):
        row = {k: _f(v) for k, v in med.loc[c].items()}
        row.update({
            "size": _i(sizes[c]),
            "pct": _f(sizes[c] / len(prof_df) * 100),
            "protocol_type": str(modes.loc[c, "protocol_type"]),
            "service": str(modes.loc[c, "service"]),
            "flag": str(modes.loc[c, "flag"]),
        })
        profiles[str(c)] = row

    normal = train[train["class"] == "normal"]
    anom = anomalies

    def flag_dist(frame):
        counts = frame["flag"].value_counts(normalize=True)
        out = {k: _f(v * 100) for k, v in counts.items()}
        return out

    normal_stats = {
        "rows": _i(len(normal)),
        "pct": _f(len(normal) / len(train) * 100),
        "services": _i(normal["service"].nunique()),
        "logged_in": _f(normal["logged_in"].mean() * 100),
        "serror": _f(normal["serror_rate"].mean() * 100),
        "rerror": _f(normal["rerror_rate"].mean() * 100),
        "src_median": _f(normal["src_bytes"].median()),
        "dst_median": _f(normal["dst_bytes"].median()),
        "flags": flag_dist(normal),
    }
    anomaly_stats = {
        "rows": _i(len(anom)),
        "pct": _f(len(anom) / len(train) * 100),
        "services": _i(anom["service"].nunique()),
        "logged_in": _f(anom["logged_in"].mean() * 100),
        "serror": _f(anom["serror_rate"].mean() * 100),
        "rerror": _f(anom["rerror_rate"].mean() * 100),
        "src_median": _f(anom["src_bytes"].median()),
        "dst_median": _f(anom["dst_bytes"].median()),
        "flags": flag_dist(anom),
    }

    result = {
        "dataset": {
            "train_rows": _i(len(train)),
            "test_rows": _i(test_rows),
            "normal_rows": _i(len(normal)),
            "anomaly_rows": _i(len(anom)),
            "columns": _i(train.shape[1]),
            "features": _i(train.shape[1] - 1),
            "ssh_rows": _i((train["service"] == "ssh").sum()),
            "ssh_anomalies": _i((anom["service"] == "ssh").sum()),
        },
        "preprocessing": {
            "encoded": _i(Xp.shape[1]),
            "pca_components": _i(pca95.n_components_),
            "pca_variance": _f(pca95.explained_variance_ratio_.sum() * 100),
            "pc1": _f(pca2.explained_variance_ratio_[0] * 100),
            "pc2": _f(pca2.explained_variance_ratio_[1] * 100),
            "pca2_variance": _f(pca2.explained_variance_ratio_.sum() * 100),
            "rare_services": _i(len(rare)),
        },
        "selection": {
            "k_range": k_range,
            "inertias": inertias,
            "silhouettes": silhouettes,
            "bics": bics,
            "aics": aics,
            "elbow_k": _i(elbow_k),
            "best_sil_k": _i(best_sil_k),
            "best_bic_k": _i(best_bic_k),
            "best_aic_k": _i(best_aic_k),
            "eps": eps,
            "min_samples": _i(min_samples),
            "db_clusters": _i(db_clusters),
            "db_outliers": _i(db_outliers),
        },
        "metrics": {"kmeans": km_m, "gmm": gmm_m, "dbscan": db_m},
        "stability": {
            "kmeans_mean": km_ari, "kmeans_std": km_std,
            "gmm_mean": gmm_ari, "gmm_std": gmm_std,
        },
        "profiles": profiles,
        "kmeans_sizes": [int(x) for x in np.bincount(km_labels)],
        "gmm_sizes": [int(x) for x in np.bincount(gmm_labels)],
        "normal_stats": normal_stats,
        "anomaly_stats": anomaly_stats,
    }

    PAIR3.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(result, indent=2))
    np.save(coords, X2)
    np.save(labels, gmm_labels)
    np.save(PAIR3 / "kmeans_labels.npy", km_labels)
    return result


# ── Matplotlib assets (real data where available) ────────────────────────────
HX = {
    "bg": "#090D14", "bg2": "#111827", "card": "#182235", "line": "#243044",
    "accent": "#22D3EE", "blue": "#3B82F6", "threat": "#F43F5E",
    "warn": "#FBBF24", "good": "#34D399", "text": "#F1F5F9",
    "muted": "#94A3B8", "dim": "#64748B",
}


def _setup_mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.font_manager as fm
    import matplotlib.pyplot as plt
    for folder in [Path.home() / ".local/share/fonts",
                   Path("/usr/share/fonts/truetype/custom")]:
        if folder.exists():
            for f in folder.glob("*.ttf"):
                try:
                    fm.fontManager.addfont(str(f))
                except Exception:
                    pass
    plt.rcParams.update({
        "font.family": "Inter",
        "text.color": HX["muted"],
        "axes.labelcolor": HX["muted"],
        "xtick.color": HX["dim"],
        "ytick.color": HX["dim"],
        "axes.edgecolor": HX["line"],
        "grid.color": HX["line"],
        "figure.facecolor": "none",
        "axes.facecolor": "none",
        "savefig.transparent": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })
    return plt


def _save(fig, path, pad=0.02):
    fig.savefig(path, dpi=220, transparent=True, bbox_inches="tight",
                pad_inches=pad, facecolor="none")
    import matplotlib.pyplot as plt
    plt.close(fig)


def _title_network(plt):
    rng = np.random.default_rng(7)
    fig, ax = plt.subplots(figsize=(6.2, 7.4))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    gx, gy = np.meshgrid(np.linspace(0.02, 0.98, 23), np.linspace(0.02, 0.98, 28))
    ax.scatter(gx.ravel(), gy.ravel(), s=0.5, c=HX["line"], alpha=0.5, zorder=0)

    centers = [(0.24, 0.79), (0.64, 0.66), (0.35, 0.31), (0.80, 0.23)]
    counts = [22, 30, 17, 19]
    colors = [HX["accent"], HX["threat"], HX["blue"], HX["warn"]]
    pts_by_cluster = []
    for (cx, cy), n, color in zip(centers, counts, colors):
        pts = np.column_stack([rng.normal(cx, 0.075, n), rng.normal(cy, 0.065, n)])
        pts[:, 0] = np.clip(pts[:, 0], 0.03, 0.97)
        pts[:, 1] = np.clip(pts[:, 1], 0.03, 0.97)
        pts_by_cluster.append(pts)
        ax.add_patch(plt.Circle((cx, cy), 0.13, fill=False, ec=color, lw=0.8, alpha=0.18))
        # intra-cluster edges to two nearest neighbours
        for i, p in enumerate(pts):
            d = np.linalg.norm(pts - p, axis=1)
            for j in np.argsort(d)[1:3]:
                ax.plot([p[0], pts[j, 0]], [p[1], pts[j, 1]],
                        color=color, lw=0.55, alpha=0.16, zorder=1)
        ax.scatter(pts[:, 0], pts[:, 1], s=95, c=color, alpha=0.05, zorder=2)
        ax.scatter(pts[:, 0], pts[:, 1], s=42, c=color, alpha=0.13, zorder=3)
        ax.scatter(pts[:, 0], pts[:, 1], s=9, c=color, alpha=0.95,
                   edgecolors=HX["bg"], linewidths=0.35, zorder=4)

    # a few cross-cluster links, very faint
    for _ in range(7):
        a = rng.integers(0, 4); b = rng.integers(0, 4)
        if a == b:
            continue
        pa = pts_by_cluster[a][rng.integers(0, len(pts_by_cluster[a]))]
        pb = pts_by_cluster[b][rng.integers(0, len(pts_by_cluster[b]))]
        ax.plot([pa[0], pb[0]], [pa[1], pb[1]], color=HX["blue"],
                lw=0.5, alpha=0.07, zorder=0)
    fig.subplots_adjust(0, 0, 1, 1)
    _save(fig, ASSETS / "title_network.png", pad=0)


def _pca_plot(plt, a):
    coords = np.load(PAIR3 / "pca_coords.npy")
    labels = np.load(PAIR3 / "cluster_labels.npy")
    colors = [HX["accent"], HX["threat"], HX["blue"], HX["warn"]]
    fig, ax = plt.subplots(figsize=(6.7, 4.75))
    for c in range(4):
        m = labels == c
        ax.scatter(coords[m, 0], coords[m, 1], s=3.6, c=colors[c],
                   alpha=0.38, linewidths=0, rasterized=True, zorder=2)
    for c in range(4):
        m = labels == c
        cx, cy = np.median(coords[m, 0]), np.median(coords[m, 1])
        ax.annotate(f"0{c}", (cx, cy), fontsize=9.5, fontfamily="JetBrains Mono",
                    color=colors[c], ha="center", va="center", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.32", fc="#0B1220",
                              ec=colors[c], lw=0.8, alpha=0.92))
    ax.set_xlabel(f"PC1 · {a['preprocessing']['pc1']:.1f}%", fontsize=8.5)
    ax.set_ylabel(f"PC2 · {a['preprocessing']['pc2']:.1f}%", fontsize=8.5)
    ax.tick_params(labelsize=7)
    ax.grid(True, alpha=0.16, lw=0.6)
    ax.set_axisbelow(True)
    ax.text(0.01, 0.99, "11,743 anomalies · 20-D space projected to 2-D",
            transform=ax.transAxes, fontsize=7.2, color=HX["dim"], va="top")
    _save(fig, ASSETS / "pca_clusters.png")


def _selection_plots(plt, a):
    s = a["selection"]
    ks = s["k_range"]

    fig, ax = plt.subplots(figsize=(6.0, 2.05))
    ax.plot(ks, s["silhouettes"], "-o", color=HX["accent"], lw=1.4,
            ms=3.2, mfc=HX["bg"], mew=0.9)
    ax.axvline(s["elbow_k"], color=HX["good"], ls=(0, (3, 3)), lw=1.0, alpha=0.9)
    ax.axvline(s["best_sil_k"], color=HX["warn"], ls=(0, (3, 3)), lw=1.0, alpha=0.8)
    ax.annotate(f"k={s['elbow_k']} selected", (s["elbow_k"], 0.515),
                xytext=(5, 0), textcoords="offset points", fontsize=7.2,
                color=HX["good"], va="bottom")
    ax.annotate(f"max {max(s['silhouettes']):.3f}", (s["best_sil_k"], max(s["silhouettes"])),
                xytext=(-4, 7), textcoords="offset points", fontsize=7.2,
                color=HX["warn"], ha="right")
    ax.set_xlabel("k", fontsize=8)
    ax.set_ylabel("silhouette", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.set_xticks(range(2, 16, 2))
    ax.grid(True, axis="y", alpha=0.15, lw=0.6)
    ax.set_axisbelow(True)
    _save(fig, ASSETS / "selection_silhouette.png")

    fig, ax = plt.subplots(figsize=(6.0, 2.05))
    ax.plot(ks, s["bics"], "-o", color=HX["threat"], lw=1.4, ms=3.2,
            mfc=HX["bg"], mew=0.9, label="BIC")
    ax.plot(ks, s["aics"], "--s", color=HX["blue"], lw=1.2, ms=3.0,
            mfc=HX["bg"], mew=0.9, label="AIC")
    ax.axvline(s["best_bic_k"], color=HX["warn"], ls=(0, (3, 3)), lw=1.0, alpha=0.85)
    ax.annotate(f"k={s['best_bic_k']} min", (s["best_bic_k"], min(s["bics"])),
                xytext=(-4, 10), textcoords="offset points", fontsize=7.2,
                color=HX["warn"], ha="right")
    ax.set_xlabel("k", fontsize=8)
    ax.set_ylabel("information criterion", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.set_xticks(range(2, 16, 2))
    ax.grid(True, axis="y", alpha=0.15, lw=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=7.2, loc="upper right", labelcolor=HX["muted"])
    _save(fig, ASSETS / "selection_bic.png")


def _concepts(plt):
    rng = np.random.default_rng(11)

    def blob(cx, cy, n=90, sx=0.075, sy=0.07):
        return np.column_stack([rng.normal(cx, sx, n), rng.normal(cy, sy, n)])

    # K-Means: compact partitions with centroids
    fig, ax = plt.subplots(figsize=(3.2, 1.85))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    for (cx, cy), color in zip([(0.25, 0.55), (0.55, 0.28), (0.76, 0.70)],
                               [HX["accent"], HX["blue"], HX["warn"]]):
        p = blob(cx, cy)
        ax.scatter(p[:, 0], p[:, 1], s=10, c=color, alpha=0.55, linewidths=0)
        ax.scatter([cx], [cy], marker="X", s=110, c=color, edgecolors=HX["bg"], linewidths=1.0)
        ax.add_patch(plt.Circle((cx, cy), 0.145, fill=False, ec=color, lw=1.0,
                                ls=(0, (3, 3)), alpha=0.7))
    _save(fig, ASSETS / "concept_kmeans.png")

    # GMM: overlapping Gaussian components
    from matplotlib.patches import Ellipse
    fig, ax = plt.subplots(figsize=(3.2, 1.85))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    comps = [((0.28, 0.52), 0.30, 0.18, 18, HX["accent"]),
             ((0.55, 0.40), 0.34, 0.20, -25, HX["blue"]),
             ((0.74, 0.66), 0.26, 0.16, 8, HX["warn"])]
    for (cx, cy), w, h, ang, color in comps:
        p = blob(cx, cy, sx=w / 4.0, sy=h / 4.0)
        ax.scatter(p[:, 0], p[:, 1], s=9, c=color, alpha=0.38, linewidths=0)
        ax.add_patch(Ellipse((cx, cy), w, h, angle=ang, facecolor=color,
                             edgecolor=color, lw=1.1, alpha=0.12))
    _save(fig, ASSETS / "concept_gmm.png")

    # DBSCAN: density regions plus noise
    fig, ax = plt.subplots(figsize=(3.2, 1.85))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    for (cx, cy), color in zip([(0.28, 0.45), (0.62, 0.62), (0.78, 0.25)],
                               [HX["accent"], HX["blue"], HX["good"]]):
        p = blob(cx, cy, n=110, sx=0.06, sy=0.055)
        ax.scatter(p[:, 0], p[:, 1], s=10, c=color, alpha=0.62, linewidths=0)
    ax.add_patch(plt.Circle((0.28, 0.45), 0.15, fill=False, ec=HX["accent"],
                            lw=1.0, ls=(0, (3, 3)), alpha=0.75))
    noise = np.column_stack([rng.uniform(0.05, 0.95, 12), rng.uniform(0.05, 0.95, 12)])
    ax.scatter(noise[:, 0], noise[:, 1], s=16, c=HX["dim"], marker="x", linewidths=0.9, alpha=0.9)
    _save(fig, ASSETS / "concept_dbscan.png")


def build_assets(a, force=False):
    ASSETS.mkdir(parents=True, exist_ok=True)
    names = ["title_network.png", "pca_clusters.png", "selection_silhouette.png",
             "selection_bic.png", "concept_kmeans.png", "concept_gmm.png",
             "concept_dbscan.png"]
    if all((ASSETS / n).exists() for n in names) and not force:
        return
    plt = _setup_mpl()
    _title_network(plt)
    _pca_plot(plt, a)
    _selection_plots(plt, a)
    _concepts(plt)

# ── Slides 01–08 ─────────────────────────────────────────────────────────────
def slide_01(prs, a):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    s.shapes.add_picture(str(ASSETS / "title_network.png"), Inches(6.95), Inches(0),
                         width=Inches(6.35), height=Inches(7.5))
    tx(s, ML, 1.15, 6.0, 0.22, "HONEYBADGER RESEARCH  ·  PAIR 03", size=9.5,
       color=ACCENT, font=MONO_FONT, bold=True, spc=1.6)
    tx(s, 0.72, 1.50, 6.4, 1.0, "HONEYBADGER", size=54, color=TEXT,
       font=TITLE_FONT, bold=True, spc=-1.4)
    hline(s, ML, 2.68, 1.15, color=ACCENT, lw=2.0)
    tx(s, ML, 2.90, 5.95, 0.95,
       "Profiling Network Attack Behaviors\nThrough Unsupervised Learning",
       size=21.5, color=TEXT, font=BODY_FONT, line=1.16)
    tx(s, ML, 4.08, 5.7, 0.72,
       "Four behavioral clusters from 11,743 unlabelled anomalies — and four "
       "MITRE ATT&CK hypotheses for analysts.",
       size=11.8, color=MUTED, font=BODY_FONT, line=1.32)

    stats = [("11,743", "ANOMALIES", TEXT), ("41", "FEATURES", TEXT),
             ("04", "BEHAVIORAL CLUSTERS", ACCENT)]
    xs = [0.75, 2.55, 4.25]
    ws = [1.55, 1.45, 2.2]
    for (val, lab, col), x, w in zip(stats, xs, ws):
        tx(s, x, 5.22, w, 0.45, val, size=26, color=col, font=TITLE_FONT,
           bold=True, spc=-0.8)
        tx(s, x, 5.68, w, 0.2, lab, size=7.2, color=DIM, font=MONO_FONT,
           bold=True, spc=0.8)
    vline(s, 2.40, 5.28, 0.62, color=LINE, lw=0.7)
    vline(s, 4.10, 5.28, 0.62, color=LINE, lw=0.7)

    tx(s, ML, 6.48, 8.0, 0.2, "PAIR 03  |  ATTACK TYPE PROFILING  |  CLUSTERING",
       size=8.4, color=ACCENT, font=MONO_FONT, bold=True, spc=1.1)
    tx(s, ML, 6.75, 8.2, 0.2,
       "KAGGLE NETWORK INTRUSION DETECTION  ·  KDD-STYLE CONNECTIONS",
       size=6.9, color=DIM, font=MONO_FONT, spc=0.6)
    hline(s, ML, 7.02, CW, color=LINE, lw=0.6)
    tx(s, ML, 7.10, 4.0, 0.18, "HONEYBADGER  ·  PAIR 03", size=7.2, color=DIM,
       font=MONO_FONT, spc=0.6)
    tx(s, 11.35, 7.10, 1.23, 0.18, f"01 / {TOTAL_SLIDES:02d}", size=7.2,
       color=MUTED, font=MONO_FONT, align=PP_ALIGN.RIGHT, spc=0.6)
    notes(s, "Title. Evidence: data/kaggle/Train_data.csv (25,192 rows; 11,743 anomalies); "
             "ml/pair3/run_pair3.py; ml/pair3/pair3_cluster_profiles.csv. "
             "The four profiles are the archived GMM k=4 partition; see slide 15.")


def slide_02(prs, a):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    kicker(s, "01 / THE CHALLENGE")
    tx(s, ML, 0.84, 7.4, 0.6, "11,743 anomalies.", size=38, color=TEXT,
       font=TITLE_FONT, bold=True, spc=-0.8)
    tx(s, ML, 1.38, 7.4, 0.6, "Zero attack-type labels.", size=38, color=THREAT,
       font=TITLE_FONT, bold=True, spc=-0.8)

    tx(s, ML, 2.42, 6.35, 0.62,
       "The dataset gives us a binary verdict — normal or anomaly. It does not "
       "say which attack family produced an anomaly.",
       size=12.8, color=MUTED, font=BODY_FONT, line=1.35)
    tx(s, ML, 3.18, 6.35, 0.62,
       "Without labels, clustering is the only way to ask whether the anomalies "
       "fall into coherent behavioral groups.",
       size=12.8, color=MUTED, font=BODY_FONT, line=1.35)

    rect(s, ML, 4.28, 6.4, 1.35, fill=CARD, line=LINE, lw=0.6, radius=0.04)
    rect(s, ML, 4.28, 0.055, 1.35, fill=ACCENT, radius=0)
    tx(s, ML + 0.22, 4.44, 5.9, 0.18, "BUSINESS QUESTION", size=7.8,
       color=ACCENT, font=MONO_FONT, bold=True, spc=1.2)
    tx(s, ML + 0.22, 4.68, 5.95, 0.8,
       "Can unsupervised learning discover meaningful behavioral groups that "
       "help analysts understand suspicious traffic?",
       size=14.2, color=TEXT, font=BODY_FONT, line=1.22)

    # Label-availability card
    rect(s, 7.90, 1.90, 4.65, 4.50, fill=CARD, line=LINE, lw=0.6, radius=0.05)
    tx(s, 8.15, 2.08, 4.1, 0.18, "LABEL AVAILABILITY", size=7.8, color=MUTED,
       font=MONO_FONT, bold=True, spc=1.1)
    tx(s, 8.08, 2.22, 2.6, 1.35, "0", size=104, color=WARN, font=TITLE_FONT,
       bold=True, spc=-3)
    tx(s, 8.18, 3.48, 4.0, 0.28, "attack-type labels", size=13, color=TEXT,
       font=BODY_FONT, bold=True)
    tx(s, 8.18, 3.78, 4.0, 0.24, "in the 25,192-record training set", size=9.2,
       color=MUTED, font=BODY_FONT)
    hline(s, 8.15, 4.18, 4.12, color=LINE, lw=0.7)
    tx(s, 8.15, 4.34, 4.0, 0.28, "11,743 / 25,192", size=14.5, color=TEXT,
       font=MONO_FONT, bold=True)
    tx(s, 8.15, 4.64, 4.0, 0.2, "records flagged anomaly", size=8.8, color=MUTED,
       font=BODY_FONT)
    rect(s, 8.15, 5.02, 4.10, 0.08, fill=LINE, radius=0.5)
    rect(s, 8.15, 5.02, 4.10 * 0.466, 0.08, fill=THREAT, radius=0.5)
    tx(s, 8.15, 5.18, 4.0, 0.2, "46.6% of the training set", size=8.2, color=DIM,
       font=MONO_FONT)
    tx(s, 8.15, 5.62, 4.05, 0.5,
       "The missing taxonomy is the research problem — not a modelling detail.",
       size=9.4, color=MUTED, font=BODY_FONT, line=1.25, italic=True)
    footer(s, 2)
    notes(s, "Problem framing. Counts verified from Train_data.csv: 25,192 rows, "
             "13,449 normal, 11,743 anomaly. The dataset has no attack-type label.")


def slide_03(prs, a):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "02 / SCOPE", "The experiment at a glance.")
    cards = [
        ("25,192", "TRAINING RECORDS", "41 features + class label", TEXT),
        ("13,449", "NORMAL RECORDS", "53.4% · reference baseline", BLUE),
        ("11,743", "ANOMALOUS RECORDS", "46.6% · clustering target", THREAT),
        ("41", "ORIGINAL FEATURES", "39 after constant drop", ACCENT),
    ]
    xs = [0.75, 3.74, 6.73, 9.72]
    for (val, lab, sub, col), x in zip(cards, xs):
        metric(s, x, 1.82, 2.85, 1.48, val, lab, sub, col, vsize=30)

    stages = [
        ("01", "DATASET", "25,192 labelled\nconnections"),
        ("02", "ANOMALY FILTER", "11,743 anomalies\nonly"),
        ("03", "FEATURE ENGINEERING", "encode · group\nscale · log1p"),
        ("04", "PCA", "79 → 20 components\n95.6% variance"),
        ("05", "CLUSTERING", "K-Means · GMM\nDBSCAN"),
        ("06", "EVALUATION", "silhouette · DB\nCH · ARI"),
        ("07", "PROFILES", "4 signatures\n+ MITRE hypotheses"),
    ]
    gap = 0.18
    bw = (CW - gap * 6) / 7
    for i, (num, name, detail) in enumerate(stages):
        x = ML + i * (bw + gap)
        hi = i == 1
        rect(s, x, 3.78, bw, 1.34, fill=(CARD if not hi else CARD_HI),
             line=(ACCENT if hi else LINE), lw=(1.0 if hi else 0.6), radius=0.05)
        if hi:
            rect(s, x, 3.78, bw, 0.045, fill=ACCENT, radius=0)
        tx(s, x + 0.12, 3.88, bw - 0.2, 0.16, num, size=6.8, color=(ACCENT if hi else DIM),
           font=MONO_FONT, bold=True, spc=0.8)
        tx(s, x + 0.12, 4.08, bw - 0.2, 0.38, name, size=8.4, color=TEXT,
           font=BODY_FONT, bold=True, line=1.0)
        tx(s, x + 0.12, 4.58, bw - 0.2, 0.42, detail, size=7.1, color=MUTED,
           font=BODY_FONT, line=1.12)
        if i < 6:
            tx(s, x + bw + 0.015, 4.30, 0.15, 0.25, "›", size=13, color=DIM,
               font=BODY_FONT, bold=True, align=PP_ALIGN.CENTER)

    rect(s, ML, 5.48, 0.045, 0.52, fill=ACCENT, radius=0)
    tx(s, ML + 0.18, 5.48, 11.4, 0.5,
       "Clustering is performed only on the 11,743 anomalous records. Normal "
       "records are used only as a reference baseline.",
       size=10.8, color=MUTED, font=BODY_FONT, line=1.25)

    for i, (label, col) in enumerate([("K-MEANS", ACCENT), ("GAUSSIAN MIXTURE", BLUE),
                                      ("DBSCAN", GOOD)]):
        pill(s, ML + i * 2.25, 6.18, 2.05, 0.32, label, col, size=7.8)
    tx(s, 7.35, 6.25, 5.2, 0.2, "SELECTION  ·  ELBOW / SILHOUETTE / BIC–AIC / k-DISTANCE",
       size=6.9, color=DIM, font=MONO_FONT, align=PP_ALIGN.RIGHT, spc=0.5)
    footer(s, 3)
    notes(s, "Scope. 41 features excluding the class label; 39 after dropping "
             "num_outbound_cmds and is_host_login. Test_data.csv has 22,544 unlabelled rows.")


def slide_04(prs, a):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "03 / PREPROCESSING", "From raw traffic to model-ready data.")
    p = a["preprocessing"]
    rows = [
        ("41", "original features", "class label excluded  ·  KDD-style connection records"),
        ("39", "features after constant drop", "num_outbound_cmds, is_host_login removed"),
        ("79", "encoded features", "43 one-hot columns + 36 numeric features"),
        (f"{p['pca_components']}", "principal components",
         f"{p['pca_variance']:.1f}% of variance retained  ·  seed 42"),
    ]
    widths = [7.35, 6.85, 6.35, 5.55]
    ys = [1.82, 2.82, 3.82, 4.82]
    for i, ((num, lab, detail), w, y) in enumerate(zip(rows, widths, ys)):
        rect(s, ML, y, w, 0.82, fill=CARD, line=LINE, lw=0.6, radius=0.05)
        rect(s, ML, y, 0.05, 0.82, fill=(ACCENT if i == 3 else BLUE), radius=0)
        tx(s, ML + 0.18, y + 0.10, 0.95, 0.5, num, size=25, color=(ACCENT if i == 3 else TEXT),
           font=TITLE_FONT, bold=True, spc=-0.8)
        tx(s, ML + 1.18, y + 0.13, w - 1.35, 0.25, lab, size=11.5, color=TEXT,
           font=BODY_FONT, bold=True)
        tx(s, ML + 1.18, y + 0.42, w - 1.35, 0.26, detail, size=8.2, color=MUTED,
           font=BODY_FONT, line=1.0)
        if i < 3:
            vline(s, ML + 0.52, y + 0.82, 0.18, color=LINE, lw=0.8)

    # Two distinct spaces
    rect(s, 8.55, 1.82, 4.03, 2.05, fill=CARD, line=LINE, lw=0.6, radius=0.05)
    tx(s, 8.75, 1.96, 3.6, 0.18, "MODELING SPACE", size=7.6, color=ACCENT,
       font=MONO_FONT, bold=True, spc=1.1)
    tx(s, 8.75, 2.16, 1.4, 0.55, "20", size=33, color=TEXT, font=TITLE_FONT,
       bold=True, spc=-1.0)
    tx(s, 9.55, 2.32, 2.8, 0.24, "principal components", size=9.4, color=MUTED,
       font=BODY_FONT)
    tx(s, 8.75, 2.78, 3.6, 0.22, f"{p['pca_variance']:.1f}% variance retained",
       size=9.6, color=GOOD, font=MONO_FONT, bold=True)
    hline(s, 8.75, 3.12, 3.62, color=LINE, lw=0.6)
    tx(s, 8.75, 3.24, 3.6, 0.24, "Clustering operates here.", size=9.2, color=MUTED,
       font=BODY_FONT, bold=True)

    rect(s, 8.55, 4.05, 4.03, 2.05, fill=CARD, line=LINE, lw=0.6, radius=0.05)
    tx(s, 8.75, 4.19, 3.6, 0.18, "VISUALIZATION SPACE", size=7.6, color=WARN,
       font=MONO_FONT, bold=True, spc=1.1)
    tx(s, 8.75, 4.39, 1.4, 0.55, "2", size=33, color=TEXT, font=TITLE_FONT,
       bold=True, spc=-1.0)
    tx(s, 9.35, 4.55, 2.9, 0.24, "principal components", size=9.4, color=MUTED,
       font=BODY_FONT)
    tx(s, 8.75, 5.01, 3.6, 0.22, f"{p['pca2_variance']:.1f}% variance",
       size=9.6, color=WARN, font=MONO_FONT, bold=True)
    tx(s, 8.75, 5.26, 3.6, 0.2, f"PC1 {p['pc1']:.1f}%  +  PC2 {p['pc2']:.1f}%",
       size=8.2, color=MUTED, font=MONO_FONT)
    hline(s, 8.75, 5.54, 3.62, color=LINE, lw=0.6)
    tx(s, 8.75, 5.66, 3.6, 0.24, "Only for looking — never for clustering.",
       size=9.0, color=MUTED, font=BODY_FONT, bold=True)

    rect(s, ML, 6.18, CW, 0.48, fill=BG2, line=LINE, lw=0.5, radius=0.03)
    tx(s, ML + 0.16, 6.30, CW - 0.3, 0.22,
       'OneHotEncoder(protocol_type, service, flag)  ·  32 rare services → "other"  ·  '
       'log1p(duration, src_bytes, dst_bytes)  ·  StandardScaler(36)  ·  PCA(0.95)',
       size=7.4, color=MUTED, font=MONO_FONT)
    footer(s, 4)
    notes(s, "Preprocessing verified by re-running the pipeline. 41 features → 39 after "
             "dropping two constants; 43 one-hot + 36 numeric = 79; PCA retains 20 components "
             "at 95.6%. The 2D projection explains 39.2% (22.7% + 16.5%), not 31% as the earlier deck said.")


def slide_05(prs, a):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "04 / METHODS", "Three algorithms. Three perspectives.")
    specs = [
        ("K-MEANS", "Partition into k compact groups; every point belongs to its nearest centroid.",
         "Elbow + silhouette", "PARTITION", ACCENT, "concept_kmeans.png"),
        ("GAUSSIAN MIXTURE", "Model each group as a probability distribution; points may be shared.",
         "BIC + AIC", "PROBABILISTIC", BLUE, "concept_gmm.png"),
        ("DBSCAN", "Grow groups from dense regions; leave sparse points as noise.",
         "k-distance + min_samples", "DENSITY", GOOD, "concept_dbscan.png"),
    ]
    for i, (name, desc, sel, tag, col, img) in enumerate(specs):
        x = 0.75 + i * 4.0
        rect(s, x, 1.80, 3.55, 4.42, fill=CARD, line=LINE, lw=0.6, radius=0.05)
        rect(s, x, 1.80, 3.55, 0.045, fill=col, radius=0)
        s.shapes.add_picture(str(ASSETS / img), Inches(x + 0.10), Inches(1.94),
                             width=Inches(3.35), height=Inches(1.80))
        tx(s, x + 0.22, 3.88, 3.1, 0.3, name, size=15.5, color=TEXT,
           font=TITLE_FONT, bold=True, spc=-0.2)
        tx(s, x + 0.22, 4.20, 3.10, 0.62, desc, size=9.6, color=MUTED,
           font=BODY_FONT, line=1.24)
        tx(s, x + 0.22, 4.95, 3.0, 0.18, "SELECTION", size=6.8, color=DIM,
           font=MONO_FONT, bold=True, spc=1.0)
        tx(s, x + 0.22, 5.14, 3.1, 0.26, sel, size=9.8, color=TEXT,
           font=BODY_FONT, bold=True)
        pill(s, x + 0.22, 5.58, 1.55, 0.30, tag, col, size=7.2)

    tx(s, ML, 6.45, 11.6, 0.24,
       "All three operate in the 20-component PCA space. Diagrams are conceptual, "
       "not experimental output.",
       size=9.2, color=DIM, font=BODY_FONT)
    footer(s, 5)
    notes(s, "Methods. K-Means k range 2–15, n_init=10; GMM n_init=5; DBSCAN "
             "eps from the 90th percentile of 21-NN distances, min_samples=21.")


def slide_06(prs, a):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "05 / MODEL SELECTION", "The criteria disagree. The analyst decides.")
    sel = a["selection"]
    rows = [
        ["METHOD", "CRITERION", "RESULT"],
        ["K-Means", "Elbow", f"k = {sel['elbow_k']}"],
        ["K-Means", "Silhouette", f"k = {sel['best_sil_k']}"],
        ["GMM", "BIC", f"k = {sel['best_bic_k']}"],
        ["GMM", "AIC", f"k = {sel['best_aic_k']}"],
        ["DBSCAN", "k-distance", f"eps = {sel['eps']:.2f}"],
        ["DBSCAN", "min_samples", f"{sel['min_samples']}"],
        ["DBSCAN", "result", f"{sel['db_clusters']} clusters · {sel['db_outliers']} noise"],
    ]
    table(s, ML, 1.80, 5.55, 3.55, rows, [1.25, 1.55, 2.75], size=9.2,
          row_h=0.39, mono_cols=(2,))
    tx(s, ML, 5.48, 5.55, 0.2, "Silhouette sampled at 5,000 points.", size=7.4,
       color=DIM, font=BODY_FONT)

    s.shapes.add_picture(str(ASSETS / "selection_silhouette.png"), Inches(6.95),
                         Inches(1.78), width=Inches(5.55), height=Inches(1.89))
    tx(s, 6.95, 3.68, 5.5, 0.2,
       "Silhouette vs k  ·  k=4 selected for reporting, k=15 is the metric maximum",
       size=7.6, color=MUTED, font=BODY_FONT)
    s.shapes.add_picture(str(ASSETS / "selection_bic.png"), Inches(6.95),
                         Inches(3.90), width=Inches(5.55), height=Inches(1.89))
    tx(s, 6.95, 5.78, 5.5, 0.16,
       "BIC / AIC vs k  ·  both criteria minimise at k=14",
       size=7.6, color=MUTED, font=BODY_FONT)

    rect(s, ML, 5.98, CW, 0.78, fill=CARD, line=LINE, lw=0.6, radius=0.04)
    rect(s, ML, 5.98, 0.05, 0.78, fill=ACCENT, radius=0)
    tx(s, ML + 0.2, 6.06, 11.3, 0.18, "SELECTED FOR REPORTING — K-MEANS k=4",
       size=7.8, color=ACCENT, font=MONO_FONT, bold=True, spc=1.0)
    tx(s, ML + 0.2, 6.26, 11.35, 0.45,
       "Stable (ARI 0.9999), simple, and granular enough to brief an analyst. It is not "
       "the metric optimum: silhouette prefers k=15, BIC prefers k=14, and DBSCAN "
       "separates best but produces 24 micro-clusters.",
       size=9.2, color=TEXT, font=BODY_FONT, line=1.15)
    footer(s, 6)
    notes(s, "Selection results from re-running run_pair3.py. Elbow k=4; silhouette k=15 "
             "(0.7318); BIC and AIC both k=14; DBSCAN eps=0.9278 (0.93), min_samples=21, "
             "24 clusters, 723 noise points. The earlier deck reported AIC k=15; the code gives k=14.")


def slide_07(prs, a):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "06 / SCORECARD", "Separation is not the same as usefulness.")
    km, gmm, db = a["metrics"]["kmeans"], a["metrics"]["gmm"], a["metrics"]["dbscan"]
    st = a["stability"]
    max_sil = max(km["silhouette"], gmm["silhouette"], db["silhouette"])
    min_db = min(km["davies_bouldin"], gmm["davies_bouldin"], db["davies_bouldin"])
    max_ch = max(km["calinski_harabasz"], gmm["calinski_harabasz"], db["calinski_harabasz"])
    cards = [
        ("K-MEANS", f"{km['n_clusters']} clusters", ACCENT,
         [("SILHOUETTE  ↑", f"{km['silhouette']:.3f}", km["silhouette"] / max_sil),
          ("DAVIES–BOULDIN  ↓", f"{km['davies_bouldin']:.3f}", min_db / km["davies_bouldin"]),
          ("CALINSKI–HARABASZ  ↑", f"{km['calinski_harabasz']:,.0f}", km["calinski_harabasz"] / max_ch),
          ("STABILITY  ARI", f"{st['kmeans_mean']:.4f} ± {st['kmeans_std']:.4f}", st["kmeans_mean"])]),
        ("GMM", f"{gmm['n_clusters']} clusters", BLUE,
         [("SILHOUETTE  ↑", f"{gmm['silhouette']:.3f}", gmm["silhouette"] / max_sil),
          ("DAVIES–BOULDIN  ↓", f"{gmm['davies_bouldin']:.3f}", min_db / gmm["davies_bouldin"]),
          ("CALINSKI–HARABASZ  ↑", f"{gmm['calinski_harabasz']:,.0f}", gmm["calinski_harabasz"] / max_ch),
          ("STABILITY  ARI", f"{st['gmm_mean']:.3f} ± {st['gmm_std']:.3f}", st["gmm_mean"])]),
        ("DBSCAN", f"{db['n_clusters']} clusters", GOOD,
         [("SILHOUETTE  ↑", f"{db['silhouette']:.3f}", db["silhouette"] / max_sil),
          ("DAVIES–BOULDIN  ↓", f"{db['davies_bouldin']:.3f}", min_db / db["davies_bouldin"]),
          ("CALINSKI–HARABASZ  ↑", f"{db['calinski_harabasz']:,.0f}", db["calinski_harabasz"] / max_ch),
          ("STABILITY  ARI", "deterministic", 1.0)]),
    ]
    for i, (name, ncl, col, rows) in enumerate(cards):
        x = 0.75 + i * 3.8
        rect(s, x, 1.80, 3.55, 4.12, fill=CARD, line=LINE, lw=0.6, radius=0.05)
        tx(s, x + 0.2, 1.95, 2.2, 0.3, name, size=15.5, color=TEXT,
           font=TITLE_FONT, bold=True, spc=-0.2)
        pill(s, x + 2.35, 1.98, 1.0, 0.26, ncl.replace(" clusters", ""), col, size=7.4)
        for j, (lab, val, frac) in enumerate(rows):
            yy = 2.48 + j * 0.82
            tx(s, x + 0.2, yy, 3.0, 0.18, lab, size=6.9, color=MUTED,
               font=MONO_FONT, bold=True, spc=0.7)
            tx(s, x + 0.2, yy + 0.18, 3.1, 0.28, val,
               size=(11.6 if j == 3 else 15.0), color=TEXT, font=TITLE_FONT,
               bold=True, spc=-0.3)
            rect(s, x + 0.2, yy + 0.53, 3.10, 0.055, fill=LINE, radius=0.5)
            if frac > 0:
                rect(s, x + 0.2, yy + 0.53, max(0.05, 3.10 * min(1.0, frac)), 0.055,
                     fill=col, radius=0.5)
    tx(s, 8.55, 1.58, 4.0, 0.18, "BARS = RELATIVE GOODNESS WITHIN EACH METRIC",
       size=6.5, color=DIM, font=MONO_FONT, align=PP_ALIGN.RIGHT, spc=0.5)

    rich(s, ML, 6.08, 11.7, 0.26, [
        ("DBSCAN → best separation", {"color": GOOD, "bold": True}),
        ("     ·     ", {"color": DIM}),
        ("K-Means → best reproducibility", {"color": ACCENT, "bold": True}),
        ("     ·     ", {"color": DIM}),
        ("4 clusters → best interpretability", {"color": BLUE, "bold": True}),
    ], size=10.4)
    tx(s, ML, 6.42, 11.7, 0.3,
       "Computed in the 20-D PCA space. Silhouette sampled at 5,000 points; DBSCAN "
       "metrics exclude 723 noise points. ARI across 10 seeds.",
       size=7.5, color=DIM, font=BODY_FONT)
    footer(s, 7)
    notes(s, "Metrics from re-running the pipeline: K-Means 0.6078 / 0.9395 / 3610.20, "
             "ARI 0.99986 ± 0.00019; GMM 0.5058 / 1.5814 / 2260.34, ARI 0.92613 ± 0.06090; "
             "DBSCAN 0.7277 / 0.5848 / 8954.58, deterministic. DBSCAN has stronger separation "
             "but 24 micro-clusters; K-Means is the reproducible four-cluster reporting model.")


def slide_08(prs, a):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "07 / DISCOVERY", "Four clusters. Four behavioral signatures.")
    s.shapes.add_picture(str(ASSETS / "pca_clusters.png"), Inches(0.60),
                         Inches(1.72), width=Inches(6.70), height=Inches(4.72))
    tx(s, ML, 6.48, 6.5, 0.2,
       f"PCA 2D projection  ·  {a['preprocessing']['pca2_variance']:.1f}% of variance  ·  "
       "colored by archived cluster",
       size=7.4, color=DIM, font=MONO_FONT)

    # Native PowerPoint chart (editable) — records per archived cluster.
    cd = CategoryChartData()
    cd.categories = ["03  Ping sweep · 11.8%", "02  ICMP enumeration · 8.4%",
                     "01  SYN flood / DoS · 52.6%", "00  Connection scanning · 27.2%"]
    cd.add_series("Records", (1385, 988, 6181, 3189))
    gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(7.55), Inches(1.78),
                            Inches(4.95), Inches(2.95), cd)
    ch = gf.chart
    ch.has_legend = False
    ch.font.name = BODY_FONT
    ch.font.size = Pt(8.2)
    ch.font.color.rgb = TEXT
    chart_bg(ch, CARD)
    plot = ch.plots[0]
    plot.gap_width = 55
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.font.size = Pt(9.0); dl.font.name = MONO_FONT
    dl.font.color.rgb = TEXT; dl.font.bold = True
    dl.number_format = "#,##0"; dl.number_format_is_linked = False
    for idx, col in enumerate([C3, C2, C1, C0]):
        pt = plot.series[0].points[idx]
        pt.format.fill.solid(); pt.format.fill.fore_color.rgb = col
        pt.format.line.fill.background()
    ch.category_axis.tick_labels.font.size = Pt(8.2)
    ch.category_axis.tick_labels.font.name = BODY_FONT
    ch.category_axis.tick_labels.font.color.rgb = TEXT
    ch.category_axis.format.line.color.rgb = LINE
    ch.category_axis.has_major_gridlines = False
    ch.value_axis.visible = False
    ch.value_axis.has_major_gridlines = False

    tx(s, 7.55, 4.82, 4.95, 0.2, "BAR LENGTH = RECORDS IN THE ARCHIVED PARTITION",
       size=6.6, color=DIM, font=MONO_FONT, spc=0.5)
    tx(s, 7.55, 5.08, 4.95, 0.2, "ARCHIVED 4-CLUSTER PARTITION · GMM k=4",
       size=7.2, color=MUTED, font=MONO_FONT, bold=True, spc=0.6)
    rect(s, 7.55, 5.46, 4.95, 0.62, fill=CARD, line=WARN, lw=0.7, radius=0.04)
    rect(s, 7.55, 5.46, 0.05, 0.62, fill=WARN, radius=0)
    tx(s, 7.75, 5.56, 4.6, 0.4,
       "Behavioral clusters — not verified attack classifications.",
       size=10.2, color=WARN, font=BODY_FONT, bold=True, line=1.15)
    tx(s, 7.55, 6.24, 4.95, 0.4,
       "Exact counts from the archived assignment CSV — not rounded estimates.",
       size=7.2, color=DIM, font=BODY_FONT, line=1.2)
    footer(s, 8)
    notes(s, "Cluster sizes from pair3_cluster_assignments.csv: 3,189 / 6,181 / 988 / 1,385. "
             "They match the GMM k=4 partition exactly. The original deck's rounded sizes "
             "(~3,800 / ~5,200 / ~1,900 / ~800) do not match any artifact.")



# ── Slides 09–12: cluster profiles ───────────────────────────────────────────
def _diagram_scan(s, color):
    sx, sy = 6.95, 5.20
    circle(s, sx, sy, 0.17, color)
    tx(s, sx - 0.22, sy + 0.20, 0.44, 0.16, "SOURCE", size=5.8, color=DIM,
       font=MONO_FONT, align=PP_ALIGN.CENTER)
    targets = [(9.55, 4.45), (10.45, 4.25), (11.35, 4.45), (12.05, 4.95),
               (11.55, 5.65), (10.55, 5.85), (9.55, 5.65)]
    for tx_, ty_ in targets:
        arrow(s, sx + 0.17, sy, tx_ - 0.10, ty_, color=THREAT, lw=0.8,
              dash=MSO_LINE_DASH_STYLE.DASH)
        circle(s, tx_, ty_, 0.10, BG2, line=MUTED, lw=0.8)
        circle(s, tx_ + 0.055, ty_ - 0.055, 0.035, THREAT)
    tx(s, 6.95, 6.08, 5.5, 0.18, "REJ  ·  rerror_rate 1.00  ·  dst_host_count 255",
       size=7.2, color=THREAT, font=MONO_FONT)


def _diagram_syn(s, color):
    tx_, ty_ = 11.95, 5.15
    circle(s, tx_, ty_, 0.22, color)
    tx(s, tx_ - 0.30, ty_ + 0.26, 0.60, 0.16, "TARGET", size=5.8, color=DIM,
       font=MONO_FONT, align=PP_ALIGN.CENTER)
    sources = [(7.05, 4.35), (7.65, 5.05), (7.25, 5.80), (8.15, 4.30),
               (8.65, 5.10), (8.25, 5.95), (9.25, 4.55), (9.55, 5.65)]
    for x, y in sources:
        arrow(s, x, y, tx_ - 0.22, ty_, color=color, lw=0.9)
        circle(s, x, y, 0.065, color)
    tx(s, 7.05, 6.08, 5.4, 0.18, "S0  ·  serror_rate 1.00  ·  src_bytes 0  ·  dst_bytes 0",
       size=7.2, color=color, font=MONO_FONT)


def _diagram_icmp_enum(s, color):
    sx, sy = 6.95, 5.10
    hx_, hy_ = 9.30, 5.10
    circle(s, sx, sy, 0.15, color)
    tx(s, sx - 0.22, sy + 0.18, 0.44, 0.14, "SOURCE", size=5.8, color=DIM,
       font=MONO_FONT, align=PP_ALIGN.CENTER)
    arrow(s, sx + 0.15, sy, hx_ - 0.24, hy_, color=color, lw=1.0)
    circle(s, hx_, hy_, 0.23, color)
    tx(s, hx_ - 0.30, hy_ + 0.28, 0.60, 0.14, "HOST", size=5.8, color=DIM,
       font=MONO_FONT, align=PP_ALIGN.CENTER)
    for i in range(6):
        ang = math.radians(-90 + i * 60)
        px = hx_ + 0.62 * math.cos(ang)
        py = hy_ + 0.62 * math.sin(ang)
        arrow(s, hx_ + 0.23 * math.cos(ang), hy_ + 0.23 * math.sin(ang),
              px - 0.07 * math.cos(ang), py - 0.07 * math.sin(ang),
              color=color, lw=0.7, head=False)
        circle(s, px, py, 0.07, BG2, line=color, lw=0.8)
    tx(s, 6.95, 6.08, 5.5, 0.18, "ecr_i  ·  srv_count 99  ·  same_srv_rate 1.00  ·  520 B",
       size=7.2, color=color, font=MONO_FONT)


def _diagram_ping(s, color):
    sx, sy = 6.95, 5.10
    circle(s, sx, sy, 0.15, color)
    tx(s, sx - 0.22, sy + 0.18, 0.44, 0.14, "SOURCE", size=5.8, color=DIM,
       font=MONO_FONT, align=PP_ALIGN.CENTER)
    for i in range(6):
        x = 8.55 + i * 0.68
        arrow(s, sx + 0.15, sy, x - 0.09, sy, color=color, lw=0.8)
        circle(s, x, sy, 0.09, BG2, line=color, lw=0.9)
    tx(s, 6.95, 6.08, 5.4, 0.18, "eco_i  ·  src_bytes 8  ·  count 1  ·  dst_host_count 2",
       size=7.2, color=color, font=MONO_FONT)


def cluster_slide(prs, a, n, cid, kick, ttl, color, size, pct, signature,
                  interpretation, mitre, confidence, conf_color, features, diagram):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    kicker(s, kick)
    title(s, ttl, size=33)
    tx(s, ML, 1.66, 1.6, 0.18, f"CLUSTER {cid}", size=7.6, color=MUTED,
       font=MONO_FONT, bold=True, spc=1.2)
    section_number(s, 0.70, 1.82, cid, color)
    tx(s, ML, 2.94, 4.7, 0.22, f"{size:,} records  ·  {pct:.1f}% of anomalies",
       size=10.2, color=color, font=MONO_FONT, bold=True)
    tx(s, ML, 3.22, 4.75, 0.72, signature, size=16.2, color=TEXT,
       font=TITLE_FONT, bold=True, line=1.12)
    tx(s, ML, 4.10, 4.75, 0.95, interpretation, size=10.3, color=MUTED,
       font=BODY_FONT, line=1.30)

    rect(s, ML, 5.12, 4.95, 1.35, fill=CARD, line=LINE, lw=0.6, radius=0.04)
    tx(s, ML + 0.18, 5.24, 4.5, 0.16, "MITRE ATT&CK HYPOTHESES", size=7.2,
       color=ACCENT, font=MONO_FONT, bold=True, spc=1.0)
    tx(s, ML + 0.18, 5.46, 4.55, 0.22, f"{mitre[0][0]}   {mitre[0][1]}", size=9.3,
       color=TEXT, font=BODY_FONT, bold=True)
    tx(s, ML + 0.18, 5.72, 4.55, 0.22, f"{mitre[1][0]}   {mitre[1][1]}", size=9.3,
       color=TEXT, font=BODY_FONT, bold=True)
    pill(s, ML + 0.18, 6.02, 1.42, 0.27, f"CONFIDENCE {confidence}", conf_color, size=6.7)
    tx(s, ML, 6.60, 4.85, 0.18, "Hypothesis derived from feature patterns — not ground truth.",
       size=6.8, color=DIM, font=BODY_FONT, italic=True)

    tx(s, 6.15, 1.66, 6.2, 0.18, "BEHAVIORAL SIGNATURE", size=7.6, color=MUTED,
       font=MONO_FONT, bold=True, spc=1.1)
    for i, (label, value) in enumerate(features):
        col = i % 4
        row = i // 4
        x = 6.15 + col * 1.58
        y = 1.92 + row * 0.76
        rect(s, x, y, 1.48, 0.64, fill=BG2, line=LINE, lw=0.5, radius=0.04)
        tx(s, x + 0.09, y + 0.08, 1.30, 0.16, label.upper(), size=6.3,
           color=DIM, font=MONO_FONT, bold=True, spc=0.5)
        tx(s, x + 0.09, y + 0.28, 1.32, 0.28, value, size=11.2, color=TEXT,
           font=MONO_FONT, bold=True)
    tx(s, 6.15, 3.58, 6.2, 0.18, "CONCEPTUAL PATTERN", size=7.2, color=DIM,
       font=MONO_FONT, bold=True, spc=1.0)
    rect(s, 6.15, 3.82, 6.35, 2.55, fill=BG2, line=LINE, lw=0.5, radius=0.04)
    diagram(s, color)
    tx(s, 6.15, 6.44, 6.2, 0.18, "Conceptual illustration — not a packet capture.",
       size=6.8, color=DIM, font=BODY_FONT, italic=True)
    footer(s, n)
    return s


def slide_09(prs, a):
    p = a["profiles"]["0"]
    s = cluster_slide(
        prs, a, 9, "00", "08 / CLUSTER 00", "Broad probing, rejected connections.",
        C0, p["size"], p["pct"],
        "Many destinations, few services, every connection rejected.",
        "Broad target coverage with rejected connections and relatively few services "
        "probed. The pattern is consistent with active scanning that never completes a session.",
        [("T1595", "Active Scanning"), ("T1046", "Network Service Discovery")],
        "HIGH", GOOD,
        [("protocol", p["protocol_type"]), ("service", p["service"]),
         ("flag", p["flag"]), ("count", f"{p['count']:.0f}"),
         ("srv_count", f"{p['srv_count']:.0f}"), ("rerror_rate", f"{p['rerror_rate']:.2f}"),
         ("dst_host_count", f"{p['dst_host_count']:.0f}"), ("src_bytes", f"{p['src_bytes']:.0f}")],
        _diagram_scan)
    notes(s, "Cluster 00 profile from pair3_cluster_profiles.csv: TCP / private / REJ, "
             "count 121, srv_count 4, rerror_rate 1.0, dst_host_count 255, src_bytes 0. "
             "Size 3,189 (27.2%). MITRE mapping from pair3_mitre_mapping.json; confidence High.")


def slide_10(prs, a):
    p = a["profiles"]["1"]
    s = cluster_slide(
        prs, a, 10, "01", "09 / CLUSTER 01", "Half-open connections at volume.",
        C1, p["size"], p["pct"],
        "SYN attempts with no handshake and no payload.",
        "High-volume TCP connection attempts with SYN errors and no payload transfer. "
        "Half-open connections are the signature of a SYN flood.",
        [("T1499", "Endpoint Denial of Service"), ("T1498", "Network Denial of Service")],
        "HIGH", GOOD,
        [("protocol", p["protocol_type"]), ("service", p["service"]),
         ("flag", p["flag"]), ("count", f"{p['count']:.0f}"),
         ("srv_count", f"{p['srv_count']:.0f}"), ("serror_rate", f"{p['serror_rate']:.2f}"),
         ("src_bytes", f"{p['src_bytes']:.0f}"), ("dst_bytes", f"{p['dst_bytes']:.0f}")],
        _diagram_syn)
    notes(s, "Cluster 01 profile: TCP / private / S0, count 199, srv_count 11, "
             "serror_rate 1.0, src_bytes 0, dst_bytes 0. Size 6,181 (52.6%). "
             "MITRE T1499 / T1498; confidence High.")


def slide_11(prs, a):
    p = a["profiles"]["2"]
    s = cluster_slide(
        prs, a, 11, "02", "10 / CLUSTER 02", "One host, many services.",
        C2, p["size"], p["pct"],
        "Echo-reply traffic concentrated on a single target host.",
        "ICMP echo-reply traffic with a high service count and consistent service behavior. "
        "The pattern suggests service enumeration from a single source.",
        [("T1595", "Active Scanning"), ("T1046", "Network Service Discovery")],
        "MEDIUM-HIGH", ACCENT,
        [("protocol", p["protocol_type"]), ("service", p["service"]),
         ("flag", p["flag"]), ("count", f"{p['count']:.1f}"),
         ("srv_count", f"{p['srv_count']:.0f}"), ("same_srv_rate", f"{p['same_srv_rate']:.2f}"),
         ("src_bytes", f"{p['src_bytes']:.0f}"), ("dst_host_count", f"{p['dst_host_count']:.0f}")],
        _diagram_icmp_enum)
    notes(s, "Cluster 02 profile: ICMP / ecr_i / SF, count 119.5, srv_count 99, "
             "same_srv_rate 1.0, src_bytes 520, dst_host_count 255. Size 988 (8.4%). "
             "MITRE T1595 / T1046; confidence Medium-High.")


def slide_12(prs, a):
    p = a["profiles"]["3"]
    s = cluster_slide(
        prs, a, 12, "03", "11 / CLUSTER 03", "A small payload, a wide sweep.",
        C3, p["size"], p["pct"],
        "Echo-request traffic built for host discovery.",
        "ICMP echo-request traffic with a tiny payload and a narrow destination set. "
        "The pattern is consistent with host discovery before a deeper scan.",
        [("T1595.001", "Scanning IP Blocks"), ("T1018", "Remote System Discovery")],
        "MEDIUM", WARN,
        [("protocol", p["protocol_type"]), ("service", p["service"]),
         ("flag", p["flag"]), ("src_bytes", f"{p['src_bytes']:.0f}"),
         ("count", f"{p['count']:.0f}"), ("srv_count", f"{p['srv_count']:.0f}"),
         ("dst_host_count", f"{p['dst_host_count']:.0f}"), ("same_srv_rate", f"{p['same_srv_rate']:.2f}")],
        _diagram_ping)
    notes(s, "Cluster 03 profile: ICMP / eco_i / SF, src_bytes 8, count 1, srv_count 6, "
             "dst_host_count 2. Size 1,385 (11.8%). MITRE T1595.001 / T1018; confidence Medium.")


# ── Slide 13: normal vs anomalous ────────────────────────────────────────────
def slide_13(prs, a):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "12 / CONTRAST", "Normal is heterogeneous. Anomalies are not.")
    n, an = a["normal_stats"], a["anomaly_stats"]

    def panel(x, label, color, stats, is_normal):
        rect(s, x, 1.78, 5.70, 3.72, fill=CARD, line=LINE, lw=0.6, radius=0.05)
        tx(s, x + 0.22, 1.94, 2.4, 0.2, label, size=8.0, color=color,
           font=MONO_FONT, bold=True, spc=1.2)
        tx(s, x + 0.22, 2.16, 5.2, 0.2,
           f"{stats['rows']:,} records  ·  {stats['pct']:.1f}% of training set",
           size=9.2, color=MUTED, font=MONO_FONT)
        # 100% stacked flag bar
        y = 2.48
        w = 5.26
        segs = ([("SF", stats["flags"].get("SF", 0), BLUE),
                 ("REJ", stats["flags"].get("REJ", 0), WARN),
                 ("S1", stats["flags"].get("S1", 0), MUTED),
                 ("other", max(0.0, 100 - stats["flags"].get("SF", 0)
                               - stats["flags"].get("REJ", 0) - stats["flags"].get("S1", 0)), LINE)]
                if is_normal else
                [("S0", stats["flags"].get("S0", 0), THREAT),
                 ("SF", stats["flags"].get("SF", 0), BLUE),
                 ("REJ", stats["flags"].get("REJ", 0), WARN),
                 ("RSTR", stats["flags"].get("RSTR", 0), ACCENT),
                 ("other", max(0.0, 100 - stats["flags"].get("S0", 0)
                               - stats["flags"].get("SF", 0) - stats["flags"].get("REJ", 0)
                               - stats["flags"].get("RSTR", 0)), LINE)])
        cx = x + 0.22
        for name, pct, col in segs:
            sw = w * pct / 100.0
            if sw > 0:
                rect(s, cx, y, sw, 0.22, fill=col, radius=0)
                if sw > 0.55:
                    tx(s, cx + 0.06, y + 0.04, sw - 0.1, 0.16, f"{name} {pct:.1f}%",
                       size=6.4, color=(BG if col in (WARN, GOOD, ACCENT) else TEXT),
                       font=MONO_FONT, bold=True)
            cx += sw
        # legend
        lx = x + 0.22
        for name, pct, col in segs:
            circle(s, lx + 0.04, 2.91, 0.035, col)
            tx(s, lx + 0.12, 2.84, 0.9, 0.16, f"{name} {pct:.1f}%", size=6.5,
               color=MUTED, font=MONO_FONT)
            lx += 1.02

        metrics = [("logged_in", stats["logged_in"], 100, "%"),
                   ("serror_rate", stats["serror"], 100, "%"),
                   ("SF flag share", stats["flags"].get("SF", 0), 100, "%"),
                   ("median src_bytes", stats["src_median"], 250, " B")]
        for j, (lab, val, mx, unit) in enumerate(metrics):
            yy = 3.28 + j * 0.50
            tx(s, x + 0.22, yy, 1.75, 0.18, lab, size=7.2, color=MUTED,
               font=MONO_FONT, bold=True, spc=0.4)
            tx(s, x + 1.95, yy - 0.04, 1.35, 0.24,
               (f"{val:.1f}{unit}" if unit == "%" else f"{val:.0f}{unit}"),
               size=11.4, color=TEXT, font=MONO_FONT, bold=True)
            rect(s, x + 3.30, yy + 0.06, 2.15, 0.055, fill=LINE, radius=0.5)
            rect(s, x + 3.30, yy + 0.06, max(0.04, 2.15 * min(1.0, val / mx)), 0.055,
                 fill=color, radius=0.5)

    panel(0.75, "NORMAL", BLUE, n, True)
    panel(6.88, "ANOMALIES", THREAT, an, False)
    circle(s, 6.665, 3.65, 0.24, BG, line=LINE, lw=0.8)
    tx(s, 6.55, 3.57, 0.24, 0.16, "VS", size=6.8, color=MUTED, font=MONO_FONT,
       bold=True, align=PP_ALIGN.CENTER)

    tx(s, ML, 5.66, 11.8, 0.45,
       "Normal traffic is heterogeneous; the anomaly clusters collapse into a few "
       "extreme, homogeneous signatures.",
       size=13.2, color=TEXT, font=TITLE_FONT, bold=True, line=1.15)
    tx(s, ML, 6.18, 11.8, 0.2,
       "The four archived clusters have logged_in = 0, and their flag / error-rate "
       "profiles sit at the extremes.",
       size=9.2, color=MUTED, font=BODY_FONT)
    rect(s, ML, 6.52, 0.04, 0.30, fill=WARN, radius=0)
    tx(s, ML + 0.16, 6.52, 11.6, 0.30,
       "The 'normal' class is synthetic / network background — not a representative "
       "sample of benign internet traffic.",
       size=8.2, color=WARN, font=BODY_FONT, line=1.15)
    footer(s, 13)
    notes(s, "Normal vs anomaly statistics from Train_data.csv. Normal: 13,449 rows, "
             "SF 94.2%, logged_in 70.9%, serror 1.5%, median src_bytes 234. Anomalies: "
             "11,743 rows, S0 59.0%, logged_in 3.5%, serror 59.7%, median src_bytes 0.")


# ── Slide 14: HoneyBadger connection ────────────────────────────────────────
def slide_14(prs, a):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "13 / HONEYBADGER", "From research to the honeypot.")
    cols = [
        ("WHAT OVERLAPS", ACCENT, [
            ("service → ", "RawEvent.service (ssh / http)"),
            ("login counts → ", "derivable from login_info + technique_id"),
            ("count / srv_count → ", "aggregations over source_ip + time windows"),
            ("dst_host_* → ", "destination-side aggregates from destination_ip; not stored"),
        ]),
        ("WHAT KAGGLE HAS", THREAT, [
            ("TCP flags ", "(S0, REJ, SF) — not captured"),
            ("serror_rate / rerror_rate ", "— not captured"),
            ("duration ", "— not captured"),
            ("src_bytes / dst_bytes ", "— not captured"),
            ("window aggregates ", "same_srv_rate, diff_srv_rate, dst_host_* rates"),
        ]),
        ("WHAT HONEYBADGER ADDS", BLUE, [
            ("technique_id ", "rule-based, backend/mitre.py"),
            ("credentials ", "username + SHA-256 hash"),
            ("payloads ", "URL, hash, size — never fetched"),
            ("GeoIP ", "country, city, ASN"),
            ("source IP + timestamps ", "—"),
            ("shell commands, HTTP method / path / UA ", "—"),
        ]),
    ]
    for i, (head, col, items) in enumerate(cols):
        x = 0.75 + i * 3.80
        rect(s, x, 1.78, 3.55, 3.55, fill=CARD, line=LINE, lw=0.6, radius=0.05)
        rect(s, x, 1.78, 3.55, 0.045, fill=col, radius=0)
        tx(s, x + 0.2, 1.94, 3.1, 0.2, head, size=7.6, color=col,
           font=MONO_FONT, bold=True, spc=1.0)
        bullets(s, x + 0.2, 2.24, 3.12, 2.95, items, size=8.6, color=MUTED,
                gap=6, line=1.16, prefix_color=col, prefix="›  ")

    # architecture strip
    nodes = [("SSH / HTTP SENSOR", 2.05), ("RAW EVENT", 1.55),
             ("ENRICHMENT", 2.55), ("POSTGRESQL", 1.75), ("DASHBOARD", 1.75)]
    x = 0.75
    for i, (label, w) in enumerate(nodes):
        rect(s, x, 5.62, w, 0.55, fill=BG2, line=LINE, lw=0.6, radius=0.04)
        tx(s, x, 5.74, w, 0.18, label, size=6.6, color=(ACCENT if i == 2 else TEXT),
           font=MONO_FONT, bold=True, align=PP_ALIGN.CENTER, spc=0.5)
        if i == 2:
            tx(s, x, 5.94, w, 0.16, "GeoIP · MITRE · credentials · payloads",
               size=5.4, color=MUTED, font=MONO_FONT, align=PP_ALIGN.CENTER)
        if i < 4:
            tx(s, x + w + 0.03, 5.74, 0.22, 0.2, "›", size=12, color=DIM,
               font=BODY_FONT, bold=True, align=PP_ALIGN.CENTER)
        x += w + 0.28

    tx(s, ML, 6.38, 11.8, 0.3,
       "This experiment validates the behavioral grouping approach — not a directly "
       "deployable model.",
       size=11.8, color=ACCENT, font=BODY_FONT, bold=True)
    footer(s, 14)
    notes(s, "HoneyBadger fields verified in backend/schemas.py, backend/pipeline.py, "
             "backend/storage.py, backend/mitre.py. HoneyBadger stores application-level "
             "events, not TCP flow records; Kaggle features are not directly available. "
             "technique_id is rule-based, not learned.")


# ── Slide 15: limitations ───────────────────────────────────────────────────
def slide_15(prs, a):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "14 / LIMITATIONS", "What this experiment cannot tell us.")
    items = [
        ("01", "No ground-truth attack-type labels."),
        ("02", "Kaggle features ≠ HoneyBadger events."),
        ("03", "SSH subset: 58 records, all anomalies."),
        ("04", "Attack families may overlap."),
        ("05", "Normal traffic is synthetic / background."),
        ("06", "K-Means assumes spherical, similar-sized clusters."),
        ("07", "Single dataset snapshot; no temporal validation."),
        ("08", "Feature engineering choices shape the result."),
    ]
    for i, (num, text) in enumerate(items):
        col = i % 2
        row = i // 2
        x = 0.75 + col * 3.15
        y = 1.84 + row * 0.98
        tx(s, x, y, 0.35, 0.18, num, size=7.8, color=THREAT,
           font=MONO_FONT, bold=True)
        tx(s, x + 0.38, y - 0.01, 2.55, 0.75, text, size=9.8, color=TEXT,
           font=BODY_FONT, line=1.18)

    rect(s, 7.35, 1.82, 5.20, 3.95, fill=CARD, line=LINE, lw=0.6, radius=0.05)
    rect(s, 7.35, 1.82, 0.06, 3.95, fill=THREAT, radius=0)
    tx(s, 7.62, 2.02, 4.7, 0.2, "THE CENTRAL LIMITATION", size=8.0, color=THREAT,
       font=MONO_FONT, bold=True, spc=1.1)
    tx(s, 7.62, 2.34, 4.65, 1.85,
       "MITRE ATT&CK mappings are hypotheses derived from observed feature patterns "
       "— not independently verified classifications.",
       size=15.2, color=TEXT, font=TITLE_FONT, bold=True, line=1.22)
    hline(s, 7.62, 4.35, 4.6, color=LINE, lw=0.7)
    tx(s, 7.62, 4.52, 4.6, 0.6,
       "No label exists in the dataset to confirm an attack family. Confidence is an "
       "analyst judgement, not a measured accuracy.",
       size=9.0, color=MUTED, font=BODY_FONT, line=1.25)

    rect(s, ML, 5.95, CW, 0.76, fill=BG2, line=LINE, lw=0.5, radius=0.03)
    rect(s, ML, 5.95, 0.045, 0.76, fill=WARN, radius=0)
    tx(s, ML + 0.18, 6.05, 11.45, 0.18, "REPRODUCIBILITY NOTE", size=7.0,
       color=WARN, font=MONO_FONT, bold=True, spc=1.0)
    tx(s, ML + 0.18, 6.24, 11.45, 0.4,
       "The archived assignments were produced by GMM k=4. The documented K-Means k=4 "
       "selection collapses one cluster to a single record in the current environment. "
       "Re-run and archive the model and labels together.",
       size=7.8, color=MUTED, font=BODY_FONT, line=1.18)
    footer(s, 15)
    notes(s, "Limitations. SSH: 58 rows, all anomalies. K-Means k=4 sizes in the current "
             "environment are 2,591 / 6,989 / 1 / 2,162 (degenerate singleton); the archived "
             "CSV is the GMM partition 3,189 / 6,181 / 988 / 1,385. This provenance gap is "
             "disclosed rather than hidden.")


# ── Slide 16: roadmap ───────────────────────────────────────────────────────
def slide_16(prs, a):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "15 / ROAD AHEAD", "From a research partition to an operational signal.")
    stages = [
        ("01", "VALIDATION", ACCENT, [
            "Expert review of cluster interpretations.",
            "Test on HoneyBadger event exports.",
            "Compare with Pair 1 and Pair 2 findings.",
        ]),
        ("02", "METHODOLOGICAL", BLUE, [
            "Hierarchical clustering for sub-families.",
            "Semi-supervised learning with weak MITRE labels.",
            "Temporal clustering of attack campaigns.",
            "Feature importance per cluster.",
        ]),
        ("03", "PRODUCTION", GOOD, [
            "Collect labeled HoneyBadger sessions.",
            "Train on HoneyBadger-native features.",
            "Investigate online clustering.",
            "Dashboard: cluster ID + MITRE hypothesis + triage.",
        ]),
    ]
    for i, (num, name, col, items) in enumerate(stages):
        x = 0.75 + i * 3.80
        rect(s, x, 1.78, 3.55, 3.78, fill=CARD, line=LINE, lw=0.6, radius=0.05)
        rect(s, x, 1.78, 3.55, 0.045, fill=col, radius=0)
        tx(s, x + 0.2, 1.96, 0.5, 0.2, num, size=8.0, color=col,
           font=MONO_FONT, bold=True, spc=1.0)
        tx(s, x + 0.2, 2.22, 3.1, 0.3, name, size=14.5, color=TEXT,
           font=TITLE_FONT, bold=True, spc=-0.2)
        bullets(s, x + 0.2, 2.68, 3.1, 2.7, items, size=9.0, color=MUTED,
                gap=8, line=1.2, prefix_color=col, prefix="—  ")

    hline(s, 0.95, 5.88, 11.4, color=LINE, lw=0.8)
    for x, lab in [(2.52, "NOW"), (6.32, "NEXT"), (10.12, "LATER")]:
        circle(s, x, 5.88, 0.055, BG, line=LINE, lw=0.8)
        circle(s, x, 5.88, 0.028, ACCENT)
        tx(s, x - 0.35, 5.98, 0.7, 0.16, lab, size=6.2, color=DIM,
           font=MONO_FONT, align=PP_ALIGN.CENTER, spc=0.8)

    tx(s, ML, 6.18, 11.8, 0.4,
       "From unexplained anomalies to interpretable behavioral intelligence.",
       size=19.0, color=TEXT, font=TITLE_FONT, bold=True, align=PP_ALIGN.CENTER, spc=-0.4)
    tx(s, ML, 6.62, 11.8, 0.2,
       "4 behavioral clusters   ·   4 attack-family hypotheses   ·   1 foundation for further validation",
       size=8.2, color=ACCENT, font=MONO_FONT, align=PP_ALIGN.CENTER, spc=0.7)
    footer(s, 16)
    notes(s, "Roadmap. Stage 1 validation; stage 2 methodological improvements; stage 3 "
             "production path. The experiment is a foundation, not a deployed classifier.")


# ── Slide 17: Q&A ───────────────────────────────────────────────────────────
def slide_17(prs, a):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    s.shapes.add_picture(str(ASSETS / "title_network.png"), Inches(6.55), Inches(0),
                         width=Inches(6.78), height=Inches(7.5))
    tx(s, ML, 1.35, 5.5, 0.2, "PAIR 03  ·  HONEYBADGER", size=9.0, color=ACCENT,
       font=MONO_FONT, bold=True, spc=1.6)
    tx(s, 0.72, 1.62, 5.4, 1.2, "Q&A", size=96, color=ACCENT, font=TITLE_FONT,
       bold=True, spc=-3)
    tx(s, ML, 3.08, 5.45, 0.8,
       "From unexplained anomalies to interpretable behavioral intelligence.",
       size=17.0, color=TEXT, font=TITLE_FONT, bold=True, line=1.18)
    tx(s, ML, 4.02, 5.2, 0.3, "Thank you.", size=13.0, color=MUTED, font=BODY_FONT)
    hline(s, ML, 4.55, 1.1, color=ACCENT, lw=1.6)

    stats = [("4", "behavioral clusters"), ("4", "attack-family hypotheses"),
             ("1", "foundation for validation")]
    for i, (v, lab) in enumerate(stats):
        x = 0.75 + i * 1.85
        tx(s, x, 4.85, 0.8, 0.45, v, size=26, color=TEXT, font=TITLE_FONT,
           bold=True, spc=-0.8)
        tx(s, x, 5.32, 1.62, 0.4, lab, size=7.6, color=MUTED, font=BODY_FONT,
           line=1.15)
    tx(s, ML, 6.28, 5.8, 0.2, "github.com/scriptsl0th/HoneyBadger", size=8.2,
       color=MUTED, font=MONO_FONT)
    tx(s, ML, 6.55, 5.8, 0.2, "HONEYBADGER  ·  PAIR 03  ·  ATTACK TYPE PROFILING",
       size=6.8, color=DIM, font=MONO_FONT, spc=0.6)
    footer(s, 17)
    notes(s, "Q&A. Closing statement: 4 behavioral clusters, 4 attack-family hypotheses, "
             "1 foundation for further validation. All mappings remain hypotheses.")


# ── Build / render ──────────────────────────────────────────────────────────
def build_deck(a):
    prs = Presentation()
    prs.slide_width = Inches(SW)
    prs.slide_height = Inches(SH)
    slide_01(prs, a); slide_02(prs, a); slide_03(prs, a); slide_04(prs, a)
    slide_05(prs, a); slide_06(prs, a); slide_07(prs, a); slide_08(prs, a)
    slide_09(prs, a); slide_10(prs, a); slide_11(prs, a); slide_12(prs, a)
    slide_13(prs, a); slide_14(prs, a); slide_15(prs, a); slide_16(prs, a)
    slide_17(prs, a)
    prs.save(OUT_PPTX)
    print(f"Saved: {OUT_PPTX}")


def _font(path, size):
    try:
        return ImageFont.truetype(str(path), size)
    except Exception:
        return ImageFont.load_default()


def contact_sheet(pdf_path, out_path):
    tmp = Path("/tmp/hb_pair3_slides")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    subprocess.run(["pdftoppm", "-png", "-r", "110", str(pdf_path),
                    str(tmp / "slide")], check=True)
    files = sorted(tmp.glob("slide-*.png"))
    if not files:
        print("No rendered slides found.")
        return
    thumb_w, thumb_h = 480, 270
    cols, gap, margin, header = 4, 22, 36, 74
    rows = math.ceil(len(files) / cols)
    W = margin * 2 + cols * thumb_w + (cols - 1) * gap
    H = header + margin + rows * (thumb_h + 24) + (rows - 1) * gap
    sheet = Image.new("RGB", (W, H), "#090D14")
    d = ImageDraw.Draw(sheet)
    f_title = _font(Path.home() / ".local/share/fonts/SpaceGrotesk-Bold.ttf", 22)
    f_sub = _font(Path.home() / ".local/share/fonts/JetBrainsMono-Regular.ttf", 9)
    f_num = _font(Path.home() / ".local/share/fonts/JetBrainsMono-Bold.ttf", 9)
    d.text((margin, 20), "HONEYBADGER  ·  PAIR 03", font=f_title, fill="#F1F5F9")
    d.text((margin, 48), "SLIDE CONTACT SHEET  ·  17 SLIDES", font=f_sub, fill="#22D3EE")
    for i, f in enumerate(files):
        r, c = divmod(i, cols)
        x = margin + c * (thumb_w + gap)
        y = header + r * (thumb_h + 24 + gap)
        d.text((x, y - 15), f"{i+1:02d}", font=f_num, fill="#94A3B8")
        img = Image.open(f).convert("RGB").resize((thumb_w, thumb_h), Image.LANCZOS)
        sheet.paste(img, (x, y))
        d.rectangle([x - 1, y - 1, x + thumb_w, y + thumb_h], outline="#243044")
    sheet.save(out_path)
    print(f"Saved: {out_path}")


def render_outputs():
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        print("LibreOffice not found; skipping PDF. Use the Docker render step or install LibreOffice.")
        return
    subprocess.run([soffice, "--headless", "--convert-to", "pdf",
                    "--outdir", str(OUT_PDF.parent), str(OUT_PPTX)], check=True)
    print(f"Saved: {OUT_PDF}")
    contact_sheet(OUT_PDF, OUT_SHEET)


def main():
    force = "--force" in sys.argv
    a = ensure_analysis(force=force)
    build_assets(a, force=force)
    build_deck(a)
    if "--render" in sys.argv:
        render_outputs()


if __name__ == "__main__":
    main()
