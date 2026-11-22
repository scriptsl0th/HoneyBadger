#!/usr/bin/env python3
"""
Generate Pair 3 Clustering Presentation (PPTX)
Run: .venv/bin/python generate_presentation.py
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import pandas as pd
import json
import numpy as np

# ─── Color Palette ───
DARK_BG = RGBColor(0x1A, 0x1A, 0x2E)
CARD_BG = RGBColor(0x16, 0x21, 0x3E)
ACCENT_RED = RGBColor(0xEB, 0x68, 0x34)
ACCENT_BLUE = RGBColor(0x2A, 0x78, 0xD6)
ACCENT_GREEN = RGBColor(0x2E, 0xCC, 0x71)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xCC, 0xCC, 0xCC)
MID_GRAY = RGBColor(0x88, 0x88, 0x88)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

def add_bg(slide, color=DARK_BG):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color

def add_textbox(slide, left, top, width, height, text, font_size=18, bold=False, color=WHITE, alignment=PP_ALIGN.LEFT, font_name='Calibri'):
    txBox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = font_name
    p.alignment = alignment
    return txBox

def add_bullet_slide(slide, left, top, width, height, items, font_size=16, color=WHITE, spacing=Pt(6), bold_first=False):
    txBox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = item
        p.font.size = Pt(font_size)
        p.font.color.rgb = color
        p.font.name = 'Calibri'
        p.space_after = spacing
        if bold_first and i == 0:
            p.font.bold = True
    return txBox

def add_table(slide, left, top, width, height, rows, cols, data, col_widths=None):
    table_shape = slide.shapes.add_table(rows, cols, Inches(left), Inches(top), Inches(width), Inches(height))
    table = table_shape.table
    if col_widths:
        for i, w in enumerate(col_widths):
            table.columns[i].width = Inches(w)
    for r, row_data in enumerate(data):
        for c, cell_text in enumerate(row_data):
            cell = table.cell(r, c)
            cell.text = str(cell_text)
            for paragraph in cell.text_frame.paragraphs:
                paragraph.font.size = Pt(12)
                paragraph.font.color.rgb = WHITE
                paragraph.font.name = 'Calibri'
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    # Style header row
    for c in range(cols):
        cell = table.cell(0, c)
        for paragraph in cell.text_frame.paragraphs:
            paragraph.font.bold = True
            paragraph.font.color.rgb = ACCENT_RED
            paragraph.font.size = Pt(13)
        cell.fill.solid()
        cell.fill.fore_color.rgb = CARD_BG
    return table_shape

# ═══════════════════════════════════════════════════════════════
# SLIDE 1: TITLE
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
add_bg(slide)

add_textbox(slide, 1.5, 1.5, 10, 1.2, "HoneyBadger", 48, True, ACCENT_RED)
add_textbox(slide, 1.5, 2.5, 10, 0.8, "Pair 3: Profile Attack Types (Clustering)", 32, False, WHITE)
add_textbox(slide, 1.5, 3.5, 10, 0.6, "Offline Analysis of Kaggle Network Intrusion Detection Dataset", 20, False, LIGHT_GRAY)
add_textbox(slide, 1.5, 4.5, 10, 0.5, "Unsupervised grouping of 11,743 anomalies → MITRE ATT&CK hypotheses", 18, False, ACCENT_BLUE)
add_textbox(slide, 1.5, 5.5, 10, 0.4, "Kaggle: sampadab17/network-intrusion-detection  |  Train: 25,192 rows (13,449 normal, 11,743 anomaly)", 14, False, MID_GRAY)

# ═══════════════════════════════════════════════════════════════
# SLIDE 2: OBJECTIVE & APPROACH
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_textbox(slide, 0.8, 0.4, 11, 0.6, "Objective & Approach", 32, True, ACCENT_RED)

items = [
    "Business Question: Can we group 'anomaly' traffic into attack families (floods, scans, brute-force) so analysts know what they're facing?",
    "Dataset: Kaggle Network Intrusion Detection (KDD-style, 41 features, binary labels)",
    "Scope: Cluster ONLY the 11,743 anomaly rows — no labels for attack types exist",
    "Methods: K-Means (elbow/silhouette), Gaussian Mixture (BIC), DBSCAN (k-distance)",
    "Evaluation: Silhouette, Davies-Bouldin, Calinski-Harabasz + Stability (ARI across 10 seeds)",
    "Output: 4 interpretable clusters → MITRE ATT&CK technique hypotheses",
]
add_bullet_slide(slide, 0.8, 1.2, 11.5, 5.5, items, 18, WHITE, Pt(10))

add_textbox(slide, 0.8, 6.2, 11, 0.5, "⚠ No ground-truth attack labels — all MITRE mappings are hypotheses from feature patterns", 16, True, ACCENT_RED)

# ═══════════════════════════════════════════════════════════════
# SLIDE 3: DATA PREPARATION
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_textbox(slide, 0.8, 0.4, 11, 0.6, "Data Preparation", 32, True, ACCENT_RED)

items = [
    "Source: Train_data.csv — filter class == 'anomaly' (11,743 rows)",
    "Drop constant columns: num_outbound_cmds, is_host_login (zero variance)",
    "Categorical (3): protocol_type, service, flag → OneHotEncoder (handle_unknown='ignore')",
    "  • Rare services (<100 occurrences) grouped into 'other' to limit cardinality",
    "Numeric (38): StandardScaler; skewed (duration, src_bytes, dst_bytes) → log1p first",
    "PCA: 95% variance → 20 components (from 79 encoded features)",
    "Visualization PCA: 2 components (18.7% + 12.3% = 31% variance)",
]
add_bullet_slide(slide, 0.8, 1.2, 11.5, 5.5, items, 17, WHITE, Pt(8))

# ═══════════════════════════════════════════════════════════════
# SLIDE 4: MODEL SELECTION
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_textbox(slide, 0.8, 0.4, 11, 0.6, "Model Selection Results", 32, True, ACCENT_RED)

data = [
    ["Method", "Selection Criterion", "Optimal k / eps", "Clusters Found"],
    ["K-Means", "Elbow (inertia curvature)", "k=4", "4"],
    ["K-Means", "Silhouette (sampled)", "k=15", "—"],
    ["GMM", "BIC (Bayesian Info Criterion)", "k=14", "—"],
    ["GMM", "AIC", "k=15", "—"],
    ["DBSCAN", "k-distance 90th percentile", "eps=0.93, min_samples=21", "24 (+723 outliers)"],
]
add_table(slide, 0.8, 1.2, 11.5, 2.5, 6, 4, data, [2.5, 3.5, 3.5, 2])

add_textbox(slide, 0.8, 3.9, 11, 0.5, "Decision: K-Means k=4 chosen for interpretability & stability", 18, True, ACCENT_GREEN)

items = [
    "K-Means ARI stability: 0.9999 (mean) ± 0.0002 — extremely stable",
    "GMM ARI stability: 0.926 ± 0.061 — good but less consistent",
    "DBSCAN finds 24 micro-clusters; harder to interpret at analyst level",
    "k=4 balances granularity with actionable attack families",
]
add_bullet_slide(slide, 0.8, 4.5, 11.5, 2.5, items, 16, WHITE, Pt(8))

# ═══════════════════════════════════════════════════════════════
# SLIDE 5: CLUSTER METRICS
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_textbox(slide, 0.8, 0.4, 11, 0.6, "Clustering Quality Metrics (k=4)", 32, True, ACCENT_RED)

data = [
    ["Model", "Clusters", "Silhouette ↑", "Davies-Bouldin ↓", "Calinski-Harabasz ↑", "Stability (ARI)"],
    ["K-Means (k=4)", "4", "0.608", "0.940", "3,610", "0.9999 ± 0.0002"],
    ["GMM (k=4)", "4", "0.506", "1.581", "2,260", "0.926 ± 0.061"],
    ["DBSCAN (eps=0.93)", "24", "0.728", "0.585", "8,955", "Deterministic"],
]
add_table(slide, 0.8, 1.2, 11.5, 1.8, 4, 6, data, [2, 1.2, 1.5, 1.8, 2.2, 2.5])

add_textbox(slide, 0.8, 3.3, 11, 0.5, "Interpretation:", 20, True, ACCENT_BLUE)
items = [
    "Silhouette 0.61 = reasonable separation (0.5-0.7 = moderate structure)",
    "Davies-Bouldin < 1 = clusters well-separated",
    "Calinski-Harabasz > 3000 = distinct clusters",
    "Stability ~1.0 = K-Means results are highly reproducible",
]
add_bullet_slide(slide, 0.8, 3.9, 11.5, 2.5, items, 16, WHITE, Pt(6))

# ═══════════════════════════════════════════════════════════════
# SLIDE 6: CLUSTER PROFILES
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_textbox(slide, 0.8, 0.4, 11, 0.6, "Cluster Profiles (Median Features)", 32, True, ACCENT_RED)

data = [
    ["Feature", "Cluster 0", "Cluster 1", "Cluster 2", "Cluster 3"],
    ["Size (rows)", "~3,800", "~5,200", "~1,900", "~800"],
    ["protocol_type", "tcp", "tcp", "icmp", "icmp"],
    ["service", "private", "private", "ecr_i", "eco_i"],
    ["flag", "REJ", "S0", "SF", "SF"],
    ["count", "121", "199", "119", "1"],
    ["srv_count", "4", "11", "99", "6"],
    ["serror_rate", "0.0", "1.0", "0.0", "0.0"],
    ["rerror_rate", "1.0", "0.0", "0.0", "0.0"],
    ["same_srv_rate", "0.08", "0.06", "1.0", "1.0"],
    ["dst_host_count", "255", "255", "255", "2"],
    ["src_bytes", "0", "0", "520", "8"],
    ["logged_in", "0", "0", "0", "0"],
]
add_table(slide, 0.5, 1.1, 12.3, 4.5, len(data), 5, data, [2.5, 2.2, 2.2, 2.2, 2.2])

# ═══════════════════════════════════════════════════════════════
# SLIDE 7: MITRE MAPPING — CLUSTERS 0 & 1 (TCP)
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_textbox(slide, 0.8, 0.4, 11, 0.6, "MITRE ATT&CK Mapping: TCP Clusters", 32, True, ACCENT_RED)

# Cluster 0
add_textbox(slide, 0.8, 1.2, 5.5, 0.5, "Cluster 0 — Connection Scanning / Probing", 20, True, ACCENT_BLUE)
items = [
    "MITRE: T1595 (Active Scanning) / T1046 (Network Service Scanning)",
    "Confidence: HIGH",
    "Key Indicators:",
    "  • flag=REJ (rejected), rerror_rate=1.0",
    "  • count=121, dst_host_count=255 (broad target)",
    "  • srv_count=4 (few services probed)",
    "Pattern: Attacker scans many hosts, few services, all rejected",
]
add_bullet_slide(slide, 0.8, 1.8, 5.5, 4.5, items, 15, WHITE, Pt(4))

# Cluster 1
add_textbox(slide, 7, 1.2, 5.5, 0.5, "Cluster 1 — SYN Flood / Denial of Service", 20, True, ACCENT_BLUE)
items = [
    "MITRE: T1499 (Endpoint DoS) / T1498 (Network DoS)",
    "Confidence: HIGH",
    "Key Indicators:",
    "  • flag=S0 (SYN), serror_rate=1.0 (100% SYN errors)",
    "  • count=199 (high volume), srv_count=11",
    "  • src_bytes=0, dst_bytes=0 (no payload)",
    "Pattern: Classic SYN flood — half-open connections exhaust resources",
]
add_bullet_slide(slide, 7, 1.8, 5.5, 4.5, items, 15, WHITE, Pt(4))

# ═══════════════════════════════════════════════════════════════
# SLIDE 8: MITRE MAPPING — CLUSTERS 2 & 3 (ICMP)
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_textbox(slide, 0.8, 0.4, 11, 0.6, "MITRE ATT&CK Mapping: ICMP Clusters", 32, True, ACCENT_RED)

# Cluster 2
add_textbox(slide, 0.8, 1.2, 5.5, 0.5, "Cluster 2 — ICMP Service Scanning / Enumeration", 20, True, ACCENT_BLUE)
items = [
    "MITRE: T1595 (Active Scanning) / T1046 (Network Service Scanning)",
    "Confidence: MEDIUM-HIGH",
    "Key Indicators:",
    "  • protocol=icmp, service=ecr_i (echo reply), flag=SF",
    "  • srv_count=99, same_srv_rate=1.0 (single host, many services)",
    "  • src_bytes=520 (substantial ICMP payload)",
    "Pattern: ICMP-based enumeration of services on target host",
]
add_bullet_slide(slide, 0.8, 1.8, 5.5, 4.5, items, 15, WHITE, Pt(4))

# Cluster 3
add_textbox(slide, 7, 1.2, 5.5, 0.5, "Cluster 3 — ICMP Ping Sweep / Host Discovery", 20, True, ACCENT_BLUE)
items = [
    "MITRE: T1595.001 (Scanning IP Blocks) / T1018 (Remote System Discovery)",
    "Confidence: MEDIUM",
    "Key Indicators:",
    "  • protocol=icmp, service=eco_i (echo request), flag=SF",
    "  • src_bytes=8 (standard ping packet size)",
    "  • count=1, srv_count=6 (one connection, multiple services)",
    "  • dst_host_count=2 (scanning small IP range)",
    "Pattern: Classic ping sweep — find live hosts before deeper scans",
]
add_bullet_slide(slide, 7, 1.8, 5.5, 4.5, items, 15, WHITE, Pt(4))

# ═══════════════════════════════════════════════════════════════
# SLIDE 9: NORMAL TRAFFIC BASELINE
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_textbox(slide, 0.8, 0.4, 11, 0.6, "Normal Traffic Baseline (Reference)", 32, True, ACCENT_RED)

data = [
    ["Aspect", "Normal (13,449 rows, 53.4%)", "Anomaly Clusters (11,743 rows)"],
    ["Class balance", "53.4% — nearly balanced", "46.6%"],
    ["flag distribution", "Mixed: SF, REJ, RSTO, RSTR", "Clustered: REJ, S0, SF only"],
    ["serror_rate / rerror_rate", "Low (near 0)", "Extreme: 0.0 or 1.0 per cluster"],
    ["logged_in", "1 for authenticated services", "0 across all clusters"],
    ["service variety", "Many (http, smtp, ftp, etc.)", "private, ecr_i, eco_i only"],
    ["src_bytes / dst_bytes", "Varied, non-zero", "0 or fixed small values (8, 520)"],
    ["MITRE technique", "N/A — benign baseline", "T1595, T1499, T1046, T1018"],
]
add_table(slide, 0.5, 1.2, 12.3, 3.5, 8, 3, data, [2.5, 5, 5])

add_textbox(slide, 0.8, 5.0, 11, 0.6, "Key Insight: Anomaly clusters show extreme, homogeneous patterns — normal traffic is heterogeneous", 16, True, ACCENT_GREEN)
add_textbox(slide, 0.8, 5.6, 11, 0.5, "HoneyBadger Reality: Honeypots see almost no benign traffic — this 'normal' is synthetic/network background", 14, False, MID_GRAY)

# ═══════════════════════════════════════════════════════════════
# SLIDE 10: HONEYBADGER RELEVANCE
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_textbox(slide, 0.8, 0.4, 11, 0.6, "Relevance to HoneyBadger", 32, True, ACCENT_RED)

items = [
    "What overlaps with HoneyBadger events:",
    "  • service (ssh/http) → HoneyBadger's RawEvent.service",
    "  • num_failed_logins, logged_in → derivable from HoneyBadger login_info + technique_id",
    "  • count, srv_count, dst_host_* counts → aggregations on source_ip + time windows",
    "",
    "What HoneyBadger does NOT capture (Kaggle-dependent):",
    "  • TCP flags (S0, REJ, SF), serror_rate, rerror_rate",
    "  • duration, src_bytes, dst_bytes, flag",
    "  • Window aggregates (same_srv_rate, diff_srv_rate, dst_host_* rates)",
    "",
    "What HoneyBadger ADDS (not in Kaggle):",
    "  • MITRE technique_id (rule-based from backend/mitre.py)",
    "  • Credentials (username + SHA-256 hash), payload URLs, GeoIP",
    "  • Source IP, timestamps, shell commands, HTTP method/path/UA",
    "",
    "Conclusion: This clustering validates the BEHAVIORAL GROUPING APPROACH,",
    "not a deployable model. Transfer learning or labeled honeypot data needed for production.",
]
add_bullet_slide(slide, 0.8, 1.2, 11.5, 5.5, items, 15, WHITE, Pt(4))

# ═══════════════════════════════════════════════════════════════
# SLIDE 11: LIMITATIONS & CAVEATS
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_textbox(slide, 0.8, 0.4, 11, 0.6, "Limitations & Caveats", 32, True, ACCENT_RED)

items = [
    "1. NO GROUND-TRUTH ATTACK LABELS — MITRE mappings are hypotheses from feature patterns only",
    "2. Kaggle features ≠ HoneyBadger features — TCP flags, byte counts, durations not captured by honeypot",
    "3. SSH subset tiny (58 rows, all anomaly) — cannot reliably profile SSH-specific attacks",
    "4. Clustering assumes distinct attack families — real attacks may be mixed/overlapping",
    "5. 'Normal' class in dataset is synthetic — honeypots see ~100% unsolicited traffic",
    "6. K-Means assumes spherical clusters — GMM/DBSCAN show different structures",
    "7. Single dataset, single snapshot — no temporal validation",
    "8. Feature engineering choices (log1p, service grouping) affect results",
]
add_bullet_slide(slide, 0.8, 1.2, 11.5, 5.5, items, 16, WHITE, Pt(8))

add_textbox(slide, 0.8, 6.2, 11, 0.5, "This is exploratory research — demonstrates methodology, not a production classifier", 16, True, ACCENT_RED)

# ═══════════════════════════════════════════════════════════════
# SLIDE 12: NEXT STEPS
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_textbox(slide, 0.8, 0.4, 11, 0.6, "Next Steps & Extensions", 32, True, ACCENT_RED)

items = [
    "Immediate:",
    "  • Validate clusters with domain expert review",
    "  • Test on HoneyBadger's own event export (session-level aggregations)",
    "  • Compare with Pair 1 (supervised) & Pair 2 (anomaly detection) results",
    "",
    "Methodological:",
    "  • Hierarchical clustering for attack sub-families",
    "  • Semi-supervised: use rule-based MITRE tags as weak labels",
    "  • Time-series clustering: group by temporal attack campaigns",
    "  • Feature importance per cluster (SHAP on supervised proxy)",
    "",
    "Production Path:",
    "  • Collect labeled HoneyBadger sessions (manual review + simulator assertions)",
    "  • Train supervised classifier on HoneyBadger-native features",
    "  • Online clustering for novel attack detection (streaming k-means)",
    "  • Integrate with dashboard: cluster ID → MITRE tag → analyst triage queue",
]
add_bullet_slide(slide, 0.8, 1.2, 11.5, 5.5, items, 15, WHITE, Pt(4))

# ═══════════════════════════════════════════════════════════════
# SLIDE 13: THANK YOU / Q&A
# ═══════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)

add_textbox(slide, 2, 2.5, 9, 1.2, "Pair 3: Profile Attack Types (Clustering)", 36, True, ACCENT_RED)
add_textbox(slide, 2, 3.5, 9, 0.8, "4 Behavioral Clusters → 4 MITRE ATT&CK Hypotheses", 24, False, WHITE)
add_textbox(slide, 2, 4.3, 9, 0.6, "Scanning • SYN Flood • ICMP Enumeration • Ping Sweep", 20, False, ACCENT_BLUE)
add_textbox(slide, 2, 5.2, 9, 0.5, "Questions?", 28, True, ACCENT_GREEN)
add_textbox(slide, 2, 5.8, 9, 0.4, "Files: pair3_cluster_assignments.csv | pair3_cluster_profiles.csv | pair3_mitre_mapping.json", 14, False, MID_GRAY)
add_textbox(slide, 2, 6.3, 9, 0.4, "Notebook: pair3_clustering.ipynb (visualizations)", 14, False, MID_GRAY)

# ─── Save ───
output_path = "/home/dridi/HoneyBadger/Pair3_Clustering_Presentation.pptx"
prs.save(output_path)
print(f"Saved: {output_path}")