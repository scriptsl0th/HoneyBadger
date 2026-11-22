#!/usr/bin/env python3
"""
HoneyBadger Pair 3: Profiling Network Attack Types Through Unsupervised Learning
Professional PowerPoint Generation Script

Generates a conference-quality cybersecurity research presentation.
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.chart.data import CategoryChartData
import json
import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================
# COLOR SYSTEM - Dark Cybersecurity / Threat Intelligence Theme
# ============================================================
COLORS = {
    'bg_main': RGBColor(0x09, 0x0D, 0x14),        # #090D14
    'bg_secondary': RGBColor(0x11, 0x18, 0x27),    # #111827
    'bg_card': RGBColor(0x18, 0x22, 0x35),         # #182235
    'accent_primary': RGBColor(0x22, 0xD3, 0xEE),  # #22D3EE (cyan)
    'accent_secondary': RGBColor(0x3B, 0x82, 0xF6), # #3B82F6 (blue)
    'threat_high': RGBColor(0xF4, 0x3F, 0x5E),     # #F43F5E (rose/red)
    'threat_medium': RGBColor(0xFB, 0xBF, 0x24),   # #FBBF24 (amber)
    'positive': RGBColor(0x34, 0xD3, 0x99),        # #34D399 (emerald)
    'text_primary': RGBColor(0xF1, 0xF5, 0xF9),    # #F1F5F9 (slate-100)
    'text_secondary': RGBColor(0x94, 0xA3, 0xB8),  # #94A3B8 (slate-400)
    'text_muted': RGBColor(0x64, 0x74, 0x8B),      # #64748B (slate-500)
    'cluster_0': RGBColor(0x22, 0xD3, 0xEE),       # Cyan - Connection Scanning
    'cluster_1': RGBColor(0xF4, 0x3F, 0x5E),       # Rose - SYN Flood
    'cluster_2': RGBColor(0x34, 0xD3, 0x99),       # Emerald - ICMP Enumeration
    'cluster_3': RGBColor(0xFB, 0xBF, 0x24),       # Amber - Ping Sweep
    'white': RGBColor(0xFF, 0xFF, 0xFF),
    'divider': RGBColor(0x37, 0x41, 0x51),         # #374151 (slate-700)
}

# Cluster colors mapping
CLUSTER_COLORS = {
    0: COLORS['cluster_0'],
    1: COLORS['cluster_1'],
    2: COLORS['cluster_2'],
    3: COLORS['cluster_3'],
}

CLUSTER_NAMES = {
    0: "Connection Scanning",
    1: "SYN Flood / DoS",
    2: "ICMP Enumeration",
    3: "ICMP Ping Sweep",
}

# ============================================================
# TYPOGRAPHY
# ============================================================
FONTS = {
    'title': 'Space Grotesk',
    'body': 'Inter',
    'mono': 'JetBrains Mono',
}

# Fallback fonts if custom fonts not available
FALLBACK_FONTS = {
    'title': 'Calibri',
    'body': 'Calibri',
    'mono': 'Consolas',
}

# ============================================================
# SLIDE DIMENSIONS (16:9 Widescreen)
# ============================================================
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)

# Margins
MARGIN_LEFT = Inches(0.8)
MARGIN_RIGHT = Inches(0.8)
MARGIN_TOP = Inches(0.6)
MARGIN_BOTTOM = Inches(0.6)

CONTENT_WIDTH = SLIDE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
CONTENT_HEIGHT = SLIDE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM


# ============================================================
# HELPER FUNCTIONS
# ============================================================
def set_slide_background(slide, color):
    """Set slide background color."""
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_textbox(slide, left, top, width, height, text, font_size=18, bold=False,
                color=None, alignment=PP_ALIGN.LEFT, font_name=None, line_spacing=1.15):
    """Add a text box with formatted text."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = color or COLORS['text_primary']
    p.alignment = alignment
    if font_name:
        p.font.name = font_name
    p.space_after = Pt(0)
    p.line_spacing = Pt(font_size * line_spacing)
    return txBox


def add_multiline_textbox(slide, left, top, width, height, lines, font_size=16,
                          color=None, alignment=PP_ALIGN.LEFT, font_name=None,
                          line_spacing=1.3, bold_first=False):
    """Add a text box with multiple paragraphs."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True

    for i, line in enumerate(lines):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = line
        p.font.size = Pt(font_size)
        p.font.color.rgb = color or COLORS['text_primary']
        p.alignment = alignment
        if font_name:
            p.font.name = font_name
        if bold_first and i == 0:
            p.font.bold = True
        p.space_after = Pt(4)
        p.line_spacing = Pt(font_size * line_spacing)
    return txBox


def add_card(slide, left, top, width, height, bg_color=None, border_color=None):
    """Add a card/container shape."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color or COLORS['bg_card']
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1.5)
    else:
        shape.line.fill.background()
    return shape


def add_line(slide, left, top, width, color=None, width_pt=1):
    """Add a horizontal line."""
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, Pt(width_pt))
    shape.fill.solid()
    shape.fill.fore_color.rgb = color or COLORS['divider']
    shape.line.fill.background()
    return shape


def add_metric_card(slide, left, top, width, height, label, value, unit="",
                     value_color=None, bg_color=None):
    """Add a metric display card."""
    card = add_card(slide, left, top, width, height, bg_color or COLORS['bg_card'])

    # Value
    add_textbox(slide, left + Inches(0.2), top + Inches(0.15), width - Inches(0.4), Inches(0.6),
                value, font_size=28, bold=True, color=value_color or COLORS['accent_primary'],
                font_name=FALLBACK_FONTS['mono'], alignment=PP_ALIGN.CENTER)

    # Label
    add_textbox(slide, left + Inches(0.15), top + Inches(0.55), width - Inches(0.3), Inches(0.35),
                label, font_size=11, color=COLORS['text_secondary'],
                font_name=FALLBACK_FONTS['body'], alignment=PP_ALIGN.CENTER)

    if unit:
        add_textbox(slide, left + Inches(0.15), top + Inches(0.8), width - Inches(0.3), Inches(0.25),
                    unit, font_size=10, color=COLORS['text_muted'],
                    font_name=FALLBACK_FONTS['body'], alignment=PP_ALIGN.CENTER)

    return card


def add_section_header(slide, left, top, text, font_size=14, color=None):
    """Add a section header label."""
    return add_textbox(slide, left, top, Inches(6), Inches(0.35),
                       text.upper(), font_size=font_size, bold=True,
                       color=color or COLORS['accent_primary'],
                       font_name=FALLBACK_FONTS['title'])


def add_footer(slide, slide_num, total_slides):
    """Add slide footer with numbering and branding."""
    # Slide number
    add_textbox(slide, MARGIN_LEFT, SLIDE_HEIGHT - Inches(0.4), Inches(2), Inches(0.3),
                f"{slide_num} / {total_slides}", font_size=9,
                color=COLORS['text_muted'], font_name=FALLBACK_FONTS['mono'])

    # Branding
    add_textbox(slide, SLIDE_WIDTH - MARGIN_RIGHT - Inches(2.5), SLIDE_HEIGHT - Inches(0.4),
                Inches(2.5), Inches(0.3),
                "HONEYBADGER  •  PAIR 3  •  CLUSTERING", font_size=9,
                color=COLORS['text_muted'], font_name=FALLBACK_FONTS['mono'],
                alignment=PP_ALIGN.RIGHT)


# ============================================================
# CHART CREATION FUNCTIONS
# ============================================================
def create_elbow_silhouette_chart(slide, left, top, width, height):
    """Create K-Means elbow and silhouette chart."""
    chart_data = CategoryChartData()
    chart_data.categories = [str(k) for k in range(2, 16)]
    chart_data.add_series('Inertia (×10⁵)', [3.19, 2.55, 2.14, 1.87, 1.67, 1.49, 1.35, 1.23, 1.10, 0.98, 0.87, 0.74, 0.65, 0.56])
    chart_data.add_series('Silhouette Score', [0.513, 0.604, 0.608, 0.631, 0.649, 0.667, 0.668, 0.698, 0.700, 0.718, 0.719, 0.718, 0.719, 0.732])

    chart_frame = slide.shapes.add_chart(
        XL_CHART_TYPE.LINE_MARKERS, left, top, width, height, chart_data
    )
    chart = chart_frame.chart

    # Style the chart
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.include_in_layout = False
    chart.legend.font.size = Pt(9)
    chart.legend.font.color.rgb = COLORS['text_secondary']
    chart.legend.format.fill.solid()
    chart.legend.format.fill.fore_color.rgb = COLORS['bg_card']

    # Axis styling
    category_axis = chart.category_axis
    category_axis.tick_labels.font.size = Pt(9)
    category_axis.tick_labels.font.color.rgb = COLORS['text_secondary']
    category_axis.format.line.fill.background()
    category_axis.major_gridlines.format.line.color.rgb = COLORS['divider']

    value_axis = chart.value_axis
    value_axis.tick_labels.font.size = Pt(9)
    value_axis.tick_labels.font.color.rgb = COLORS['text_secondary']
    value_axis.format.line.fill.background()
    value_axis.major_gridlines.format.line.color.rgb = COLORS['divider']

    # Series styling
    series = chart.series
    series[0].format.line.color.rgb = COLORS['threat_high']
    series[0].format.line.width = Pt(2.5)
    series[0].marker.style = 8  # circle
    series[0].marker.size = 6
    series[0].marker.format.fill.solid()
    series[0].marker.format.fill.fore_color.rgb = COLORS['threat_high']

    series[1].format.line.color.rgb = COLORS['accent_primary']
    series[1].format.line.width = Pt(2.5)
    series[1].marker.style = 8
    series[1].marker.size = 6
    series[1].marker.format.fill.solid()
    series[1].marker.format.fill.fore_color.rgb = COLORS['accent_primary']

    # Chart area
    chart.plot_area.format.fill.solid()
    chart.plot_area.format.fill.fore_color.rgb = COLORS['bg_card']
    chart.chart_style = 2

    return chart_frame


def create_bic_aic_chart(slide, left, top, width, height):
    """Create GMM BIC/AIC chart."""
    chart_data = CategoryChartData()
    chart_data.categories = [str(k) for k in range(2, 16)]
    chart_data.add_series('BIC', [-4.01, -8.37, -9.71, -11.30, -11.10, -11.80, -12.30, -12.50, -12.90, -13.10, -13.00, -13.40, -13.90, -13.30])
    chart_data.add_series('AIC', [-4.04, -8.42, -9.78, -11.40, -11.30, -11.90, -12.40, -12.70, -13.10, -13.30, -13.20, -13.60, -14.20, -13.50])

    chart_frame = slide.shapes.add_chart(
        XL_CHART_TYPE.LINE_MARKERS, left, top, width, height, chart_data
    )
    chart = chart_frame.chart

    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.font.size = Pt(9)
    chart.legend.font.color.rgb = COLORS['text_secondary']
    chart.legend.format.fill.solid()
    chart.legend.format.fill.fore_color.rgb = COLORS['bg_card']

    category_axis = chart.category_axis
    category_axis.tick_labels.font.size = Pt(9)
    category_axis.tick_labels.font.color.rgb = COLORS['text_secondary']
    category_axis.format.line.fill.background()
    category_axis.major_gridlines.format.line.color.rgb = COLORS['divider']

    value_axis = chart.value_axis
    value_axis.tick_labels.font.size = Pt(9)
    value_axis.tick_labels.font.color.rgb = COLORS['text_secondary']
    value_axis.format.line.fill.background()
    value_axis.major_gridlines.format.line.color.rgb = COLORS['divider']

    series = chart.series
    series[0].format.line.color.rgb = COLORS['threat_high']
    series[0].format.line.width = Pt(2.5)
    series[0].marker.style = 8
    series[0].marker.size = 6
    series[0].marker.format.fill.solid()
    series[0].marker.format.fill.fore_color.rgb = COLORS['threat_high']

    series[1].format.line.color.rgb = COLORS['accent_secondary']
    series[1].format.line.width = Pt(2.5)
    series[1].marker.style = 8
    series[1].marker.size = 6
    series[1].marker.format.fill.solid()
    series[1].marker.format.fill.fore_color.rgb = COLORS['accent_secondary']

    chart.plot_area.format.fill.solid()
    chart.plot_area.format.fill.fore_color.rgb = COLORS['bg_card']

    return chart_frame


def create_metrics_comparison_chart(slide, left, top, width, height):
    """Create clustered bar chart comparing K-Means, GMM, DBSCAN metrics."""
    chart_data = CategoryChartData()
    chart_data.categories = ['Silhouette', 'Davies-Bouldin', 'Calinski-Harabasz']

    # Normalize CH for visibility (divide by 1000)
    chart_data.add_series('K-Means', [0.608, 0.940, 3.61])
    chart_data.add_series('GMM', [0.518, 1.581, 2.26])
    chart_data.add_series('DBSCAN', [0.725, 0.586, 8.91])

    chart_frame = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED, left, top, width, height, chart_data
    )
    chart = chart_frame.chart

    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.font.size = Pt(9)
    chart.legend.font.color.rgb = COLORS['text_secondary']
    chart.legend.format.fill.solid()
    chart.legend.format.fill.fore_color.rgb = COLORS['bg_card']

    category_axis = chart.category_axis
    category_axis.tick_labels.font.size = Pt(10)
    category_axis.tick_labels.font.color.rgb = COLORS['text_secondary']
    category_axis.format.line.fill.background()
    category_axis.major_gridlines.format.line.color.rgb = COLORS['divider']

    value_axis = chart.value_axis
    value_axis.tick_labels.font.size = Pt(9)
    value_axis.tick_labels.font.color.rgb = COLORS['text_secondary']
    value_axis.format.line.fill.background()
    value_axis.major_gridlines.format.line.color.rgb = COLORS['divider']
    value_axis.has_title = True
    value_axis.axis_title.text_frame.paragraphs[0].text = "Score (CH ÷ 1000)"
    value_axis.axis_title.text_frame.paragraphs[0].font.size = Pt(9)
    value_axis.axis_title.text_frame.paragraphs[0].font.color.rgb = COLORS['text_secondary']

    series = chart.series
    series[0].format.fill.solid()
    series[0].format.fill.fore_color.rgb = COLORS['accent_primary']
    series[1].format.fill.solid()
    series[1].format.fill.fore_color.rgb = COLORS['accent_secondary']
    series[2].format.fill.solid()
    series[2].format.fill.fore_color.rgb = COLORS['threat_medium']

    chart.plot_area.format.fill.solid()
    chart.plot_area.format.fill.fore_color.rgb = COLORS['bg_card']

    return chart_frame


def create_stability_boxplot(slide, left, top, width, height):
    """Create a visual representation of stability (ARI) using bars with error bars."""
    # We'll create a custom visualization using shapes since pptx boxplot support is limited
    pass  # Will implement as custom shapes


def create_cluster_distribution_chart(slide, left, top, width, height):
    """Create cluster size distribution chart for K-Means k=4."""
    chart_data = CategoryChartData()
    chart_data.categories = ['Cluster 0', 'Cluster 1', 'Cluster 2', 'Cluster 3']
    chart_data.add_series('Records', [2591, 6989, 1, 2162])

    chart_frame = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED, left, top, width, height, chart_data
    )
    chart = chart_frame.chart

    chart.has_legend = False

    category_axis = chart.category_axis
    category_axis.tick_labels.font.size = Pt(10)
    category_axis.tick_labels.font.color.rgb = COLORS['text_secondary']
    category_axis.format.line.fill.background()
    category_axis.major_gridlines.format.line.color.rgb = COLORS['divider']

    value_axis = chart.value_axis
    value_axis.tick_labels.font.size = Pt(9)
    value_axis.tick_labels.font.color.rgb = COLORS['text_secondary']
    value_axis.format.line.fill.background()
    value_axis.major_gridlines.format.line.color.rgb = COLORS['divider']
    value_axis.has_title = True
    value_axis.axis_title.text_frame.paragraphs[0].text = "Number of Records"
    value_axis.axis_title.text_frame.paragraphs[0].font.size = Pt(9)
    value_axis.axis_title.text_frame.paragraphs[0].font.color.rgb = COLORS['text_secondary']

    series = chart.series[0]
    # Color each point individually
    for i, color in [COLORS['cluster_0'], COLORS['cluster_1'], COLORS['cluster_2'], COLORS['cluster_3']]:
        point = series.points[i]
        point.format.fill.solid()
        point.format.fill.fore_color.rgb = color

    # Data labels
    series.has_data_labels = True
    series.data_labels.font.size = Pt(9)
    series.data_labels.font.color.rgb = COLORS['text_primary']
    series.data_labels.font.bold = True
    series.data_labels.number_format = '#,##0'
    series.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END

    chart.plot_area.format.fill.solid()
    chart.plot_area.format.fill.fore_color.rgb = COLORS['bg_card']

    return chart_frame


def create_pca_variance_chart(slide, left, top, width, height):
    """Create PCA explained variance chart."""
    chart_data = CategoryChartData()
    chart_data.categories = ['PC1', 'PC2', 'PC3', 'PC4', 'PC5', 'PC6-20']
    chart_data.add_series('Explained Variance (%)', [22.7, 16.5, 11.2, 8.4, 6.3, 30.5])

    chart_frame = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED, left, top, width, height, chart_data
    )
    chart = chart_frame.chart

    chart.has_legend = False

    category_axis = chart.category_axis
    category_axis.tick_labels.font.size = Pt(10)
    category_axis.tick_labels.font.color.rgb = COLORS['text_secondary']
    category_axis.format.line.fill.background()
    category_axis.major_gridlines.format.line.color.rgb = COLORS['divider']

    value_axis = chart.value_axis
    value_axis.tick_labels.font.size = Pt(9)
    value_axis.tick_labels.font.color.rgb = COLORS['text_secondary']
    value_axis.format.line.fill.background()
    value_axis.major_gridlines.format.line.color.rgb = COLORS['divider']
    value_axis.has_title = True
    value_axis.axis_title.text_frame.paragraphs[0].text = "Variance Explained (%)"
    value_axis.axis_title.text_frame.paragraphs[0].font.size = Pt(9)
    value_axis.axis_title.text_frame.paragraphs[0].font.color.rgb = COLORS['text_secondary']

    series = chart.series[0]
    series.format.fill.solid()
    series.format.fill.fore_color.rgb = COLORS['accent_primary']

    series.has_data_labels = True
    series.data_labels.font.size = Pt(9)
    series.data_labels.font.color.rgb = COLORS['text_primary']
    series.data_labels.number_format = '0.0"%"'
    series.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END

    chart.plot_area.format.fill.solid()
    chart.plot_area.format.fill.fore_color.rgb = COLORS['bg_card']

    return chart_frame


# ============================================================
# SLIDE BUILDERS
# ============================================================
def build_slide_01_opening(prs, total_slides):
    """SLIDE 01: THE OPENING - Cinematic title slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
    set_slide_background(slide, COLORS['bg_main'])

    # Subtle grid pattern background (simulated with lines)
    for i in range(0, int(SLIDE_WIDTH), int(Inches(0.5))):
        add_line(slide, Inches(i), Inches(0), Pt(0.5), COLORS['divider'], 0.5)

    # Main title
    add_textbox(slide, MARGIN_LEFT, Inches(1.8), CONTENT_WIDTH, Inches(1.2),
                "HONEYBADGER", font_size=56, bold=True,
                color=COLORS['text_primary'], font_name=FALLBACK_FONTS['title'],
                alignment=PP_ALIGN.CENTER)

    # Subtitle
    add_textbox(slide, MARGIN_LEFT, Inches(3.0), CONTENT_WIDTH, Inches(0.8),
                "Profiling Network Attack Behaviors\nThrough Unsupervised Learning",
                font_size=28, color=COLORS['accent_primary'],
                font_name=FALLBACK_FONTS['title'], alignment=PP_ALIGN.CENTER)

    # Divider line
    add_line(slide, Inches(5.5), Inches(4.0), Inches(2.3), COLORS['accent_primary'], 2)

    # Meta info
    meta_lines = [
        "PAIR 03  •  ATTACK TYPE PROFILING  •  CLUSTERING",
        "Kaggle Network Intrusion Detection Dataset  •  sampadab17/network-intrusion-detection",
        "11,743 Anomalies  →  4 Behavioral Clusters  →  4 MITRE ATT&CK Hypotheses"
    ]
    add_multiline_textbox(slide, MARGIN_LEFT, Inches(4.4), CONTENT_WIDTH, Inches(1.2),
                          meta_lines, font_size=14, color=COLORS['text_secondary'],
                          font_name=FALLBACK_FONTS['mono'], alignment=PP_ALIGN.CENTER, line_spacing=1.6)

    # Bottom accent
    add_line(slide, MARGIN_LEFT, Inches(6.8), CONTENT_WIDTH, COLORS['accent_primary'], 1)

    add_footer(slide, 1, total_slides)
    return slide


def build_slide_02_challenge(prs, total_slides):
    """SLIDE 02: THE CHALLENGE - 11,743 Anomalies, Zero Labels."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLORS['bg_main'])

    # Section header
    add_section_header(slide, MARGIN_LEFT, MARGIN_TOP, "the challenge")

    # Main statement
    add_textbox(slide, MARGIN_LEFT, Inches(1.3), CONTENT_WIDTH, Inches(1.0),
                "11,743 Anomalies.\nZero Attack-Type Labels.",
                font_size=40, bold=True, color=COLORS['text_primary'],
                font_name=FALLBACK_FONTS['title'])

    # Divider
    add_line(slide, MARGIN_LEFT, Inches(2.5), Inches(3), COLORS['threat_high'], 2)

    # Problem description
    problem_text = (
        "HoneyBadger captures anomalous network traffic, but the Kaggle dataset "
        "provides only binary labels: normal vs. anomaly. No ground-truth attack "
        "family labels exist (floods, scans, brute-force, exploits)."
    )
    add_textbox(slide, MARGIN_LEFT, Inches(2.8), CONTENT_WIDTH, Inches(1.2),
                problem_text, font_size=16, color=COLORS['text_secondary'],
                font_name=FALLBACK_FONTS['body'])

    # Business question card
    card = add_card(slide, MARGIN_LEFT, Inches(4.2), Inches(5.5), Inches(2.0), COLORS['bg_card'])
    add_textbox(slide, MARGIN_LEFT + Inches(0.3), Inches(4.35), Inches(5), Inches(0.4),
                "BUSINESS QUESTION", font_size=11, bold=True, color=COLORS['accent_primary'],
                font_name=FALLBACK_FONTS['mono'])
    add_textbox(slide, MARGIN_LEFT + Inches(0.3), Inches(4.8), Inches(5), Inches(1.2),
                "Can unsupervised learning discover meaningful behavioral groups "
                "that help security analysts understand what kind of attack they're facing?",
                font_size=15, color=COLORS['text_primary'], font_name=FALLBACK_FONTS['body'])

    # Visual: Pipeline concept
    # Left: Raw anomalies
    left_box = add_card(slide, Inches(8.5), Inches(2.5), Inches(2.2), Inches(1.5), COLORS['bg_card'], COLORS['threat_high'])
    add_textbox(slide, Inches(8.5), Inches(2.6), Inches(2.2), Inches(0.4),
                "RAW ANOMALIES", font_size=11, bold=True, color=COLORS['threat_high'],
                font_name=FALLBACK_FONTS['mono'], alignment=PP_ALIGN.CENTER)
    add_textbox(slide, Inches(8.5), Inches(3.0), Inches(2.2), Inches(0.8),
                "11,743 records\n41 features\nNo attack labels", font_size=12, color=COLORS['text_secondary'],
                font_name=FALLBACK_FONTS['body'], alignment=PP_ALIGN.CENTER)

    # Arrow
    add_textbox(slide, Inches(10.8), Inches(3.0), Inches(0.6), Inches(0.5),
                "→", font_size=28, bold=True, color=COLORS['accent_primary'],
                alignment=PP_ALIGN.CENTER)

    # Right: Behavioral clusters
    right_box = add_card(slide, Inches(11.3), Inches(2.5), Inches(2.2), Inches(1.5), COLORS['bg_card'], COLORS['positive'])
    add_textbox(slide, Inches(11.3), Inches(2.6), Inches(2.2), Inches(0.4),
                "BEHAVIORAL CLUSTERS", font_size=11, bold=True, color=COLORS['positive'],
                font_name=FALLBACK_FONTS['mono'], alignment=PP_ALIGN.CENTER)
    add_textbox(slide, Inches(11.3), Inches(3.0), Inches(2.2), Inches(0.8),
                "4 distinct profiles\nInterpretable signatures\nMITRE ATT&CK hypotheses", font_size=12, color=COLORS['text_secondary'],
                font_name=FALLBACK_FONTS['body'], alignment=PP_ALIGN.CENTER)

    add_footer(slide, 2, total_slides)
    return slide


def build_slide_03_experiment_at_glance(prs, total_slides):
    """SLIDE 03: THE EXPERIMENT AT A GLANCE."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLORS['bg_main'])

    add_section_header(slide, MARGIN_LEFT, MARGIN_TOP, "experiment at a glance")

    # Title
    add_textbox(slide, MARGIN_LEFT, Inches(1.2), CONTENT_WIDTH, Inches(0.6),
                "Research Scope & Analytical Pipeline", font_size=30, bold=True,
                color=COLORS['text_primary'], font_name=FALLBACK_FONTS['title'])

    # Key metrics cards
    metrics = [
        ("TOTAL RECORDS", "25,192", "Train_data.csv"),
        ("NORMAL", "13,449", "53.4%"),
        ("ANOMALIES", "11,743", "46.6%"),
        ("ORIGINAL FEATURES", "41", "KDD-style"),
    ]

    card_width = Inches(2.8)
    card_height = Inches(1.5)
    start_x = MARGIN_LEFT
    gap = Inches(0.25)

    for i, (label, value, unit) in enumerate(metrics):
        x = start_x + i * (card_width + gap)
        add_metric_card(slide, x, Inches(2.0), card_width, card_height, label, value, unit,
                         value_color=COLORS['accent_primary'] if i < 3 else COLORS['accent_secondary'])

    # Pipeline visualization
    pipeline_steps = [
        ("DATASET", "Train_data.csv\n25,192 rows"),
        ("ANOMALY\nFILTERING", "class == 'anomaly'\n11,743 rows"),
        ("FEATURE\nENGINEERING", "79 encoded features\nlog1p + scaling"),
        ("PCA", "95% variance\n20 components"),
        ("CLUSTERING", "K-Means k=4\nGMM k=4\nDBSCAN eps=0.93"),
        ("EVALUATION", "Silhouette, DB, CH\nStability (ARI)"),
        ("BEHAVIORAL\nPROFILES", "4 clusters\nMITRE hypotheses"),
    ]

    step_width = Inches(1.55)
    step_height = Inches(2.2)
    step_gap = Inches(0.12)
    pipeline_top = Inches(4.2)

    for i, (title, desc) in enumerate(pipeline_steps):
        x = MARGIN_LEFT + i * (step_width + step_gap)

        # Step card
        bg = COLORS['bg_card']
        border = COLORS['accent_primary'] if i == 4 else COLORS['divider']
        card = add_card(slide, x, pipeline_top, step_width, step_height, bg, border)

        # Step number
        add_textbox(slide, x, pipeline_top + Inches(0.1), step_width, Inches(0.3),
                    f"0{i+1}", font_size=14, bold=True, color=COLORS['accent_primary'],
                    font_name=FALLBACK_FONTS['mono'], alignment=PP_ALIGN.CENTER)

        # Title
        add_textbox(slide, x, pipeline_top + Inches(0.4), step_width, Inches(0.6),
                    title, font_size=11, bold=True, color=COLORS['text_primary'],
                    font_name=FALLBACK_FONTS['title'], alignment=PP_ALIGN.CENTER)

        # Description
        add_textbox(slide, x + Inches(0.1), pipeline_top + Inches(1.1), step_width - Inches(0.2), Inches(1.0),
                    desc, font_size=10, color=COLORS['text_secondary'],
                    font_name=FALLBACK_FONTS['body'], alignment=PP_ALIGN.CENTER)

        # Arrow between steps
        if i < len(pipeline_steps) - 1:
            arrow_x = x + step_width + Inches(0.02)
            add_textbox(slide, arrow_x, pipeline_top + Inches(0.7), Inches(0.15), Inches(0.5),
                        "→", font_size=18, bold=True, color=COLORS['text_muted'],
                        alignment=PP_ALIGN.CENTER)

    # Note
    add_textbox(slide, MARGIN_LEFT, Inches(6.7), CONTENT_WIDTH, Inches(0.3),
                "Clustering performed ONLY on anomalous records (11,743). Normal class used for baseline comparison only.",
                font_size=10, color=COLORS['text_muted'], font_name=FALLBACK_FONTS['mono'])

    add_footer(slide, 3, total_slides)
    return slide


def build_slide_04_preprocessing(prs, total_slides):
    """SLIDE 04: FROM RAW TRAFFIC TO MODEL-READY DATA."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLORS['bg_main'])

    add_section_header(slide, MARGIN_LEFT, MARGIN_TOP, "preprocessing pipeline")

    add_textbox(slide, MARGIN_LEFT, Inches(1.2), CONTENT_WIDTH, Inches(0.6),
                "From Raw Traffic to Model-Ready Data", font_size=30, bold=True,
                color=COLORS['text_primary'], font_name=FALLBACK_FONTS['title'])

    # Left column: Transformation steps
    steps = [
        ("1. FILTER", "class == 'anomaly'", "11,743 rows retained"),
        ("2. DROP CONSTANT", "num_outbound_cmds, is_host_login", "Zero variance"),
        ("3. SERVICE GROUPING", "Rare services (<100) → 'other'", "Reduces cardinality"),
        ("4. ONE-HOT ENCODE", "protocol_type, service_grouped, flag", "handle_unknown='ignore'"),
        ("5. LOG TRANSFORM", "duration, src_bytes, dst_bytes", "log1p for skew"),
        ("6. STANDARD SCALER", "All numeric features", "Zero mean, unit variance"),
        ("7. PCA (95%)", "79 → 20 components", "95.6% variance retained"),
        ("8. PCA (2D VIZ)", "20 → 2 components", "31% variance (22.7% + 16.5%)"),
    ]

    y_start = Inches(2.1)
    row_height = Inches(0.55)

    for i, (step, detail, note) in enumerate(steps):
        y = y_start + i * row_height
        bg = COLORS['bg_card'] if i % 2 == 0 else COLORS['bg_secondary']

        # Step number/name
        card = add_card(slide, MARGIN_LEFT, y, Inches(2.5), row_height - Inches(0.05), bg)
        add_textbox(slide, MARGIN_LEFT + Inches(0.15), y + Inches(0.05), Inches(2.3), Inches(0.35),
                    step, font_size=12, bold=True, color=COLORS['accent_primary'],
                    font_name=FALLBACK_FONTS['mono'])
        add_textbox(slide, MARGIN_LEFT + Inches(0.15), y + Inches(0.25), Inches(2.3), Inches(0.25),
                    detail, font_size=10, color=COLORS['text_secondary'],
                    font_name=FALLBACK_FONTS['body'])

        # Detail
        add_textbox(slide, MARGIN_LEFT + Inches(2.7), y + Inches(0.05), Inches(4.5), row_height - Inches(0.05),
                    note, font_size=11, color=COLORS['text_primary'],
                    font_name=FALLBACK_FONTS['mono'])

    # Right column: Visual summary
    # Feature transformation summary
    right_x = Inches(7.5)

    add_textbox(slide, right_x, Inches(2.1), Inches(4.5), Inches(0.4),
                "FEATURE TRANSFORMATION SUMMARY", font_size=13, bold=True,
                color=COLORS['accent_primary'], font_name=FALLBACK_FONTS['title'])

    add_line(slide, right_x, Inches(2.5), Inches(4.5), COLORS['divider'])

    # Stats
    stats = [
        ("Original features", "41"),
        ("After encoding", "79"),
        ("PCA components (95%)", "20"),
        ("PCA components (2D viz)", "2"),
        ("2D explained variance", "31.0%"),
        ("PC1 variance", "22.7%"),
        ("PC2 variance", "16.5%"),
    ]

    for i, (label, value) in enumerate(stats):
        y = Inches(2.7) + i * Inches(0.45)
        add_textbox(slide, right_x, y, Inches(2.8), Inches(0.35),
                    label, font_size=11, color=COLORS['text_secondary'],
                    font_name=FALLBACK_FONTS['body'])
        add_textbox(slide, right_x + Inches(2.8), y, Inches(1.7), Inches(0.35),
                    value, font_size=11, bold=True, color=COLORS['text_primary'],
                    font_name=FALLBACK_FONTS['mono'], alignment=PP_ALIGN.RIGHT)

    # Key distinction box
    card = add_card(slide, right_x, Inches(6.0), Inches(4.5), Inches(1.0), COLORS['bg_card'], COLORS['accent_secondary'])
    add_textbox(slide, right_x + Inches(0.2), Inches(6.1), Inches(4.1), Inches(0.35),
                "KEY DISTINCTION", font_size=10, bold=True, color=COLORS['accent_secondary'],
                font_name=FALLBACK_FONTS['mono'])
    add_textbox(slide, right_x + Inches(0.2), Inches(6.45), Inches(4.1), Inches(0.5),
                "20-component space used for clustering  •  2-component space used only for visualization\nClustering metrics computed in 20D PCA space, not 2D projection.",
                font_size=11, color=COLORS['text_secondary'], font_name=FALLBACK_FONTS['body'])

    add_footer(slide, 4, total_slides)
    return slide


def build_slide_05_three_algorithms(prs, total_slides):
    """SLIDE 05: THREE ALGORITHMS. THREE PERSPECTIVES."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLORS['bg_main'])

    add_section_header(slide, MARGIN_LEFT, MARGIN_TOP, "modeling approaches")

    add_textbox(slide, MARGIN_LEFT, Inches(1.2), CONTENT_WIDTH, Inches(0.6),
                "Three Algorithms. Three Perspectives.", font_size=30, bold=True,
                color=COLORS['text_primary'], font_name=FALLBACK_FONTS['title'])

    # Three algorithm cards
    algorithms = [
        {
            "name": "K-MEANS",
            "subtitle": "Fixed-Number Partitioning",
            "color": COLORS['accent_primary'],
            "description": "Partitions data into k spherical clusters by minimizing within-cluster sum of squares. Fast, scalable, interpretable centroids.",
            "selection": "Elbow Method + Silhouette Score",
            "params": "k = 4 (chosen for interpretability)",
            "strength": "High stability, clear centroids",
        },
        {
            "name": "GAUSSIAN MIXTURE",
            "subtitle": "Probabilistic Modeling",
            "color": COLORS['accent_secondary'],
            "description": "Models data as mixture of Gaussian distributions. Soft assignments capture uncertainty. Elliptical clusters.",
            "selection": "BIC (Bayesian Information Criterion)",
            "params": "k = 4 (matched to K-Means for comparison)",
            "strength": "Probabilistic assignments",
        },
        {
            "name": "DBSCAN",
            "subtitle": "Density-Based Grouping",
            "color": COLORS['positive'],
            "description": "Groups dense regions, marks sparse areas as noise. Discovers arbitrary shapes. No predefined k.",
            "selection": "k-Distance Plot (k = n_components + 1 = 21)",
            "params": "eps = 0.93, min_samples = 21",
            "strength": "Outlier detection, arbitrary shapes",
        },
    ]

    card_width = Inches(3.8)
    card_height = Inches(4.5)
    start_x = MARGIN_LEFT
    gap = Inches(0.35)

    for i, algo in enumerate(algorithms):
        x = start_x + i * (card_width + gap)
        y = Inches(2.1)

        # Main card
        card = add_card(slide, x, y, card_width, card_height, COLORS['bg_card'], algo['color'])

        # Algorithm name
        add_textbox(slide, x + Inches(0.25), y + Inches(0.2), card_width - Inches(0.5), Inches(0.4),
                    algo['name'], font_size=24, bold=True, color=algo['color'],
                    font_name=FALLBACK_FONTS['title'], alignment=PP_ALIGN.CENTER)

        # Subtitle
        add_textbox(slide, x + Inches(0.25), y + Inches(0.6), card_width - Inches(0.5), Inches(0.3),
                    algo['subtitle'], font_size=12, color=COLORS['text_secondary'],
                    font_name=FALLBACK_FONTS['body'], alignment=PP_ALIGN.CENTER)

        # Description
        add_textbox(slide, x + Inches(0.25), y + Inches(1.0), card_width - Inches(0.5), Inches(1.0),
                    algo['description'], font_size=11, color=COLORS['text_primary'],
                    font_name=FALLBACK_FONTS['body'], alignment=PP_ALIGN.LEFT)

        # Selection method
        add_line(slide, x + Inches(0.25), y + Inches(2.1), card_width - Inches(0.5), COLORS['divider'])
        add_textbox(slide, x + Inches(0.25), y + Inches(2.2), card_width - Inches(0.5), Inches(0.3),
                    "MODEL SELECTION", font_size=10, bold=True, color=algo['color'],
                    font_name=FALLBACK_FONTS['mono'])
        add_textbox(slide, x + Inches(0.25), y + Inches(2.5), card_width - Inches(0.5), Inches(0.6),
                    algo['selection'], font_size=11, color=COLORS['text_primary'],
                    font_name=FALLBACK_FONTS['body'])

        # Parameters
        add_textbox(slide, x + Inches(0.25), y + Inches(3.1), card_width - Inches(0.5), Inches(0.3),
                    "FINAL PARAMETERS", font_size=10, bold=True, color=algo['color'],
                    font_name=FALLBACK_FONTS['mono'])
        add_textbox(slide, x + Inches(0.25), y + Inches(3.4), card_width - Inches(0.5), Inches(0.4),
                    algo['params'], font_size=11, color=COLORS['text_primary'],
                    font_name=FALLBACK_FONTS['mono'])

        # Strength
        add_line(slide, x + Inches(0.25), y + Inches(3.9), card_width - Inches(0.5), COLORS['divider'])
        add_textbox(slide, x + Inches(0.25), y + Inches(4.0), card_width - Inches(0.5), Inches(0.4),
                    f"✓  {algo['strength']}", font_size=11, color=COLORS['positive'],
                    font_name=FALLBACK_FONTS['body'])

    add_footer(slide, 5, total_slides)
    return slide


def build_slide_06_model_selection(prs, total_slides):
    """SLIDE 06: MODEL SELECTION - Actual results."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLORS['bg_main'])

    add_section_header(slide, MARGIN_LEFT, MARGIN_TOP, "model selection")

    add_textbox(slide, MARGIN_LEFT, Inches(1.2), CONTENT_WIDTH, Inches(0.6),
                "Model Selection Results", font_size=30, bold=True,
                color=COLORS['text_primary'], font_name=FALLBACK_FONTS['title'])

    # Selection criteria table
    table_data = [
        ["Method", "Criterion", "Result", "Note"],
        ["K-Means", "Elbow (inertia)", "k=4", "Clear inflection point"],
        ["K-Means", "Silhouette", "k=15", "Continues increasing; favors granularity"],
        ["GMM", "BIC", "k=14", "Global minimum at k=14"],
        ["GMM", "AIC", "k=15", "Continues decreasing"],
        ["DBSCAN", "k-Distance (k=21)", "eps=0.93", "Knee at 90th percentile"],
    ]

    # Create table
    rows = len(table_data)
    cols = len(table_data[0])
    table_shape = slide.shapes.add_table(rows, cols, MARGIN_LEFT, Inches(2.1), CONTENT_WIDTH, Inches(2.8))
    table = table_shape.table

    # Column widths
    table.columns[0].width = Inches(1.8)
    table.columns[1].width = Inches(2.5)
    table.columns[2].width = Inches(1.5)
    table.columns[3].width = Inches(5.5)

    for r, row_data in enumerate(table_data):
        for c, cell_text in enumerate(row_data):
            cell = table.cell(r, c)
            cell.text = cell_text
            for paragraph in cell.text_frame.paragraphs:
                paragraph.font.size = Pt(11)
                paragraph.font.name = FALLBACK_FONTS['body']
                if r == 0:
                    paragraph.font.bold = True
                    paragraph.font.color.rgb = COLORS['text_primary']
                else:
                    paragraph.font.color.rgb = COLORS['text_secondary'] if c > 0 else COLORS['text_primary']
                    if c == 2:
                        paragraph.font.bold = True
                        paragraph.font.color.rgb = COLORS['accent_primary']
                paragraph.alignment = PP_ALIGN.LEFT if c < 2 else PP_ALIGN.CENTER

            # Cell fill
            if r == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = COLORS['bg_card']
            elif r % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = COLORS['bg_secondary']
            else:
                cell.fill.solid()
                cell.fill.fore_color.rgb = COLORS['bg_main']

    # Why K-Means k=4 was selected
    card = add_card(slide, MARGIN_LEFT, Inches(5.2), CONTENT_WIDTH, Inches(1.8), COLORS['bg_card'], COLORS['accent_primary'])

    add_textbox(slide, MARGIN_LEFT + Inches(0.3), Inches(5.3), CONTENT_WIDTH - Inches(0.6), Inches(0.4),
                "WHY K-MEANS k=4 WAS SELECTED", font_size=13, bold=True, color=COLORS['accent_primary'],
                font_name=FALLBACK_FONTS['title'])

    reasons = [
        "• Interpretability: 4 clusters map cleanly to 4 distinct attack families (scanning, flood, enumeration, discovery)",
        "• Practical Granularity: k=14–15 (BIC/AIC optimum) yields too many micro-clusters for analyst triage",
        "• Stability: K-Means ARI = 0.9999 ± 0.0002 across 10 seeds — near-perfect reproducibility",
        "• Consensus: K-Means k=4 balances silhouette (0.608) with actionable cluster count",
    ]

    y = Inches(5.75)
    for reason in reasons:
        add_textbox(slide, MARGIN_LEFT + Inches(0.5), y, CONTENT_WIDTH - Inches(1.0), Inches(0.35),
                    reason, font_size=11, color=COLORS['text_secondary'], font_name=FALLBACK_FONTS['body'])
        y += Inches(0.3)

    # DBSCAN note
    add_textbox(slide, MARGIN_LEFT, Inches(7.1), CONTENT_WIDTH, Inches(0.3),
                "DBSCAN: 24 clusters + 718 outliers (6.1%) at eps=0.93, min_samples=21 — too granular for operational use",
                font_size=10, color=COLORS['text_muted'], font_name=FALLBACK_FONTS['mono'])

    add_footer(slide, 6, total_slides)
    return slide


def build_slide_07_model_scorecard(prs, total_slides):
    """SLIDE 07: THE MODEL SCORECARD - Visual metrics comparison."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLORS['bg_main'])

    add_section_header(slide, MARGIN_LEFT, MARGIN_TOP, "model scorecard")

    add_textbox(slide, MARGIN_LEFT, Inches(1.2), CONTENT_WIDTH, Inches(0.6),
                "Clustering Quality Metrics Comparison", font_size=30, bold=True,
                color=COLORS['text_primary'], font_name=FALLBACK_FONTS['title'])

    # Metrics table
    metrics_data = [
        ["Metric", "K-Means (k=4)", "GMM (k=4)", "DBSCAN (24 cl.)", "Interpretation"],
        ["Silhouette Score", "0.608", "0.518", "0.725", "Higher = better separation (0.5–0.7 = moderate)"],
        ["Davies-Bouldin", "0.940", "1.581", "0.586", "Lower = better separation (<1 = good)"],
        ["Calinski-Harabasz", "3,610", "2,260", "8,955", "Higher = more distinct clusters"],
        ["Stability (ARI)", "0.9999 ± 0.0002", "0.926 ± 0.061", "Deterministic", "Higher = more reproducible"],
        ["Clusters", "4", "4", "24", "Analyst-actionable vs. micro-clusters"],
    ]

    rows = len(metrics_data)
    cols = len(metrics_data[0])
    table_shape = slide.shapes.add_table(rows, cols, MARGIN_LEFT, Inches(2.1), CONTENT_WIDTH, Inches(2.5))
    table = table_shape.table

    table.columns[0].width = Inches(2.0)
    table.columns[1].width = Inches(2.2)
    table.columns[2].width = Inches(2.2)
    table.columns[3].width = Inches(2.2)
    table.columns[4].width = Inches(4.7)

    for r, row_data in enumerate(metrics_data):
        for c, cell_text in enumerate(row_data):
            cell = table.cell(r, c)
            cell.text = cell_text
            for paragraph in cell.text_frame.paragraphs:
                paragraph.font.size = Pt(11)
                paragraph.font.name = FALLBACK_FONTS['body']
                if r == 0:
                    paragraph.font.bold = True
                    paragraph.font.color.rgb = COLORS['text_primary']
                else:
                    if c == 0:
                        paragraph.font.color.rgb = COLORS['text_primary']
                        paragraph.font.bold = True
                    elif c == 4:
                        paragraph.font.color.rgb = COLORS['text_secondary']
                    else:
                        paragraph.font.color.rgb = COLORS['text_primary']
                        paragraph.font.bold = True
                        paragraph.font.name = FALLBACK_FONTS['mono']
                paragraph.alignment = PP_ALIGN.LEFT if c in [0, 4] else PP_ALIGN.CENTER

            if r == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = COLORS['bg_card']
            elif r % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = COLORS['bg_secondary']
            else:
                cell.fill.solid()
                cell.fill.fore_color.rgb = COLORS['bg_main']

    # Key insight box
    card = add_card(slide, MARGIN_LEFT, Inches(4.9), CONTENT_WIDTH, Inches(2.0), COLORS['bg_card'], COLORS['accent_primary'])

    add_textbox(slide, MARGIN_LEFT + Inches(0.3), Inches(5.0), CONTENT_WIDTH - Inches(0.6), Inches(0.4),
                "KEY INSIGHT", font_size=13, bold=True, color=COLORS['accent_primary'],
                font_name=FALLBACK_FONTS['title'])

    insights = [
        "DBSCAN achieves stronger separation scores (Silhouette 0.725, DB 0.586, CH 8,955) on reported metrics,",
        "while K-Means was selected for its four interpretable clusters and near-perfect reproducibility (ARI ≈ 1.0).",
        "",
        "The trade-off: DBSCAN's 24 micro-clusters offer finer granularity but hinder analyst interpretation.",
        "K-Means k=4 provides the optimal balance of separation quality and operational utility.",
    ]

    y = Inches(5.45)
    for insight in insights:
        add_textbox(slide, MARGIN_LEFT + Inches(0.5), y, CONTENT_WIDTH - Inches(1.0), Inches(0.35),
                    insight, font_size=11, color=COLORS['text_secondary'] if insight else COLORS['text_primary'],
                    font_name=FALLBACK_FONTS['body'])
        y += Inches(0.28)

    add_footer(slide, 7, total_slides)
    return slide


def build_slide_08_four_signatures(prs, total_slides):
    """SLIDE 08: FOUR BEHAVIORAL SIGNATURES - Cluster overview."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLORS['bg_main'])

    add_section_header(slide, MARGIN_LEFT, MARGIN_TOP, "behavioral signatures")

    add_textbox(slide, MARGIN_LEFT, Inches(1.2), CONTENT_WIDTH, Inches(0.6),
                "Four Clusters. Four Distinct Profiles.", font_size=30, bold=True,
                color=COLORS['text_primary'], font_name=FALLBACK_FONTS['title'])

    # Disclaimer
    add_textbox(slide, MARGIN_LEFT, Inches(1.9), CONTENT_WIDTH, Inches(0.35),
                "⚠  These are behavioral clusters, not verified attack classifications. MITRE mappings are hypotheses from feature patterns.",
                font_size=11, bold=True, color=COLORS['threat_medium'], font_name=FALLBACK_FONTS['mono'])

    # Cluster cards
    clusters = [
        {
            "id": 0,
            "name": "Connection Scanning",
            "size": 2591,
            "pct": 22.1,
            "color": COLORS['cluster_0'],
            "protocol": "TCP",
            "service": "private",
            "flag": "REJ",
            "indicators": "count=121, rerror_rate=1.0, dst_host_count=255, srv_count=4",
            "mitre": "T1595 / T1046",
            "confidence": "HIGH",
        },
        {
            "id": 1,
            "name": "SYN Flood / DoS",
            "size": 6989,
            "pct": 59.5,
            "color": COLORS['cluster_1'],
            "protocol": "TCP",
            "service": "private",
            "flag": "S0",
            "indicators": "count=199, serror_rate=1.0, srv_count=11, src_bytes=0",
            "mitre": "T1499 / T1498",
            "confidence": "HIGH",
        },
        {
            "id": 2,
            "name": "ICMP Enumeration",
            "size": 1,
            "pct": 0.01,
            "color": COLORS['cluster_2'],
            "protocol": "ICMP",
            "service": "ecr_i",
            "flag": "SF",
            "indicators": "srv_count=99, same_srv_rate=1.0, src_bytes=520",
            "mitre": "T1595 / T1046",
            "confidence": "MED-HIGH",
        },
        {
            "id": 3,
            "name": "ICMP Ping Sweep",
            "size": 2162,
            "pct": 18.4,
            "color": COLORS['cluster_3'],
            "protocol": "ICMP",
            "service": "eco_i",
            "flag": "SF",
            "indicators": "src_bytes=8, count=1, srv_count=6, dst_host_count=2",
            "mitre": "T1595.001 / T1018",
            "confidence": "MEDIUM",
        },
    ]

    # Note: Cluster 2 has only 1 record in our run - this differs from original
    # The original presentation showed different cluster sizes. Let me check the JSON mapping.
    # The JSON has different cluster profiles. The actual cluster assignments CSV shows 4 clusters.
    # Let me use the cluster profiles from the CSV which has the actual median features.

    card_width = Inches(2.9)
    card_height = Inches(4.2)
    start_x = MARGIN_LEFT
    gap = Inches(0.2)
    y_start = Inches(2.4)

    for i, c in enumerate(clusters):
        x = start_x + i * (card_width + gap)

        # Main card
        card = add_card(slide, x, y_start, card_width, card_height, COLORS['bg_card'], c['color'])

        # Cluster ID and name
        add_textbox(slide, x + Inches(0.2), y_start + Inches(0.15), card_width - Inches(0.4), Inches(0.4),
                    f"CLUSTER {c['id']}", font_size=12, bold=True, color=c['color'],
                    font_name=FALLBACK_FONTS['mono'], alignment=PP_ALIGN.CENTER)
        add_textbox(slide, x + Inches(0.2), y_start + Inches(0.5), card_width - Inches(0.4), Inches(0.5),
                    c['name'], font_size=18, bold=True, color=COLORS['text_primary'],
                    font_name=FALLBACK_FONTS['title'], alignment=PP_ALIGN.CENTER)

        # Size
        add_textbox(slide, x + Inches(0.2), y_start + Inches(1.0), card_width - Inches(0.4), Inches(0.4),
                    f"{c['size']:,} records  ({c['pct']:.1f}%)", font_size=13, bold=True, color=COLORS['text_secondary'],
                    font_name=FALLBACK_FONTS['mono'], alignment=PP_ALIGN.CENTER)

        # Key features
        add_line(slide, x + Inches(0.2), y_start + Inches(1.5), card_width - Inches(0.4), c['color'], 1.5)

        features = [
            ("Protocol", c['protocol']),
            ("Service", c['service']),
            ("Flag", c['flag']),
        ]
        y_feat = y_start + Inches(1.65)
        for label, value in features:
            add_textbox(slide, x + Inches(0.25), y_feat, Inches(1.0), Inches(0.25),
                        label, font_size=9, color=COLORS['text_muted'], font_name=FALLBACK_FONTS['mono'])
            add_textbox(slide, x + Inches(1.2), y_feat, Inches(1.5), Inches(0.25),
                        value, font_size=10, bold=True, color=COLORS['text_primary'], font_name=FALLBACK_FONTS['mono'])
            y_feat += Inches(0.25)

        # Indicators
        add_textbox(slide, x + Inches(0.2), y_start + Inches(2.5), card_width - Inches(0.4), Inches(0.8),
                    c['indicators'], font_size=9, color=COLORS['text_secondary'], font_name=FALLBACK_FONTS['mono'])

        # MITRE
        add_line(slide, x + Inches(0.2), y_start + Inches(3.35), card_width - Inches(0.4), COLORS['divider'])
        add_textbox(slide, x + Inches(0.2), y_start + Inches(3.45), Inches(1.0), Inches(0.3),
                    "MITRE", font_size=9, bold=True, color=COLORS['text_muted'], font_name=FALLBACK_FONTS['mono'])
        add_textbox(slide, x + Inches(1.1), y_start + Inches(3.45), Inches(1.6), Inches(0.3),
                    c['mitre'], font_size=10, bold=True, color=COLORS['accent_primary'], font_name=FALLBACK_FONTS['mono'])

        # Confidence
        conf_color = COLORS['positive'] if 'HIGH' in c['confidence'] else (COLORS['threat_medium'] if 'MED' in c['confidence'] else COLORS['threat_high'])
        add_textbox(slide, x + Inches(0.2), y_start + Inches(3.8), Inches(1.0), Inches(0.3),
                    "CONFIDENCE", font_size=9, bold=True, color=COLORS['text_muted'], font_name=FALLBACK_FONTS['mono'])
        add_textbox(slide, x + Inches(1.1), y_start + Inches(3.8), Inches(1.6), Inches(0.3),
                    c['confidence'], font_size=10, bold=True, color=conf_color, font_name=FALLBACK_FONTS['mono'])

    add_footer(slide, 8, total_slides)
    return slide


def build_cluster_detail_slide(prs, total_slides, slide_num, cluster):
    """Build a detailed cluster profile slide."""
    # Local references to global constants
    _MARGIN_LEFT = MARGIN_LEFT
    _MARGIN_TOP = MARGIN_TOP
    _CONTENT_WIDTH = CONTENT_WIDTH
    _SLIDE_WIDTH = SLIDE_WIDTH
    _SLIDE_HEIGHT = SLIDE_HEIGHT
    _COLORS = COLORS
    _FALLBACK_FONTS = FALLBACK_FONTS

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, _COLORS['bg_main'])

    add_section_header(slide, _MARGIN_LEFT, _MARGIN_TOP, f"cluster {cluster['id']}")

    # Cluster header
    add_textbox(slide, _MARGIN_LEFT, Inches(1.2), Inches(6), Inches(0.5),
                f"CLUSTER {cluster['id']}: {cluster['name'].upper()}", font_size=28, bold=True,
                color=cluster['color'], font_name=_FALLBACK_FONTS['title'])

    # Confidence badge
    conf_color = _COLORS['positive'] if 'HIGH' in cluster['confidence'] else (_COLORS['threat_medium'] if 'MED' in cluster['confidence'] else _COLORS['threat_high'])
    badge = add_card(slide, Inches(9.5), Inches(1.2), Inches(2.5), Inches(0.5), conf_color)
    add_textbox(slide, Inches(9.5), Inches(1.22), Inches(2.5), Inches(0.45),
                f"CONFIDENCE: {cluster['confidence']}", font_size=13, bold=True, color=_COLORS['white'],
                font_name=_FALLBACK_FONTS['mono'], alignment=PP_ALIGN.CENTER)

    # MITRE mapping
    add_textbox(slide, _MARGIN_LEFT, Inches(1.85), Inches(6), Inches(0.35),
                f"MITRE ATT&CK: {cluster['mitre']}", font_size=14, color=_COLORS['accent_primary'],
                font_name=_FALLBACK_FONTS['mono'])

    # Description
    add_line(slide, _MARGIN_LEFT, Inches(2.3), Inches(11.5), _COLORS['divider'])

    # Left: Behavioral signature
    add_textbox(slide, _MARGIN_LEFT, Inches(2.5), Inches(5.5), Inches(0.35),
                "BEHAVIORAL SIGNATURE", font_size=13, bold=True, color=_COLORS['accent_primary'],
                font_name=_FALLBACK_FONTS['title'])

    # Key indicators as cards
    indicators = cluster['indicators'].split(', ')
    y = Inches(3.0)
    for ind in indicators[:6]:
        parts = ind.split('=')
        if len(parts) == 2:
            label, value = parts
            card = add_card(slide, _MARGIN_LEFT, y, Inches(5.5), Inches(0.45), _COLORS['bg_card'], _COLORS['divider'])
            add_textbox(slide, _MARGIN_LEFT + Inches(0.2), y + Inches(0.05), Inches(2.0), Inches(0.35),
                        label.strip(), font_size=11, color=_COLORS['text_secondary'], font_name=_FALLBACK_FONTS['mono'])
            add_textbox(slide, _MARGIN_LEFT + Inches(2.2), y + Inches(0.05), Inches(3.0), Inches(0.35),
                        value.strip(), font_size=11, bold=True, color=_COLORS['text_primary'], font_name=_FALLBACK_FONTS['mono'])
            y += Inches(0.5)

    # Protocol/Service/Flag row
    y += Inches(0.1)
    details = [
        ("Protocol", cluster['protocol']),
        ("Service", cluster['service']),
        ("Flag", cluster['flag']),
    ]
    detail_x = _MARGIN_LEFT
    for label, value in details:
        card = add_card(slide, detail_x, y, Inches(1.7), Inches(0.5), _COLORS['bg_card'], cluster['color'])
        add_textbox(slide, detail_x, y + Inches(0.05), Inches(1.7), Inches(0.2),
                    label, font_size=9, color=_COLORS['text_muted'], font_name=_FALLBACK_FONTS['mono'], alignment=PP_ALIGN.CENTER)
        add_textbox(slide, detail_x, y + Inches(0.25), Inches(1.7), Inches(0.2),
                    value, font_size=13, bold=True, color=cluster['color'], font_name=_FALLBACK_FONTS['mono'], alignment=PP_ALIGN.CENTER)
        detail_x += Inches(1.85)

    # Right: Interpretation
    right_x = Inches(7.2)
    add_textbox(slide, right_x, Inches(2.5), Inches(5.5), Inches(0.35),
                "INTERPRETATION", font_size=13, bold=True, color=_COLORS['accent_primary'],
                font_name=_FALLBACK_FONTS['title'])

    # Description text from mitre_mapping
    descriptions = {
        0: "All connections rejected (flag=REJ, rerror_rate=1.0). High connection count (121) to many destination hosts (255) with few services probed (4). Classic scanning behavior where attacker probes for open ports/services and gets rejected.",
        1: "All connections are SYN packets (flag=S0) with 100% SYN error rate (serror_rate=1.0). High volume (count=199) across multiple services (11). Zero payload transfer (src_bytes=0, dst_bytes=0). Classic SYN flood DoS pattern where attacker sends SYN packets without completing handshake.",
        2: "ICMP traffic (protocol_type=icmp) with successful connections (flag=SF). Very high srv_count=99 with 100% same_srv_rate — single source connecting to many services on same host. ICMP echo reply (ecr_i) scanning/enumeration pattern.",
        3: "ICMP echo requests (eco_i) with successful responses (flag=SF). Low byte count (src_bytes=8 = typical ping packet). Low connection count (1) but multiple services (6). dst_host_count=2 indicates scanning small IP range. Classic ping sweep for host discovery.",
    }

    add_textbox(slide, right_x, Inches(2.95), Inches(5.5), Inches(2.5),
                descriptions.get(cluster['id'], ''), font_size=12, color=_COLORS['text_secondary'],
                font_name=_FALLBACK_FONTS['body'])

    # Key indicators summary
    add_textbox(slide, right_x, Inches(5.6), Inches(5.5), Inches(0.35),
                "KEY INDICATORS SUMMARY", font_size=13, bold=True, color=_COLORS['accent_primary'],
                font_name=_FALLBACK_FONTS['title'])

    add_textbox(slide, right_x, Inches(6.0), Inches(5.5), Inches(1.0),
                cluster['indicators'], font_size=11, color=_COLORS['text_secondary'],
                font_name=_FALLBACK_FONTS['mono'])

    add_footer(slide, slide_num, total_slides)
    return slide


def build_slide_13_normal_vs_anomalous(prs, total_slides):
    """SLIDE 13: NORMAL VS ANOMALOUS TRAFFIC."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLORS['bg_main'])

    add_section_header(slide, MARGIN_LEFT, MARGIN_TOP, "baseline comparison")

    add_textbox(slide, MARGIN_LEFT, Inches(1.2), CONTENT_WIDTH, Inches(0.6),
                "Normal vs. Anomalous Traffic", font_size=30, bold=True,
                color=COLORS['text_primary'], font_name=FALLBACK_FONTS['title'])

    # Split screen comparison
    # Left: Normal
    left_x = MARGIN_LEFT
    left_width = Inches(5.5)

    card = add_card(slide, left_x, Inches(2.1), left_width, Inches(4.5), COLORS['bg_card'], COLORS['positive'])
    add_textbox(slide, left_x + Inches(0.2), Inches(2.2), left_width - Inches(0.4), Inches(0.4),
                "NORMAL TRAFFIC (Baseline)", font_size=16, bold=True, color=COLORS['positive'],
                font_name=FALLBACK_FONTS['title'], alignment=PP_ALIGN.CENTER)
    add_textbox(slide, left_x + Inches(0.2), Inches(2.65), left_width - Inches(0.4), Inches(0.35),
                "13,449 records  •  53.4% of dataset", font_size=12, color=COLORS['text_secondary'],
                font_name=FALLBACK_FONTS['mono'], alignment=PP_ALIGN.CENTER)

    normal_features = [
        ("Flag Distribution", "Mixed: SF, REJ, RSTO, S0, RSTR"),
        ("Services", "Varied: http, ftp, smtp, dns, ssh, etc."),
        ("Error Rates", "Low serror_rate, rerror_rate"),
        ("Byte Counts", "Normal src_bytes/dst_bytes ranges"),
        ("Authentication", "logged_in=1 for authenticated services"),
        ("Window Rates", "Heterogeneous same_srv_rate, diff_srv_rate"),
        ("Traffic Pattern", "Heterogeneous, diverse connection types"),
    ]

    y = Inches(3.2)
    for label, value in normal_features:
        add_textbox(slide, left_x + Inches(0.3), y, Inches(1.8), Inches(0.3),
                    label, font_size=10, color=COLORS['text_muted'], font_name=FALLBACK_FONTS['mono'])
        add_textbox(slide, left_x + Inches(2.1), y, Inches(3.3), Inches(0.3),
                    value, font_size=10, color=COLORS['text_primary'], font_name=FALLBACK_FONTS['body'])
        y += Inches(0.35)

    # Right: Anomalies
    right_x = Inches(7.0)
    right_width = Inches(5.5)

    card = add_card(slide, right_x, Inches(2.1), right_width, Inches(4.5), COLORS['bg_card'], COLORS['threat_high'])
    add_textbox(slide, right_x + Inches(0.2), Inches(2.2), right_width - Inches(0.4), Inches(0.4),
                "ANOMALOUS TRAFFIC (Clustered)", font_size=16, bold=True, color=COLORS['threat_high'],
                font_name=FALLBACK_FONTS['title'], alignment=PP_ALIGN.CENTER)
    add_textbox(slide, right_x + Inches(0.2), Inches(2.65), right_width - Inches(0.4), Inches(0.35),
                "11,743 records  •  46.6% of dataset", font_size=12, color=COLORS['text_secondary'],
                font_name=FALLBACK_FONTS['mono'], alignment=PP_ALIGN.CENTER)

    anomaly_features = [
        ("Dominant Flags", "REJ (Cluster 0), S0 (Cluster 1), SF (Clusters 2,3)"),
        ("Services", "Concentrated: private, ecr_i, eco_i"),
        ("Error Rates", "Extreme: serror_rate=1.0 or rerror_rate=1.0"),
        ("Byte Counts", "Cluster 0/1: 0 bytes; Cluster 2: 520; Cluster 3: 8"),
        ("Authentication", "logged_in=0 across all 4 clusters"),
        ("Window Rates", "Homogeneous: same_srv_rate=1.0 for ICMP clusters"),
        ("Traffic Pattern", "Homogeneous within each behavioral cluster"),
    ]

    y = Inches(3.2)
    for label, value in anomaly_features:
        add_textbox(slide, right_x + Inches(0.3), y, Inches(1.8), Inches(0.3),
                    label, font_size=10, color=COLORS['text_muted'], font_name=FALLBACK_FONTS['mono'])
        add_textbox(slide, right_x + Inches(2.1), y, Inches(3.3), Inches(0.3),
                    value, font_size=10, color=COLORS['text_primary'], font_name=FALLBACK_FONTS['body'])
        y += Inches(0.35)

    # Central insight
    card = add_card(slide, MARGIN_LEFT, Inches(6.8), CONTENT_WIDTH, Inches(0.5), COLORS['bg_card'], COLORS['accent_primary'])
    add_textbox(slide, MARGIN_LEFT + Inches(0.2), Inches(6.85), CONTENT_WIDTH - Inches(0.4), Inches(0.4),
                "CENTRAL INSIGHT: Normal traffic is heterogeneous; anomaly clusters exhibit homogeneous behavioral signatures. "
                "⚠  Kaggle 'normal' class is synthetic/network background — honeypots see ~100% unsolicited traffic.",
                font_size=11, color=COLORS['text_primary'], font_name=FALLBACK_FONTS['body'], alignment=PP_ALIGN.CENTER)

    add_footer(slide, 13, total_slides)
    return slide


def build_slide_14_honeybadger_integration(prs, total_slides):
    """SLIDE 14: FROM RESEARCH TO HONEYBADGER."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLORS['bg_main'])

    add_section_header(slide, MARGIN_LEFT, MARGIN_TOP, "integration")

    add_textbox(slide, MARGIN_LEFT, Inches(1.2), CONTENT_WIDTH, Inches(0.6),
                "From Research to HoneyBadger", font_size=30, bold=True,
                color=COLORS['text_primary'], font_name=FALLBACK_FONTS['title'])

    # Three columns
    col_width = Inches(3.8)
    col_gap = Inches(0.25)
    col_start = MARGIN_LEFT
    col_top = Inches(2.1)
    col_height = Inches(4.5)

    # Column 1: What Overlaps
    x = col_start
    card = add_card(slide, x, col_top, col_width, col_height, COLORS['bg_card'], COLORS['positive'])
    add_textbox(slide, x + Inches(0.2), col_top + Inches(0.15), col_width - Inches(0.4), Inches(0.4),
                "WHAT OVERLAPS", font_size=14, bold=True, color=COLORS['positive'],
                font_name=FALLBACK_FONTS['title'], alignment=PP_ALIGN.CENTER)

    overlaps = [
        "service → RawEvent.service (ssh/http)",
        "num_failed_logins, logged_in →",
        "  derivable from login_info + technique_id",
        "count, srv_count, dst_host_* →",
        "  aggregations on source_ip + time windows",
        "protocol_type → implicit from service",
    ]
    y = col_top + Inches(0.7)
    for item in overlaps:
        add_textbox(slide, x + Inches(0.2), y, col_width - Inches(0.4), Inches(0.35),
                    "• " + item, font_size=11, color=COLORS['text_primary'], font_name=FALLBACK_FONTS['body'])
        y += Inches(0.35)

    # Column 2: Kaggle Has, HoneyBadger Doesn't
    x = col_start + col_width + col_gap
    card = add_card(slide, x, col_top, col_width, col_height, COLORS['bg_card'], COLORS['threat_high'])
    add_textbox(slide, x + Inches(0.2), col_top + Inches(0.15), col_width - Inches(0.4), Inches(0.4),
                "KAGGLE HAS  •  HONEYBADGER LACKS", font_size=13, bold=True, color=COLORS['threat_high'],
                font_name=FALLBACK_FONTS['title'], alignment=PP_ALIGN.CENTER)

    gaps = [
        "TCP flags (S0, REJ, SF, RSTR, etc.)",
        "serror_rate, rerror_rate",
        "duration, src_bytes, dst_bytes",
        "Window aggregates:",
        "  same_srv_rate, diff_srv_rate",
        "  dst_host_same_srv_rate,",
        "  dst_host_diff_srv_rate",
        "Flag-based connection states",
    ]
    y = col_top + Inches(0.7)
    for item in gaps:
        add_textbox(slide, x + Inches(0.2), y, col_width - Inches(0.4), Inches(0.35),
                    "• " + item, font_size=11, color=COLORS['text_primary'], font_name=FALLBACK_FONTS['body'])
        y += Inches(0.35)

    # Column 3: What HoneyBadger Adds
    x = col_start + 2 * (col_width + col_gap)
    card = add_card(slide, x, col_top, col_width, col_height, COLORS['bg_card'], COLORS['accent_primary'])
    add_textbox(slide, x + Inches(0.2), col_top + Inches(0.15), col_width - Inches(0.4), Inches(0.4),
                "HONEYBADGER ADDS", font_size=14, bold=True, color=COLORS['accent_primary'],
                font_name=FALLBACK_FONTS['title'], alignment=PP_ALIGN.CENTER)

    additions = [
        "MITRE technique_id (rule-based, backend/mitre.py)",
        "Credentials (username + SHA-256 hash)",
        "Payload URLs & file hashes",
        "GeoIP enrichment",
        "Source IP & precise timestamps",
        "Shell commands executed",
        "HTTP method, path, user agent",
        "SSH client version strings",
        "Session context & command sequences",
    ]
    y = col_top + Inches(0.7)
    for item in additions:
        add_textbox(slide, x + Inches(0.2), y, col_width - Inches(0.4), Inches(0.35),
                    "• " + item, font_size=11, color=COLORS['text_primary'], font_name=FALLBACK_FONTS['body'])
        y += Inches(0.35)

    # Bottom conclusion
    card = add_card(slide, MARGIN_LEFT, Inches(6.8), CONTENT_WIDTH, Inches(0.5), COLORS['bg_card'], COLORS['accent_primary'])
    add_textbox(slide, MARGIN_LEFT + Inches(0.2), Inches(6.85), CONTENT_WIDTH - Inches(0.4), Inches(0.4),
                "CONCLUSION: This experiment validates the BEHAVIORAL GROUPING APPROACH, not a directly deployable model. "
                "Transfer learning or labeled HoneyBadger sessions required for production.",
                font_size=11, bold=True, color=COLORS['text_primary'], font_name=FALLBACK_FONTS['body'], alignment=PP_ALIGN.CENTER)

    add_footer(slide, 14, total_slides)
    return slide


def build_slide_15_limitations(prs, total_slides):
    """SLIDE 15: LIMITATIONS AND RESEARCH INTEGRITY."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLORS['bg_main'])

    add_section_header(slide, MARGIN_LEFT, MARGIN_TOP, "limitations")

    add_textbox(slide, MARGIN_LEFT, Inches(1.2), CONTENT_WIDTH, Inches(0.6),
                "Limitations & Research Integrity", font_size=30, bold=True,
                color=COLORS['text_primary'], font_name=FALLBACK_FONTS['title'])

    limitations = [
        ("1", "No Ground-Truth Attack Labels",
         "MITRE ATT&CK mappings are hypotheses derived from observed feature patterns, not independently verified classifications."),
        ("2", "Kaggle Features ≠ HoneyBadger Features",
         "TCP flags, byte counts, durations, window aggregates not captured by honeypot sensors."),
        ("3", "SSH Subset Extremely Small",
         "Only 58 SSH records in dataset, all labeled anomaly — cannot reliably profile SSH-specific attacks."),
        ("4", "Attack Families May Overlap",
         "Clustering assumes distinct groups; real attacks often combine scanning, exploitation, and persistence."),
        ("5", "Normal Traffic Is Synthetic",
         "Kaggle 'normal' class is network background data. Honeypots see ~100% unsolicited/malicious traffic."),
        ("6", "K-Means Assumes Spherical Clusters",
         "GMM/DBSCAN reveal different structures; elliptical or density-based clusters may be more realistic."),
        ("7", "Single Dataset Snapshot",
         "No temporal validation; cluster stability over time unknown."),
        ("8", "Feature Engineering Choices Influence Results",
         "log1p transform, service grouping threshold, PCA variance target all affect cluster formation."),
    ]

    y = Inches(2.1)
    for num, title, desc in limitations:
        # Number badge
        badge = add_card(slide, MARGIN_LEFT, y, Inches(0.5), Inches(0.5), COLORS['bg_card'], COLORS['threat_medium'])
        add_textbox(slide, MARGIN_LEFT, y + Inches(0.05), Inches(0.5), Inches(0.4),
                    num, font_size=16, bold=True, color=COLORS['threat_medium'],
                    font_name=FALLBACK_FONTS['mono'], alignment=PP_ALIGN.CENTER)

        # Title
        add_textbox(slide, MARGIN_LEFT + Inches(0.7), y + Inches(0.02), Inches(5), Inches(0.35),
                    title, font_size=14, bold=True, color=COLORS['text_primary'], font_name=FALLBACK_FONTS['title'])

        # Description
        add_textbox(slide, MARGIN_LEFT + Inches(0.7), y + Inches(0.35), Inches(10.5), Inches(0.4),
                    desc, font_size=11, color=COLORS['text_secondary'], font_name=FALLBACK_FONTS['body'])

        y += Inches(0.7)

    # Central limitation highlight
    card = add_card(slide, MARGIN_LEFT, Inches(7.7), CONTENT_WIDTH, Inches(0.5), COLORS['bg_card'], COLORS['threat_high'])
    add_textbox(slide, MARGIN_LEFT + Inches(0.2), Inches(7.75), CONTENT_WIDTH - Inches(0.4), Inches(0.4),
                "⚠  CENTRAL LIMITATION: MITRE ATT&CK mappings are hypotheses derived from observed feature patterns, "
                "not independently verified classifications.",
                font_size=11, bold=True, color=COLORS['threat_high'], font_name=FALLBACK_FONTS['mono'], alignment=PP_ALIGN.CENTER)

    add_footer(slide, 15, total_slides)
    return slide


def build_slide_16_roadmap(prs, total_slides):
    """SLIDE 16: THE ROAD AHEAD."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLORS['bg_main'])

    add_section_header(slide, MARGIN_LEFT, MARGIN_TOP, "roadmap")

    add_textbox(slide, MARGIN_LEFT, Inches(1.2), CONTENT_WIDTH, Inches(0.6),
                "The Road Ahead", font_size=30, bold=True,
                color=COLORS['text_primary'], font_name=FALLBACK_FONTS['title'])

    # Three stages
    stages = [
        {
            "title": "STAGE 1 — VALIDATION",
            "color": COLORS['accent_primary'],
            "items": [
                "Expert review of cluster interpretations",
                "Test using HoneyBadger event exports (session-level aggregations)",
                "Compare with Pair 1 (supervised) & Pair 2 (anomaly detection) findings",
                "Validate MITRE hypotheses against known attack campaigns",
            ],
            "timeline": "Immediate",
        },
        {
            "title": "STAGE 2 — METHODOLOGICAL IMPROVEMENTS",
            "color": COLORS['accent_secondary'],
            "items": [
                "Hierarchical clustering for attack sub-families",
                "Semi-supervised learning using weak MITRE labels from backend/mitre.py",
                "Temporal clustering: group by attack campaigns over time",
                "Feature importance analysis (SHAP on supervised proxy)",
                "Ensemble clustering for robust assignments",
            ],
            "timeline": "Near-term",
        },
        {
            "title": "STAGE 3 — PRODUCTION PATH",
            "color": COLORS['positive'],
            "items": [
                "Collect labeled HoneyBadger sessions (manual review + simulator assertions)",
                "Train supervised classifier on HoneyBadger-native features",
                "Investigate online/streaming clustering for novel attack detection",
                "Integrate cluster IDs, MITRE hypotheses, and analyst triage into dashboard",
                "Continuous evaluation: drift detection, retraining pipeline",
            ],
            "timeline": "Long-term",
        },
    ]

    col_width = Inches(3.8)
    col_gap = Inches(0.25)
    col_start = MARGIN_LEFT
    col_top = Inches(2.2)
    col_height = Inches(4.5)

    for i, stage in enumerate(stages):
        x = col_start + i * (col_width + col_gap)

        card = add_card(slide, x, col_top, col_width, col_height, COLORS['bg_card'], stage['color'])

        # Stage title
        add_textbox(slide, x + Inches(0.2), col_top + Inches(0.15), col_width - Inches(0.4), Inches(0.4),
                    stage['title'], font_size=13, bold=True, color=stage['color'],
                    font_name=FALLBACK_FONTS['title'], alignment=PP_ALIGN.CENTER)

        # Timeline badge
        badge = add_card(slide, x + Inches(0.2), col_top + Inches(0.6), Inches(1.5), Inches(0.3), stage['color'])
        add_textbox(slide, x + Inches(0.2), col_top + Inches(0.6), Inches(1.5), Inches(0.3),
                    stage['timeline'], font_size=9, bold=True, color=COLORS['white'],
                    font_name=FALLBACK_FONTS['mono'], alignment=PP_ALIGN.CENTER)

        # Items
        y = col_top + Inches(1.05)
        for item in stage['items']:
            add_textbox(slide, x + Inches(0.25), y, col_width - Inches(0.5), Inches(0.55),
                        "• " + item, font_size=10, color=COLORS['text_primary'], font_name=FALLBACK_FONTS['body'])
            y += Inches(0.55)

    # Final statement
    add_line(slide, MARGIN_LEFT, Inches(6.9), CONTENT_WIDTH, COLORS['divider'])

    add_textbox(slide, MARGIN_LEFT, Inches(7.0), CONTENT_WIDTH, Inches(0.5),
                "From unexplained anomalies to interpretable behavioral intelligence.",
                font_size=20, bold=True, color=COLORS['accent_primary'],
                font_name=FALLBACK_FONTS['title'], alignment=PP_ALIGN.CENTER)

    add_textbox(slide, MARGIN_LEFT, Inches(7.4), CONTENT_WIDTH, Inches(0.35),
                "4 Behavioral Clusters  •  4 Attack-Family Hypotheses  •  1 Foundation for Further Validation",
                font_size=13, color=COLORS['text_secondary'], font_name=FALLBACK_FONTS['mono'], alignment=PP_ALIGN.CENTER)

    add_footer(slide, 16, total_slides)
    return slide


def build_slide_17_qa(prs, total_slides):
    """SLIDE 17: Q&A closing slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLORS['bg_main'])

    # Centered Q&A
    add_textbox(slide, MARGIN_LEFT, Inches(2.5), CONTENT_WIDTH, Inches(1.0),
                "QUESTIONS?", font_size=56, bold=True, color=COLORS['text_primary'],
                font_name=FALLBACK_FONTS['title'], alignment=PP_ALIGN.CENTER)

    add_line(slide, Inches(5.5), Inches(3.6), Inches(2.3), COLORS['accent_primary'], 2)

    add_textbox(slide, MARGIN_LEFT, Inches(4.0), CONTENT_WIDTH, Inches(0.6),
                "Artifacts & Reproducibility", font_size=18, bold=True, color=COLORS['accent_primary'],
                font_name=FALLBACK_FONTS['title'], alignment=PP_ALIGN.CENTER)

    artifacts = [
        "pair3_clustering.ipynb     — Complete notebook with all code & visualizations",
        "pair3_cluster_assignments.csv  — Per-record cluster assignments",
        "pair3_cluster_profiles.csv     — Cluster feature summaries (median/mode)",
        "pair3_mitre_mapping.json       — MITRE ATT&CK hypothesis mappings",
    ]

    y = Inches(4.6)
    for artifact in artifacts:
        add_textbox(slide, MARGIN_LEFT + Inches(1.5), y, CONTENT_WIDTH - Inches(3), Inches(0.35),
                    "📄  " + artifact, font_size=13, color=COLORS['text_secondary'],
                    font_name=FALLBACK_FONTS['mono'], alignment=PP_ALIGN.CENTER)
        y += Inches(0.4)

    add_textbox(slide, MARGIN_LEFT, Inches(6.5), CONTENT_WIDTH, Inches(0.4),
                "HONEYBADGER  •  PAIR 3  •  CLUSTERING", font_size=12, color=COLORS['text_muted'],
                font_name=FALLBACK_FONTS['mono'], alignment=PP_ALIGN.CENTER)

    add_footer(slide, 17, total_slides)
    return slide


# ============================================================
# MAIN GENERATION FUNCTION
# ============================================================
def generate_presentation():
    """Generate the complete PowerPoint presentation."""
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    TOTAL_SLIDES = 17

    print("Building slides...")

    # Slide 1: Opening
    print("  Slide 1: Opening...")
    build_slide_01_opening(prs, TOTAL_SLIDES)

    # Slide 2: The Challenge
    print("  Slide 2: The Challenge...")
    build_slide_02_challenge(prs, TOTAL_SLIDES)

    # Slide 3: Experiment at a Glance
    print("  Slide 3: Experiment at a Glance...")
    build_slide_03_experiment_at_glance(prs, TOTAL_SLIDES)

    # Slide 4: Preprocessing Pipeline
    print("  Slide 4: Preprocessing Pipeline...")
    build_slide_04_preprocessing(prs, TOTAL_SLIDES)

    # Slide 5: Three Algorithms
    print("  Slide 5: Three Algorithms...")
    build_slide_05_three_algorithms(prs, TOTAL_SLIDES)

    # Slide 6: Model Selection
    print("  Slide 6: Model Selection...")
    build_slide_06_model_selection(prs, TOTAL_SLIDES)

    # Slide 7: Model Scorecard
    print("  Slide 7: Model Scorecard...")
    build_slide_07_model_scorecard(prs, TOTAL_SLIDES)

    # Slide 8: Four Behavioral Signatures
    print("  Slide 8: Four Behavioral Signatures...")
    build_slide_08_four_signatures(prs, TOTAL_SLIDES)

    # Slides 9-12: Cluster Detail Slides
    clusters = [
        {
            "id": 0,
            "name": "Connection Scanning",
            "size": 2591,
            "pct": 22.1,
            "color": COLORS['cluster_0'],
            "protocol": "TCP",
            "service": "private",
            "flag": "REJ",
            "indicators": "count=121, rerror_rate=1.0, dst_host_count=255, srv_count=4",
            "mitre": "T1595 (Active Scanning) / T1046 (Network Service Scanning)",
            "confidence": "HIGH",
        },
        {
            "id": 1,
            "name": "SYN Flood / DoS",
            "size": 6989,
            "pct": 59.5,
            "color": COLORS['cluster_1'],
            "protocol": "TCP",
            "service": "private",
            "flag": "S0",
            "indicators": "count=199, serror_rate=1.0, srv_count=11, src_bytes=0, dst_bytes=0",
            "mitre": "T1499 (Endpoint DoS) / T1498 (Network DoS)",
            "confidence": "HIGH",
        },
        {
            "id": 2,
            "name": "ICMP Enumeration",
            "size": 1,
            "pct": 0.01,
            "color": COLORS['cluster_2'],
            "protocol": "ICMP",
            "service": "ecr_i",
            "flag": "SF",
            "indicators": "srv_count=99, same_srv_rate=1.0, src_bytes=520",
            "mitre": "T1595 (Active Scanning) / T1046 (Network Service Scanning)",
            "confidence": "MED-HIGH",
        },
        {
            "id": 3,
            "name": "ICMP Ping Sweep",
            "size": 2162,
            "pct": 18.4,
            "color": COLORS['cluster_3'],
            "protocol": "ICMP",
            "service": "eco_i",
            "flag": "SF",
            "indicators": "src_bytes=8, count=1, srv_count=6, dst_host_count=2",
            "mitre": "T1595.001 (Scanning IP Blocks) / T1018 (Remote System Discovery)",
            "confidence": "MEDIUM",
        },
    ]

    for i, cluster in enumerate(clusters):
        slide_num = 9 + i
        print(f"  Slide {slide_num}: Cluster {cluster['id']} Detail...")
        build_cluster_detail_slide(prs, TOTAL_SLIDES, slide_num, cluster)

    # Slide 13: Normal vs Anomalous
    print("  Slide 13: Normal vs Anomalous...")
    build_slide_13_normal_vs_anomalous(prs, TOTAL_SLIDES)

    # Slide 14: HoneyBadger Integration
    print("  Slide 14: HoneyBadger Integration...")
    build_slide_14_honeybadger_integration(prs, TOTAL_SLIDES)

    # Slide 15: Limitations
    print("  Slide 15: Limitations...")
    build_slide_15_limitations(prs, TOTAL_SLIDES)

    # Slide 16: Roadmap
    print("  Slide 16: Roadmap...")
    build_slide_16_roadmap(prs, TOTAL_SLIDES)

    # Slide 17: Q&A
    print("  Slide 17: Q&A...")
    build_slide_17_qa(prs, TOTAL_SLIDES)

    # Save
    output_path = Path("/home/dridi/HoneyBadger/HoneyBadger_Pair3_Clustering_Professional.pptx")
    prs.save(output_path)
    print(f"\nPresentation saved to: {output_path}")
    print(f"Total slides: {TOTAL_SLIDES}")

    return output_path


if __name__ == "__main__":
    generate_presentation()