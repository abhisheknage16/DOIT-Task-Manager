"""
Document Intelligence Backend
==============================
FastAPI service that integrates:
  - Docling  → parse PDFs, PPTX, DOCX, web URLs into structured text
  - Azure OpenAI GPT (gpt-5.2-chat) → extract KPIs, insights, recommendations
  - ReportLab → export branded PDF insight report

Uses your existing Azure OpenAI credentials from .env
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional, List

from openai import AzureOpenAI
from fastapi import HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ── ReportLab imports ──────────────────────────────────────────────────────
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Azure OpenAI Configuration ─────────────────────────────────────────────
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

# Initialize Azure OpenAI client
try:
    azure_client = AzureOpenAI(
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
    )
    print("✅ Document Intelligence: Azure OpenAI client ready")
except Exception as e:
    print(f"❌ Document Intelligence: Azure OpenAI init failed: {e}")
    azure_client = None


# ── Pydantic models ────────────────────────────────────────────────────────
class KPI(BaseModel):
    label: str
    value: str
    trend: str  # "up" | "down" | "neutral"
    score: int  # 0-100


class Insight(BaseModel):
    category: str  # "Strategic" | "Financial" | "Market" | "Operational" | "Performance" | "Risk"
    priority: str  # "HIGH" | "MEDIUM" | "LOW"
    title: str
    body: str


class Performer(BaseModel):
    rank: int
    name: str
    score: str
    highlights: str


class ScoreDistribution(BaseModel):
    excellent: int = 0
    proficient: int = 0
    developing: int = 0
    needs_improvement: int = 0


class InsightReport(BaseModel):
    doc_name: str
    question: str
    summary: str
    kpis: List[KPI]
    insights: List[Insight]
    recommendations: List[str]
    top_performers: List[Performer] = []
    bottom_performers: List[Performer] = []
    score_distribution: Optional[ScoreDistribution] = None
    generated_at: str


# ── Document parsing via Docling ──────────────────────────────────────────
def parse_document(source: str) -> str:
    """
    Parse a local file path or URL to text.
    - CSV / Excel → pandas summary + first 50 rows as markdown table
    - PDF / PPTX / DOCX / TXT → Docling (falls back to plain-text read)
    - URL → Docling
    """
    ext = Path(source).suffix.lower()

    # ── CSV / Excel: use pandas ───────────────────────────────────────────
    if ext in (".csv", ".xlsx", ".xls"):
        try:
            import pandas as pd
            import numpy as np

            df = pd.read_csv(source) if ext == ".csv" else pd.read_excel(source)
            rows, cols = df.shape
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            text_cols = df.select_dtypes(include="object").columns.tolist()

            lines = [
                f"# Full Spreadsheet Data for Deep Analysis",
                f"**File:** {Path(source).name}",
                f"**Total Records:** {rows}  |  **Columns:** {cols}",
                f"**Numeric columns:** {', '.join(numeric_cols) or 'none'}",
                f"**Text/categorical columns:** {', '.join(text_cols) or 'none'}",
                "",
            ]

            # ── Descriptive statistics ─────────────────────────────────────
            if numeric_cols:
                lines += ["## Descriptive Statistics (all numeric columns)"]
                stats = df[numeric_cols].describe().round(3)
                lines.append(stats.to_string())
                lines.append("")

                # Correlation matrix if 2+ numeric cols
                if len(numeric_cols) >= 2:
                    lines += ["## Correlation Matrix"]
                    lines.append(df[numeric_cols].corr().round(3).to_string())
                    lines.append("")

            # ── Categorical distributions ──────────────────────────────────
            if text_cols:
                lines += ["## Categorical Distributions"]
                for col in text_cols[:8]:
                    vc = df[col].value_counts()
                    pct = (vc / rows * 100).round(1)
                    lines.append(f"\n### {col}")
                    for val, cnt in vc.items():
                        lines.append(f"  {val}: {cnt} ({pct[val]}%)")
                lines.append("")

            # ── Per-person / per-row rankings (the key missing piece) ──────
            if numeric_cols:
                # Try to detect a "name" or "id" column for individual attribution
                name_col = None
                for candidate in [
                    "name",
                    "intern",
                    "participant",
                    "employee",
                    "student",
                    "person",
                    "id",
                    "Name",
                    "Intern",
                    "Participant",
                ]:
                    if candidate in df.columns:
                        name_col = candidate
                        break
                # Fallback: first text column
                if name_col is None and text_cols:
                    name_col = text_cols[0]

                # Detect the primary score/metric column
                score_col = None
                for candidate in [
                    "total",
                    "score",
                    "Total",
                    "Score",
                    "TOTAL",
                    "SCORE",
                    "marks",
                    "Marks",
                    "points",
                    "Points",
                    "result",
                    "Result",
                ]:
                    if candidate in numeric_cols:
                        score_col = candidate
                        break
                # Fallback: numeric col with highest variance
                if score_col is None and numeric_cols:
                    score_col = df[numeric_cols].var().idxmax()

                if score_col:
                    lines += [f"## Individual Rankings by '{score_col}'"]
                    ranked = (
                        df[
                            [name_col, score_col]
                            + [c for c in numeric_cols if c != score_col]
                        ].copy()
                        if name_col
                        else df[numeric_cols].copy()
                    )
                    ranked = ranked.sort_values(score_col, ascending=False).reset_index(
                        drop=True
                    )
                    ranked.index += 1  # 1-based rank
                    lines.append(ranked.to_string())
                    lines.append("")

                    # Top 5 performers
                    lines += [f"## TOP 5 PERFORMERS (by {score_col})"]
                    top5 = ranked.head(5)
                    for rank, row2 in top5.iterrows():
                        name_val = row2[name_col] if name_col else f"Row {rank}"
                        score_val = row2[score_col]
                        other = {
                            c: round(row2[c], 2)
                            for c in numeric_cols
                            if c != score_col and c in row2
                        }
                        lines.append(
                            f"  #{rank}: {name_val} — {score_col}={score_val}  |  {other}"
                        )
                    lines.append("")

                    # Bottom 5 performers
                    lines += [f"## BOTTOM 5 PERFORMERS (by {score_col})"]
                    bot5 = ranked.tail(5).sort_values(score_col)
                    for rank, row2 in bot5.iterrows():
                        name_val = row2[name_col] if name_col else f"Row {rank}"
                        score_val = row2[score_col]
                        other = {
                            c: round(row2[c], 2)
                            for c in numeric_cols
                            if c != score_col and c in row2
                        }
                        lines.append(
                            f"  #{rank}: {name_val} — {score_col}={score_val}  |  {other}"
                        )
                    lines.append("")

                    # Outlier detection using IQR
                    lines += [f"## OUTLIERS DETECTED (IQR method on {score_col})"]
                    q1, q3 = df[score_col].quantile(0.25), df[score_col].quantile(0.75)
                    iqr = q3 - q1
                    outliers = df[
                        (df[score_col] < q1 - 1.5 * iqr)
                        | (df[score_col] > q3 + 1.5 * iqr)
                    ]
                    if outliers.empty:
                        lines.append(
                            "  No outliers detected — scores are tightly clustered."
                        )
                    else:
                        lines.append(outliers.to_string())
                    lines.append("")

                    # Score distribution buckets
                    lines += ["## SCORE DISTRIBUTION BUCKETS"]
                    max_score = df[score_col].max()
                    if max_score > 0:
                        buckets = pd.cut(
                            df[score_col],
                            bins=[
                                0,
                                max_score * 0.5,
                                max_score * 0.7,
                                max_score * 0.85,
                                max_score,
                            ],
                            labels=[
                                "Needs Improvement (<50%)",
                                "Developing (50-70%)",
                                "Proficient (70-85%)",
                                "Excellent (85-100%)",
                            ],
                        )
                        dist = buckets.value_counts().sort_index()
                        for bucket, cnt in dist.items():
                            lines.append(f"  {bucket}: {cnt} ({cnt / rows * 100:.1f}%)")
                    lines.append("")

                    # Per-category averages (group by each text col)
                    for tcol in text_cols[:3]:
                        if tcol == name_col:
                            continue
                        lines += [f"## Average {score_col} by {tcol}"]
                        grp = (
                            df.groupby(tcol)[numeric_cols]
                            .mean()
                            .round(2)
                            .sort_values(score_col, ascending=False)
                        )
                        lines.append(grp.to_string())
                        lines.append("")

            # ── Full data dump (all rows) ──────────────────────────────────
            lines += [f"## COMPLETE DATA TABLE ({rows} rows)"]
            lines.append(df.to_string(index=True))

            return "\n".join(lines)

        except Exception as e:
            return f"[CSV/Excel parse error: {str(e)}]"

    # ── All other file types: Docling → plain-text fallback ───────────────
    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(str(source))
        return result.document.export_to_markdown()
    except ImportError:
        try:
            with open(source, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return f"[Could not parse document: {source}]"
    except Exception as e:
        return f"[Docling parse error: {str(e)}]"


# ── Azure OpenAI insight extraction ──────────────────────────────────────
SYSTEM_PROMPT = """You are an elite business intelligence analyst and data scientist.
Given structured data (CSV, Excel, or document text) and an optional business question,
return a JSON object with EXACTLY this structure (no extra keys, no markdown fences):

{
  "summary": "<3-4 sentence executive summary with specific numbers, top/bottom performer names if available, and key patterns>",
  "kpis": [
    {"label": "<metric name>", "value": "<formatted value with units>", "trend": "up|down|neutral", "score": <0-100>}
  ],
  "insights": [
    {
      "category": "Strategic|Financial|Market|Operational|Performance|Risk",
      "priority": "HIGH|MEDIUM|LOW",
      "title": "<concise, specific title>",
      "body": "<3-4 sentences. MUST include specific names, numbers, percentages from the data. Do not say 'data not available' — use what IS in the data.>"
    }
  ],
  "recommendations": ["<specific, time-bound, actionable recommendation with a measurable target>"],
  "top_performers": [
    {"rank": 1, "name": "<name/id>", "score": "<primary metric value>", "highlights": "<2-3 key strengths from their scores>"}
  ],
  "bottom_performers": [
    {"rank": 1, "name": "<name/id>", "score": "<primary metric value>", "highlights": "<2-3 specific areas needing improvement>"}
  ],
  "score_distribution": {
    "excellent": <count>,
    "proficient": <count>,
    "developing": <count>,
    "needs_improvement": <count>
  }
}

CRITICAL RULES — violating these makes the analysis useless:
1. TOP/BOTTOM PERFORMERS: If the data contains individual names/IDs and scores, you MUST populate top_performers and bottom_performers with real names and real scores from the data. List top 5 and bottom 5. Never say "not available" if names exist in the data.
2. KPIs: Extract 6-8 KPIs. Include average score, max/min scores, score spread (max-min), plus sub-metric averages. Use actual numbers.
3. INSIGHTS: Generate 6-8 insights. Each MUST reference specific names, scores, or percentages. Include: performance distribution insight, skill gap analysis, outlier analysis, group/category comparison if applicable.
4. RECOMMENDATIONS: Provide 5-6 recommendations. Each must be specific (e.g. "Coach [Name] on delivery — scored 2/4 on confidence") and time-bound.
5. SCORE DISTRIBUTION: Count how many fall into each band. Excellent = top 15%, Proficient = next 35%, Developing = next 35%, Needs Improvement = bottom 15%.
6. SPECIFICITY: Never use vague language. "Several participants scored low" → BAD. "4 participants (16%) scored below 14/25: [names]" → GOOD.
7. Return ONLY valid JSON. No markdown fences, no preamble, no explanation outside JSON.
"""


def extract_insights_azure(doc_text: str, question: str) -> dict:
    """Extract insights using Azure OpenAI."""
    if azure_client is None:
        raise HTTPException(
            status_code=503,
            detail="Azure OpenAI client not initialised. Check environment variables.",
        )

    user_prompt = f"""Business question: {question or "Provide a comprehensive, deep analysis. Identify every named top and bottom performer explicitly. Leave nothing vague."}

Document content:
{doc_text[:20000]}
"""
    try:
        response = azure_client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_completion_tokens=4000,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if the model adds them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Azure OpenAI error: {str(e)}")


# ── ReportLab PDF builder ─────────────────────────────────────────────────

C_BG = colors.HexColor("#0f1117")
C_SURFACE = colors.HexColor("#1a1d27")
C_ACCENT = colors.HexColor("#4f8ef7")
C_SUCCESS = colors.HexColor("#22c55e")
C_WARNING = colors.HexColor("#f59e0b")
C_DANGER = colors.HexColor("#ef4444")
C_TEXT = colors.HexColor("#e2e8f0")
C_MUTED = colors.HexColor("#64748b")
C_WHITE = colors.white


def build_styles() -> dict:
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=32,
            textColor=C_WHITE,
            alignment=TA_LEFT,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            textColor=C_MUTED,
            alignment=TA_LEFT,
        ),
        "section": ParagraphStyle(
            "Section",
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=C_ACCENT,
            spaceBefore=6,
            spaceAfter=4,
            letterSpacing=1,
        ),
        "body": ParagraphStyle(
            "Body", fontName="Helvetica", fontSize=10, leading=15, textColor=C_TEXT
        ),
        "kpi_value": ParagraphStyle(
            "KPIValue",
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=C_WHITE,
            alignment=TA_CENTER,
        ),
        "kpi_label": ParagraphStyle(
            "KPILabel",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=C_MUTED,
            alignment=TA_CENTER,
        ),
        "insight_title": ParagraphStyle(
            "InsightTitle",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=C_WHITE,
        ),
        "insight_body": ParagraphStyle(
            "InsightBody",
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=C_TEXT,
            spaceAfter=4,
        ),
        "tag": ParagraphStyle(
            "Tag", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=C_ACCENT
        ),
        "rec": ParagraphStyle(
            "Rec",
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=C_TEXT,
            leftIndent=12,
        ),
        "footer": ParagraphStyle(
            "Footer",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=C_MUTED,
            alignment=TA_CENTER,
        ),
    }


def draw_dark_background(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(C_BG)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, h - 3 * mm, w, 3 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(C_MUTED)
    canvas.setLineWidth(0.5)
    canvas.line(20 * mm, 15 * mm, w - 20 * mm, 15 * mm)
    canvas.setFillColor(C_MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(w / 2, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def generate_pdf_report(report: InsightReport) -> bytes:
    """Generate a dark-branded business insight PDF using ReportLab Platypus."""
    buffer = io.BytesIO()
    st = build_styles()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=22 * mm,
    )
    story = []
    W = A4[0] - 40 * mm

    # Cover
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("DOCUMENT INTELLIGENCE REPORT", st["subtitle"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(report.doc_name, st["title"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(f"Generated: {report.generated_at}", st["subtitle"]))
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width=W, thickness=1, color=C_ACCENT, spaceAfter=6 * mm))

    # Summary
    story.append(Paragraph("EXECUTIVE SUMMARY", st["section"]))
    story.append(Spacer(1, 2 * mm))
    summary_table = Table([[Paragraph(report.summary, st["body"])]], colWidths=[W])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), C_SURFACE),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 6 * mm))

    # KPIs
    story.append(Paragraph("KEY PERFORMANCE INDICATORS", st["section"]))
    story.append(Spacer(1, 2 * mm))
    kpi_cells, row = [], []
    col_w = W / 4 - 2 * mm
    for i, kpi in enumerate(report.kpis[:8]):
        trend_char = (
            "(+)" if kpi.trend == "up" else "(-)" if kpi.trend == "down" else "(=)"
        )
        trend_color = (
            "22c55e"
            if kpi.trend == "up"
            else "ef4444"
            if kpi.trend == "down"
            else "64748b"
        )
        cell = [
            Paragraph(kpi.value, st["kpi_value"]),
            Spacer(1, 1 * mm),
            Paragraph(kpi.label.upper(), st["kpi_label"]),
            Spacer(1, 1 * mm),
            Paragraph(
                f'<font color="#{trend_color}">{trend_char} {kpi.score}/100</font>',
                st["kpi_label"],
            ),
        ]
        row.append(cell)
        if len(row) == 4 or i == len(report.kpis) - 1:
            while len(row) < 4:
                row.append([Paragraph("", st["kpi_label"])])
            kpi_cells.append(row)
            row = []
    if kpi_cells:
        kpi_table = Table(kpi_cells, colWidths=[col_w] * 4)
        kpi_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), C_SURFACE),
                    ("GRID", (0, 0), (-1, -1), 0.5, C_BG),
                    ("TOPPADDING", (0, 0), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(kpi_table)
    story.append(Spacer(1, 6 * mm))

    # ── Score Distribution ─────────────────────────────────────────────────
    if report.score_distribution:
        story.append(Paragraph("SCORE DISTRIBUTION", st["section"]))
        story.append(Spacer(1, 2 * mm))
        sd = report.score_distribution
        dist_data = [
            [
                Paragraph(
                    "EXCELLENT",
                    ParagraphStyle(
                        "dh",
                        fontName="Helvetica-Bold",
                        fontSize=8,
                        textColor=C_SUCCESS,
                        alignment=TA_CENTER,
                    ),
                ),
                Paragraph(
                    "PROFICIENT",
                    ParagraphStyle(
                        "dh",
                        fontName="Helvetica-Bold",
                        fontSize=8,
                        textColor=C_ACCENT,
                        alignment=TA_CENTER,
                    ),
                ),
                Paragraph(
                    "DEVELOPING",
                    ParagraphStyle(
                        "dh",
                        fontName="Helvetica-Bold",
                        fontSize=8,
                        textColor=C_WARNING,
                        alignment=TA_CENTER,
                    ),
                ),
                Paragraph(
                    "NEEDS IMPROVEMENT",
                    ParagraphStyle(
                        "dh",
                        fontName="Helvetica-Bold",
                        fontSize=8,
                        textColor=C_DANGER,
                        alignment=TA_CENTER,
                    ),
                ),
            ],
            [
                Paragraph(
                    str(sd.excellent),
                    ParagraphStyle(
                        "dv",
                        fontName="Helvetica-Bold",
                        fontSize=22,
                        textColor=C_WHITE,
                        alignment=TA_CENTER,
                    ),
                ),
                Paragraph(
                    str(sd.proficient),
                    ParagraphStyle(
                        "dv",
                        fontName="Helvetica-Bold",
                        fontSize=22,
                        textColor=C_WHITE,
                        alignment=TA_CENTER,
                    ),
                ),
                Paragraph(
                    str(sd.developing),
                    ParagraphStyle(
                        "dv",
                        fontName="Helvetica-Bold",
                        fontSize=22,
                        textColor=C_WHITE,
                        alignment=TA_CENTER,
                    ),
                ),
                Paragraph(
                    str(sd.needs_improvement),
                    ParagraphStyle(
                        "dv",
                        fontName="Helvetica-Bold",
                        fontSize=22,
                        textColor=C_WHITE,
                        alignment=TA_CENTER,
                    ),
                ),
            ],
        ]
        dist_table = Table(dist_data, colWidths=[W / 4] * 4)
        dist_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), C_SURFACE),
                    ("GRID", (0, 0), (-1, -1), 0.5, C_BG),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(dist_table)
        story.append(Spacer(1, 6 * mm))

    # ── Top Performers ─────────────────────────────────────────────────────
    if report.top_performers:
        story.append(Paragraph("TOP PERFORMERS", st["section"]))
        story.append(Spacer(1, 2 * mm))
        perf_header = [
            Paragraph(
                "RANK",
                ParagraphStyle(
                    "ph",
                    fontName="Helvetica-Bold",
                    fontSize=8,
                    textColor=C_MUTED,
                    alignment=TA_CENTER,
                ),
            ),
            Paragraph(
                "NAME",
                ParagraphStyle(
                    "ph", fontName="Helvetica-Bold", fontSize=8, textColor=C_MUTED
                ),
            ),
            Paragraph(
                "SCORE",
                ParagraphStyle(
                    "ph",
                    fontName="Helvetica-Bold",
                    fontSize=8,
                    textColor=C_MUTED,
                    alignment=TA_CENTER,
                ),
            ),
            Paragraph(
                "HIGHLIGHTS",
                ParagraphStyle(
                    "ph", fontName="Helvetica-Bold", fontSize=8, textColor=C_MUTED
                ),
            ),
        ]
        perf_rows = [perf_header]
        medal = {1: "#FFD700", 2: "#C0C0C0", 3: "#CD7F32"}
        for p in report.top_performers:
            color_hex = medal.get(p.rank, "#4f8ef7")
            rank_style = ParagraphStyle(
                "rk",
                fontName="Helvetica-Bold",
                fontSize=11,
                textColor=colors.HexColor(color_hex),
                alignment=TA_CENTER,
            )
            perf_rows.append(
                [
                    Paragraph(f"#{p.rank}", rank_style),
                    Paragraph(str(p.name), st["body"]),
                    Paragraph(
                        str(p.score),
                        ParagraphStyle(
                            "sc",
                            fontName="Helvetica-Bold",
                            fontSize=11,
                            textColor=C_SUCCESS,
                            alignment=TA_CENTER,
                        ),
                    ),
                    Paragraph(str(p.highlights), st["insight_body"]),
                ]
            )
        top_table = Table(perf_rows, colWidths=[14 * mm, 50 * mm, 22 * mm, W - 86 * mm])
        top_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d1117")),
                    ("BACKGROUND", (0, 1), (-1, -1), C_SURFACE),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.5, C_BG),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(top_table)
        story.append(Spacer(1, 6 * mm))

    # ── Bottom Performers ──────────────────────────────────────────────────
    if report.bottom_performers:
        story.append(Paragraph("NEEDS ATTENTION", st["section"]))
        story.append(Spacer(1, 2 * mm))
        bot_header = [
            Paragraph(
                "RANK",
                ParagraphStyle(
                    "ph",
                    fontName="Helvetica-Bold",
                    fontSize=8,
                    textColor=C_MUTED,
                    alignment=TA_CENTER,
                ),
            ),
            Paragraph(
                "NAME",
                ParagraphStyle(
                    "ph", fontName="Helvetica-Bold", fontSize=8, textColor=C_MUTED
                ),
            ),
            Paragraph(
                "SCORE",
                ParagraphStyle(
                    "ph",
                    fontName="Helvetica-Bold",
                    fontSize=8,
                    textColor=C_MUTED,
                    alignment=TA_CENTER,
                ),
            ),
            Paragraph(
                "DEVELOPMENT AREAS",
                ParagraphStyle(
                    "ph", fontName="Helvetica-Bold", fontSize=8, textColor=C_MUTED
                ),
            ),
        ]
        bot_rows = [bot_header]
        for p in report.bottom_performers:
            bot_rows.append(
                [
                    Paragraph(
                        f"#{p.rank}",
                        ParagraphStyle(
                            "rk",
                            fontName="Helvetica-Bold",
                            fontSize=11,
                            textColor=C_DANGER,
                            alignment=TA_CENTER,
                        ),
                    ),
                    Paragraph(str(p.name), st["body"]),
                    Paragraph(
                        str(p.score),
                        ParagraphStyle(
                            "sc",
                            fontName="Helvetica-Bold",
                            fontSize=11,
                            textColor=C_DANGER,
                            alignment=TA_CENTER,
                        ),
                    ),
                    Paragraph(str(p.highlights), st["insight_body"]),
                ]
            )
        bot_table = Table(bot_rows, colWidths=[14 * mm, 50 * mm, 22 * mm, W - 86 * mm])
        bot_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d1117")),
                    ("BACKGROUND", (0, 1), (-1, -1), C_SURFACE),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.5, C_BG),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(bot_table)
        story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("BUSINESS INSIGHTS", st["section"]))
    story.append(Spacer(1, 2 * mm))
    for ins in report.insights:
        priority_color = (
            "#ef4444"
            if ins.priority == "HIGH"
            else "#f59e0b"
            if ins.priority == "MEDIUM"
            else "#64748b"
        )
        header_text = f'<font color="{priority_color}">* {ins.priority}</font>  <font color="#4f8ef7">{ins.category.upper()}</font>'
        cell_content = [
            Paragraph(header_text, st["tag"]),
            Spacer(1, 2 * mm),
            Paragraph(ins.title, st["insight_title"]),
            Spacer(1, 2 * mm),
            Paragraph(ins.body, st["insight_body"]),
        ]
        t = Table([[cell_content]], colWidths=[W])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), C_SURFACE),
                    ("LEFTPADDING", (0, 0), (-1, -1), 14),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                    ("TOPPADDING", (0, 0), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 3 * mm))
    story.append(Spacer(1, 4 * mm))

    # Recommendations
    story.append(Paragraph("STRATEGIC RECOMMENDATIONS", st["section"]))
    story.append(Spacer(1, 2 * mm))
    rec_rows = []
    for i, rec in enumerate(report.recommendations, 1):
        num_cell = Paragraph(
            f'<font color="#4f8ef7"><b>{i}</b></font>',
            ParagraphStyle(
                "Num",
                fontName="Helvetica-Bold",
                fontSize=12,
                leading=14,
                textColor=C_ACCENT,
                alignment=TA_CENTER,
            ),
        )
        rec_rows.append([num_cell, Paragraph(rec, st["rec"])])
    if rec_rows:
        rec_table = Table(rec_rows, colWidths=[12 * mm, W - 12 * mm])
        rec_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), C_SURFACE),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.5, C_BG),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (0, -1), 10),
                    ("LEFTPADDING", (1, 0), (1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(rec_table)

    # Footer
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width=W, thickness=0.5, color=C_MUTED))
    story.append(Spacer(1, 2 * mm))
    story.append(
        Paragraph(
            "Powered by Docling · Azure OpenAI (GPT) · ReportLab  |  Document Intelligence Platform",
            st["footer"],
        )
    )

    doc.build(
        story, onFirstPage=draw_dark_background, onLaterPages=draw_dark_background
    )
    buffer.seek(0)
    return buffer.getvalue()


# ── Controller functions (called by the router) ───────────────────────────


def _build_report(filename: str, question: str, raw: dict) -> InsightReport:
    """Build InsightReport from raw AI JSON, safely handling optional new fields."""
    performers_top = [Performer(**p) for p in raw.get("top_performers", [])]
    performers_bot = [Performer(**p) for p in raw.get("bottom_performers", [])]
    dist_raw = raw.get("score_distribution")
    dist = ScoreDistribution(**dist_raw) if dist_raw else None

    return InsightReport(
        doc_name=filename,
        question=question or "Comprehensive business analysis",
        summary=raw.get("summary", ""),
        kpis=[KPI(**k) for k in raw.get("kpis", [])],
        insights=[Insight(**i) for i in raw.get("insights", [])],
        recommendations=raw.get("recommendations", []),
        top_performers=performers_top,
        bottom_performers=performers_bot,
        score_distribution=dist,
        generated_at=datetime.now().strftime("%B %d, %Y %H:%M"),
    )


def analyze_document_from_file(
    file_bytes: bytes, filename: str, question: str = ""
) -> InsightReport:
    """Parse uploaded file + run Azure OpenAI analysis."""
    suffix = Path(filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        doc_text = parse_document(tmp_path)
    finally:
        os.unlink(tmp_path)

    raw = extract_insights_azure(doc_text, question)
    return _build_report(filename, question, raw)


def analyze_document_from_url(url: str, question: str = "") -> InsightReport:
    """Parse URL with Docling + run Azure OpenAI analysis."""
    doc_text = parse_document(url)
    raw = extract_insights_azure(doc_text, question)
    return _build_report(url, question, raw)
