#!/usr/bin/env python3
"""python3 report.py reports/people.txt [--llm]
   명단의 각 사람에 대해 reports/<이름>.html + .md 사주 리포트를 만든다. 명단 안 사람들끼리 상호 궁합도 넣는다.
   형식: 이름 YYYY-MM-DD HH:MM(모름 --) MBTI(--) 혈액형(--) 성별(M/F/--)"""
import html, json, os, sys
from datetime import date
import saju, app
from saju import STEMS, BRANCHES, EL, STEM_EL, BR_EL, ganzi, branch_rel, unseong
from app import EL_WORK, TEN_WORK, TEN10_WORK, compat, compat_mbti, ZOD_EL, zodiac

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
COLOR = {"목": "#3E8E5A", "화": "#D6453D", "토": "#D9A62E", "금": "#8C96A0", "수": "#2B4C7E"}
ZODIAC_ANIMAL = "쥐 소 호랑이 토끼 용 뱀 말 양 원숭이 닭 개 돼지".split()
STEM_DESC = {
    "갑": "큰 나무. 곧게 위로 자라는 기질이라 방향이 정해지면 흔들리지 않고, 남 밑에서 굽히는 걸 힘들어합니다.",
    "을": "풀·덩굴. 유연하게 감고 올라가는 기질이라 환경 적응이 빠르고, 사람 사이에서 자기 자리를 잘 찾습니다.",
    "병": "태양. 밝고 넓게 비추는 기질이라 표현이 시원하고 숨기는 게 없지만, 세부 마무리는 남에게 맡기는 편입니다.",
    "정": "촛불·등불. 가까운 곳을 따뜻하고 세밀하게 밝히는 기질이라 집중력과 배려가 깊고, 분위기에 민감합니다.",
    "무": "큰 산. 묵직하고 중심을 잡는 기질이라 신뢰를 주지만, 변화에 느리고 고집이 있습니다.",
    "기": "논밭의 흙. 무엇이든 받아 키우는 기질이라 실무 조율과 뒷받침에 강하고, 자기 주장은 뒤로 미룹니다.",
    "경": "원석·도끼. 결단력과 의리가 강한 기질이라 맺고 끊음이 분명하고, 다듬어질수록 빛납니다.",
    "신": "보석·바늘. 섬세하고 예리한 기질이라 정제된 것과 완성도를 추구하고, 흠집에 민감합니다.",
    "임": "바다·큰 강. 넓고 깊게 흐르는 기질이라 포용력과 지략이 있고, 한곳에 머무르기 어려워합니다.",
    "계": "이슬비·안개. 조용히 스며드는 기질이라 세심하고 순응적이며, 틀이 있을 때 힘을 냅니다."}
GYEOK_DESC = {
    "건록격": "자기 힘으로 서는 구조. 독립·자영·전문가형이고 남의 지시보다 자기 방식이 편합니다.",
    "양인격": "칼을 쥔 구조. 추진력과 경쟁심이 강하고 위기에 강하지만 과하면 마찰이 생깁니다.",
    "겁재격": "동료·경쟁 속에서 크는 구조. 사람을 끌어모으지만 나눠야 할 게 많습니다.",
    "식신격": "몰입해서 결과물을 내는 구조. 연구·제작·요리처럼 손에 잡히는 산출에 강합니다.",
    "상관격": "표현과 비판의 구조. 말·글·기획이 뛰어나고 기존 틀을 뒤집는 데 능하지만 윗사람과 부딪히기 쉽습니다.",
    "편재격": "기회를 보고 판을 키우는 구조. 사업·영업·확장에 강하고 씀씀이가 큽니다.",
    "정재격": "꼼꼼하게 쌓는 구조. 관리·회계·품질처럼 정확함이 필요한 일에 맞고 안정을 중시합니다.",
    "편관격": "압박 속에서 단단해지는 구조. 위기 대응·기술·전문직에 맞고, 권위를 배워 자기 것으로 만듭니다.",
    "정관격": "규범과 책임의 구조. 조직·행정·관리에 맞고 신뢰를 받지만 융통성은 적습니다.",
    "편인격": "탐구와 직관의 구조. 비주류 지식·연구·기술에 강하고 혼자 파는 걸 좋아합니다.",
    "정인격": "배우고 가르치는 구조. 학문·교육·문서에 강하고 명분을 중시합니다."}
UNSEONG_DESC = {"장생": "새로 태어나는 힘, 시작에 강함", "목욕": "불안정하지만 매력적, 변화 많음", "관대": "성장기, 의욕과 자신감", "건록": "자립, 실력으로 섬",
                "제왕": "정점, 주도권", "쇠": "완숙, 한발 물러서 조율", "병": "감수성, 남을 돌봄", "사": "조용한 집중, 내면", "묘": "저장·수집, 신중", "절": "단절과 재출발",
                "태": "잠재력, 아직 형체 없음", "양": "보호받으며 자람"}


def parse(path):
    people = []
    for line in open(path, encoding="utf-8"):
        line = line.split("#")[0].strip()
        if not line: continue
        name, ymd, hm, mbti, blood, gender = (line.split() + ["--"] * 6)[:6]
        y, m, d = map(int, ymd.split("-"))
        hh, mi = (None, 0) if hm == "--" else map(int, hm.split(":"))
        people.append({"name": name, "y": y, "m": m, "d": d, "hh": hh, "mi": mi, "mbti": None if mbti == "--" else mbti.upper(),
                       "blood": None if blood == "--" else blood.upper(), "gender": None if gender == "--" else gender.upper()})
    return people


def build(p):
    r = saju.calc(p["y"], p["m"], p["d"], p["hh"], p["mi"])
    a = saju.analyze(r["pillars"], p["gender"], r["utc"], r["prev_term"], r["next_term"])
    a.update(pillars=[ganzi(x) for x in r["pillars"]], raw=r["pillars"], day_branch=r["pillars"][2][1], birth_year=p["y"], gender=p["gender"],
             lmt=r["lmt"].strftime("%H:%M") if p["hh"] is not None else None, mbti=p["mbti"], blood=p["blood"], name=p["name"],
             zodiac=zodiac(p["m"], p["d"]), id=p["name"], age=date.today().year - p["y"],
             prev_term=r["prev_term"], next_term=r["next_term"], utc=r["utc"])
    return a


# ── 잘 맞는 상대 분석 ──────────────────────────────────────────────────────
def stem_fit(a):
    ds, dm = STEMS.index(a["day_master"]), EL.index(a["dm_el"])
    out = []
    for s in range(10):
        e = STEM_EL[s]
        if (s - ds) % 10 == 5: sc, w = 1.0, "천간합"
        elif e == dm: sc, w = 0.6, "같은 오행"
        elif (e + 1) % 5 == dm: sc, w = 0.9, "나를 생함"
        elif (dm + 1) % 5 == e: sc, w = 0.8, "내가 생함"
        elif (e + 2) % 5 == dm: sc, w = 0.25, "나를 극함"
        else: sc, w = 0.35, "내가 극함"
        if EL[e] == a["yong"]: sc += 0.15; w += "·용신"
        if EL[e] == a["gi"]: sc -= 0.15; w += "·기신"
        out.append((STEMS[s], round(min(1, max(0, sc)) * 100), w, EL[e]))
    return sorted(out, key=lambda x: -x[1])


def year_fit(a, y0=1960, y1=2012):
    ds, dm, db, yb = STEMS.index(a["day_master"]), EL.index(a["dm_el"]), a["day_branch"], a["raw"][0][1]
    out = []
    for y in range(y0, y1 + 1):
        ys, ybr = (y - 4) % 10, (y - 4) % 12
        sc = 0.5
        rel, mod = branch_rel(db, ybr); sc += mod
        rel2, mod2 = branch_rel(yb, ybr); sc += mod2 * 0.6
        e = STEM_EL[ys]
        if (ys - ds) % 10 == 5: sc += 0.2
        elif (e + 1) % 5 == dm: sc += 0.1
        elif (e + 2) % 5 == dm: sc -= 0.1
        if EL[e] == a["yong"]: sc += 0.15
        if EL[e] == a["gi"]: sc -= 0.1
        why = [x for x in (f"일지와 {rel}" if rel else None, f"띠끼리 {rel2}" if rel2 else None, "용신 해" if EL[e] == a["yong"] else None) if x]
        out.append((y, ganzi([ys, ybr]), ZODIAC_ANIMAL[ybr], round(min(1, max(0, sc)) * 100), why))
    return out


def mbti_fit(a):
    if not a["mbti"]: return []
    types = [e + n + t + j for e in "EI" for n in "NS" for t in "TF" for j in "JP"]
    return sorted([(t, round(compat_mbti(a["mbti"], t)[0] * 100)) for t in types], key=lambda x: -x[1])


# ── 연애·결혼 ─────────────────────────────────────────────────────────────
DOHWA = {2: 3, 6: 3, 10: 3, 8: 9, 0: 9, 4: 9, 5: 6, 9: 6, 1: 6, 11: 0, 3: 0, 7: 0}  # 일지 삼합국별 도화 지지
EL_PERSON = {"목": "성장하고 싶어 하는, 기획·계획형", "화": "밝고 표현이 큰, 추진형", "토": "듬직하고 안정적인, 조율형", "금": "원칙 있고 깔끔한, 분석형", "수": "유연하고 아는 게 많은, 지적인"}


def love(a):
    g = a.get("gender")
    if g not in ("M", "F"): return None
    ds, dm = STEMS.index(a["day_master"]), EL.index(a["dm_el"])
    star_k = 3 if g == "F" else 2                      # 여: 관성 / 남: 재성
    main, sub = ("정관", "편관") if g == "F" else ("정재", "편재")
    sel = EL[(dm + star_k) % 5]
    main_stem = next(STEMS[s] for s in range(10) if STEM_EL[s] == EL.index(sel) and s % 2 != ds % 2)
    sub_stem = next(STEMS[s] for s in range(10) if STEM_EL[s] == EL.index(sel) and s % 2 == ds % 2)
    # 원국 내 배우자별 위치
    where = []
    for n, t in a["tens"].items():
        if t["stem"] in (main, sub): where.append(f"{n}간 {t['stem']}")
        if t["branch"] in (main, sub): where.append(f"{n}지 {t['branch']}")
    hidden_only = [f"{n}지 지장간" for n, t in a["tens"].items() if t["branch"] not in (main, sub) and any(h in (main, sub) for _, h in t["hidden"])]
    ilji = a["tens"]["일"]; db = a["day_branch"]
    ilji_el = EL[BR_EL[db]]
    # 시기 점수 (2025~2040)
    du = a["daeun"]; years = []
    for y in range(2025, 2041):
        ys, yb = (y - 4) % 10, (y - 4) % 12
        sg, bg = saju.ten_god10(ds, ys), saju.ten_god10(ds, saju.HIDDEN[yb][-1][0])
        sc, why = 0, []
        if sg == main: sc += 2; why.append(f"세운 천간 {main}")
        elif sg == sub: sc += 1.5; why.append(f"세운 천간 {sub}")
        if bg == main: sc += 1.5; why.append(f"세운 지지 {main}")
        elif bg == sub: sc += 1; why.append(f"세운 지지 {sub}")
        rel, mod = branch_rel(db, yb)
        if rel in ("육합", "삼합"): sc += 1.5; why.append(f"배우자 자리와 {rel}")
        elif rel == "충": sc += 0.5; why.append("배우자 자리 충(변동·이별 또는 새 만남)")
        if yb == DOHWA[db]: sc += 1; why.append("도화")
        if du:
            cur = next((x for x in du["list"] if x["age"] <= y - a["birth_year"] < x["age"] + 10), None)
            if cur and (cur["stem_god"] in (main, sub) or cur["branch_god"] in (main, sub)): sc += 1; why.append(f"대운 {cur['ganzi']}에 배우자별")
        years.append((y, ganzi([ys, yb]), y - a["birth_year"], round(sc, 1), why))
    ranked = sorted(years, key=lambda x: -x[3])
    strict = [x for x in ranked if any("배우자 자리와" in w for w in x[4]) and any(main in w for w in x[4])]
    marriage = strict or ranked[:3]
    return {"gender": g, "main": main, "sub": sub, "el": sel, "main_stem": main_stem, "sub_stem": sub_stem, "where": where, "hidden_only": hidden_only,
            "count": len(where), "strict": bool(strict), "ilji": ilji, "ilji_el": ilji_el, "years": years, "love_years": ranked[:4], "marry_years": marriage[:3],
            "partner": f"{sel}({EL_WORK[sel]}) 기운의 사람. {EL_PERSON[sel]} 사람이 배우자별입니다. 일간이 {main_stem}이면 {main}(안정형), {sub_stem}이면 {sub}(자극형)."}


def love_text(a, lv):
    g = "여성" if lv["gender"] == "F" else "남성"
    s = [f"{g}이라 {'관성' if lv['gender']=='F' else '재성'}({lv['main']}·{lv['sub']})을 배우자별로 봅니다. 원국에 배우자별이 "
         + (f"{lv['count']}개({', '.join(lv['where'])}) 있습니다. " if lv["count"] else "겉으로는 없고 ")
         + (f"지장간에는 {', '.join(lv['hidden_only'])}에 숨어 있습니다. " if lv["hidden_only"] else "")
         + ("배우자별이 많으면 인연은 많지만 고르기 어렵고, " if lv["count"] >= 3 else "배우자별이 없으면 운에서 들어올 때 인연이 열리고, " if lv["count"] == 0 else "")
         + "배우자별이 용신·희신이면 좋은 인연입니다."]
    s.append(f"배우자 자리(일지 {BRANCHES[a['day_branch']]})는 {lv['ilji']['branch']}({TEN10_WORK[lv['ilji']['branch']]}) · {lv['ilji_el']} 기운 · 12운성 {lv['ilji']['unseong']}({UNSEONG_DESC[lv['ilji']['unseong']]}). "
             f"상대는 {EL_PERSON[lv['ilji_el']]} 성격이 되기 쉽고, 관계의 분위기도 그렇습니다.")
    s.append("잘 맞는 상대: " + lv["partner"])
    s.append("연애가 들어오기 쉬운 해: " + ", ".join(f"{y}년({age}세, {gz}) {' · '.join(why)}" for y, gz, age, sc, why in lv["love_years"] if sc > 0))
    s.append(("결혼 인연이 열리는 해(배우자별 + 배우자 자리 합): " if lv["strict"] else "배우자별과 배우자 자리 합이 같이 오는 해는 없음. 점수순 후보: ") + ", ".join(f"{y}년({age}세, {gz})" for y, gz, age, sc, why in lv["marry_years"]))
    return s


# ── 그림 (SVG) ────────────────────────────────────────────────────────────
def svg_radar(power, size=260):
    import math
    c, r = size / 2, size * 0.3
    mx = max(power.values()) or 1
    pt = lambda i, k: (c + math.cos(-math.pi / 2 + i * 2 * math.pi / 5) * r * k, c + math.sin(-math.pi / 2 + i * 2 * math.pi / 5) * r * k)
    ring = lambda k: " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, k) for i in range(5)))
    val = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, power[e] / mx) for i, e in enumerate(EL)))
    s = [f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" style="overflow:visible">']
    s += [f'<polygon points="{ring(k)}" fill="none" stroke="#DDE1E8"/>' for k in (.33, .66, 1)]
    s += [f'<line x1="{c}" y1="{c}" x2="{pt(i,1)[0]:.1f}" y2="{pt(i,1)[1]:.1f}" stroke="#DDE1E8"/>' for i in range(5)]
    s.append(f'<polygon points="{val}" fill="#2B4C7E" fill-opacity=".25" stroke="#2B4C7E" stroke-width="2" stroke-linejoin="round"/>')
    for i, e in enumerate(EL):
        x, y = pt(i, power[e] / mx); s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{COLOR[e]}"/>')
        x, y = pt(i, 1.38); s.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" dominant-baseline="middle" font-size="14" font-weight="700" fill="{COLOR[e]}">{e} {EL_WORK[e].split("·")[0]} <tspan fill="#6B7280" font-weight="500">{power[e]}</tspan></text>')
    return "".join(s) + "</svg>"


def svg_years(years):
    w, h, bw = 1040, 120, 1040 / len(years)
    s = [f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px">']
    for i, (y, gz, ani, sc, why) in enumerate(years):
        col = "#2B4C7E" if sc >= 70 else "#D6453D" if sc < 45 else "#C9CED6"
        s.append(f'<rect x="{i*bw:.1f}" y="{100-sc*0.8:.1f}" width="{bw-1.5:.1f}" height="{sc*0.8:.1f}" fill="{col}" opacity="{.35+sc/150:.2f}"><title>{y} {gz} {ani}띠 {sc}점 {" / ".join(why)}</title></rect>')
        if y % 5 == 0: s.append(f'<text x="{i*bw+bw/2:.1f}" y="116" text-anchor="middle" font-size="11" fill="#6B7280">{y}</text>')
    return "".join(s) + "</svg>"


def svg_love(years):
    w, h, bw = 1040, 130, 1040 / len(years); mx = max(x[3] for x in years) or 1
    s = [f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px">']
    for i, (y, gz, age, sc, why) in enumerate(years):
        hh = sc / mx * 90
        s.append(f'<rect x="{i*bw+4:.1f}" y="{100-hh:.1f}" width="{bw-8:.1f}" height="{hh:.1f}" rx="4" fill="#D6453D" opacity="{.25+sc/mx*.65:.2f}"><title>{y} {gz} {age}세 {sc}점 {" / ".join(why)}</title></rect>'
                 f'<text x="{i*bw+bw/2:.1f}" y="116" text-anchor="middle" font-size="12" fill="#6B7280">{y}</text><text x="{i*bw+bw/2:.1f}" y="{96-hh:.1f}" text-anchor="middle" font-size="12" font-weight="700" fill="#14181F">{sc if sc else ""}</text>')
    return "".join(s) + "</svg>"


def svg_stems(fit):
    s = ['<svg viewBox="0 0 520 250" width="100%" style="max-width:520px">']
    for i, (st, sc, w, e) in enumerate(fit):
        y = i * 24 + 4
        s.append(f'<text x="14" y="{y+15}" font-size="15" font-weight="800" fill="{COLOR[e]}">{st}</text>'
                 f'<rect x="40" y="{y+3}" width="{sc*3.2:.0f}" height="16" rx="4" fill="{COLOR[e]}" opacity=".7"/>'
                 f'<text x="{48+sc*3.2:.0f}" y="{y+15}" font-size="12" fill="#14181F">{sc} <tspan fill="#6B7280">{w}</tspan></text>')
    return "".join(s) + "</svg>"


# ── 문장 ──────────────────────────────────────────────────────────────────
def narrative(a):
    ds = STEMS.index(a["day_master"])
    t = a["tens"]; d = a["daeun"]
    s = []
    s.append(f"일간 {a['day_master']}{a['dm_el']}({'음' if a['dm_yin'] else '양'}). {STEM_DESC[a['day_master']]}")
    dom = max(a["power"], key=a["power"].get)
    s.append(f"오행은 {dom}({EL_WORK[dom]})이 {a['power'][dom]}로 가장 강하고 {', '.join(e for e in a['lacking']) or '없는 오행 없이'} "
             f"{'약합니다' if a['lacking'] else '고르게 분포합니다'}. 부조 비율 {a['support_ratio']}로 {a['strength']}"
             f"{' (경계)' if 0.42 <= a['support_ratio'] <= 0.58 else ''}이며, 득령 {'했고' if a['deukryeong'] else '못 했고'} 통근은 {'·'.join(a['rooted']) + '지' if a['rooted'] else '없습니다'}.")
    s.append(f"격국은 {a['gyeok']}. {GYEOK_DESC[a['gyeok']]}")
    s.append(f"용신은 {a['yong']}({EL_WORK[a['yong']]}), 희신 {a['hui']}({EL_WORK[a['hui']]}), 기신 {a['gi']}({EL_WORK[a['gi']]}). {a['yong_why']}. "
             f"{'조후로 ' + a['johu'] + ' 기운이 먼저 필요한 계절 출생입니다. ' if a['johu'] else ''}"
             f"따라서 {EL_WORK[a['yong']]} 쪽 일과 사람이 이 사람을 살리고, {EL_WORK[a['gi']]}에 치우치면 지칩니다.")
    ilji = t["일"]
    s.append(f"일지 {a['pillars'][2][1]}는 {ilji['branch']}({TEN10_WORK[ilji['branch']]}) 자리이고 지장간 {''.join(h for h, _ in ilji['hidden'])}, 12운성 {ilji['unseong']}({UNSEONG_DESC[ilji['unseong']]}). "
             f"가장 가까운 파트너·실무 자리의 성격입니다.")
    if a["relations"]: s.append("원국 관계: " + ", ".join(a["relations"]) + ".")
    s.append(f"공망은 {''.join(a['gongmang'])}" + (f"이고 {'·'.join(a['gongmang_hit'])}지가 공망에 듭니다." if a["gongmang_hit"] else "이며 원국에는 들지 않습니다."))
    if d:
        cur = next((x for x in d["list"] if x["age"] <= a["age"] < x["age"] + 10), None)
        s.append(f"대운은 {'순행' if d['forward'] else '역행'} {d['start_age']}세 시작. " + (f"현재 {cur['ganzi']} 대운({cur['age']}세~, {cur['stem_god']}/{cur['branch_god']}, {cur['unseong']})." if cur else ""))
    else:
        s.append("성별이 없어 대운은 생략했습니다(명단에 M/F를 적으면 계산).")
    return s


GLOSSARY = [("일간", "나 자신을 나타내는 글자"), ("오행 힘", "다섯 기운이 내 판에서 얼마나 센지"), ("신강·신약", "내 기운이 센가 약한가"), ("격국", "타고난 일하는 틀"),
            ("용신", "나에게 필요한 기운"), ("희신", "용신을 돕는 기운"), ("기신", "피해야 할 기운"), ("합", "붙어서 하나가 됨"), ("충", "정면으로 부딪힘"), ("형·파·해", "마찰·어긋남·오해"),
            ("공망", "비어 있는 자리, 힘이 안 실림"), ("대운", "10년 단위 흐름"), ("세운", "그해의 흐름"), ("12운성", "내 기운이 그 자리에서 얼마나 살아 있나"), ("배우자별", "여성은 관성, 남성은 재성"), ("배우자 자리", "일지, 가장 가까운 사람 자리")]


def easy(a):
    """reports/<이름>.easy.md 가 있으면 [(제목, [문장…])] 로 읽는다."""
    p = os.path.join(OUT, a["name"] + ".easy.md")
    if not os.path.exists(p): return []
    secs = []
    for line in open(p, encoding="utf-8"):
        line = line.rstrip()
        if line.startswith("## "): secs.append((line[3:], []))
        elif line.startswith("- ") and secs: secs[-1][1].append(line[2:])
    return secs


def md_report(a, fits, cross):
    L = [f"# {a['name']} 사주 리포트", "", f"- 원국: {' · '.join(x or '시주 모름' for x in a['pillars'])}" + (f" (진태양시 {a['lmt']})" if a["lmt"] else ""),
         f"- 일간 {a['day_master']}{a['dm_el']} · {a['strength']}({a['support_ratio']}) · {a['gyeok']} · 용신 {a['yong']} 희신 {a['hui']} 기신 {a['gi']}",
         f"- 오행 힘: " + ", ".join(f"{k} {v}" for k, v in a["power"].items()), f"- MBTI {a['mbti'] or '-'} · {a['blood'] or '-'}형 · {a['zodiac']}자리", ""]
    for title, lines in easy(a): L += [f"## 쉬운 말로 · {title}", ""] + [f"- {x}" for x in lines] + [""]
    L += ["## 용어", ""] + [f"- {k}: {v}" for k, v in GLOSSARY] + ["", "## 해설", ""]
    L += [f"- {x}" for x in narrative(a)]
    lv = love(a)
    if lv: L += ["", "## 연애운 · 결혼운", ""] + [f"- {x}" for x in love_text(a, lv)]
    L += ["", "## 잘 맞는 일간", ""] + [f"- {st} {sc}점 ({w})" for st, sc, w, e in fits["stems"][:5]]
    L += ["", "## 잘 맞는 출생 연도 (상위 10)", ""] + [f"- {y}년 {gz} {ani}띠 {sc}점 {' / '.join(why)}" for y, gz, ani, sc, why in fits["top_years"]]
    L += ["", "## 피할 출생 연도 (하위 5)", ""] + [f"- {y}년 {gz} {ani}띠 {sc}점" for y, gz, ani, sc, why in fits["bad_years"]]
    if fits["mbti"]: L += ["", "## MBTI 상성 (상위 5)", ""] + [f"- {t} {sc}점" for t, sc in fits["mbti"][:5]]
    if cross: L += ["", "## 명단 내 궁합", ""] + [f"- {o['name']} ({' '.join(o['pillars'][:3])}) {sc}점 — {' / '.join(why)}" for o, sc, why in cross]
    return "\n".join(L) + "\n"


CSS = """*{box-sizing:border-box}body{margin:0;background:#EEF0F4;color:#14181F;font:15px/1.6 "Pretendard","Apple SD Gothic Neo",system-ui,"Malgun Gothic",sans-serif;font-variant-numeric:tabular-nums}
main{max-width:1080px;margin:0 auto;padding:28px 16px 60px}h1{font-size:34px;font-weight:800;letter-spacing:-.03em;margin:0}h1 small{display:block;font-size:14px;font-weight:500;color:#6B7280;margin-top:6px;letter-spacing:0}
h2{font-size:17px;font-weight:700;margin:0 0 12px}.card{background:#fff;border:1px solid #DDE1E8;border-radius:14px;padding:20px;margin:14px 0}
.pz{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;text-align:center}.pz>div{background:#F5F6F9;border-radius:10px;padding:12px 4px}.pz .h{font-size:12px;color:#6B7280;font-weight:600}.pz .g{font-size:40px;font-weight:800;line-height:1.1}.pz .s{font-size:12px;color:#6B7280}
.two{display:grid;grid-template-columns:300px 1fr;gap:20px;align-items:center}@media(max-width:700px){.two{grid-template-columns:1fr}}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}.grid3>div{background:#F5F6F9;border-radius:10px;padding:14px}.grid3 b{display:block;font-size:12px;color:#6B7280;margin-bottom:6px}
.tag{display:inline-block;padding:3px 9px;border-radius:99px;font-size:12px;background:#F5F6F9;border:1px solid #DDE1E8;margin:2px 4px 2px 0;font-weight:600}
.du{display:grid;grid-template-columns:repeat(auto-fit,minmax(92px,1fr));gap:6px}.du>div{border:1px solid #DDE1E8;border-radius:8px;padding:8px 4px;text-align:center;font-size:12px;color:#6B7280}.du b{display:block;font-size:19px;color:#14181F}.du .cur{border-color:#2B4C7E;background:#F5F6F9}
table{width:100%;border-collapse:collapse;font-size:14px}td,th{padding:8px 6px;border-bottom:1px solid #DDE1E8;text-align:left;vertical-align:top}th{font-size:12px;color:#6B7280}.sc{font-size:22px;font-weight:800;letter-spacing:-.02em}
.easy{border-color:#2B4C7E;border-width:2px}.easy h3{font-size:14px;color:#2B4C7E;margin:14px 0 4px}.easy li{font-size:15.5px}.gl{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px;color:#6B7280}.gl b{color:#14181F}
ol,ul{margin:0;padding-left:20px}li{margin:6px 0}.mut{color:#6B7280;font-size:13px}footer{color:#6B7280;font-size:12px;text-align:center;padding:20px}"""


def html_report(a, fits, cross):
    E = html.escape
    N = "년월일시"
    cols = []
    for i in range(4):
        g = a["pillars"][i]
        if not g: cols.append(f'<div><div class="h">{N[i]}주</div><div class="g" style="color:#aaa">--</div><div class="s">시각 모름</div></div>'); continue
        t = a["tens"][N[i]]
        gm = ' <span style="color:#D6453D">공망</span>' if (g[1] in a["gongmang"] and i != 2) else ""
        cols.append(f'<div><div class="h">{N[i]}주 · {t["stem"] or "일간"}</div><div class="g"><span style="color:{COLOR[EL[STEM_EL[STEMS.index(g[0])]]]}">{g[0]}</span>'
                    f'<span style="color:{COLOR[EL[BR_EL[BRANCHES.index(g[1])]]]}">{g[1]}</span></div><div class="s">{t["branch"]}{gm}<br>지장간 {"".join(h for h,_ in t["hidden"])} · {t["unseong"]}</div></div>')
    d = a["daeun"]
    du = "".join(f'<div class="{"cur" if x["age"] <= a["age"] < x["age"] + 10 else ""}">{x["age"]}세<b>{x["ganzi"]}</b>{x["stem_god"]}/{x["branch_god"]}<br>{x["unseong"]}</div>' for x in d["list"]) if d else '<p class="mut">성별을 적으면 대운을 계산합니다.</p>'
    top = "".join(f"<tr><td class='sc'>{sc}</td><td><b>{y}년</b> {gz} · {ani}띠</td><td class='mut'>{' / '.join(why) or '무난'}</td></tr>" for y, gz, ani, sc, why in fits["top_years"])
    bad = ", ".join(f"{y}년({ani}띠) {sc}" for y, gz, ani, sc, why in fits["bad_years"])
    mb = "".join(f'<span class="tag">{t} {sc}</span>' for t, sc in fits["mbti"][:6]) if fits["mbti"] else '<span class="mut">MBTI 없음</span>'
    cr = "".join(f"<tr><td class='sc'>{sc}</td><td><b>{E(o['name'])}</b> <span class='mut'>{' '.join(o['pillars'][:3])} · {o['mbti'] or '-'} · {o['blood'] or '-'}형</span></td><td class='mut'>{' / '.join(E(w) for w in why)}</td></tr>" for o, sc, why in cross)
    good_el = f"{a['yong']} {EL_WORK[a['yong']]} · {a['hui']} {EL_WORK[a['hui']]}"
    ez = easy(a)
    ez_html = ('<div class="card easy"><h2>쉬운 말로</h2>' + ''.join(f'<h3>{E(t)}</h3><ul>{"".join(f"<li>{E(x)}</li>" for x in ls)}</ul>' for t, ls in ez) + '</div>') if ez else ''
    gl = '<div class="card"><h2>용어 한 줄</h2><div class="gl">' + ''.join(f'<span><b>{k}</b> {v}</span>' for k, v in GLOSSARY) + '</div></div>'
    lv = love(a)
    lv_html = ('<div class="card"><h2>연애운 · 결혼운 <span class="mut" style="font-weight:500;font-size:13px">' + ('여성' if lv['gender']=='F' else '남성') + ' 기준 · 재미로</span></h2><ul>' + ''.join(f'<li>{E(x)}</li>' for x in love_text(a, lv)) + '</ul>'
               '<h2 style="margin-top:14px">해별 연애 점수 (2025~2040)</h2>' + svg_love(lv["years"]) + '</div>') if lv else ''

    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(a['name'])} 사주 리포트</title><style>{CSS}</style></head><body><main>
<h1>{E(a['name'])}<small>{' · '.join(x or '시주 모름' for x in a['pillars'])}{' · 진태양시 ' + a['lmt'] if a['lmt'] else ''} · {a['mbti'] or '-'} · {a['blood'] or '-'}형 · {a['zodiac']}자리 · 재미로 보는 자료</small></h1>
{ez_html}{gl}<div class="card"><h2>사주 원국</h2><div class="pz">{''.join(cols)}</div>
<div class="grid3" style="margin-top:12px"><div><b>일간 · 강약</b>{a['day_master']} {a['dm_el']} · {'음' if a['dm_yin'] else '양'}간 · <b style="display:inline;color:#14181F;font-size:15px">{a['strength']}</b> (부조 비율 {a['support_ratio']}) · 득령 {'O' if a['deukryeong'] else 'X'} · 통근 {'·'.join(a['rooted']) or '없음'}</div>
<div><b>격국 · 용신</b><span style="font-size:18px;font-weight:800">{a['gyeok']}</span> ({a['gyeok_god']})<br>용신 <b style="display:inline;color:{COLOR[a['yong']]};font-size:15px">{a['yong']}</b> · 희신 {a['hui']} · 기신 {a['gi']}{' · 조후 ' + a['johu'] if a['johu'] else ''}<br><span class="mut">{a['yong_why']}</span></div>
<div><b>합충형파해 · 공망</b>{'<br>'.join(a['relations']) or '특이 관계 없음'}<br>공망 {''.join(a['gongmang'])}{' (' + '·'.join(a['gongmang_hit']) + '지)' if a['gongmang_hit'] else ''}</div></div>
<h2 style="margin-top:16px">대운{' (' + ('순행' if d['forward'] else '역행') + ' · ' + str(d['start_age']) + '세 시작)' if d else ''}</h2><div class="du">{du}</div></div>
<div class="card"><div class="two">{svg_radar(a['power'])}<div><h2>해설</h2><ul>{''.join(f'<li>{E(x)}</li>' for x in narrative(a))}</ul></div></div></div>
<div class="card"><h2>잘 맞는 성향</h2><div class="grid3"><div><b>필요한 기운 (용신·희신)</b>{good_el}<br><span class="mut">이 성향이 강한 사람·일이 나를 살립니다.</span></div>
<div><b>피할 기운 (기신)</b>{a['gi']} {EL_WORK[a['gi']]}<br><span class="mut">이쪽에 치우친 사람·일은 소모가 큽니다.</span></div><div><b>MBTI 상성</b>{mb}</div></div>
<div class="two" style="margin-top:14px;grid-template-columns:1fr 1fr"><div><h2>잘 맞는 일간 (상대의 일간)</h2>{svg_stems(fits['stems'])}</div>
<div><h2>잘 맞는 출생 연도</h2>{svg_years(fits['years'])}<p class="mut">파란색 70점 이상 · 빨간색 45점 미만. 막대에 마우스를 올리면 이유. 일지·띠와의 합충형파해, 천간합, 용신 해로 계산.</p></div></div>
<table><tr><th></th><th>연도 (상위 10)</th><th>이유</th></tr>{top}</table><p class="mut" style="margin-top:8px">피할 연도 하위 5: {bad}</p></div>
{lv_html}{'<div class="card"><h2>명단 내 궁합</h2><table><tr><th></th><th>상대</th><th>이유</th></tr>' + cr + '</table></div>' if cross else ''}
<footer>절기는 VSOP87 기반 ±1분, 진태양시·서머타임·표준시 이력 보정. 신강약·용신·격국은 규칙 점수라 유파에 따라 다를 수 있음. 과학적 근거 없음, 재미로.</footer></main></body></html>"""


def main(path):
    people = [build(p) for p in parse(path)]
    os.makedirs(OUT, exist_ok=True)
    for a in people:
        years = year_fit(a)
        fits = {"stems": stem_fit(a), "years": years, "top_years": sorted(years, key=lambda x: -x[3])[:10],
                "bad_years": sorted(years, key=lambda x: x[3])[:5], "mbti": mbti_fit(a)}
        cross = sorted([(o, *compat(a, o)) for o in people if o is not a], key=lambda x: -x[1])
        base = os.path.join(OUT, a["name"])
        open(base + ".html", "w", encoding="utf-8").write(html_report(a, fits, cross))
        open(base + ".md", "w", encoding="utf-8").write(md_report(a, fits, cross))
        print(f"{a['name']:8} {' '.join(x or '----' for x in a['pillars'])}  {a['strength']} {a['gyeok']} 용신 {a['yong']}  → reports/{a['name']}.html")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, "people.txt"))
