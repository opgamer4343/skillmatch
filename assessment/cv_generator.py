"""
SkillMatch CV Generator v5
- 3 completely different themes: Executive Dark, Clean Minimal, Bold Gradient
- Theme selected RANDOMLY each time CV is generated
- All data from real DB (StudentProfile + AssessmentAttempt)
- Gemini AI enriches content; graceful fallback to DB data
- No SkillMatch Score section
"""
import json, logging, math, os, random
from pathlib import Path
from typing import Any, Dict, List

from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from google import genai
except Exception:
    genai = None

DEFAULT_MODEL = getattr(settings, "GOOGLE_GENAI_MODEL", "gemini-2.0-flash")


# ── Gemini ─────────────────────────────────────────────────────────────────────

def _get_client():
    key = (getattr(settings, "GEMINI_API_KEY", None)
           or getattr(settings, "GOOGLE_API_KEY", None)
           or os.getenv("GEMINI_API_KEY")
           or os.getenv("GOOGLE_API_KEY"))
    if not genai or not key:
        return None
    try:
        return genai.Client(api_key=key)
    except Exception:
        logger.exception("Gemini init failed")
        return None


def _parse_json(text: str) -> Dict:
    text = (text or "").strip()
    for attempt in [text] + [b.replace("json", "", 1).strip()
                               for b in text.split("```") if b.strip()]:
        try:
            return json.loads(attempt)
        except Exception:
            pass
    s = text.find("{")
    if s >= 0:
        for e in range(len(text), s, -1):
            try:
                return json.loads(text[s:e])
            except Exception:
                pass
    raise ValueError("No JSON found")


# ── Content generation from DB ─────────────────────────────────────────────────

def generate_cv_content(student_profile, assessment_attempt) -> Dict[str, Any]:
    user     = getattr(student_profile, "user", None)
    skills   = list(getattr(student_profile, "skills", []) or [])
    score    = float(getattr(assessment_attempt, "overall_score", 0) or 0)
    band     = str(getattr(assessment_attempt, "score_band", "") or "")
    name     = (getattr(user, "get_full_name", lambda: "")() or "").strip()
    email    = getattr(user, "email", "") or ""
    city     = getattr(student_profile, "city", "") or ""
    univ     = getattr(student_profile, "university", "") or ""
    deg      = getattr(student_profile, "degree", "") or ""
    major    = getattr(student_profile, "major", "") or ""
    year     = str(getattr(student_profile, "graduation_year", "") or "")
    bio      = getattr(student_profile, "bio", "") or ""
    linkedin = getattr(student_profile, "linkedin_url", "") or ""

    start_year = str(int(year) - 4) if year.isdigit() else "20XX"
    base = {
        "name":     name,
        "email":    email,
        "phone":    "",
        "city":     city,
        "linkedin": linkedin,
        "github":   "",
        "headline": f"{deg} Student | {' · '.join(skills[:3])}",
        "summary":  bio or (
            f"Motivated {deg} student at {univ} specialising in {major}. "
            f"Skilled in {', '.join(skills[:4]) if skills else 'software development'}. "
            f"Seeking an internship to apply technical skills and deliver real-world impact."
        ),
        "education": {
            "institution": univ,
            "degree":      deg,
            "major":       major,
            "period":      f"Aug {start_year} – May {year}",
            "gpa":         "",
        },
        "skills":         _categorise_skills(skills),
        "projects":       [],
        "certifications": [],
        "score":          score,
        "band":           band,
    }

    client = _get_client()
    if not client:
        return base

    prompt = f"""You are a professional CV writer for Indian college students.
Enhance this student's CV with realistic, ATS-optimised content. Return ONLY valid JSON.

STUDENT DATA:
- Name: {name}
- Degree: {deg} in {major} at {univ}
- Skills: {', '.join(skills)}
- Bio: {bio}
- Graduation: {year}
- SkillMatch Score: {score:.0f}/100 ({band} band)

REQUIREMENTS:
1. Write a 3-sentence professional summary. Mention the score in sentence 3.
2. Create 2-3 realistic student projects tailored to the skills. Every bullet must include a number or metric.
3. Headline max 12 words: "Role | Skill1 · Skill2 · Skill3"
4. Add 4 real certifications (Coursera/Udemy/Google/AWS) relevant to the skills.
5. Split skills into: technical, frameworks, tools, soft.
6. Add a plausible phone number and github username.

Return JSON matching this shape EXACTLY (no extra keys, no markdown):
{{
  "phone": "+91 XXXXX XXXXX",
  "github": "github.com/username",
  "headline": "...",
  "summary": "...",
  "skills": {{"technical":[],"frameworks":[],"tools":[],"soft":[]}},
  "projects": [
    {{
      "name": "...",
      "period": "Mon YYYY – Mon YYYY",
      "stack": ["Tech1","Tech2"],
      "impact": "Metric1  ·  Metric2  ·  Metric3",
      "bullets": ["Action + what + number","Action + what + metric","Action + what + outcome"]
    }}
  ],
  "certifications": [{{"name":"...","issuer":"...","year":"20XX"}}]
}}"""

    try:
        resp = client.models.generate_content(model=DEFAULT_MODEL, contents=prompt)
        data = _parse_json(getattr(resp, "text", "") or "")
        if isinstance(data, dict):
            for k in ("phone","github","headline","summary","skills","projects","certifications"):
                if data.get(k):
                    base[k] = data[k]
        return base
    except Exception:
        logger.exception("Gemini enrichment failed; using DB data only")
        return base


def _categorise_skills(skills: List[str]) -> Dict[str, List[str]]:
    FWK  = {"django","react","flask","fastapi","vue","angular","spring","laravel",
             "pandas","numpy","tensorflow","pytorch","scikit-learn","drf","express","next"}
    TOOL = {"git","docker","postgresql","mysql","mongodb","redis","figma","postman",
             "kubernetes","aws","gcp","azure","linux","jenkins","grafana","jira","notion"}
    SOFT = {"communication","teamwork","leadership","problem solving","agile","scrum",
             "time management","critical thinking","analytical","presentation"}
    tech, fwk, tools, soft = [], [], [], []
    for s in skills:
        sl = s.lower().replace(".", "").replace("-", " ").replace("_", " ")
        if sl in SOFT or any(w in sl for w in ["comm","lead","team","agile","scrum","present"]):
            soft.append(s)
        elif sl in TOOL or any(w in sl for w in ["git","docker","sql","cloud","linux","aws","gcp","figma"]):
            tools.append(s)
        elif sl in FWK or any(w in sl for w in ["react","django","flask","pandas","vue","next","express"]):
            fwk.append(s)
        else:
            tech.append(s)
    return {"technical": tech[:6], "frameworks": fwk[:5], "tools": tools[:5], "soft": soft[:4]}


# ══════════════════════════════════════════════════════════════════════════════
# PDF RENDERER — 3 THEMES
# ══════════════════════════════════════════════════════════════════════════════

def generate_cv_pdf(cv: Dict[str, Any], output_path: str) -> str:
    """Render professional PDF. Theme chosen randomly each call."""
    theme_fn = random.choice([_render_theme1, _render_theme2, _render_theme3])
    from reportlab.lib.pagesizes import A4
    W, H = A4
    out  = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    theme_fn(cv, str(out), W, H)
    return str(out)


# ── Shared drawing utils (injected per theme) ──────────────────────────────────

def _make_utils(c, W, H):
    from reportlab.lib import colors
    def C(h): return colors.HexColor(h)
    def sw(s, f, z): return c.stringWidth(str(s), f, z)
    def t(x, y, s, f="Helvetica", z=9, col=colors.white, a="left"):
        c.setFillColor(col); c.setFont(f, z)
        {"right": c.drawRightString, "center": c.drawCentredString
         }.get(a, c.drawString)(x, y, str(s))
    def wraps(s, f, z, mw):
        words = str(s).split(); lines, cur = [], []
        for w in words:
            if sw(" ".join(cur + [w]), f, z) <= mw: cur.append(w)
            else:
                if cur: lines.append(" ".join(cur))
                cur = [w]
        if cur: lines.append(" ".join(cur))
        return lines or [""]
    def par(x, y, s, f="Helvetica", z=9, col=colors.white, mw=150, lh=13):
        for line in wraps(s, f, z, mw):
            t(x, y, line, f, z, col); y -= lh
        return y
    def hline(x1, y, x2, col, thick=0.8):
        c.setStrokeColor(col); c.setLineWidth(thick); c.line(x1, y, x2, y)
    return C, sw, t, par, hline, wraps


# ══════════════════════════════════════════════════════════════════════════════
# THEME 1 — EXECUTIVE DARK
# Full dark bg · gold accents · two-column sidebar
# ══════════════════════════════════════════════════════════════════════════════

def _render_theme1(cv, out_path, W, H):
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors

    c = canvas.Canvas(out_path, pagesize=(W, H))
    c.setTitle(cv.get("name","") + " — CV"); c.setAuthor("SkillMatch AI")
    C, sw, t, par, hline, wraps = _make_utils(c, W, H)

    BG    = C("#0a0a0a"); CARD  = C("#111111"); CARD2 = C("#1a1a1a")
    GOLD  = C("#d4a017"); GOLDL = C("#f0c040"); WHITE = colors.white
    GRAY  = C("#888888"); LGRAY = C("#cccccc"); BORDER= C("#2a2a2a")
    GREEN = C("#22c55e")

    # Full dark background
    c.setFillColor(BG); c.rect(0, 0, W, H, fill=1, stroke=0)

    # Gold left header stripe + header card
    c.setFillColor(GOLD);  c.rect(0, H-82, 5, 82, fill=1, stroke=0)
    c.setFillColor(CARD);  c.rect(5, H-82, W-5, 82, fill=1, stroke=0)
    hline(5, H-82, W, GOLD, 1.5)

    # Header content
    t(24, H-32, cv.get("name",""),     "Helvetica-Bold", 24, WHITE)
    t(24, H-52, cv.get("headline",""), "Helvetica",       9.5, GOLDL)
    contact = "   |   ".join(x for x in [cv.get("email",""),cv.get("phone",""),cv.get("city","")] if x)
    t(24, H-67, contact, "Helvetica", 8, GRAY)
    if cv.get("linkedin"):
        t(W-22, H-50, cv["linkedin"].replace("https://","")[:30], "Helvetica",8,GRAY,a="right")
    if cv.get("github"):
        t(W-22, H-62, cv["github"].replace("https://","")[:30],   "Helvetica",8,GRAY,a="right")

    LW = 178; RX = LW+22; RW = W-RX-16

    def lsec(y, title):
        t(8, y, title.upper(), "Helvetica-Bold", 7.5, GOLD)
        y -= 5; hline(8, y, LW-8, GOLD, 0.8)
        return y - 10

    def rsec(y, title):
        t(RX, y, title.upper(), "Helvetica-Bold", 8.5, GOLD)
        y -= 6; hline(RX, y, W-16, GOLD, 1.2)
        hline(RX, y-1, W-16, C("#332200"), 0.5)
        return y - 11

    def tag(x, y, label, bg=CARD2, fg=GOLDL):
        f, z = "Helvetica", 7.5; pw = sw(label, f, z)+10
        c.setFillColor(bg); c.roundRect(x, y-1, pw, 12, 2, fill=1, stroke=0)
        c.setStrokeColor(C("#333300")); c.setLineWidth(0.4)
        c.roundRect(x, y-1, pw, 12, 2, fill=0, stroke=1)
        c.setFillColor(fg); c.setFont(f, z); c.drawString(x+5, y+2, label)
        return pw+5

    sy = H-98
    # Avatar
    c.setFillColor(CARD2); c.circle(LW/2, sy-26, 30, fill=1, stroke=0)
    c.setStrokeColor(GOLD); c.setLineWidth(2); c.circle(LW/2, sy-26, 30, fill=0, stroke=1)
    initials = "".join(w[0].upper() for w in cv.get("name","??").split()[:2])
    t(LW/2, sy-35, initials, "Helvetica-Bold", 20, GOLD, "center")
    sy -= 68

    sy = lsec(sy, "Contact")
    for icon, val in [("✉",cv.get("email","")),("✆",cv.get("phone","")),("⌖",cv.get("city",""))]:
        if not val: continue
        t(8, sy, icon, "Helvetica-Bold", 8, GOLD)
        t(22, sy, val[:24], "Helvetica", 8, LGRAY); sy -= 13
    sy -= 6

    edu = cv.get("education", {})
    if edu:
        sy = lsec(sy, "Education")
        t(8, sy, str(edu.get("institution",""))[:22], "Helvetica-Bold", 9.5, WHITE); sy -= 12
        sy = par(8, sy, edu.get("degree",""),  "Helvetica", 8,  LGRAY, mw=LW-16, lh=11)
        sy = par(8, sy, edu.get("major",""),   "Helvetica", 7.5,GRAY,  mw=LW-16, lh=11)
        sy -= 4
        if edu.get("period"):
            t(8, sy, edu["period"], "Helvetica", 8, GOLD); sy -= 11
        if edu.get("gpa"):
            t(8, sy, "GPA: "+str(edu["gpa"]), "Helvetica-Bold", 8.5, WHITE); sy -= 13
        sy -= 6

    skills_d = cv.get("skills", {})
    if isinstance(skills_d, list): skills_d = {"technical": skills_d}
    if skills_d:
        sy = lsec(sy, "Skills")
        palettes = [CARD2, C("#1a1500"), C("#0c1520"), C("#1c1020")]
        for idx, (key, items) in enumerate(skills_d.items()):
            if not items: continue
            t(8, sy, key.title(), "Helvetica-Bold", 7, GRAY); sy -= 11
            px = 8
            for sk in items:
                pw = sw(sk,"Helvetica",7.5)+10
                if px+pw > LW-8: px=8; sy-=15
                tag(px, sy, sk, palettes[idx % len(palettes)], GOLDL); px += pw+3
            sy -= 17

    ry = H-98
    ry = rsec(ry, "Professional Summary")
    ry = par(RX, ry, cv.get("summary",""), "Helvetica", 8.5, LGRAY, mw=RW, lh=12.5)
    ry -= 14

    if cv.get("projects"):
        ry = rsec(ry, "Projects")
        for proj in cv["projects"]:
            if ry < 115: break
            buls = proj.get("bullets", proj.get("highlights",[]))
            ch   = 15+14+14+len(buls)*12+12
            c.setFillColor(CARD); c.roundRect(RX-4,ry-ch+10,RW+8,ch,4,fill=1,stroke=0)
            c.setStrokeColor(BORDER); c.setLineWidth(0.6)
            c.roundRect(RX-4,ry-ch+10,RW+8,ch,4,fill=0,stroke=1)
            c.setFillColor(GOLD); c.rect(RX-4,ry-ch+10,3,ch,fill=1,stroke=0)

            t(RX+3, ry, str(proj.get("name",""))[:62], "Helvetica-Bold", 10, WHITE)
            t(W-16, ry, str(proj.get("period","")), "Helvetica", 7.5, GRAY, a="right"); ry -= 15
            px = RX+3
            for tk in proj.get("stack",[]):
                pw = sw(tk,"Helvetica",7.5)+10
                if px+pw > W-18: px=RX+3; ry-=13
                tag(px,ry,tk,C("#1a1500"),GOLDL); px+=pw+4
            ry -= 14
            impact = proj.get("impact","")
            if impact:
                t(RX+3, ry, "►  "+impact[:74], "Helvetica",7.5,GOLD); ry -= 13
            for pt in buls:
                c.setFillColor(GOLD); c.circle(RX+7,ry+3.5,2,fill=1,stroke=0)
                ry = par(RX+14,ry,str(pt),"Helvetica",8,LGRAY,mw=RW-14,lh=11.5)
            ry -= 11

    if cv.get("certifications") and ry > 100:
        ry = rsec(ry, "Certifications")
        for i, cert in enumerate(cv["certifications"]):
            if ry < 48: break
            c.setFillColor(CARD2); c.roundRect(RX-4,ry-4,RW+8,24,3,fill=1,stroke=0)
            c.setFillColor(GREEN);  c.circle(RX+6,ry+8,5,fill=1,stroke=0)
            t(RX+6,ry+4.5,"✓","Helvetica-Bold",7,WHITE,"center")
            t(RX+15,ry+10,cert.get("name","")[:58],"Helvetica-Bold",9,WHITE)
            t(RX+15,ry+1,f'{cert.get("issuer","")} · {cert.get("year","")}',
              "Helvetica",7.5,GRAY); ry -= 26

    hline(0,18,W,GOLD,0.8)
    t(W/2,7,"Generated by SkillMatch AI  ·  SkillMatch Platform","Helvetica",6.5,GRAY,a="center")
    c.save()


# ══════════════════════════════════════════════════════════════════════════════
# THEME 2 — CLEAN MINIMAL WHITE
# Pure white bg · teal + coral · soft chip pills
# ══════════════════════════════════════════════════════════════════════════════

def _render_theme2(cv, out_path, W, H):
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors

    c = canvas.Canvas(out_path, pagesize=(W, H))
    c.setTitle(cv.get("name","") + " — CV"); c.setAuthor("SkillMatch AI")
    C, sw, t, par, hline, wraps = _make_utils(c, W, H)

    WHITE = colors.white;  BG    = C("#fafafa")
    TEAL  = C("#0d9488");  TEALL = C("#ccfbf1"); TEALD = C("#0f766e")
    CORAL = C("#f97316");  S900  = C("#111827"); S600  = C("#4b5563")
    S400  = C("#9ca3af");  S100  = C("#f3f4f6"); BORD  = C("#e5e7eb")
    GREEN = C("#059669")

    c.setFillColor(BG); c.rect(0,0,W,H,fill=1,stroke=0)
    # Top accent stripes
    c.setFillColor(TEAL);  c.rect(0,H-8,W,8,fill=1,stroke=0)
    c.setFillColor(CORAL); c.rect(0,H-13,W,5,fill=1,stroke=0)
    # White header card
    c.setFillColor(WHITE); c.rect(0,H-92,W,79,fill=1,stroke=0)
    hline(0,H-92,W,BORD,0.8)
    # Left accent bar
    c.setFillColor(TEAL); c.rect(26,H-78,4,50,fill=1,stroke=0)
    t(36,H-44,cv.get("name",""),     "Helvetica-Bold",22,S900)
    t(36,H-60,cv.get("headline",""),"Helvetica",9,TEALD)
    # Contact pills in header
    px0 = 36
    for val in [cv.get("email",""),cv.get("phone",""),cv.get("city","")]:
        if not val: continue
        pw = sw(val,"Helvetica",7.5)+12
        if px0+pw > W-100: break
        c.setFillColor(TEALL); c.roundRect(px0,H-78,pw,13,3,fill=1,stroke=0)
        c.setFillColor(TEALD); c.setFont("Helvetica",7.5); c.drawString(px0+6,H-74,val[:26])
        px0 += pw+6

    LW=188; RX=LW+20; RW=W-RX-20
    sy=H-108; ry=H-108

    def lsec(y,title):
        c.setFillColor(TEAL); c.roundRect(8,y+1,3,10,1,fill=1,stroke=0)
        t(14,y,title.upper(),"Helvetica-Bold",7.5,TEAL)
        y-=5; hline(8,y,LW-8,BORD,0.8)
        return y-10

    def rsec(y,title):
        t(RX,y,title.upper(),"Helvetica-Bold",9.5,TEAL)
        y-=6; hline(RX,y,W-20,TEAL,1.5)
        return y-10

    def chip(x,y,label,bg=TEALL,fg=TEALD):
        f,z="Helvetica-Bold",7.5; pw=sw(label,f,z)+12
        c.setFillColor(bg); c.roundRect(x,y-1,pw,13,4,fill=1,stroke=0)
        c.setFillColor(fg); c.setFont(f,z); c.drawString(x+6,y+2.5,label)
        return pw+5

    def rpill(x,y,label):
        f,z="Helvetica",7.5; pw=sw(label,f,z)+10
        c.setFillColor(S100); c.roundRect(x,y-1.5,pw,12,3,fill=1,stroke=0)
        c.setStrokeColor(BORD); c.setLineWidth(0.4)
        c.roundRect(x,y-1.5,pw,12,3,fill=0,stroke=1)
        c.setFillColor(S600); c.setFont(f,z); c.drawString(x+5,y+2,label)
        return pw+4

    sy = lsec(sy,"Contact")
    for icon,val in [("✉",cv.get("email","")),("✆",cv.get("phone","")),
                     ("⌖",cv.get("city","")),
                     ("in",cv.get("linkedin","").replace("https://","")[:24]),
                     ("⌥",cv.get("github","").replace("https://","")[:24])]:
        if not val: continue
        c.setFillColor(TEALL); c.circle(13,sy+4,5,fill=1,stroke=0)
        t(13,sy+0.5,icon,"Helvetica-Bold",6,TEALD,"center")
        t(22,sy+1,val[:24],"Helvetica",8,S600); sy-=14
    sy-=6

    edu=cv.get("education",{})
    if edu:
        sy=lsec(sy,"Education")
        t(8,sy,str(edu.get("institution",""))[:23],"Helvetica-Bold",10,S900); sy-=12
        sy=par(8,sy,edu.get("degree",""),"Helvetica",8.5,S600,mw=LW-16,lh=11)
        sy=par(8,sy,edu.get("major",""), "Helvetica",8,  S400,mw=LW-16,lh=11); sy-=5
        if edu.get("period"):
            chip(8,sy,edu["period"],TEALL,TEALD); sy-=16
        if edu.get("gpa"):
            t(8,sy,"GPA:","Helvetica-Bold",8.5,S600)
            t(36,sy,str(edu["gpa"]),"Helvetica-Bold",8.5,S900); sy-=13
        sy-=6

    skills_d=cv.get("skills",{})
    if isinstance(skills_d,list): skills_d={"technical":skills_d}
    SCFG=[("technical",TEALL,TEALD),("frameworks",C("#ede9fe"),C("#5b21b6")),
          ("tools",C("#fef3c7"),C("#92400e")),("soft",C("#fce7f3"),C("#9d174d"))]
    if skills_d:
        sy=lsec(sy,"Skills")
        for key,bg,fg in SCFG:
            items=skills_d.get(key,[])
            if not items: continue
            t(8,sy,key.title(),"Helvetica-Bold",7,S400); sy-=11
            px=8
            for sk in items:
                pw=sw(sk,"Helvetica-Bold",7.5)+12
                if px+pw>LW-8: px=8; sy-=15
                chip(px,sy,sk,bg,fg); px+=pw+4
            sy-=16

    ry=rsec(ry,"Professional Summary")
    ry=par(RX,ry,cv.get("summary",""),"Helvetica",8.5,S600,mw=RW,lh=12.5); ry-=14

    if cv.get("projects"):
        ry=rsec(ry,"Projects")
        for proj in cv["projects"]:
            if ry<115: break
            buls=proj.get("bullets",proj.get("highlights",[]))
            ch=16+14+15+len(buls)*12+12
            c.setFillColor(WHITE); c.roundRect(RX-4,ry-ch+10,RW+8,ch,5,fill=1,stroke=0)
            c.setStrokeColor(BORD); c.setLineWidth(0.8)
            c.roundRect(RX-4,ry-ch+10,RW+8,ch,5,fill=0,stroke=1)
            c.setFillColor(TEAL); c.roundRect(RX-4,ry-ch+10,3,ch,2,fill=1,stroke=0)

            t(RX+3,ry,str(proj.get("name",""))[:62],"Helvetica-Bold",10,S900)
            t(W-20,ry,str(proj.get("period","")),"Helvetica",7.5,S400,a="right"); ry-=16
            px=RX+3
            for tk in proj.get("stack",[]):
                pw=sw(tk,"Helvetica",7.5)+10
                if px+pw>W-22: px=RX+3; ry-=14
                rpill(px,ry,tk); px+=pw+4
            ry-=15
            impact=proj.get("impact","")
            if impact:
                c.setFillColor(TEALL); c.roundRect(RX+3,ry-3,RW-6,14,3,fill=1,stroke=0)
                t(RX+8,ry+2,"⚡  "+impact[:74],"Helvetica",7.5,TEALD); ry-=15
            for pt in buls:
                c.setFillColor(CORAL); c.circle(RX+7,ry+3.5,2.5,fill=1,stroke=0)
                ry=par(RX+15,ry,str(pt),"Helvetica",8.5,S600,mw=RW-15,lh=11.5)
            ry-=12

    if cv.get("certifications") and ry>100:
        ry=rsec(ry,"Certifications & Courses")
        for i,cert in enumerate(cv["certifications"]):
            if ry<48: break
            if i%2==0: c.setFillColor(S100); c.roundRect(RX-4,ry-4,RW+8,26,3,fill=1,stroke=0)
            c.setFillColor(GREEN); c.circle(RX+6,ry+8,5.5,fill=1,stroke=0)
            t(RX+6,ry+4.5,"✓","Helvetica-Bold",7,colors.white,"center")
            t(RX+16,ry+11,cert.get("name","")[:60],"Helvetica-Bold",9,S900)
            t(RX+16,ry+1,f'{cert.get("issuer","")} · {cert.get("year","")}',
              "Helvetica",7.5,S400); ry-=27

    c.setFillColor(TEAL); c.rect(0,0,W,20,fill=1,stroke=0)
    t(W/2,7,"Generated by SkillMatch AI CV Generator","Helvetica",6.5,colors.white,a="center")
    c.save()


# ══════════════════════════════════════════════════════════════════════════════
# THEME 3 — BOLD GRADIENT
# Rose→Indigo gradient header · full-width cards · warm accent
# ══════════════════════════════════════════════════════════════════════════════

def _render_theme3(cv, out_path, W, H):
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors

    c = canvas.Canvas(out_path, pagesize=(W, H))
    c.setTitle(cv.get("name","") + " — CV"); c.setAuthor("SkillMatch AI")
    C, sw, t, par, hline, wraps = _make_utils(c, W, H)

    WHITE = colors.white; BG   = C("#f9fafb")
    ROSE  = C("#e11d48"); ROSE2= C("#fb7185"); ROSEL= C("#fff1f2")
    IND   = C("#4338ca"); INDL = C("#eef2ff")
    S900  = C("#111827"); S700 = C("#374151"); S500 = C("#6b7280")
    S200  = C("#e5e7eb"); S100 = C("#f3f4f6")
    GREEN = C("#059669")

    c.setFillColor(BG); c.rect(0,0,W,H,fill=1,stroke=0)

    # Gradient header rose→indigo
    HEADER_H = 108
    steps = 60
    for i in range(steps):
        tr = i/steps
        r=int(0xe1+(0x43-0xe1)*tr); g=int(0x1d+(0x38-0x1d)*tr); b=int(0x48+(0xca-0x48)*tr)
        c.setFillColorRGB(r/255,g/255,b/255)
        c.rect(i*(W/steps),H-HEADER_H,W/steps+1,HEADER_H,fill=1,stroke=0)
    # Rounded white bottom of header
    c.setFillColor(BG); c.roundRect(-10,H-HEADER_H-12,W+20,30,16,fill=1,stroke=0)

    t(28,H-42,cv.get("name",""),     "Helvetica-Bold",22,WHITE)
    t(28,H-60,cv.get("headline","")[:60],"Helvetica",9,C("#fda4af"))
    cx0=28
    for icon,val in [("✉",cv.get("email","")),("✆",cv.get("phone","")),("⌖",cv.get("city",""))]:
        if not val: continue
        label=icon+"  "+val[:22]
        t(cx0,H-76,label,"Helvetica",7.5,C("#fecdd3")); cx0+=sw(label,"Helvetica",7.5)+16
    if cv.get("linkedin"):
        t(W-22,H-60,cv["linkedin"].replace("https://","")[:26],"Helvetica",7.5,C("#fecdd3"),a="right")
    if cv.get("github"):
        t(W-22,H-72,cv["github"].replace("https://","")[:26],  "Helvetica",7.5,C("#fecdd3"),a="right")

    # Avatar circle
    AX,AY=W-65,H-62
    c.setFillColor(WHITE); c.circle(AX,AY,28,fill=1,stroke=0)
    c.setFillColor(ROSE);  c.circle(AX,AY,23,fill=1,stroke=0)
    initials="".join(w[0].upper() for w in cv.get("name","??").split()[:2])
    t(AX,AY-8,initials,"Helvetica-Bold",20,WHITE,"center")

    PAD=24; CW=(W-PAD*3)/2
    ry=H-HEADER_H-22

    def sec(y,title,x=None,width=None):
        x=x or PAD; width=width or W-PAD*2
        c.setFillColor(ROSE); c.roundRect(x,y+1,4,14,2,fill=1,stroke=0)
        t(x+8,y,title.upper(),"Helvetica-Bold",9.5,S900)
        y-=7; hline(x,y,x+width,S200,1.2)
        return y-11

    def pill(x,y,label,bg=INDL,fg=IND):
        f,z="Helvetica-Bold",7.5; pw=sw(label,f,z)+12
        c.setFillColor(bg); c.roundRect(x,y-1.5,pw,13,4,fill=1,stroke=0)
        c.setFillColor(fg); c.setFont(f,z); c.drawString(x+6,y+2,label)
        return pw+5

    def tpill(x,y,label):
        f,z="Helvetica",7.5; pw=sw(label,f,z)+10
        c.setFillColor(S100); c.roundRect(x,y-1.5,pw,12,3,fill=1,stroke=0)
        c.setStrokeColor(S200); c.setLineWidth(0.4)
        c.roundRect(x,y-1.5,pw,12,3,fill=0,stroke=1)
        c.setFillColor(IND); c.setFont(f,z); c.drawString(x+5,y+1.5,label)
        return pw+4

    # Summary
    ry=sec(ry,"Professional Summary",width=W-PAD*2)
    ry=par(PAD,ry,cv.get("summary",""),"Helvetica",8.5,S700,mw=W-PAD*2,lh=12.5); ry-=14

    # Skills + Education side by side
    skills_d=cv.get("skills",{})
    if isinstance(skills_d,list): skills_d={"technical":skills_d}
    edu=cv.get("education",{})

    c1y=sec(ry,"Skills",PAD,CW)
    SCFG=[("technical",INDL,IND),("frameworks",ROSEL,ROSE),
          ("tools",C("#f0fdf4"),C("#166534")),("soft",C("#fefce8"),C("#854d0e"))]
    if skills_d:
        for key,bg,fg in SCFG:
            items=skills_d.get(key,[])
            if not items: continue
            t(PAD,c1y,key.title(),"Helvetica-Bold",7.5,S500); c1y-=12
            px=PAD
            for sk in items:
                pw=sw(sk,"Helvetica-Bold",7.5)+12
                if px+pw>PAD+CW-4: px=PAD; c1y-=16
                pill(px,c1y,sk,bg,fg); px+=pw+4
            c1y-=17

    cx2=PAD+CW+PAD
    c2y=sec(ry,"Education",cx2,CW)
    if edu:
        t(cx2,c2y,str(edu.get("institution",""))[:22],"Helvetica-Bold",10,S900); c2y-=13
        c2y=par(cx2,c2y,edu.get("degree",""),"Helvetica",8.5,S700,mw=CW,lh=11)
        c2y=par(cx2,c2y,edu.get("major",""), "Helvetica",8,  S500,mw=CW,lh=11); c2y-=5
        if edu.get("period"):
            pill(cx2,c2y,edu["period"],ROSEL,ROSE); c2y-=16
        if edu.get("gpa"):
            t(cx2,c2y,"GPA:","Helvetica-Bold",9,S500)
            t(cx2+35,c2y,str(edu["gpa"]),"Helvetica-Bold",9,S900); c2y-=13
        if cv.get("linkedin"):
            t(cx2,c2y,cv["linkedin"].replace("https://","")[:28],"Helvetica",8,IND); c2y-=11

    ry=min(c1y,c2y)-16

    # Projects full width
    if cv.get("projects"):
        ry=sec(ry,"Projects",width=W-PAD*2)
        for proj in cv["projects"]:
            if ry<115: break
            buls=proj.get("bullets",proj.get("highlights",[]))
            ch=16+14+15+len(buls)*12+12
            c.setFillColor(WHITE); c.roundRect(PAD-4,ry-ch+10,W-PAD*2+8,ch,6,fill=1,stroke=0)
            c.setStrokeColor(S200); c.setLineWidth(0.8)
            c.roundRect(PAD-4,ry-ch+10,W-PAD*2+8,ch,6,fill=0,stroke=1)
            # Gradient top bar
            for ii in range(20):
                tr2=ii/20
                r2=int(0xe1+(0x43-0xe1)*tr2); g2=int(0x1d+(0x38-0x1d)*tr2); b2=int(0x48+(0xca-0x48)*tr2)
                c.setFillColorRGB(r2/255,g2/255,b2/255)
                sw_=( W-PAD*2+8)/20
                c.rect(PAD-4+ii*sw_,ry-ch+10,sw_+1,3,fill=1,stroke=0)

            t(PAD,ry,str(proj.get("name",""))[:68],"Helvetica-Bold",10.5,S900)
            t(W-PAD,ry,str(proj.get("period","")),"Helvetica",7.5,S500,a="right"); ry-=16
            px=PAD
            for tk in proj.get("stack",[]):
                pw=sw(tk,"Helvetica",7.5)+10
                if px+pw>W-PAD-8: px=PAD; ry-=14
                tpill(px,ry,tk); px+=pw+4
            ry-=15
            impact=proj.get("impact","")
            if impact:
                c.setFillColor(ROSEL); c.roundRect(PAD,ry-3,W-PAD*2,15,3,fill=1,stroke=0)
                t(PAD+6,ry+2,"⚡  "+impact[:80],"Helvetica",7.5,ROSE); ry-=16
            for pt in buls:
                c.setFillColor(ROSE); c.roundRect(PAD+2,ry+2,4,4,1,fill=1,stroke=0)
                ry=par(PAD+12,ry,str(pt),"Helvetica",8.5,S700,mw=W-PAD*2-12,lh=12)
            ry-=12

    if cv.get("certifications") and ry>100:
        ry=sec(ry,"Certifications & Courses",width=W-PAD*2)
        cert_cw=(W-PAD*3)/2
        for i,cert in enumerate(cv["certifications"]):
            if ry<45: break
            cx3=PAD if i%2==0 else PAD+cert_cw+PAD
            if i%2==0 and i>0: ry+=27
            c.setFillColor(S100); c.roundRect(cx3-4,ry-4,cert_cw+8,25,3,fill=1,stroke=0)
            c.setFillColor(GREEN); c.circle(cx3+5,ry+8,5,fill=1,stroke=0)
            t(cx3+5,ry+4.5,"✓","Helvetica-Bold",7,WHITE,"center")
            t(cx3+14,ry+10,cert.get("name","")[:30],"Helvetica-Bold",8.5,S900)
            t(cx3+14,ry+1,f'{cert.get("issuer","")[:22]} · {cert.get("year","")}',
              "Helvetica",7,S500)
            if i%2==1: ry-=27

    # Gradient footer
    for i in range(30):
        tr3=i/30
        r3=int(0xe1+(0x43-0xe1)*tr3); g3=int(0x1d+(0x38-0x1d)*tr3); b3=int(0x48+(0xca-0x48)*tr3)
        c.setFillColorRGB(r3/255,g3/255,b3/255)
        c.rect(i*(W/30),0,W/30+1,20,fill=1,stroke=0)
    t(W/2,7,"Generated by SkillMatch AI  ·  SkillMatch Platform","Helvetica",6.5,WHITE,a="center")
    c.save()