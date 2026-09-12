"""September readability revision: explicit relationship routes and larger diagram text."""
import json


def schema(drawing, tables, pack, table, crow):
    d = drawing("01_Database_Schema", 3120, 2320, "DATABASE SCHEMA")
    # Every relationship has its own complete path. No shared ownership bus.
    routes = [
        ("R1", "users.id", "transactions.user_id", [(770,221),(870,221),(870,953),(770,953)], "1", "0..*"),
        ("R2", "users.id", "budgets.user_id", [(770,285),(930,285),(930,1523),(770,1523)], "1", "0..*"),
        ("R3", "users.id", "analysis_runs.user_id", [(770,349),(990,349),(990,253),(1300,253)], "1", "0..*"),
        ("R4", "users.id", "forecasts.user_id", [(770,413),(1050,413),(1050,114),(2210,114),(2210,285),(2350,285)], "1", "0..*"),
        ("R5", "users.id", "anomaly_alerts.user_id", [(770,477),(1110,477),(1110,885),(1300,885)], "1", "0..*"),
        ("R6", "users.id", "recommendations.user_id", [(770,541),(1170,541),(1170,1780),(3070,1780),(3070,1025),(3040,1025)], "1", "0..*"),
        ("R7", "analysis_runs.id", "forecasts.analysis_run_id", [(1990,221),(2100,221),(2100,253),(2350,253)], "1", "0..1"),
        ("R8", "analysis_runs.id", "anomaly_alerts.analysis_run_id", [(1645,429),(1645,610),(1230,610),(1230,853),(1300,853)], "1", "0..*"),
        ("R9", "analysis_runs.id", "recommendations.analysis_run_id", [(1990,350),(2160,350),(2160,993),(2350,993)], "1", "0..*"),
        ("R10", "transactions.id", "anomaly_alerts.transaction_id", [(425,860),(425,810),(1200,810),(1200,917),(1300,917)], "0..1", "0..*"),
    ]
    vertical = []
    horizontal = []
    for rid, parent, child, pts, a, b in routes:
        for p,q in zip(pts,pts[1:]):
            assert p[0] == q[0] or p[1] == q[1]
            (vertical if p[0] == q[0] else horizontal).append((rid,p,q))
    # Draw verticals first, then horizontal arcs jumping over any crossing vertical.
    for rid,p,q in vertical:d.line(*p,*q,sw=2)
    crossings=[]
    for rid,p,q in horizontal:
        left,right=sorted([p[0],q[0]])
        y=p[1]
        hits=sorted(set(vp[0] for vr,vp,vq in vertical if vr!=rid and left<vp[0]<right and min(vp[1],vq[1])<y<max(vp[1],vq[1])))
        commands=[f'M {left} {y}']
        for x in hits:
            commands += [f'L {x-10} {y}', f'Q {x} {y-20} {x+10} {y}']
            crossings.append({"horizontal":rid,"x":x,"y":y})
        commands.append(f'L {right} {y}')
        path=" ".join(commands)
        d.items.append(f'<path d="{path}" fill="none" stroke="white" stroke-width="8"/>')
        d.items.append(f'<path d="{path}" fill="none" stroke="#111111" stroke-width="2"/>')
    for rid,parent,child,pts,a,b in routes:
        crow(d,pts[0],pts[1],a);crow(d,pts[-1],pts[-2],b)
    # Table boxes stay large; the extra width is dedicated connector space.
    table(d,tables["users"],80,160,690,notes=["UQ: email; google_subject; username_normalized"],size=22)
    table(d,tables["analysis_runs"],1300,160,690,size=22)
    table(d,tables["forecasts"],2350,160,690)
    table(d,tables["transactions"],80,860,690,notes=["UQ: (user_id, fingerprint)"])
    table(d,tables["anomaly_alerts"],1300,760,690,size=22)
    table(d,tables["recommendations"],2350,900,690,size=22)
    table(d,tables["budgets"],80,1430,690,notes=["UQ: (user_id, period_start, period_end, category)"])
    # Identical IDs beside both endpoints make each path directly traceable.
    labels = {
        "R1": [(813,190),(813,919)], "R2": [(813,254),(813,1489)],
        "R3": [(813,318),(1245,222)], "R4": [(813,382),(2275,288)],
        "R5": [(813,446),(1245,890)], "R6": [(813,510),(3082,1054)],
        "R7": [(2019,187),(2275,221)], "R8": [(1662,463),(1245,823)],
        "R9": [(2020,318),(2275,959)], "R10": [(439,823),(1237,922)],
    }
    for rid,positions in labels.items():
        for x,y in positions:d.label(x,y,rid,20)
    d.text(1300,1250,"RELATIONSHIP KEY",27,bold=True)
    for i,(rid,parent,child,pts,a,b) in enumerate(routes):
        d.text(1300,1305+i*35,f"{rid}   {parent}  →  {child}",23)
    d.text(1300,1695,"Matching R labels identify one complete relationship.",24)
    d.line(2430,1515,2430,1580,sw=2)
    d.items.append('<path d="M 2370 1550 L 2420 1550 Q 2430 1530 2440 1550 L 2500 1550" fill="none" stroke="white" stroke-width="8"/>')
    d.items.append('<path d="M 2370 1550 L 2420 1550 Q 2430 1530 2440 1550 L 2500 1550" fill="none" stroke="#111111" stroke-width="2"/>')
    d.text(2530,1535,"Crossing only",24)
    d.text(2350,1600,"Bridge = lines cross; no connection.",24)
    d.text(80,1840,"Operational tables (no declared foreign-key relationships)",25)
    for x,name in [(80,"admin_audit"),(850,"model_versions"),(1620,"admin_login_attempts"),(2390,"system_settings")]:
        table(d,tables[name],x,1890,650,notes=["UQ: (component, version)"] if name=="model_versions" else [],size=22,row=32)
    d.text(80,2250,"PK = primary key    FK = foreign key    UQ = unique    ? = nullable    |    Money: NUMERIC(14,2)    Timestamps: UTC",24)
    d.finish()
    (pack/"source/schema_routes.json").write_text(json.dumps({"routes":[{"id":rid,"parent":parent,"child":child,"points":pts,"parent_cardinality":a,"child_cardinality":b} for rid,parent,child,pts,a,b in routes],"bridge_crossings":crossings},indent=2)+"\n")


def sequence(Drawing, wrapped, text_width):
    d=Drawing("05_Sequence_Diagram",2250,2150)
    d.text(1125,38,"SPENDLY - SEQUENCE DIAGRAM",36,anchor="middle")
    d.text(1125,92,"Generate spending insights",30,anchor="middle")
    actors=[(100,"User"),(465,"Mobile interface"),(875,"Flask backend"),(1310,"Feature\npreparation"),(1740,"Model registry"),(2110,"Database")]
    d.actor(100,157,"User",.65)
    for x,name in actors[1:]:
        d.rect(x-137,157,274,92,r=3)
        d.block(x-128,162,256,84,name,30)
    for x,_ in actors:d.line(x,280,x,2070,dash=True)
    for x,y,h in [(465,326,1684),(875,416,1524),(1310,667,104),(1310,1192,98),(1740,915,75),(1740,1377,93),(2110,537,73),(2110,1757,93)]:d.rect(x-8,y,16,h,r=2)
    def msg(a,b,y,label,ret=False):
        d.arrow([(a,y),(b,y)],dash=ret,open_head=ret)
        lines=wrapped(label,30,abs(b-a)-26)
        for i,line in enumerate(lines):d.label((a+b)/2-text_width(line,30)/2,y-(len(lines)-i)*38-10,line,30)
    msg(100,465,335,"1. Request insights")
    msg(465,875,425,"2. POST /analysis/run + JWT")
    msg(875,2110,545,"3. Read access state, transactions and budgets")
    msg(2110,875,610,"4. Return user-owned data and access state",True)
    msg(875,1310,675,"5. Build weekly features")
    msg(1310,875,770,"6. History + budget context",True)
    d.rect(720,815,1190,310,fill=None,sw=1.5)
    d.rect(720,815,70,44);d.text(733,822,"alt",28)
    d.label(930,827,"[8 or more history weeks]",28)
    msg(875,1740,925,"7a. Forecast with linear regression")
    msg(1740,875,990,"8a. Return spending estimate",True)
    d.line(720,1020,1910,1020,dash=True)
    d.label(930,1033,"[fewer than 8 history weeks]",28)
    d.arrow([(883,1075),(990,1075),(990,1110),(883,1110)])
    d.label(1035,1079,"7b. Use weekly-average baseline",28)
    msg(875,1310,1200,"9. Build expense features")
    msg(1310,875,1290,"10. Return expense features",True)
    msg(875,1740,1385,"11. Score with Isolation Forest")
    msg(1740,875,1470,"12. Return alerts and explanations",True)
    d.arrow([(883,1570),(980,1570),(980,1630),(883,1630)])
    d.label(1010,1570,"13. Apply recommendation rules\nto forecast, budgets and alerts",30)
    msg(875,2110,1765,"14. Store run, forecast, alerts and recommendations")
    msg(2110,875,1850,"15. Confirm database commit",True)
    msg(875,465,1930,"16. Return results",True)
    msg(465,100,2010,"17. Display insights",True)
    d.finish()


def architecture(Drawing, wrapped, GRAY, BLUE):
    d=Drawing("07_System_Architecture",2650,1660)
    d.text(1325,44,"SPENDLY - SYSTEM ARCHITECTURE",38,anchor="middle")
    def box(x,y,w,h,title,body,logos=(),icon=None):
        d.rect(x,y,w,h,r=12,stroke=GRAY,sw=1.7)
        if logos:
            step=(w-60)/len(logos)
            for i,fn in enumerate(logos):d.image(fn,x+30+i*step,y+23,step-15,115)
        elif icon=="user":
            d.ellipse(x+w/2,y+52,26,29,BLUE,BLUE)
            d.rect(x+w/2-46,y+93,92,49,r=22,fill=BLUE,stroke=BLUE)
        elif icon=="browser":
            d.rect(x+w/2-65,y+24,130,108,r=5,stroke=BLUE,sw=3)
            d.line(x+w/2-65,y+45,x+w/2+65,y+45,color=BLUE,sw=3)
            d.ellipse(x+w/2,y+91,28,28,stroke=BLUE,sw=3)
        elif icon=="features":
            for j in range(3):d.rect(x+w/2-55,y+32+j*27,110,18,r=3,stroke=BLUE,sw=2)
        d.block(x+20,y+154,w-40,102,title,38,color=BLUE)
        d.line(x+25,y+270,x+w-25,y+270,color=BLUE,sw=1.2)
        rows=[]
        for line in body:rows+=wrapped("• "+line,32,w-52)
        assert 292+len(rows)*44 <= h-12, (title,rows,h)
        for i,line in enumerate(rows):d.text(x+26,y+292+i*44,line,32,max_width=w-52)
    box(45,210,365,430,"GENERAL USER",["Track spending","View insights"],icon="user")
    box(45,855,365,450,"ADMINISTRATOR",["Manage users","Control system"],icon="user")
    box(570,210,420,490,"FLUTTER\nMOBILE APP",["Transactions","Budgets","Forecasts and alerts"],logos=["flutter.svg"])
    box(570,880,420,445,"WEB ADMIN\nCONSOLE",["Manage records","Review activity"],icon="browser")
    box(1200,530,485,535,"FLASK BACKEND\nREST API",["Authenticate users","Run spending analysis","Store / retrieve data"],logos=["python.svg","flask.svg"])
    box(2000,160,600,430,"FEATURE\nPREPARATION",["Weekly spending history","Expense and budget features"],icon="features")
    box(2000,650,600,460,"SPENDING ANALYSIS",["Linear regression / baseline","Isolation Forest alerts","Rule-based guidance"],logos=["scikit-learn.svg"])
    box(2000,1175,600,430,"POSTGRESQL",["Accounts and financial data","Analysis results and audit"],logos=["postgresql.png"])
    for pts,txt,xy in [([(410,428),(570,428)],"Uses",(455,382)), ([(410,1100),(570,1100)],"Uses",(455,1054)), ([(990,600),(1200,600)],"HTTPS / JSON",(1000,547)), ([(990,1035),(1200,1035)],"HTTPS / HTML",(997,980))]:
        d.arrow(pts,both=True,color=GRAY);d.label(*xy,txt,28)
    d.arrow([(1685,670),(1820,670),(1820,370),(2000,370)],both=True,color=GRAY)
    d.label(1740,440,"History /\nfeatures",30)
    d.arrow([(1685,860),(2000,860)],both=True,color=GRAY)
    d.label(1720,764,"Features /\nresults",30)
    d.arrow([(1442,1065),(1442,1445),(2000,1445)],both=True,color=GRAY)
    d.label(1535,1370,"SQL read / write",30)
    d.text(1720,984,"Python modules",28,color=BLUE)
    d.text(1720,1028,"inside backend",28)
    d.text(50,1575,"Android app  |  Render backend  |  Neon PostgreSQL  |  Lightweight v1",30)
    d.finish()


def wireframes(mobile_shell, button, nav, GRAY):
    d=mobile_shell("12_Wireframe_Budgets","Budgets",1250)
    button(d,50,245,400,58,"+ Add budget")
    button(d,473,245,238,58,"Refresh")
    for y,category in [(343,"Total budget"),(708,"[Category] budget")]:
        d.rect(50,y,661,330,r=4,stroke=GRAY,sw=1.2)
        d.text(73,y+20,category,27)
        d.text(73,y+65,"[Period start] - [Period end]",22)
        d.text(73,y+110,"[XX%] used",24)
        d.text(73,y+153,"KES [spent] of KES [limit]",23)
        d.rect(73,y+197,612,21,stroke=GRAY,sw=1.2)
        d.text(73,y+245,"Budget left: KES [amount]",22)
        d.text(73,y+283,"Available to spend: KES [amount]",22)
        d.text(684,y+24,"...",27,anchor="end")
    d.text(50,1077,"Tap a budget to edit. Menu: Edit / Delete.",22)
    nav(d,1141);d.finish()

    d=mobile_shell("13_Wireframe_Spending_Check","Spending Check",1250)
    d.rect(50,250,661,159,r=4,stroke=GRAY,sw=1.2)
    d.text(73,272,"[X] items are worth a look",27)
    d.text(73,321,"These entries differ from your recent pattern.",22)
    d.text(73,365,"An unusual entry does not mean fraud.",22)
    for y,index in [(450,1),(751,2)]:
        d.rect(50,y,661,260,r=4,stroke=GRAY,sw=1.2)
        d.text(73,y+22,f"Check {index}",26)
        d.text(73,y+76,"[Explanation of unusual spending]",24)
        d.text(73,y+130,"Compare with your receipt or transaction history.",21)
        d.text(73,y+182,"If the entry is correct, no action is needed.",22)
    button(d,50,1120,188,61,"Back");d.finish()
