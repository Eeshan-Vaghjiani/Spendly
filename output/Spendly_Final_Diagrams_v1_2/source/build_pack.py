"""Build implementation-aligned Spendly diagrams as editable SVG and vector PDF.

Run export_schema.py with the repository's Python first. This builder only needs
reportlab, Pillow and pypdf; pdftoppm renders the final PDF to high-resolution PNG.
It never changes the application, database, model artifacts or APK.
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from html import escape
from pathlib import Path

from PIL import Image, ImageOps, ImageDraw
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

PACK = Path(__file__).resolve().parent.parent
SVG_DIR = PACK / "svg"
PNG_DIR = PACK / "png"
PDF = PACK / "Spendly_Final_Diagrams.pdf"
INK = "#20262B"
MUTED = "#58646B"
LINE = "#8B969C"
FAINT = "#D8DFE2"
PALE = "#F5F7F8"
TEAL = "#176657"
TINT = "#EEF6F3"
WHITE = "#FFFFFF"

for folder in (SVG_DIR, PNG_DIR):
    folder.mkdir(parents=True, exist_ok=True)
pdfmetrics.registerFont(TTFont("Spendly", "C:/Windows/Fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("SpendlyBold", "C:/Windows/Fonts/arialbd.ttf"))


def width(text, size, bold=False):
    return pdfmetrics.stringWidth(str(text), "SpendlyBold" if bold else "Spendly", size)


def wrap(text, size, max_width, bold=False):
    result = []
    for paragraph in str(text).split("\n"):
        line = ""
        for word in paragraph.split():
            candidate = (line + " " + word).strip()
            if width(candidate, size, bold) > max_width and line:
                result.append(line)
                line = word
            else:
                line = candidate
        result.append(line)
    return result


class Figure:
    def __init__(self, pdf, name, w, h, page_width=1190):
        self.pdf = pdf
        self.name, self.w, self.h = name, w, h
        self.scale = page_width / w
        self.pdf.setPageSize((page_width, h * self.scale))
        self.pdf.saveState()
        self.pdf.scale(self.scale, self.scale)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
                    f'<title>{escape(name.replace("_", " "))}</title>',
                    '<desc>Spendly v1.2.0 implementation-aligned technical figure. All wireframe values are illustrative.</desc>']
        self.text_count = 0
        self.rect(0, 0, w, h, WHITE, None)

    def color(self, color):
        from reportlab.lib.colors import HexColor
        return HexColor(color)

    def rect(self, x, y, w, h, fill=WHITE, stroke=LINE, radius=0, sw=1.4, dash=False):
        self.pdf.saveState()
        self.pdf.setLineWidth(sw)
        self.pdf.setDash([7, 5] if dash else [])
        if fill:
            self.pdf.setFillColor(self.color(fill))
        if stroke:
            self.pdf.setStrokeColor(self.color(stroke))
        fn = self.pdf.roundRect if radius else self.pdf.rect
        args = (x, self.h - y - h, w, h, radius) if radius else (x, self.h - y - h, w, h)
        fn(*args, fill=int(bool(fill)), stroke=int(bool(stroke)))
        self.pdf.restoreState()
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill or "none"}" stroke="{stroke or "none"}" stroke-width="{sw}"' + (' stroke-dasharray="7 5"' if dash else '') + '/>')

    def line(self, x1, y1, x2, y2, color=LINE, sw=1.5, dash=False):
        self.poly([(x1, y1), (x2, y2)], color, sw, dash)

    def poly(self, points, color=LINE, sw=1.5, dash=False, fill=None, close=False):
        self.pdf.saveState()
        self.pdf.setStrokeColor(self.color(color))
        self.pdf.setLineWidth(sw)
        self.pdf.setDash([7, 6] if dash else [])
        p = self.pdf.beginPath()
        p.moveTo(points[0][0], self.h - points[0][1])
        for x, y in points[1:]:
            p.lineTo(x, self.h - y)
        if close:
            p.close()
        if fill:
            self.pdf.setFillColor(self.color(fill))
        self.pdf.drawPath(p, stroke=1, fill=int(bool(fill)))
        self.pdf.restoreState()
        tag = "polygon" if close else "polyline"
        self.svg.append(f'<{tag} points="' + " ".join(f"{x},{y}" for x, y in points) + f'" fill="{fill or "none"}" stroke="{color}" stroke-width="{sw}"' + (' stroke-dasharray="7 6"' if dash else '') + '/>')

    def circle(self, x, y, r, fill=WHITE, stroke=LINE, sw=1.5):
        self.pdf.saveState()
        self.pdf.setLineWidth(sw)
        if fill:
            self.pdf.setFillColor(self.color(fill))
        if stroke:
            self.pdf.setStrokeColor(self.color(stroke))
        self.pdf.circle(x, self.h-y, r, fill=int(bool(fill)), stroke=int(bool(stroke)))
        self.pdf.restoreState()
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill or "none"}" stroke="{stroke or "none"}" stroke-width="{sw}"/>')

    def text(self, x, y, text, size=20, bold=False, color=INK, anchor="start", max_width=None):
        text = str(text)
        tw = width(text, size, bold)
        if max_width is not None and tw > max_width + 0.2:
            raise ValueError(f"Text too wide in {self.name}: {text!r} ({tw:.1f}>{max_width})")
        left = x - (tw/2 if anchor == "middle" else tw if anchor == "end" else 0)
        if left < -0.2 or left + tw > self.w + 0.2 or y < 0 or y + size > self.h:
            raise ValueError(f"Text outside canvas in {self.name}: {text}")
        baseline = y + size * 0.82
        self.pdf.setFont("SpendlyBold" if bold else "Spendly", size)
        self.pdf.setFillColor(self.color(color))
        self.pdf.drawString(left, self.h-baseline, text)
        self.svg.append(f'<text x="{x}" y="{baseline}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}" text-anchor="{anchor}">{escape(text)}</text>')
        self.text_count += 1

    def para(self, x, y, text, max_width, size=20, leading=None, color=INK, bold=False):
        leading = leading or size * 1.38
        lines = wrap(text, size, max_width, bold)
        for i, ln in enumerate(lines):
            self.text(x, y+i*leading, ln, size, bold, color, max_width=max_width)
        return y + len(lines)*leading

    def label(self, x, y, text, size=18, color=MUTED):
        tw = width(text, size)
        self.rect(x-7, y-3, tw+14, size+8, WHITE, None)
        self.text(x, y, text, size, color=color)

    def arrow(self, points, label=None, label_at=None, color=LINE, dash=False, both=False, sw=1.7):
        self.poly(points, color, sw, dash)
        def head(a, b):
            angle = math.atan2(b[1]-a[1], b[0]-a[0])
            p1 = (b[0]-10*math.cos(angle)+4*math.sin(angle), b[1]-10*math.sin(angle)-4*math.cos(angle))
            p2 = (b[0]-10*math.cos(angle)-4*math.sin(angle), b[1]-10*math.sin(angle)+4*math.cos(angle))
            self.poly([b, p1, p2], color, 1, fill=color, close=True)
        head(points[-2], points[-1])
        if both:
            head(points[1], points[0])
        if label:
            self.label(*label_at, label)

    def title(self, number, title, subtitle):
        self.text(54, 30, "SPENDLY", 19, True, TEAL)
        self.text(self.w-54, 30, f"FIGURE {number:02d} / 07", 16, color=MUTED, anchor="end")
        self.text(54, 68, title, 34, True)
        self.text(54, 115, subtitle, 18, color=MUTED, max_width=self.w-108)
        self.line(54, 151, self.w-54, 151, FAINT)

    def footer(self, source, number):
        self.line(54, self.h-62, self.w-54, self.h-62, FAINT)
        self.text(54, self.h-43, source, 14, color=MUTED, max_width=self.w-460)
        self.text(self.w-54, self.h-43, f"v1.2.0 | 31 Aug 2026 | {number:02d}", 14, color=MUTED, anchor="end")

    def end(self):
        self.svg.append("</svg>")
        (SVG_DIR / f"{self.name}.svg").write_text("\n".join(self.svg), encoding="utf-8")
        self.pdf.restoreState()
        self.pdf.showPage()
        return {"name": self.name, "width": self.w, "height": self.h, "text_elements": self.text_count}


def erd_mark(f, end, other, mode, color):
    dx, dy = other[0]-end[0], other[1]-end[1]
    length = math.hypot(dx, dy)
    dx, dy = dx/length, dy/length
    nx, ny = -dy, dx
    def bar(d):
        x, y = end[0]+dx*d, end[1]+dy*d
        f.line(x+nx*10, y+ny*10, x-nx*10, y-ny*10, color, 2)
    if mode == "one":
        bar(14); bar(23)
    elif mode == "optional_one":
        bar(13)
        f.circle(end[0]+dx*34, end[1]+dy*34, 7, WHITE, color, 2)
    else:
        root = (end[0]+dx*24, end[1]+dy*24)
        for delta in (-11, 0, 11):
            f.line(root[0], root[1], end[0]+nx*delta, end[1]+ny*delta, color, 2)
        f.circle(end[0]+dx*39, end[1]+dy*39, 7, WHITE, color, 2)


def relationship(f, points, start="one", end="many", color=LINE):
    f.poly(points, color, 2)
    erd_mark(f, points[0], points[1], start, color)
    erd_mark(f, points[-1], points[-2], end, color)


def table(f, table_data, x, y, w, foot=None, size=22, row=30):
    cols = table_data["columns"]
    foot_lines = []
    for note in foot or []:
        foot_lines += wrap(note, 18, w-28)
    h = 86 + len(cols)*row + (len(foot_lines)*24+18 if foot_lines else 10)
    f.rect(x, y, w, h, WHITE, INK, radius=7, sw=2)
    f.rect(x+1, y+1, w-2, 49, TINT, None, radius=6)
    f.text(x+w/2, y+13, table_data["name"].upper(), 25, True, anchor="middle")
    f.line(x, y+50, x+w, y+50, INK, 1.5)
    f.text(x+14, y+61, "KEY", 15, True, MUTED)
    f.text(x+86, y+61, "COLUMN", 15, True, MUTED)
    f.text(x+w-176, y+61, "TYPE", 15, True, MUTED)
    for i, col in enumerate(cols):
        yy = y+86+i*row
        if i%2:
            f.rect(x+2, yy-2, w-4, row, PALE, None)
        key = "PK" if col["pk"] else "FK" if col["foreign_keys"] else "UQ" if col["unique"] else ""
        field = col["name"] + (" ?" if col["nullable"] else "")
        ty = col["type"].lower().replace("timestamp without time zone", "timestamp").replace("integer", "int").replace(" ", "")
        f.text(x+14, yy+2, key, 18, bool(key), TEAL if key else INK)
        f.text(x+86, yy+2, field, size, bool(col["pk"]), max_width=w-272)
        f.text(x+w-176, yy+2, ty, 20, max_width=165)
    foot_y = y+86+len(cols)*row
    if foot_lines:
        f.line(x+12, foot_y+4, x+w-12, foot_y+4, FAINT)
        for i, txt in enumerate(foot_lines):
            f.text(x+14, foot_y+14+i*24, txt, 18, color=MUTED)
    return h


def schema_figure(pdf, schema):
    f = Figure(pdf, "01_Database_Schema", 2460, 2510)
    f.title(1, "Database schema", "Physical application schema | PostgreSQL | 11 tables, 97 columns and 10 foreign-key relationships")
    # Draw connectors first; table faces remain clean. Shared ownership spine.
    f.poly([(740, 330), (820, 330), (820, 1940)], LINE, 2)
    erd_mark(f, (740,330), (820,330), "one", LINE)
    for points in [[(820,330),(900,330)], [(820,930),(900,930)], [(820,1090),(740,1090)], [(820,1650),(740,1650)]]:
        f.poly(points, LINE, 2)
        erd_mark(f, points[-1], points[-2], "many", LINE)
    # Remote ownership branches are explicitly labelled to disambiguate crossings.
    f.poly([(820,330),(820,175),(1660,175),(1660,320),(1720,320)], LINE, 2)
    erd_mark(f,(1720,320),(1660,320),"many",LINE)
    f.poly([(820,1940),(2440,1940),(2440,1090),(2400,1090)],LINE,2)
    erd_mark(f,(2400,1090),(2440,1090),"many",LINE)
    f.label(1070,164,"users.id -> result user_id",18)
    f.label(1100,1927,"users.id -> recommendations.user_id",18)
    relationship(f, [(1550,425),(1605,425),(1720,425)], end="optional_one", color=TEAL)
    f.label(1575,378,"run",18,TEAL)
    relationship(f, [(1225,538),(1225,820)], color=TEAL)
    f.label(1245,650,"analysis_run_id",19,TEAL)
    relationship(f, [(1550,470),(1590,470),(1590,1445),(2060,1445),(2060,1386)], color=TEAL)
    f.label(1750,1423,"analysis_run_id",19,TEAL)
    relationship(f, [(390,1468),(390,1506),(862,1506),(862,1160),(900,1160)], start="optional_one", color=INK)
    f.label(475,1481,"transaction_id (SET NULL)",18,INK)
    t = {t["name"]: t for t in schema["tables"]}
    table(f,t["users"],60,200,680, ["UQ: email; google_subject; username_normalized"],size=21)
    table(f,t["analysis_runs"],900,200,650,["Version values are text, not model_versions FKs."],size=21)
    table(f,t["forecasts"],1720,200,680,["UQ: analysis_run_id"],size=22)
    table(f,t["transactions"],60,980,680,["UQ: (user_id, fingerprint)"],size=22)
    table(f,t["anomaly_alerts"],900,820,650, size=21)
    table(f,t["recommendations"],1720,930,680,size=22)
    table(f,t["budgets"],60,1540,680,["UQ: (user_id, period_start, period_end, category)"],size=22)

    f.rect(930,1510,1450,350,PALE,FAINT,8)
    f.text(956,1535,"RELATIONSHIPS AND STORAGE RULES",25,True)
    relationship(f,[(965,1600),(1135,1600)])
    f.text(1165,1586,"One user owns zero or many records in each of six child tables.",23)
    relationship(f,[(965,1655),(1135,1655)],end="optional_one",color=TEAL)
    f.text(1165,1641,"One analysis run has zero or one forecast (unique foreign key).",23)
    f.text(956,1702,"PK = primary key    FK = foreign key    UQ = unique    ? = nullable",22)
    f.text(956,1743,"Run -> alerts / recommendations: 1 to 0..*. Transaction -> alerts: 0..1 to 0..*.",22)
    f.para(956,1784,"Foreign keys use ON DELETE CASCADE except anomaly_alerts.transaction_id (SET NULL). Result version strings are not foreign keys. Crossed lines are not junctions.",1372,21)
    f.text(60,1982,"INDEPENDENT OPERATIONAL TABLES",27,True)
    table(f,t["admin_audit"],60,2030,570,["target_id is intentionally not an FK."],size=20,row=29)
    table(f,t["model_versions"],650,2030,570,["UQ: (component, version)"],size=20,row=29)
    table(f,t["admin_login_attempts"],1240,2030,570,["client_key: hashed client identifier"],size=20,row=29)
    table(f,t["system_settings"],1830,2030,570,["Current key: analysis_enabled"],size=20,row=29)
    f.para(1260,2275,"Admin identity is configured outside the users table. No admin role, feedback, category or inferred-schedule table is invented here. Full SQL types, unique constraints and indexes are in the accompanying data dictionary.",1090,22)
    f.footer("Source: backend/app/models/entities.py | UUIDs stored as varchar(36); timestamps use UTC; money uses numeric(14,2).",1)
    return f.end()


def node(f,x,y,w,h,title,body,tag=None):
    f.rect(x,y,w,h,WHITE,LINE,8,1.5)
    if tag:
        f.text(x+20,y+17,tag,14,True,TEAL)
    title_y=y+(42 if tag else 21)
    end=f.para(x+20,title_y,title,w-40,24,29,bold=True)
    f.line(x+20,end+12,x+w-20,end+12,FAINT)
    bottom=f.para(x+20,end+29,body,w-40,19,27)
    if bottom>y+h-8:
        raise ValueError(f"Node overflow: {title} {bottom-y}>{h}")


def architecture_figure(pdf):
    f=Figure(pdf,"02_System_Architecture",1900,1390)
    f.title(2,"System architecture","Deployed mobile-first setup | Android client, browser admin, Flask backend and PostgreSQL storage")
    f.poly([(760,190),(1435,190),(1435,930),(1865,930),(1865,1190),(760,1190)],LINE,1.5,True,PALE,True)
    f.text(785,209,"RENDER HOSTED BACKEND",20,True,TEAL)
    f.text(785,239,"One Python / Flask process; not separate ML microservices",17,color=MUTED)
    node(f,55,210,255,225,"General user","Record income and expenses\nSet budgets\nReview spending insights", "ACTOR")
    node(f,385,205,290,315,"Flutter mobile app","Android APK\nDart + Riverpod\nDashboard / transactions\nBudgets / analytics / more\nSecure token storage", "CLIENT")
    node(f,55,670,255,250,"Administrator","Manage accounts and data\nControl new analysis\nReview audit and health", "PRIVILEGED ACTOR")
    node(f,385,655,290,315,"Admin console","Browser-based interface\nServer-rendered HTML\nProtected session + CSRF\nPassword reconfirmation\nReason for every change", "CLIENT")
    node(f,785,295,625,300,"Flask REST API + admin routes","/api/v1: authentication, profile, transactions, budgets and insights\nJWT, active-account and consent checks; user-owned data access\nAdmin session authentication; validation; audit logging\nSQLAlchemy repositories + Alembic migrations", "APPLICATION LAYER")
    node(f,785,650,625,240,"Analysis service","Chronological transaction history + budget context\nWeekly feature preparation and expense anomaly features\nModelRegistry inference -> rule-based recommendations\nPersist run, forecast, unusual-spending alerts and guidance", "IN-PROCESS ORCHESTRATION")
    f.rect(785,930,300,190,WHITE,LINE,8)
    f.text(805,950,"Forecasting v1",23,True)
    f.para(805,989,"8+ weeks: multiple linear regression\nUnder 8 weeks: personal weekly-average baseline",258,19,27)
    f.rect(1110,930,300,190,WHITE,LINE,8)
    f.text(1130,950,"Anomaly detection v1",22,True)
    f.para(1130,989,"Isolation Forest + stored threshold\nExplain unusual expense patterns",255,19,27)
    node(f,1520,210,325,245,"Google Identity","Optional sign-in\nMobile obtains an ID token\nBackend verifies its audience and identity claims", "EXTERNAL AUTHENTICATION")
    node(f,1520,580,325,300,"Neon PostgreSQL","Users, transactions, budgets\nAnalysis runs + result records\nModel-version metadata\nAdmin audit + login attempts\nSystem settings", "PERSISTENT DATA")
    node(f,1520,960,325,220,"Versioned artifacts","Joblib models and transforms\nJSON feature schemas\nLoaded from container files\nNo training during requests", "BACKEND FILESYSTEM")

    f.arrow([(310,315),(385,315)],both=True)
    f.arrow([(310,780),(385,780)],both=True)
    f.arrow([(675,400),(785,400)],both=True)
    f.label(680,355,"HTTPS",17)
    f.label(680,425,"JSON / JWT",16)
    f.arrow([(675,720),(725,720),(725,550),(785,550)],both=True)
    f.label(682,605,"HTTPS",17)
    f.arrow([(1100,595),(1100,650)],color=TEAL,both=True)
    f.arrow([(935,890),(935,930)],both=True,color=TEAL)
    f.arrow([(1260,890),(1260,930)],both=True,color=TEAL)
    f.arrow([(1410,400),(1465,400),(1465,340),(1520,340)],both=True)
    f.label(1435,363,"Verify",16)
    f.arrow([(1410,550),(1470,550),(1470,700),(1520,700)],both=True)
    f.label(1460,655,"SQL",17)
    f.arrow([(1520,1090),(1452,1090),(1452,842),(1410,842)],dash=True)
    f.label(1441,935,"Load",17)
    f.arrow([(530,205),(530,174),(1682,174),(1682,210)],both=True)
    f.label(1045,163,"Optional Google sign-in / ID token",16)
    f.rect(55,1198,1790,110,TINT,None,8)
    f.text(78,1215,"LIVE / RESEARCH BOUNDARY",18,True,TEAL)
    f.para(78,1248,"Live: MODEL_RUNTIME=lightweight, forecast v1 and anomaly v1. LSTM is available only in the optional full runtime, not this deployment. Frozen V2 research candidates remain outside the live request path; integration requires a reviewed model package and adapter.",1740,19,26)
    f.footer("Sources: render.yaml; backend/app/services; backend/app/routes; mobile/lib | Deployment baseline: commit b0a0f85.",2)
    return f.end()


def sequence_figure(pdf):
    f=Figure(pdf,"03_Sequence_Generate_Insights",1900,1690)
    f.title(3,"Sequence diagram - generate spending insights","Successful user flow with forecast-readiness branches | Internal calls are within the same Flask backend")
    names=[("General user",140),("Flutter app",430),("Flask API",760),("Analysis service",1080),("Models + rules",1400),("PostgreSQL",1750)]
    for name,x in names:
        f.rect(x-113,195,226,64,WHITE,INK,5)
        f.text(x,215,name,22,True,anchor="middle")
        f.line(x,259,x,1580,LINE,1.4,True)
    for x,y,h in [(430,320,1230),(760,355,1130),(1080,545,880),(1400,815,85),(1400,1065,75),(1400,1180,70),(1750,440,75),(1750,600,65),(1750,1298,72)]:
        f.rect(x-7,y,14,h,WHITE,LINE,2)

    def msg(a,b,y,txt,dash=False,size=19):
        f.arrow([(a,y),(b,y)],dash=dash,color=INK if not dash else MUTED)
        tw=width(txt,size)
        xx=(a+b)/2-tw/2
        if tw>abs(a-b)-16:
            # Two-line labels stay inside the span where possible.
            lines=wrap(txt,size,abs(a-b)-24)
            for i,ln in enumerate(lines):
                f.label((a+b)/2-width(ln,size)/2,y-(len(lines)-i)*24-8,ln,size)
        else:
            f.label(xx,y-31,txt,size)

    msg(140,430,320,"1. Tap Refresh insights")
    msg(430,760,385,"2. POST /api/v1/analysis/run + JWT")
    msg(760,1750,452,"3. Check active user, consent, token version and analysis_enabled")
    msg(1750,760,515,"4. Authentication and system-control state",True)
    f.rect(55,535,605,127,PALE,FAINT,7)
    f.text(75,553,"Guard before inference",20,True)
    f.para(75,585,"Invalid token, inactive account, missing consent or paused analysis returns an error. The flow below continues only when these checks pass.",565,18,25)
    msg(760,1080,570,"5. run(user)")
    msg(1080,1750,613,"6. Load this user's transactions and budgets")
    msg(1750,1080,665,"7. Chronological history + budget context",True)
    f.rect(925,688,335,48,TINT,FAINT,5)
    f.text(1092,702,"8. Prepare weekly features",18,True,anchor="middle")

    f.rect(865,760,680,260,None,LINE,0,1.3)
    f.rect(865,760,65,32,PALE,LINE)
    f.text(879,766,"alt",19,True)
    f.text(945,767,"[at least 8 history weeks]",18,True)
    msg(1080,1400,835,"9a. Linear regression v1")
    msg(1400,1080,886,"Next-week estimate",True)
    f.line(865,916,1545,916,LINE,1.3,True)
    f.text(890,931,"[fewer than 8 history weeks]",18,True)
    f.rect(1000,964,450,38,PALE,FAINT,4)
    f.text(1225,973,"9b. Use personal weekly-average baseline",18,anchor="middle")
    msg(1080,1400,1075,"10. Score expenses (IF v1)")
    msg(1400,1080,1130,"Scores + explanations",True)
    msg(1080,1400,1190,"11. Apply guidance rules")
    msg(1400,1080,1238,"Recommendations",True)
    msg(1080,1750,1310,"12. Save run, forecast, alerts and recommendations; commit")
    msg(1750,1080,1370,"13. Stored result records",True)
    msg(1080,760,1425,"14. Serialized analysis",True)
    msg(760,430,1485,"15. Return JSON result",True)
    msg(430,140,1550,"16. Display insight cards",True)
    f.rect(900,1462,945,120,TINT,None,7)
    f.text(922,1479,"Result contract",20,True,TEAL)
    f.para(922,1512,"Forecast + horizon + data readiness, unusual-spending alerts and explanations, rule-based guidance, timestamps and model versions. Estimates do not automatically change transactions or budgets.",900,18,25)
    f.footer("Sources: backend/app/routes/analysis.py; services/analysis.py; services/model_registry.py; models/entities.py.",3)
    return f.end()


def phone(f,x,y,w,h,title,back=False,bottom=False):
    f.rect(x,y,w,h,WHITE,INK,27,2.4)
    f.rect(x+w/2-36,y+9,72,5,INK,None,2)
    f.text(x+23,y+23,"9:41",13,True)
    f.text(x+w-25,y+23,"LTE  [||||]",11,anchor="end")
    if back:
        f.poly([(x+29,y+69),(x+21,y+77),(x+29,y+85)],INK,2)
    f.text(x+(49 if back else 22),y+64,title,23,True)
    if not back:
        f.text(x+w-27,y+67,"R",18,color=MUTED,anchor="end")
    f.line(x+1,y+103,x+w-1,y+103,FAINT)
    f.rect(x+w-8,y+140,3,95,FAINT,None,1)
    if bottom:
        yy=y+h-81
        f.line(x+1,yy,x+w-1,yy,FAINT)
        labels=["Dashboard","Transactions","Budgets","Analytics","More"]
        for i,label in enumerate(labels):
            xx=x+11+(w-22)*(i+.5)/5
            f.circle(xx,yy+24,7,TINT if i==0 else WHITE,TEAL if i==0 else LINE)
            f.text(xx,yy+42,label,9.8,i==0,TEAL if i==0 else MUTED,anchor="middle")
    f.rect(x+w/2-40,y+h-15,80,4,INK,None,2)
    return x+20,y+122,w-40


def button(f,x,y,w,text,primary=False,h=46,size=17):
    f.rect(x,y,w,h,TINT if primary else WHITE,TEAL if primary else LINE,6)
    f.text(x+w/2,y+(h-size)/2-1,text,size,True if primary else False,TEAL if primary else INK,anchor="middle",max_width=w-18)


def field(f,x,y,w,label,value,h=48):
    f.text(x,y,label,17,True)
    f.rect(x,y+28,w,h,WHITE,LINE,5)
    f.text(x+13,y+28+(h-18)/2,value,18,color=MUTED,max_width=w-25)


def callout(f,x,y,n,title,body,w=370):
    f.circle(x+16,y+16,16,TINT,TEAL)
    f.text(x+16,y+7,str(n),17,True,TEAL,anchor="middle")
    f.text(x+43,y+2,title,21,True,max_width=w-43)
    return f.para(x+43,y+39,body,w-43,18,26,color=MUTED)


def card(f,x,y,w,title,value,sub=None,h=117):
    f.rect(x,y,w,h,WHITE,LINE,9)
    f.text(x+16,y+17,title,17,True)
    f.text(x+16,y+48,value,28,True)
    if sub:
        f.text(x+16,y+88,sub,14,color=MUTED,max_width=w-32)


def dashboard_figure(pdf):
    f=Figure(pdf,"04_Wireframe_Mobile_Dashboard",1500,1180,page_width=1050)
    f.title(4,"Mobile wireframe - dashboard","Main financial overview | Two scroll positions of the same screen, not two separate wireframes")
    f.text(90,180,"A. TOP OF SCREEN",17,True,TEAL)
    f.text(600,180,"B. SCROLLED TO INSIGHTS",17,True,TEAL)
    x,y,w=phone(f,75,219,415,842,"Dashboard",bottom=True)
    f.text(x,y,"Hello, Eeshan",24,True)
    f.para(x,y+34,"Your spending picture at a glance.",w,16)
    f.text(x,y+74,"Dashboard period",17,True)
    for xx,ww,label,on in [(x,105,"Weekly",False),(x+114,109,"Monthly",True),(x+232,143,"Last 3 months",False)]:
        button(f,xx,y+104,ww,label,on,37,14)
    f.text(x,y+153,"Aug 1 - Aug 31, 2026",14,color=MUTED)
    card(f,x,y+185,w,"Expense for period","KES 24,800","Monthly expense total",117)
    card(f,x,y+315,w,"Income for period","KES 42,000","Monthly income total",117)
    card(f,x,y+445,w,"Net cash flow","KES 17,200","Income minus expenses",117)
    f.text(x,y+578,"Scroll for counts, category and budgets",13,color=MUTED)

    x2,y2,w2=phone(f,585,219,415,842,"Dashboard",bottom=True)
    f.rect(x2,y2,w2,75,PALE,FAINT,7)
    f.text(x2+13,y2+12,"All-time balance: KES 56,900",17,True)
    f.text(x2+13,y2+43,"Active budget used: 62%",16)
    f.text(x2,y2+98,"Your latest insight",22,True)
    button(f,x2,y2+132,w2,"Refresh insights",True,43,17)
    for off,title,value,detail in [(192,"Next 7 days","KES 8,200","Week 4 of 8 - tap to view"),(316,"Spending check","2 items to review","Unusual patterns - not fraud findings"),(440,"Your next step","Review food spending","Tap to read the suggested action")]:
        f.rect(x2,y2+off,w2,110,WHITE,LINE,8)
        f.text(x2+15,y2+off+13,title,16,True)
        f.text(x2+15,y2+off+41,value,22,True,max_width=w2-38)
        f.text(x2+15,y2+off+79,detail,14,color=MUTED)
        f.text(x2+w2-16,y2+off+42,">",20,color=MUTED,anchor="end")
    f.para(x2,y2+567,"Insights help you plan. They are not guarantees or fraud findings.",w2,14,20,color=MUTED)
    f.arrow([(500,624),(574,624)],color=LINE)
    f.label(503,584,"Scroll",15)

    callout(f,1050,238,1,"Period-aware totals","Monthly is selected. Weekly, last 3 months, yearly and all-time are available through the horizontal selector.",370)
    callout(f,1050,437,2,"Single-column cards","The phone layout stacks cards. Transaction count and top spending category appear further down the summary.",370)
    callout(f,1050,642,3,"Actionable insights","Refresh analysis, open the forecast, inspect alerts or view recommendations from this screen.",370)
    callout(f,1050,847,4,"Persistent navigation","Dashboard, Transactions, Budgets, Analytics and More remain the five main destinations.",370)
    f.text(90,1082,"Structural wireframe; spacing condensed. Amounts and counts are fictional examples, not measured model results.",16,color=MUTED)
    f.footer("Sources: dashboard_screen.dart; home_shell.dart | Mobile layout, no desktop sidebar.",4)
    return f.end()


def transaction_figure(pdf):
    f=Figure(pdf,"05_Wireframe_Mobile_Add_Transaction",1280,1190,page_width=920)
    f.title(5,"Mobile wireframe - add transaction","Primary data-entry flow | Expense or income, amount, category, source and transaction date")
    x,y,w=phone(f,130,204,445,871,"Add transaction",back=True)
    button(f,x,y,w/2-4,"Expense",True,44)
    button(f,x+w/2+4,y,w/2-4,"Income",False,44)
    field(f,x,y+73,w,"Amount (KES)","850.00",51)
    field(f,x,y+183,w,"Category","Food",51)
    field(f,x,y+293,w,"Merchant or source (optional)","Example Store",51)
    f.rect(x,y+403,w,81,PALE,FAINT,6)
    f.text(x+14,y+419,"Recurring transaction",17,True)
    f.text(x+14,y+449,"Mark a repeated payment",14,color=MUTED)
    f.rect(x+w-67,y+427,50,27,WHITE,LINE,13)
    f.circle(x+w-52,y+440,10,FAINT,None)
    f.text(x,y+514,"Transaction date",17,True)
    f.rect(x,y+544,w,52,WHITE,LINE,5)
    f.text(x+13,y+560,"31 Aug 2026",18,color=MUTED)
    f.rect(x+w-41,y+557,22,22,None,LINE,2)
    f.line(x+w-41,y+564,x+w-19,y+564,LINE)
    button(f,x,y+627,w,"Save transaction",True,51,18)
    callout(f,685,234,1,"Reached from Transactions","The add action opens this page. Back returns to history; the five-tab bottom bar is not shown on this pushed page.",475)
    callout(f,685,443,2,"Clear input controls","Amount is numeric; category is a text field. Income and expense are mutually exclusive. Merchant or source is optional.",475)
    callout(f,685,652,3,"Recurring is a label","The switch tags a recurring payment. It does not create a payment schedule or initiate any bank transfer.",475)
    callout(f,685,861,4,"Validate, save, return","Inline errors explain invalid values. Save is disabled while submitting; success returns to transaction history.",475)
    f.text(130,1097,"Illustrative values. This page records financial data; it does not move money.",16,color=MUTED)
    f.footer("Source: mobile/lib/presentation/screens/transaction_entry_screen.dart.",5)
    return f.end()


def forecast_figure(pdf):
    f=Figure(pdf,"06_Wireframe_Mobile_Forecast_Results",1280,1210,page_width=920)
    f.title(6,"Mobile wireframe - forecast results","Next 7 days | Early-history example with honest data-readiness and accuracy messaging")
    x,y,w=phone(f,130,204,445,891,"Next 7 days",back=True)
    f.rect(x,y,w,136,TINT,TEAL,9)
    f.text(x+18,y+18,"Estimated spending",18,True,TEAL)
    f.text(x+18,y+57,"KES 8,200",35,True)
    f.text(x+18,y+105,"Sep 7 - Sep 13, 2026",16,color=MUTED)
    f.rect(x,y+154,w,191,WHITE,LINE,8)
    f.text(x+16,y+170,"Learning progress",20,True)
    f.text(x+w-16,y+170,"50%",20,True,TEAL,anchor="end")
    f.rect(x+16,y+209,w-32,9,PALE,FAINT,4)
    f.rect(x+16,y+209,(w-32)/2,9,TEAL,None,4)
    f.text(x+16,y+234,"Week 4 of 8 - Low",17,True)
    f.para(x+16,y+268,"This early estimate uses your recent weekly average. Each added week makes it more representative.",w-32,16,23)
    f.rect(x,y+361,w,111,PALE,FAINT,8)
    f.text(x+16,y+378,"Accuracy pending",19,True)
    f.para(x+16,y+411,"Accuracy can be measured after this forecast week ends.",w-32,16,23)
    f.rect(x,y+489,w,129,WHITE,LINE,8)
    f.text(x+16,y+505,"How to use this",19,True)
    f.para(x+16,y+539,"Use this amount as a planning guide for the week. Compare it with your budget and adjust optional spending if needed.",w-32,16,23)
    f.text(x+7,y+644,"About this estimate",19,True)
    f.text(x+w-9,y+646,"v",18,anchor="end")
    f.text(x+7,y+675,"Model details and limitations",15,color=MUTED)
    f.line(x+6,y+710,x+w-6,y+710,FAINT)
    callout(f,685,235,1,"A concrete forecast horizon","The estimate is linked to a specific seven-day period. The example here is fictional, not a claim about model performance.",475)
    callout(f,685,444,2,"Readiness is not accuracy","50% means four of eight history weeks are available. It does not mean the forecast is 50% accurate or has 50% statistical confidence.",475)
    callout(f,685,666,3,"Explain the live method","Under eight history weeks, the current backend uses the personal baseline. With enough history, the lightweight runtime uses linear regression v1.",475)
    callout(f,685,888,4,"Limitations stay visible","The details section explains synthetic-data validation and experimental status. The forecast is a planning aid, not a guaranteed outcome.",475)
    f.text(130,1117,"No accuracy percentage is invented for a forecast whose target week has not ended.",16,color=MUTED)
    f.footer("Sources: forecast_detail_screen.dart; AnalysisService; ModelRegistry.",6)
    return f.end()


def admin_figure(pdf):
    f=Figure(pdf,"07_Wireframe_Web_Admin_Management",1800,1440)
    f.title(7,"Admin wireframe - system management","Browser-based administration for the mobile system | Account controls, data management, system switch and audit")
    f.rect(55,192,1690,1040,WHITE,LINE,8)
    f.rect(55,192,246,1040,PALE,LINE,8)
    f.text(80,220,"SPENDLY",26,True,TEAL)
    f.text(80,259,"Administrator console",16,color=MUTED)
    for i,(title,sel) in enumerate([("Overview / model health",False),("Account management",True),("System controls",False),("Activity / audit",False)]):
        yy=322+i*72
        f.rect(69,yy,218,54,TINT if sel else PALE,TEAL if sel else None,5)
        f.text(82,yy+18,title,16,sel,TEAL if sel else INK,max_width=192)
    f.text(325,218,"System management",30,True)
    button(f,1598,210,125,"Sign out",h=42,size=16)
    f.text(326,263,"Manage access, inspect records and control new analysis requests.",18,color=MUTED)
    f.line(325,302,1723,302,FAINT)
    # Search and selected-account list.
    f.text(326,325,"Accounts",23,True)
    f.rect(326,368,368,46,WHITE,LINE,5)
    f.text(338,383,"Search name, username or email",16,color=MUTED)
    button(f,708,368,152,"All statuses  v",h=46,size=16)
    button(f,874,368,124,"Search",True,h=46,size=16)
    f.rect(326,438,1397,120,WHITE,LINE,5)
    f.rect(327,439,1395,43,PALE,None)
    for xx,label in [(341,"User"),(635,"Email"),(1010,"Sign-in"),(1215,"Status"),(1556,"Action")]:
        f.text(xx,451,label,16,True)
    for xx,label in [(341,"Sample User  /  sample_user"),(635,"sample@example.com"),(1010,"Password"),(1215,"Active")]:
        f.text(xx,506,label,16)
    button(f,1545,493,145,"Manage",True,h=42,size=16)
    f.text(328,572,"1 selected account",14,color=MUTED)
    f.text(1720,572,"Previous   1   Next",14,color=MUTED,anchor="end")
    # Account details and controls.
    f.rect(326,612,1397,404,WHITE,LINE,8)
    f.text(346,630,"Sample User",24,True)
    f.text(346,666,"sample_user | sample@example.com | Active | Training opt-in: No",16,color=MUTED)
    stat_x=[346,688,1030,1372]
    for xx,title,value in zip(stat_x,["Transactions","Budgets","Income","Expenses"],["124","3","KES 42,000","KES 24,800"]):
        f.rect(xx,707,322,74,PALE,FAINT,6)
        f.text(xx+13,720,title,14,color=MUTED)
        f.text(xx+13,744,value,22,True)
    for xx,ww,txt in [(346,161,"Edit profile"),(520,169,"Disable account"),(702,171,"Revoke sessions"),(886,206,"Export account data"),(1105,186,"Delete account*")]:
        button(f,xx,799,ww,txt,h=40,size=15)
    f.text(346,854,"*Disable the account first. Sensitive changes require a reason and admin-password confirmation.",15,color=MUTED)
    f.text(346,894,"Records",18,True)
    button(f,438,884,305,"Transactions  v",h=42,size=16)
    button(f,1500,884,194,"Add record",True,h=42,size=16)
    f.line(346,942,1694,942,FAINT)
    f.text(346,958,"31 Aug 2026  |  Expense  |  Food  |  Example Store  |  KES 850",16)
    button(f,1482,949,95,"Edit",h=38,size=15)
    button(f,1590,949,104,"Delete",h=38,size=15)
    # System controls and audit summary.
    f.rect(326,1040,670,169,WHITE,LINE,7)
    f.text(346,1058,"System controls",21,True)
    f.text(346,1095,"Fresh analysis: Enabled",17)
    button(f,753,1080,223,"Pause fresh insights",h=42,size=16)
    f.para(346,1135,"Lightweight runtime | Forecast v1 | Anomaly v1\nThe switch blocks new analysis, not in-flight work.",620,15,23,color=MUTED)
    f.rect(1020,1040,703,169,WHITE,LINE,7)
    f.text(1040,1058,"Activity / audit",21,True)
    f.text(1040,1095,"Time     Actor     Action     Target     Reason",16,True)
    f.text(1040,1132,"14:20    admin    profile update    sample user    correction",15)
    f.text(1040,1170,"Audit records survive deletion of the target account.",15,color=MUTED)

    f.rect(55,1254,1690,97,TINT,None,8)
    f.text(77,1271,"POWERFUL, ACCOUNTABLE ADMINISTRATION",18,True,TEAL)
    f.para(77,1305,"Record selector: transactions, budgets, forecasts, alerts and recommendations. Create applies to transactions and budgets; other supported actions follow the selected record type. Admin identity and consent are protected; existing analysis results are not silently recomputed.",1640,17,24)
    f.footer("Sources: backend/app/templates/admin/manage.html; routes/admin_management.py | All displayed account data is fictional.",7)
    return f.end()


def render(manifest):
    executable=shutil.which("pdftoppm")
    if not executable:
        raise RuntimeError("pdftoppm is required for visual QA and PNG exports")
    for i,item in enumerate(manifest,1):
        prefix=PNG_DIR/item["name"]
        subprocess.run([executable,"-f",str(i),"-l",str(i),"-singlefile","-r","210","-png",str(PDF),str(prefix)],check=True)
    thumbs=[]
    for item in manifest:
        with Image.open(PNG_DIR/(item["name"]+".png")) as im:
            th=ImageOps.contain(im.convert("RGB"),(590,560))
            tile=Image.new("RGB",(630,610),"white")
            tile.paste(th,((630-th.width)//2,15))
            ImageDraw.Draw(tile).text((18,582),item["name"],fill="black")
            thumbs.append(tile)
    sheet=Image.new("RGB",(630*3,610*3),"#e8edef")
    for i,thumb in enumerate(thumbs):
        sheet.paste(thumb,((i%3)*630,(i//3)*610))
    sheet.save(PACK/"Pack_Overview.png")


def main():
    schema=json.loads((PACK/"source/schema.json").read_text(encoding="utf-8"))
    assert len(schema["tables"])==11
    assert sum(len(t["columns"]) for t in schema["tables"])==97
    pdf=canvas.Canvas(str(PDF),pageCompression=1)
    pdf.setTitle("Spendly - Final System Diagrams and Wireframes - v1.2.0")
    pdf.setAuthor("Spendly project documentation")
    pdf.setSubject("Implementation-aligned database, architecture, sequence and four wireframes")
    manifest=[schema_figure(pdf,schema),architecture_figure(pdf),sequence_figure(pdf),dashboard_figure(pdf),transaction_figure(pdf),forecast_figure(pdf),admin_figure(pdf)]
    pdf.save()
    (PACK/"source/figure_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    render(manifest)
    print(f"Built {len(manifest)} SVGs, {len(manifest)} high-resolution PNGs, and {PDF.name}")


if __name__=="__main__":
    main()
