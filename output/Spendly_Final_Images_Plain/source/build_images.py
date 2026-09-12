"""Plain, editable technical SVGs. No application changes and no screenshot styling."""
import base64
import json
import math
from html import escape
from pathlib import Path

from PIL import ImageFont

PACK = Path(__file__).resolve().parent.parent
OUT = PACK / "svg"
OUT.mkdir(exist_ok=True)
TITLE = "SPENDLY PERSONAL FINANCE MANAGEMENT SYSTEM"
FONTS = {}
MANIFEST = []
BLACK, GRAY, WHITE, BLUE = "#111111", "#888888", "#ffffff", "#185498"


def text_width(s, size, bold=False):
    key = (size, bold)
    if key not in FONTS:
        FONTS[key] = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf", int(size*4))
    return FONTS[key].getlength(str(s))/4


def wrapped(s, size, max_width, bold=False):
    rows = []
    for para in str(s).split("\n"):
        row = ""
        for word in para.split():
            test = (row+" "+word).strip()
            if row and text_width(test,size,bold)>max_width:
                rows.append(row)
                row=word
            else:
                row=test
        rows.append(row)
    return rows


class Drawing:
    def __init__(self,name,w,h,title=None):
        self.name,self.w,self.h=name,w,h
        self.items=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',f'<title>{escape(name)}</title>','<rect width="100%" height="100%" fill="white"/>']
        self.texts=[]
        if title:
            self.text(w/2,44,TITLE+" - "+title,25,anchor="middle")

    def rect(self,x,y,w,h,r=0,stroke=BLACK,fill=WHITE,sw=1.8,dash=False):
        self.items.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill or "none"}" stroke="{stroke or "none"}" stroke-width="{sw}"'+(' stroke-dasharray="10 8"' if dash else '')+'/>')

    def ellipse(self,x,y,rx,ry,fill=WHITE,stroke=BLACK,sw=1.8):
        self.items.append(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def poly(self,pts,color=BLACK,sw=1.8,dash=False,fill=None,closed=False,halo=False):
        points=" ".join(f"{x},{y}" for x,y in pts)
        if halo:
            self.items.append(f'<polyline points="{points}" fill="none" stroke="white" stroke-width="{sw+6}"/>')
        self.items.append(f'<{"polygon" if closed else "polyline"} points="{points}" fill="{fill or "none"}" stroke="{color}" stroke-width="{sw}"'+(' stroke-dasharray="10 8"' if dash else '')+'/>')

    def line(self,x1,y1,x2,y2,**kw):
        self.poly([(x1,y1),(x2,y2)],**kw)

    def arrow(self,pts,dash=False,open_head=False,both=False,color=BLACK,halo=False):
        self.poly(pts,color=color,dash=dash,halo=halo)
        def tip(a,b):
            angle=math.atan2(b[1]-a[1],b[0]-a[0])
            p=(b[0]-12*math.cos(angle)+5*math.sin(angle),b[1]-12*math.sin(angle)-5*math.cos(angle))
            q=(b[0]-12*math.cos(angle)-5*math.sin(angle),b[1]-12*math.sin(angle)+5*math.cos(angle))
            if open_head:
                self.poly([p,b,q],color)
            else:
                self.poly([p,b,q],color,fill=color,closed=True)
        tip(pts[-2],pts[-1])
        if both:tip(pts[1],pts[0])

    def text(self,x,y,s,size=24,bold=False,anchor="start",color=BLACK,max_width=None):
        s=str(s)
        tw=text_width(s,size,bold)
        left=x-(tw/2 if anchor=="middle" else tw if anchor=="end" else 0)
        if max_width is not None and tw>max_width+.7:
            raise ValueError(f"{self.name}: text too wide: {s!r} {tw}>{max_width}")
        if left<0 or left+tw>self.w+1 or y<0 or y+size>self.h:
            raise ValueError(f"{self.name}: out-of-bounds text {s!r}")
        self.items.append(f'<text x="{x}" y="{y+size*.82}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" text-anchor="{anchor}" fill="{color}">{escape(s)}</text>')
        self.texts.append(s)

    def block(self,x,y,w,h,s,size=24,bold=False,color=BLACK,align="middle"):
        rows=wrapped(s,size,w,bold)
        lh=size*1.3
        if len(rows)*lh>h+1:
            raise ValueError(f"{self.name}: text block too tall {s!r}")
        top=y+(h-len(rows)*lh)/2
        for i,row in enumerate(rows):
            self.text(x+w/2 if align=="middle" else x,top+i*lh,row,size,bold,anchor=align if align=="middle" else "start",color=color,max_width=w)

    def label(self,x,y,s,size=21):
        rows=str(s).split("\n")
        for i,row in enumerate(rows):
            yy=y+i*size*1.25
            tw=text_width(row,size)
            self.rect(x-5,yy-3,tw+10,size+7,stroke=None)
            self.text(x,yy,row,size)

    def actor(self,x,y,label,size=1,color=BLACK):
        self.ellipse(x,y,18*size,18*size,stroke=color)
        self.line(x,y+18*size,x,y+80*size,color=color,sw=2)
        self.line(x-47*size,y+42*size,x+47*size,y+42*size,color=color,sw=2)
        self.line(x,y+80*size,x-45*size,y+136*size,color=color,sw=2)
        self.line(x,y+80*size,x+45*size,y+136*size,color=color,sw=2)
        self.text(x,y+150*size,label,24,anchor="middle",color=color)

    def image(self,filename,x,y,w,h):
        file=PACK/"assets"/filename
        if file.suffix==".svg":file=file.with_name(file.stem+"_render.png")
        mime="image/png"
        encoded=base64.b64encode(file.read_bytes()).decode()
        self.items.append(f'<image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet" xlink:href="data:{mime};base64,{encoded}"/>')

    def finish(self):
        self.items.append("</svg>")
        (OUT/(self.name+".svg")).write_text("\n".join(self.items),encoding="utf-8")
        MANIFEST.append({"name":self.name,"width":self.w,"height":self.h,"text_count":len(self.texts),"texts":self.texts})


def crow(d,p,other,kind):
    dx,dy=other[0]-p[0],other[1]-p[1]
    dist=math.hypot(dx,dy);dx/=dist;dy/=dist
    nx,ny=-dy,dx
    def bar(at):
        x,y=p[0]+at*dx,p[1]+at*dy
        d.line(x+10*nx,y+10*ny,x-10*nx,y-10*ny)
    if kind=="1":bar(13);bar(22)
    elif kind=="0..1":
        bar(13);d.ellipse(p[0]+33*dx,p[1]+33*dy,7,7)
    else:
        for n in [-10,0,10]:
            d.line(p[0]+24*dx,p[1]+24*dy,p[0]+n*nx,p[1]+n*ny)
        d.ellipse(p[0]+38*dx,p[1]+38*dy,7,7)


def er_link(d,pts,a="1",b="0..*",label=None,xy=None):
    d.poly(pts,halo=True)
    crow(d,pts[0],pts[1],a);crow(d,pts[-1],pts[-2],b)
    if label:d.label(*xy,label,20)


def data_table(d,t,x,y,w,selected=None,types=True,notes=(),size=23,row=32):
    d.items.append(f'<g id="table-{escape(t["name"])}">')
    cols=t["columns"] if selected is None else [c for name in selected for c in t["columns"] if c["name"]==name]
    h=45+len(cols)*row
    note_rows=[line for note in notes for line in wrapped(note,18,w-24)]
    final_h=h+(len(note_rows)*24+10 if note_rows else 0)
    d.rect(x,y,w,final_h,r=8,sw=2)
    d.text(x+w/2,y+11,t["name"].upper(),25,anchor="middle")
    d.line(x,y+45,x+w,y+45)
    d.line(x+82,y+45,x+82,y+h)
    if types:d.line(x+w-190,y+45,x+w-190,y+h)
    for i,c in enumerate(cols):
        d.items.append(f'<g data-column="{escape(c["name"])}">')
        yy=y+45+i*row+6
        flags=[]
        if c["pk"]:flags.append("PK")
        if c["foreign_keys"]:flags.append("FK")
        if c["unique"]:flags.append("UQ")
        d.text(x+10,yy,"/".join(flags),17)
        d.text(x+91,yy,c["name"]+(" ?" if c["nullable"] else ""),size,c["pk"],max_width=w-(286 if types else 102))
        if types:
            ty=c["type"].replace("TIMESTAMP WITHOUT TIME ZONE","TIMESTAMP").replace("INTEGER","INT").replace(" ","")
            d.text(x+w-180,yy,ty,21,max_width=170)
        d.items.append('</g>')
    if note_rows:
        d.line(x,y+h,x+w,y+h)
        for i,note in enumerate(note_rows):d.text(x+12,y+h+8+i*24,note,18)
    d.items.append('</g>')
    return final_h


def schema(tables):
    d=Drawing("01_Database_Schema",2700,2320,"DATABASE SCHEMA")
    # Ownership uses one shared trunk; every child end is its actual user_id row.
    d.poly([(770,221),(895,221),(895,1780)])
    crow(d,(770,221),(895,221),"1")
    for pts in [[(895,253),(1030,253)],[(895,953),(770,953)],[(895,1523),(770,1523)],[(895,885),(1030,885)]]:
        d.poly(pts);crow(d,pts[-1],pts[-2],"0..*")
    d.poly([(895,221),(895,114),(1830,114),(1830,285),(1910,285)],halo=True)
    crow(d,(1910,285),(1830,285),"0..*")
    d.poly([(895,1780),(2660,1780),(2660,1025),(2600,1025)])
    crow(d,(2600,1025),(2660,1025),"0..*")
    er_link(d,[(1660,221),(1730,221),(1730,253),(1910,253)],b="0..1")
    er_link(d,[(1345,429),(1345,760)])
    er_link(d,[(1660,350),(1800,350),(1800,993),(1910,993)])
    er_link(d,[(425,860),(425,810),(970,810),(970,917),(1030,917)],a="0..1")
    data_table(d,tables["users"],80,160,690,notes=["UQ: email; google_subject; username_normalized"],size=22)
    data_table(d,tables["analysis_runs"],1030,160,630,size=21)
    data_table(d,tables["forecasts"],1910,160,690)
    data_table(d,tables["transactions"],80,860,690,notes=["UQ: (user_id, fingerprint)"])
    data_table(d,tables["anomaly_alerts"],1030,760,630,size=21)
    data_table(d,tables["recommendations"],1910,900,690,size=22)
    data_table(d,tables["budgets"],80,1430,690,notes=["UQ: (user_id, period_start, period_end, category)"])
    d.text(1050,1495,"PK = primary key     FK = foreign key     UQ = unique     ? = nullable",23)
    d.text(1050,1544,"Identifiers: VARCHAR(36)     Money: NUMERIC(14,2)     Timestamps: UTC",22)
    d.text(1050,1593,"One run has 0..1 forecast; its analysis_run_id is unique.",22)
    d.text(1050,1642,"Delete rules: CASCADE, except alert transaction references use SET NULL.",22)
    d.text(80,1840,"Operational tables",24)
    for x,name in [(80,"admin_audit"),(735,"model_versions"),(1390,"admin_login_attempts"),(2045,"system_settings")]:
        notes=["UQ: (component, version)"] if name=="model_versions" else []
        data_table(d,tables[name],x,1890,575,notes=notes,size=20,row=32)
    d.text(80,2250,"Only declared foreign keys are drawn. Admin audit targets and model-version labels are not foreign keys.",21)
    d.finish()


def erd(tables):
    d=Drawing("02_Entity_Relationship_Diagram",2460,1800,"ENTITY RELATIONSHIP DIAGRAM (ERD)")
    d.rect(30,25,2400,1745,stroke=GRAY,fill=None)
    # Labelled entity relationships; attributes are intentionally selective.
    d.poly([(620,280),(735,280),(735,1250)])
    crow(d,(620,280),(735,280),"1")
    for pts,lab,xy in [([(735,280),(900,280)],"requests",(755,246)), ([(735,700),(620,700)],"records",(638,666)), ([(735,1140),(620,1140)],"sets",(652,1105)), ([(735,790),(900,790)],"owns",(747,756))]:
        d.poly(pts);crow(d,pts[-1],pts[-2],"0..*");d.label(*xy,lab,20)
    d.poly([(735,280),(735,125),(1610,125),(1610,280),(1720,280)],halo=True)
    crow(d,(1720,280),(1610,280),"0..*");d.label(1120,104,"owns forecasts",20)
    d.poly([(735,1250),(2380,1250),(2380,790),(2280,790)])
    crow(d,(2280,790),(2380,790),"0..*");d.label(1820,1220,"owns recommendations",20)
    er_link(d,[(1460,345),(1550,345),(1720,345)],b="0..1",label="produces",xy=(1510,307))
    er_link(d,[(1180,438),(1180,650)],label="generates",xy=(1204,535))
    er_link(d,[(1460,400),(1550,400),(1550,690),(1720,690)],label="produces",xy=(1570,650))
    er_link(d,[(340,650),(340,565),(825,565),(825,855),(900,855)],a="0..1",label="may be flagged by",xy=(398,530))
    pick={
        "users":["id","display_name","username","email","is_active"],
        "analysis_runs":["id","user_id","status","generated_at","history_periods"],
        "forecasts":["id","analysis_run_id","user_id","period_start","predicted_spending"],
        "transactions":["id","user_id","amount","category","transaction_timestamp"],
        "anomaly_alerts":["id","analysis_run_id","user_id","transaction_id","anomaly_score","explanation"],
        "recommendations":["id","analysis_run_id","user_id","title","suggested_action"],
        "budgets":["id","user_id","category","amount","period_start"],
    }
    for name,x,y in [("users",60,180),("analysis_runs",900,180),("forecasts",1720,180),("transactions",60,650),("anomaly_alerts",900,650),("recommendations",1720,650),("budgets",60,1020)]:
        data_table(d,tables[name],x,y,560,pick[name],False,size=25,row=42)
    d.text(930,1070,"1 to 0..* = one to zero or many",24)
    d.text(930,1120,"1 to 0..1 = one to zero or one",24)
    d.text(930,1170,"Selected attributes shown; full columns are in the database schema.",22)
    d.text(60,1330,"Independent operational entities (no declared foreign-key relationships)",24)
    for x,name,attrs in [(60,"admin_audit",["id","actor","action","target_id"]),(650,"model_versions",["id","component","version","artifact_path"]),(1240,"admin_login_attempts",["id","client_key","created_at"]),(1830,"system_settings",["key","enabled"])]:
        data_table(d,tables[name],x,1385,550,attrs,False,size=23,row=42)
    d.text(60,1685,"An alert may reference zero or one transaction. A transaction may be referenced by multiple alerts.",22)
    d.finish()


def use_case():
    d=Drawing("03_Use_Case_Diagram",2400,1730)
    d.rect(285,40,1830,1650,r=7,sw=2)
    d.text(1200,72,TITLE+" - USE CASE DIAGRAM",25,anchor="middle")
    d.actor(125,780,"App user",1.1)
    d.actor(2280,780,"Administrator",1.1)
    left=[(260,"Register / sign in"),(445,"Manage transactions"),(630,"Import transaction CSV"),(815,"Manage budgets"),(1000,"Generate spending insights"),(1185,"View forecasts, alerts\nand recommendations"),(1370,"View dashboard\nand analytics"),(1555,"Manage profile\nand consent")]
    right=[(260,"Sign in to admin console"),(475,"Manage user accounts\nand access"),(690,"Manage transactions\nand budgets"),(905,"Inspect / export\naccount data"),(1120,"Pause / resume\nnew analysis"),(1335,"View audit records\nand model information")]
    for yy,label in left:
        d.line(174,826,425,yy)
        d.ellipse(655,yy,230,58);d.block(445,yy-43,420,86,label,26)
    for yy,label in right:
        d.line(2230,826,2075,yy)
        d.ellipse(1860,yy,215,58);d.block(1664,yy-43,392,86,label,25)
    for yy,label in [(835,"Prepare spending\nfeatures"),(1000,"Estimate next-week\nspending"),(1165,"Check unusual\nspending"),(1330,"Generate rule-based\nrecommendations")]:
        d.arrow([(885,1000),(1090,yy)],dash=True,open_head=True)
        d.label(916,(1000+yy)/2-26,"<<include>>",20)
        d.ellipse(1300,yy,210,56);d.block(1111,yy-40,378,80,label,25)
    d.finish()


def action(d,x,y,w,h,label):
    d.rect(x,y,w,h,r=9,sw=2)
    d.block(x+12,y+8,w-24,h-16,label,24)


def diamond(d,cx,cy,w,h,label):
    d.poly([(cx,cy-h/2),(cx+w/2,cy),(cx,cy+h/2),(cx-w/2,cy)],closed=True,fill=WHITE,sw=2)
    d.block(cx-w*.32,cy-h*.3,w*.64,h*.6,label,24)


def final_node(d,x,y):
    d.ellipse(x,y,30,30,WHITE,BLACK,2);d.ellipse(x,y,21,21,BLACK,BLACK)


def activity():
    d=Drawing("04_Activity_Diagram",1500,2440,"ACTIVITY DIAGRAM")
    d.ellipse(350,210,23,23,BLACK)
    d.arrow([(350,233),(350,270)])
    action(d,160,270,380,78,"Open app and sign in")
    d.arrow([(540,309),(870,309)])
    action(d,870,270,410,78,"Check authentication\nand required consent")
    d.arrow([(1075,348),(1075,390)])
    diamond(d,1075,485,235,190,"Access\nallowed?")
    d.arrow([(1192.5,485),(1420,485)]);d.label(1300,449,"No",23);final_node(d,1450,485)
    d.arrow([(1075,580),(1075,630)]);d.label(1097,591,"Yes",23)
    action(d,870,630,410,78,"Display dashboard")
    d.arrow([(870,669),(540,669)])
    action(d,160,630,380,78,"Enter transaction\nor select CSV import")
    d.arrow([(350,708),(350,813),(870,813)])
    action(d,870,774,410,78,"Validate financial data")
    d.arrow([(1075,852),(1075,892)])
    diamond(d,1075,972,190,160,"Input\nvalid?")
    d.arrow([(980,972),(80,972),(80,669),(160,669)]);d.label(625,938,"No - correct input",23)
    d.arrow([(1075,1052),(1075,1110)]);d.label(1097,1067,"Yes",23)
    action(d,870,1110,410,78,"Store transactions")
    d.arrow([(870,1149),(540,1149)])
    action(d,160,1110,380,78,"Request fresh insights")
    d.arrow([(350,1188),(350,1319),(870,1319)])
    action(d,870,1270,410,98,"Check analysis availability;\nload history and budgets")
    d.arrow([(1280,1319),(1420,1319)]);d.label(1300,1283,"[Paused]",21);final_node(d,1450,1319)
    d.arrow([(1075,1368),(1075,1410)]);d.label(1094,1379,"[Enabled]",20)
    action(d,870,1410,410,78,"Prepare weekly features")
    d.arrow([(1075,1488),(1075,1540)])
    diamond(d,1075,1620,210,160,"8+ history\nweeks?")
    d.arrow([(970,1620),(540,1620)]);d.label(730,1585,"No",23)
    action(d,160,1581,380,78,"Use personal weekly-\naverage baseline")
    d.arrow([(1075,1700),(1075,1750)]);d.label(1097,1711,"Yes",23)
    action(d,870,1750,410,78,"Predict spending using\nlinear regression")
    d.arrow([(1075,1828),(1075,1868)])
    d.arrow([(350,1659),(350,1888),(1055,1888)])
    d.poly([(1075,1868),(1095,1888),(1075,1908),(1055,1888)],closed=True,fill=WHITE)
    d.arrow([(1075,1908),(1075,1940)])
    action(d,870,1940,410,78,"Score expenses with\nIsolation Forest")
    d.arrow([(1075,2018),(1075,2054)])
    action(d,870,2054,410,78,"Generate rule-based\nrecommendations")
    d.arrow([(1075,2132),(1075,2168)])
    action(d,870,2168,410,78,"Store analysis and results")
    d.arrow([(870,2207),(540,2207)])
    action(d,160,2168,380,98,"View forecast, alerts\nand recommendations")
    d.arrow([(350,2266),(350,2350)]);final_node(d,350,2380)
    d.finish()


def sequence():
    d=Drawing("05_Sequence_Diagram",2250,2100)
    d.text(1125,44,TITLE+" - SEQUENCE DIAGRAM",26,anchor="middle")
    d.text(1125,86,"Generate spending insights",24,anchor="middle")
    actors=[(100,"User"),(465,"Mobile interface"),(875,"Flask backend"),(1310,"Feature preparation"),(1740,"Model registry"),(2110,"Database")]
    d.actor(100,151,"User",.65)
    for x,name in actors[1:]:d.rect(x-137,162,274,68,r=3);d.block(x-128,172,256,48,name,24)
    for x,name in actors:d.line(x,260,x,2000,dash=True)
    for x,y,h in [(465,303,1650),(875,383,1520),(1310,610,96),(1310,1085,84),(1740,820,65),(1740,1255,80),(2110,467,86),(2110,1630,72)]:d.rect(x-8,y,16,h,r=2)
    def msg(a,b,y,label,ret=False):
        d.arrow([(a,y),(b,y)],dash=ret,open_head=ret)
        lines=wrapped(label,23,abs(b-a)-24)
        for i,ln in enumerate(lines):d.label((a+b)/2-text_width(ln,23)/2,y-(len(lines)-i)*29-10,ln,23)
    msg(100,465,310,"1. Request fresh insights")
    msg(465,875,390,"2. POST analysis/run + JWT")
    msg(875,2110,485,"3. Read active user, consent, analysis setting, transactions and budgets")
    msg(2110,875,555,"4. Return owned records and access state",True)
    msg(875,1310,630,"5. Prepare weekly features")
    msg(1310,875,705,"6. History window and budget context",True)
    d.rect(720,748,1190,300,fill=None,sw=1.5)
    d.rect(720,748,60,34);d.text(733,755,"alt",21)
    d.label(930,757,"[8 or more history weeks]",22)
    msg(875,1740,835,"7a. Predict next-week spending with linear regression")
    msg(1740,875,890,"8a. Return spending estimate",True)
    d.line(720,915,1910,915,dash=True)
    d.label(930,932,"[fewer than 8 history weeks]",22)
    d.arrow([(883,975),(990,975),(990,1020),(883,1020)])
    d.label(1035,983,"7b. Use personal weekly-average baseline",22)
    msg(875,1310,1095,"9. Prepare expense features")
    msg(1310,875,1170,"10. Return anomaly features",True)
    msg(875,1740,1270,"11. Score expenses with Isolation Forest")
    msg(1740,875,1340,"12. Return flags, scores, thresholds and explanations",True)
    d.arrow([(883,1450),(980,1450),(980,1505),(883,1505)])
    d.label(1010,1453,"13. Apply recommendation rules\nusing forecast, budgets and alerts",23)
    msg(875,2110,1640,"14. Store analysis run, forecast, alerts and recommendations")
    msg(2110,875,1710,"15. Confirm database commit",True)
    msg(875,465,1870,"16. Return analysis response",True)
    msg(465,100,1950,"17. Display spending insights",True)
    d.finish()


def class_box(d,x,y,w,name,attrs,methods):
    ah=len(attrs)*30+18
    mh=len(methods)*31+18 if methods else 0
    h=46+ah+mh
    d.rect(x,y,w,h,r=4)
    d.text(x+w/2,y+12,name,25,anchor="middle")
    d.line(x,y+46,x+w,y+46)
    for i,a in enumerate(attrs):d.text(x+13,y+57+i*30,a if a.startswith("- ") else "+ "+a,21,max_width=w-26)
    if methods:
        d.line(x,y+46+ah,x+w,y+46+ah)
        for i,m in enumerate(methods):d.text(x+13,y+57+ah+i*31,"+ "+m,21,max_width=w-26)
    return h


def class_diagram():
    d=Drawing("06_Class_Diagram",2460,2020,"CLASS DIAGRAM")
    # Associations first. Only actual Python classes and methods are shown.
    d.line(350,473,350,700);d.label(365,506,"1",23);d.label(365,650,"0..*",23);d.label(374,568,"owns",22)
    d.poly([(620,365),(745,365),(745,1240),(620,1240)]);d.label(649,389,"1",23);d.label(638,1200,"0..*",23);d.label(755,1060,"owns",22)
    d.poly([(620,290),(780,290),(780,910),(900,910)]);d.label(646,253,"1",23);d.label(840,867,"0..*",23);d.label(790,755,"requests",22)
    for pts,label,xy in [([(1520,288),(1810,288)],"uses",(1630,252)), ([(1340,476),(1340,625),(2070,625),(2070,730)],"uses",(1590,590)), ([(1420,476),(1420,650),(1750,650),(1750,1250),(1810,1250)],"uses",(1670,1192))]:
        d.arrow(pts,dash=True,open_head=True);d.label(*xy,label,22)
    d.arrow([(1200,476),(1200,850)],dash=True,open_head=True);d.label(1222,746,"creates",22)
    # AnalysisRun composition of historical result objects.
    for target in [370,1090,1800]:
        d.poly([(1190,1124),(1190,1485),(target,1485),(target,1550)])
        d.label(target+14,1510,"0..1" if target==370 else "0..*",23)
    d.poly([(1190,1124),(1200,1142),(1190,1160),(1180,1142)],closed=True,fill=BLACK)
    d.label(1211,1183,"1",23);d.label(1215,1395,"contains",22)
    d.arrow([(800,1748),(705,1748),(705,1060),(660,1060),(660,805),(620,805)],open_head=True)
    d.label(646,1020,"references",19)
    d.label(638,772,"0..1",20)
    d.label(732,1710,"0..*",20)

    class_box(d,80,180,540,"User",["id: str","email: str","username: str","monthly_income: Decimal?","is_active: bool","auth_version: int"],["to_dict(): dict"])
    class_box(d,900,180,620,"AnalysisService",["registry: ModelRegistry","features: FeaturePreparationService","recommendations: RecommendationEngine"],["run(user: User): dict","serialize(...): dict","forecast_payload(forecast): dict","latest(run: AnalysisRun): dict"])
    class_box(d,1810,180,550,"ModelRegistry",["runtime: str","forecast_version: str","anomaly_version: str"],["load(): None","forecast(raw_sequence): dict","detect_unusual(feature_frame): DataFrame","info(): dict"])
    class_box(d,80,700,540,"Transaction",["id: str","user_id: str","amount: Decimal","category: str","transaction_type: str","transaction_timestamp: datetime"],["to_dict(): dict"])
    class_box(d,80,1180,540,"Budget",["id: str","user_id: str","category: str","amount: Decimal","period_start / period_end: date"],["to_dict(): dict"])
    class_box(d,900,850,620,"AnalysisRun",["id: str","user_id: str","status: str","history_periods: int","generated_at: datetime","forecast: Forecast","alerts / recommendations: list"],[])
    class_box(d,1810,730,550,"FeaturePreparationService",["lookback: int","feature_names: list","anomaly_features: list"],["forecasting(user, transactions, budgets)","anomaly(transactions): DataFrame"])
    class_box(d,1810,1150,550,"RecommendationEngine",["- _rules: tuple","- _maximum_recommendations: int"],["evaluate(context): list[Recommendation]"])
    class_box(d,80,1550,580,"Forecast",["id: str","analysis_run_id: str","period_start / period_end: date","predicted_spending: Decimal","model_version: str"],["to_dict(): dict"])
    class_box(d,800,1550,580,"AnomalyAlert",["id: str","analysis_run_id: str","transaction_id: str?","anomaly_score: float","explanation: str"],["to_dict(): dict"])
    class_box(d,1510,1550,580,"RecommendationRecord",["id: str","analysis_run_id: str","title / message: str","severity: str","suggested_action: str"],["to_dict(): dict"])
    d.text(80,1960,"Core analysis classes with selected attributes and methods. Administrator operations are route handlers, not a User subclass.",22)
    d.finish()


def logo_placeholder(d,x,y,w=95,h=62):
    d.rect(x,y,w,h,stroke=GRAY,sw=1.4)
    d.line(x,y,x+w,y+h,color=GRAY,sw=1)
    d.line(x+w,y,x,y+h,color=GRAY,sw=1)
    d.rect(x+13,y+h/2-13,w-26,26,stroke=None)
    d.text(x+w/2,y+h/2-11,"LOGO",21,anchor="middle")


def mobile_shell(name,title,h):
    d=Drawing(name,760,h)
    d.rect(20,20,720,h-40,stroke=GRAY,sw=1.4)
    logo_placeholder(d,44,41,99,66)
    d.text(167,51,"SPENDLY",30)
    d.text(167,87,"Personal Finance Management",20)
    d.line(20,132,740,132,color=GRAY,sw=1.2)
    d.text(48,161,title,33)
    d.line(48,212,712,212,color=GRAY,sw=1.1)
    return d


def nav(d,y):
    d.line(20,y,740,y,color=GRAY,sw=1.1)
    for i,label in enumerate(["Dashboard","Transactions","Budgets","Analytics","More"]):
        x=92+i*143
        d.rect(x-8,y+18,16,16,stroke=GRAY,sw=1.2)
        d.text(x,y+48,label,17,anchor="middle")


def button(d,x,y,w,h,label):
    d.rect(x,y,w,h,r=3,stroke=GRAY,sw=1.2)
    d.block(x+10,y+8,w-20,h-16,label,23)


def input_field(d,x,y,w,label,placeholder):
    d.text(x,y,label,24)
    d.rect(x,y+40,w,63,r=3,stroke=GRAY,sw=1.2)
    d.text(x+16,y+60,placeholder,23,color="#666666")


def wf_dashboard():
    d=mobile_shell("08_Wireframe_Dashboard","Dashboard",1270)
    d.text(50,241,"Hello, [username]",25)
    d.text(50,291,"Dashboard period",23)
    button(d,50,332,661,56,"Weekly   |   Monthly   |   Last 3 months   >")
    d.text(50,410,"[Period start] - [Period end]",21)
    for y,label in [(460,"Expenses"),(590,"Income"),(720,"Net cash flow")]:
        d.rect(50,y,661,106,r=4,stroke=GRAY,sw=1.2)
        d.text(70,y+19,label,23);d.text(70,y+58,"KES XX,XXX",29)
    d.text(50,858,"Your latest insight",27)
    d.rect(50,906,661,140,r=3,stroke=GRAY,sw=1.2)
    d.text(69,925,"Next 7 days: KES XX,XXX",24)
    d.text(69,967,"Spending check: [items to review]",23)
    d.text(69,1009,"Suggested action: [recommendation]",22)
    button(d,50,1073,661,57,"Refresh insights")
    nav(d,1161);d.finish()


def wf_entry():
    d=mobile_shell("09_Wireframe_Add_Transaction","Add Transaction",1250)
    button(d,50,247,323,58,"Expense");button(d,388,247,323,58,"Income")
    input_field(d,50,346,661,"Amount (KES)","Enter amount")
    input_field(d,50,497,661,"Category","e.g. Food, Transport, Salary")
    input_field(d,50,648,661,"Merchant or source (optional)","Enter merchant or source")
    d.rect(50,805,25,25,stroke=GRAY,sw=1.2);d.text(92,804,"Recurring transaction",24)
    input_field(d,50,880,661,"Transaction date","Select date")
    d.poly([(679,947),(690,947),(684.5,955)],closed=True,fill=GRAY,color=GRAY)
    button(d,50,1075,188,61,"Back");button(d,263,1075,448,61,"Save transaction")
    d.finish()


def wf_forecast():
    d=mobile_shell("10_Wireframe_Forecast_Results","Forecast Results",1240)
    d.rect(50,249,661,190,r=4,stroke=GRAY,sw=1.2)
    d.text(74,270,"Estimated spending - next 7 days",25)
    d.text(74,325,"KES XX,XXX",38)
    d.text(74,392,"[Forecast start] - [Forecast end]",23)
    d.rect(50,472,661,209,r=4,stroke=GRAY,sw=1.2)
    d.text(73,496,"Learning progress",25)
    d.text(685,496,"[XX%]",24,anchor="end")
    d.rect(73,544,612,23,stroke=GRAY,sw=1.2)
    d.text(73,591,"Week [X] of 8",23)
    d.text(73,632,"Based on available spending history",22)
    d.rect(50,715,661,119,r=4,stroke=GRAY,sw=1.2)
    d.text(73,736,"Accuracy pending",25)
    d.text(73,782,"Measured after the forecast week ends.",22)
    d.rect(50,866,661,126,r=4,stroke=GRAY,sw=1.2)
    d.text(73,887,"Planning guidance",25)
    d.text(73,933,"Compare this estimate with your budget.",22)
    d.text(50,1030,"About this estimate                         v",23)
    d.text(50,1071,"Experimental guidance; not a guaranteed outcome.",21)
    button(d,50,1132,188,60,"Back");d.finish()


def wf_admin():
    d=Drawing("11_Wireframe_Admin_Dashboard",1770,1230)
    d.rect(15,15,1740,1200,stroke=GRAY,sw=1.3)
    logo_placeholder(d,42,39,148,77)
    d.text(221,50,"SPENDLY",32)
    d.text(221,92,"Personal Finance Management System",25)
    d.text(1470,77,"Admin",25);d.text(1630,77,"Logout",25)
    d.line(15,140,1755,140,color=GRAY,sw=1.2)
    d.line(315,140,315,1215,color=GRAY,sw=1.2)
    for i,txt in enumerate(["Dashboard","Users","Transactions","Budgets","Insights","Model information","Activity / audit","System controls"]):
        y=199+i*93
        d.rect(45,y,21,21,stroke=GRAY,sw=1.2);d.text(86,y,txt,23,max_width=216)
    d.text(350,175,"Administrator Dashboard",38)
    d.line(350,236,1715,236,color=GRAY,sw=1.2)
    for i,title in enumerate(["Registered users","Transactions","Analysis runs","Unusual alerts"]):
        x=350+i*347
        d.rect(x,271,323,152,r=4,stroke=GRAY,sw=1.2)
        d.text(x+20,298,title,23);d.text(x+20,358,"[000]",35)
    d.rect(350,464,802,430,r=4,stroke=GRAY,sw=1.2)
    d.text(375,489,"Recent users",27)
    xs=[375,611,907,1127]
    d.rect(375,540,752,247,stroke=GRAY,sw=1.1)
    for xx in xs[1:-1]:d.line(xx,540,xx,787,color=GRAY,sw=1.1)
    for yy in [590,639,688,737]:d.line(375,yy,1127,yy,color=GRAY,sw=1.1)
    for xx,tx in [(391,"Name"),(627,"Email"),(923,"Status")]:d.text(xx,555,tx,22)
    for yy in [605,654,703,752]:
        d.text(391,yy,"[User name]",21);d.text(627,yy,"[Email address]",21);d.text(923,yy,"[Active]",21)
    button(d,375,815,244,52,"View all users")
    d.rect(1181,464,534,430,r=4,stroke=GRAY,sw=1.2)
    d.text(1204,489,"Management shortcuts",27)
    for y,txt in [(547,"Manage accounts"),(626,"Manage financial records"),(705,"Inspect stored insights"),(784,"View activity / audit")]:button(d,1205,y,486,59,txt)
    d.rect(350,932,1365,213,r=4,stroke=GRAY,sw=1.2)
    d.text(375,956,"Model and system overview",27)
    d.text(375,1009,"Forecast model",22);d.text(765,1009,"Anomaly model",22);d.text(1195,1009,"New analysis",22)
    for x,w,txt in [(375,355,"Linear regression v1"),(765,395,"Isolation Forest v1"),(1195,490,"[Enabled / paused]")]:button(d,x,1047,w,62,txt)
    d.finish()


def arch_box(d,x,y,w,h,title,body,logos=(),icon=None):
    d.rect(x,y,w,h,r=12,stroke=GRAY,sw=1.7)
    if logos:
        step=(w-60)/len(logos)
        for i,fn in enumerate(logos):d.image(fn,x+30+i*step,y+23,step-15,115)
    elif icon:
        if icon=="user":
            d.ellipse(x+w/2,y+52,26,29,BLUE,BLUE)
            d.rect(x+w/2-46,y+93,92,49,r=22,fill=BLUE,stroke=BLUE)
        elif icon=="browser":
            d.rect(x+w/2-65,y+24,130,108,r=5,stroke=BLUE,sw=3)
            d.line(x+w/2-65,y+45,x+w/2+65,y+45,color=BLUE,sw=3)
            d.ellipse(x+w/2,y+91,28,28,stroke=BLUE,sw=3)
            d.line(x+w/2-28,y+91,x+w/2+28,y+91,color=BLUE,sw=2)
        elif icon=="features":
            for j in range(3):d.rect(x+w/2-55,y+32+j*27,110,18,r=3,stroke=BLUE,sw=2)
    d.block(x+20,y+161,w-40,72,title,28,color=BLUE)
    d.line(x+25,y+249,x+w-25,y+249,color=BLUE,sw=1.2)
    rows=[]
    for line in body:rows+=wrapped("• "+line,23,w-52)
    if y+272+len(rows)*34>y+h-12:raise ValueError("Architecture box overflow: "+title)
    for i,line in enumerate(rows):d.text(x+26,y+272+i*34,line,23,max_width=w-52)


def architecture():
    d=Drawing("07_System_Architecture",2650,1660,"SYSTEM ARCHITECTURE")
    # Component arrangement mirrors the supplied academic architecture example.
    arch_box(d,45,210,365,440,"GENERAL USER",["Record transactions","Manage budgets","View forecasts and alerts","Read guidance"],icon="user")
    arch_box(d,45,855,365,490,"ADMINISTRATOR",["Manage accounts","Correct financial records","Inspect / export data","Control fresh analysis","Review audit and models"],icon="user")
    arch_box(d,570,210,420,520,"FLUTTER MOBILE\nAPPLICATION",["Dashboard and analytics","Manual entry and CSV import","Budgets and financial history","Forecasts, alerts and guidance","Email/password or Google sign-in"],logos=["flutter.svg"])
    arch_box(d,570,880,420,425,"BROWSER ADMIN\nCONSOLE",["Protected administrator login","Account and record management","System controls and audit"],icon="browser")
    arch_box(d,1200,530,485,652,"FLASK BACKEND\nREST API",["Authenticate and validate requests","Enforce user-owned data access","Coordinate feature preparation","Run models and guidance rules","Store and retrieve results","Load versioned model artifacts","Serve administrator pages"],logos=["python.svg","flask.svg"])
    arch_box(d,2000,160,600,405,"FEATURE PREPARATION",["Weekly transaction aggregation","Budget and historical-spending context","Expense anomaly features"],icon="features")
    arch_box(d,2000,650,600,455,"SPENDING ANALYSIS\nscikit-learn",["Forecast: multiple linear regression v1","Early history: weekly-average baseline","Anomalies: Isolation Forest v1","Recommendations: transparent rules"],logos=["scikit-learn.svg"])
    arch_box(d,2000,1175,600,427,"POSTGRESQL DATABASE",["Users, transactions and budgets","Analysis runs, forecasts, alerts, guidance","Model metadata, admin audit and settings"],logos=["postgresql.png"])
    for pts,txt,xy in [([(410,428),(570,428)],"Interaction /\ndisplay",(421,350)), ([(410,1100),(570,1100)],"Interaction /\ndisplay",(421,1020)), ([(990,600),(1200,600)],"HTTPS / JSON\nrequest + response",(1002,519)), ([(990,1035),(1200,1035)],"HTTPS / HTML\nadmin session",(1007,955))]:
        d.arrow(pts,both=True,color=GRAY);d.label(*xy,txt,20)
    d.arrow([(1685,670),(1820,670),(1820,370),(2000,370)],both=True,color=GRAY)
    d.label(1740,430,"Financial history /\nprepared features",21)
    d.arrow([(1685,860),(2000,860)],both=True,color=GRAY)
    d.label(1720,770,"Prepared features /\nforecasts, scores\nand recommendations",21)
    d.arrow([(1442,1182),(1442,1445),(2000,1445)],both=True,color=GRAY)
    d.label(1515,1360,"SQL read / write\nquery results",22)
    d.text(1730,1060,"Internal Python modules",21,color=BLUE)
    d.text(1730,1096,"(same backend process)",21)
    d.text(50,1575,"Android mobile client | Render-hosted Flask service | Neon PostgreSQL | Lightweight v1 runtime",23)
    d.finish()


def main():
    data=json.loads((PACK/"source/schema.json").read_text(encoding="utf-8"))
    tables={t["name"]:t for t in data["tables"]}
    assert len(tables)==11 and sum(len(t["columns"]) for t in tables.values())==97
    import layout_revision as revised
    revised.schema(Drawing,tables,PACK,data_table,crow)
    erd(tables);use_case();activity()
    revised.sequence(Drawing,wrapped,text_width)
    class_diagram()
    revised.architecture(Drawing,wrapped,GRAY,BLUE)
    wf_dashboard();wf_entry();wf_forecast();wf_admin()
    revised.wireframes(mobile_shell,button,nav,GRAY)
    (PACK/"source/manifest.json").write_text(json.dumps(MANIFEST,indent=2)+"\n",encoding="utf-8")
    print("Created",len(MANIFEST),"editable SVG figures")


if __name__=="__main__":main()
