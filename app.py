#!/usr/bin/env python3
"""팀 밸런스 맵 — 사주·MBTI·별자리·혈액형 기반 팀 워크숍용 궁합/성향 지도. 표준 라이브러리만 사용.
   LLM(Ollama / OpenAI 호환)은 문장 생성에만 쓰고, 없으면 규칙 문장으로 대체된다."""
import glob, json, math, os, re, secrets, sys, threading, urllib.error, urllib.request
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("WORKSPACE") or os.path.join(ROOT, "data")  # 포털이 AGENT_DATA/<도구> 로 모아 줌
PEOPLE = os.path.join(DATA, "people.json")
PORT = int(os.environ.get("PORT", "8766"))
LLM_API = os.environ.get("LLM_API", "ollama")  # ollama | openai
BASE = os.environ.get("LLM_BASE_URL", "http://localhost:11434" if LLM_API == "ollama" else "http://localhost:8000/v1").rstrip("/")
MODEL = os.environ.get("LLM_MODEL", "qwen3:8b")
API_KEY = os.environ.get("LLM_API_KEY", "")
LOCK = threading.Lock()

import saju
from saju import STEMS, BRANCHES, EL, STEM_EL, BR_EL, TEN, ganzi, branch_rel, unseong

EL_WORK = {"목": "기획·성장", "화": "추진·표현", "토": "조율·안정", "금": "원칙·분석", "수": "유연·지식"}
TEN_WORK = {"비겁": "협업·동료", "식상": "창의·산출", "재성": "실행·성과", "관성": "규율·책임", "인성": "학습·지원"}
TEN10_WORK = {"비견": "동료·독립", "겁재": "경쟁·추진", "식신": "몰입·산출", "상관": "표현·비판", "편재": "기회·확장", "정재": "꼼꼼·성과",
              "편관": "돌파·압박", "정관": "규범·책임", "편인": "탐구·직관", "정인": "학습·지원"}


def ten_god(dm_el, el):
    return TEN[(el - dm_el) % 5]


# ── 궁합 표 ──────────────────────────────────────────────────────────────
ZODIAC = [(120, "염소"), (218, "물병"), (320, "물고기"), (420, "양"), (521, "황소"), (621, "쌍둥이"), (722, "게"),
          (823, "사자"), (923, "처녀"), (1023, "천칭"), (1122, "전갈"), (1222, "사수"), (1231, "염소")]
ZOD_EL = {"양": "불", "사자": "불", "사수": "불", "황소": "흙", "처녀": "흙", "염소": "흙",
          "쌍둥이": "공기", "천칭": "공기", "물병": "공기", "게": "물", "전갈": "물", "물고기": "물"}
ZOD_PAIR = {frozenset(["불", "공기"]): 0.85, frozenset(["흙", "물"]): 0.85, frozenset(["불", "흙"]): 0.4,
            frozenset(["불", "물"]): 0.35, frozenset(["공기", "흙"]): 0.4, frozenset(["공기", "물"]): 0.45}
BLOOD = {frozenset(["A"]): 0.7, frozenset(["A", "B"]): 0.4, frozenset(["A", "O"]): 0.9, frozenset(["A", "AB"]): 0.6,
         frozenset(["B"]): 0.6, frozenset(["B", "O"]): 0.8, frozenset(["B", "AB"]): 0.7, frozenset(["O"]): 0.6,
         frozenset(["O", "AB"]): 0.7, frozenset(["AB"]): 0.5}


def zodiac(m, d):
    return next(z for lim, z in ZODIAC if m * 100 + d < lim) if m * 100 + d < 1222 else "염소"


UNSEONG_SCORE = {"장생": .8, "관대": .8, "건록": .9, "제왕": .9, "목욕": .5, "쇠": .5, "병": .4, "양": .5, "태": .5, "사": .3, "묘": .3, "절": .25}


def compat_saju(a, b):
    ea, eb = EL.index(a["dm_el"]), EL.index(b["dm_el"])
    sa, sb = STEMS.index(a["day_master"]), STEMS.index(b["day_master"])
    why = []
    if (sa - sb) % 10 == 5:
        s1, w = 1.0, "일간 천간합 (서로 끌리는 조합)"
    elif ea == eb:
        s1, w = 0.6, f"일간 같은 성향 ({EL_WORK[a['dm_el']]})"
    elif (eb + 1) % 5 == ea:
        s1, w = 0.9, f"상대가 나를 생함 ({b['dm_el']}→{a['dm_el']}, 힘을 받음)"
    elif (ea + 1) % 5 == eb:
        s1, w = 0.8, f"내가 상대를 생함 ({a['dm_el']}→{b['dm_el']}, 힘을 줌)"
    elif (eb + 2) % 5 == ea:
        s1, w = 0.25, f"상대가 나를 극함 ({b['dm_el']}→{a['dm_el']}, 긴장)"
    else:
        s1, w = 0.35, f"내가 상대를 극함 ({a['dm_el']}→{b['dm_el']}, 긴장)"
    why.append(w)
    rel, mod = branch_rel(a["day_branch"], b["day_branch"])
    if rel: why.append(f"일지 {rel}")
    s2 = max(0, min(1, 0.5 + mod))
    # 용신 보완: 내 용신 오행이 상대 원국에서 힘이 있으면 +, 기신이 강하면 -
    pa, pb = a.get("power") or {}, b.get("power") or {}
    def fill(me, other):
        if not other or "yong" not in me: return 0.5
        tot = sum(other.values()) or 1
        return max(0, min(1, 0.4 + other.get(me["yong"], 0) / tot * 1.6 - other.get(me["gi"], 0) / tot * 0.6))
    s3 = (fill(a, pb) + fill(b, pa)) / 2
    if pb.get(a.get("yong"), 0) / (sum(pb.values()) or 1) >= 0.3: why.append(f"내게 필요한 {a['yong']}({EL_WORK[a['yong']]}) 기운을 상대가 가짐")
    if pa.get(b.get("yong"), 0) / (sum(pa.values()) or 1) >= 0.3: why.append(f"상대에게 필요한 {b['yong']}({EL_WORK[b['yong']]}) 기운을 내가 가짐")
    # 12운성: 내 일간이 상대 일지에서 얼마나 힘을 얻나 (양방향)
    ua, ub = unseong(sa, b["day_branch"]), unseong(sb, a["day_branch"])
    s4 = (UNSEONG_SCORE[ua] + UNSEONG_SCORE[ub]) / 2
    if UNSEONG_SCORE[ua] >= .8 and UNSEONG_SCORE[ub] >= .8: why.append(f"서로의 자리에서 힘을 얻음 ({ua}·{ub})")
    return (s1 * 0.35 + s2 * 0.25 + s3 * 0.25 + s4 * 0.15), why


def compat_mbti(a, b):
    s, why = 0.5, []
    if a[1] == b[1]: s += 0.25; why.append(f"MBTI 정보 처리 방식 같음 ({a[1]})")
    if a[0] != b[0]: s += 0.1; why.append("MBTI 에너지 방향 보완 (E/I)")
    if a[3] != b[3]: s += 0.1; why.append("MBTI 일 진행 방식 보완 (J/P)")
    if a[2] == b[2]: s += 0.05
    return s, why


def compat(a, b):
    parts = [(0.5, *compat_saju(a, b))]
    if a.get("mbti") and b.get("mbti"): parts.append((0.25, *compat_mbti(a["mbti"], b["mbti"])))
    if a.get("zodiac") and b.get("zodiac"):
        za, zb = ZOD_EL[a["zodiac"]], ZOD_EL[b["zodiac"]]
        s = 0.9 if za == zb else ZOD_PAIR[frozenset([za, zb])]
        parts.append((0.15, s, [f"별자리 {za}·{zb}"] if s >= 0.85 else []))
    if a.get("blood") and b.get("blood"):
        s = BLOOD[frozenset([a["blood"], b["blood"]])]
        parts.append((0.1, s, [f"혈액형 {a['blood']}·{b['blood']}"] if s >= 0.8 else []))
    tot = sum(w for w, _, _ in parts)
    score = sum(w * s for w, s, _ in parts) / tot
    why = [x for _, _, ws in parts for x in ws]
    return round(score * 100), why[:4]


# ── 오늘의 운세 (규칙) ───────────────────────────────────────────────────
def today_rule(p, day=None):
    now = datetime.utcnow() + timedelta(hours=9)
    if day: now = datetime(day.year, day.month, day.day, 12)
    day = now.date()
    yp, mp, dp, _ = saju.pillars_of(now)
    ds = STEMS.index(p["day_master"])
    ts, tb = dp
    tg = ten_god(EL.index(p["dm_el"]), STEM_EL[ts])
    rel, mod = branch_rel(p["day_branch"], tb)
    us = unseong(ds, tb)
    stars = 3 + {"인성": 1, "재성": 1, "비겁": 0, "식상": 0, "관성": -1}[tg] + round(mod * 3) + (1 if UNSEONG_SCORE[us] >= .8 else -1 if UNSEONG_SCORE[us] <= .3 else 0)
    if p.get("yong") and EL[STEM_EL[ts]] == p["yong"]: stars += 1
    if p.get("gi") and EL[STEM_EL[ts]] == p["gi"]: stars -= 1
    stars = max(1, min(5, stars))
    tel = EL[STEM_EL[ts]]
    menu = MENU[tel][(day.toordinal() + sum(map(ord, p.get("id", "")))) % 5]  # ponytail: 날짜+사람 해시로 고정
    cyc = lambda pp: {"ganzi": ganzi(pp), "god": saju.ten_god10(ds, pp[0]), "rel": branch_rel(p["day_branch"], pp[1])[0],
                      "unseong": unseong(ds, pp[1]), "yong": EL[STEM_EL[pp[0]]] == p.get("yong"), "gi": EL[STEM_EL[pp[0]]] == p.get("gi")}
    return {"date": day.isoformat(), "day": ganzi(dp), "day_god": saju.ten_god10(ds, ts), "theme": tg, "theme_work": TEN_WORK[tg],
            "branch_rel": rel, "unseong": us, "stars": stars, "day_el": tel, "menu": menu,
            "research": RESEARCH[tg], "collab": COLLAB[rel], "year": cyc(yp), "month": cyc(mp),
            "daeun": current_daeun(p)}


def current_daeun(p):
    d = p.get("daeun")
    if not d: return None
    age = date.today().year - int(p.get("birth_year", 0)) if p.get("birth_year") else None
    if age is None: return None
    cur = None
    for x in d["list"]:
        if x["age"] <= age: cur = x
    return cur


FALLBACK = {"비겁": "동료와 보조 맞추는 날. 혼자 끌지 말고 나눠서.", "식상": "아이디어가 잘 나오는 날. 초안부터 던져보기.",
            "재성": "결과가 손에 잡히는 날. 마무리 작업에 집중.", "관성": "책임이 무거운 날. 일정·규정 한 번 더 확인.",
            "인성": "배우고 정리하는 날. 문서·학습에 시간 쓰기."}
RESEARCH = {"비겁": "공동연구·미팅이 잘 풀림. 혼자 붙들던 문제를 옆자리에 물어보기.", "식상": "가설·글쓰기의 날. 초록이나 제안서 초안을 오늘 시작.",
            "재성": "데이터가 답을 주는 날. 결과 정리·그래프 그리기에 집중.", "관성": "심사·보고·규정 검토에 유리. 제출물 형식 한 번 더 확인.",
            "인성": "논문 읽기·학습에 최적. 새 방법론 하나 파보기."}
COLLAB = {"육합": "말이 잘 통하는 날. 미뤄둔 협의를 오늘 잡기.", "삼합": "팀 단위 일이 순조로움. 역할 나누기 좋은 날.",
          "방합": "같은 방향을 보는 사람들과 뭉치기 좋은 날. 팀 내부 결속.", "충": "의견 충돌 주의. 결론은 내일로 미루고 오늘은 듣기.",
          "형": "사소한 마찰이 커질 수 있는 날. 말은 짧게, 기록은 남기기.", "파": "약속·일정이 어긋나기 쉬운 날. 재확인 한 번 더.",
          "해": "오해가 생기기 쉬운 날. 텍스트보다 얼굴 보고 말하기.", "자형": "스스로 발목 잡기 쉬운 날. 완벽주의 내려놓기.",
          "같음": "비슷한 사람끼리 뭉치기 쉬운 날. 다른 팀에도 말 걸기.", None: "무난한 날. 평소처럼."}
MENU = {"목": ["비빔밥", "샐러드볼", "쌈밥", "나물정식", "월남쌈"], "화": ["김치찌개", "제육볶음", "떡볶이", "마라탕", "닭갈비"],
        "토": ["된장찌개", "돈까스", "카레", "덮밥", "백반"], "금": ["칼국수", "냉면", "우동", "쌀국수", "잔치국수"],
        "수": ["순두부찌개", "해물탕", "초밥", "물회", "설렁탕"]}

# ── LLM ─────────────────────────────────────────────────────────────────
SYSTEM = ("너는 사내 팀 워크숍용 '팀 밸런스 맵' 도우미다. 명리 한자어(십신·오행 이름) 대신 업무 성향어만 쓴다. "
          "건강·금전·연애·인사평가 언급 금지. 단정 대신 제안형. 한국어, 존댓말.")


def llm(user, timeout=300, system=None):   # vLLM 대기열(다른 도구와 같이 씀)을 고려해 넉넉히
    msgs = [{"role": "system", "content": system or SYSTEM}, {"role": "user", "content": user}]
    if LLM_API == "openai":
        url, body = BASE + "/chat/completions", {"model": MODEL, "messages": msgs, "temperature": 0.7}
    else:
        url, body = BASE + "/api/chat", {"model": MODEL, "messages": msgs, "stream": False, "think": False}
    hdr = {"Content-Type": "application/json", **({"Authorization": "Bearer " + API_KEY} if API_KEY else {})}
    for attempt in (0, 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(), hdr), timeout=timeout) as r:
                j = json.load(r)
            out = (j["choices"][0]["message"] if LLM_API == "openai" else j["message"]).get("content") or ""   # vLLM 은 빈 응답에 null
            return re.sub(r"<think>.*?</think>", "", out, flags=re.S).strip()
        except urllib.error.HTTPError as e:
            if attempt == 0 and "think" in body and "think" in e.read().decode(errors="replace"):
                body.pop("think"); continue
            raise


def describe(p):
    el = ", ".join(f"{k}({EL_WORK[k]}) {v}" for k, v in (p.get("power") or p["elements"]).items())
    tg = ", ".join(f"{TEN_WORK[k]} {v}" for k, v in p["ten_gods"].items())
    return (f"핵심 성향: {EL_WORK[p['dm_el']]} / 성향 힘 분포: {el} / 역할 분포: {tg} / 에너지: {p['strength']}"
            f" / 필요한 기운: {p.get('yong','')}({EL_WORK.get(p.get('yong'),'')})"
            f"{' / MBTI ' + p['mbti'] if p.get('mbti') else ''}")


def describe_myeongri(p):
    """명리 용어 그대로의 원국 요약 (LLM 명리 해설용)"""
    pil = " ".join(f"{n}주 {g}" for n, g in zip("년월일시", p["pillars"]) if g)
    t = p["tens"]
    tens = "; ".join(f"{n}: 천간 {v['stem'] or '일간'}, 지지 {v['branch']}({''.join(h for h, _ in v['hidden'])}), 12운성 {v['unseong']}" for n, v in t.items())
    d = p.get("daeun")
    du = ("대운 " + ("순행" if d["forward"] else "역행") + f" {d['start_age']}세 시작: " + ", ".join(f"{x['age']}세 {x['ganzi']}({x['stem_god']}/{x['branch_god']})" for x in d["list"][:6])) if d else "대운: 성별 미입력으로 생략"
    return (f"원국: {pil}. 일간 {p['day_master']}({p['dm_el']}, {'음' if p['dm_yin'] else '양'}). "
            f"오행 힘: {p['power']}. 신강약: {p['strength']}(부조 비율 {p['support_ratio']}), 득령 {'O' if p['deukryeong'] else 'X'}, 통근 {', '.join(p['rooted']) or '없음'}. "
            f"격국: {p['gyeok']}. 용신 {p['yong']}, 희신 {p['hui']}, 기신 {p['gi']} ({p['yong_why']}). 조후: {p['johu'] or '해당 없음'}. "
            f"공망: {''.join(p['gongmang'])}{' (' + ', '.join(p['gongmang_hit']) + '지 공망)' if p['gongmang_hit'] else ''}. "
            f"십신: {tens}. 원국 관계: {', '.join(p['relations']) or '없음'}. {du}.")


# ── 저장 ─────────────────────────────────────────────────────────────────
ADJ = "파란 붉은 하얀 노란 초록 보라 은빛 금빛 조용한 씩씩한 느긋한 재빠른 다정한 엉뚱한 진지한 명랑한".split()
ANI = "고래 여우 부엉이 수달 판다 거북 늑대 참새 돌고래 사슴 두루미 호랑이 고양이 다람쥐 펭귄 코끼리".split()


def load():
    try:
        with open(PEOPLE, encoding="utf-8") as f: return json.load(f)
    except FileNotFoundError:
        return []


def save(people):
    os.makedirs(DATA, exist_ok=True)
    tmp = PEOPLE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(people, f, ensure_ascii=False, indent=1)
    os.replace(tmp, PEOPLE)


# ── 포털 계정: 등록 주인·이름·부서는 X-Agent-User 의 포털 계정에서 (자칭 부서·이름 사칭 막기) ──
PORTAL_DB = os.environ.get("PORTAL_DB") or os.path.join(os.environ.get("AGENT_DATA") or os.path.join(os.path.dirname(ROOT), "_data"), "portal.db")
CUR = threading.local()  # 요청마다 handler 가 CUR.acct 를 채움(ThreadingHTTPServer = 요청당 스레드)
NO_DEPT = "포털 계정에 부서가 정해져 있지 않습니다 — 포털 '내 정보'에서 부서를 신청해 승인받은 뒤 쓸 수 있어요"


def account(uid):
    """X-Agent-User → {uid, name, dept, admin}. 포털 DB(users)를 읽기 전용으로 — 못 읽거나 비활성 계정이면 부서 없음."""
    import sqlite3
    a = {"uid": uid, "name": "", "dept": "", "admin": uid == "owner"}
    if uid == "owner" or not os.path.exists(PORTAL_DB): return a
    try:
        c = sqlite3.connect(f"file:{quote(PORTAL_DB)}?mode=ro", uri=True, timeout=5)
        try: r = c.execute("SELECT name, dept, disabled, deactivated FROM users WHERE id=?", (uid,)).fetchone()
        finally: c.close()
    except sqlite3.Error:
        return a
    if r and not r[2] and not r[3]: a["name"], a["dept"] = (r[0] or uid)[:20], (r[1] or "")[:30]
    return a


def cur():
    return getattr(CUR, "acct", None) or {"uid": "owner", "name": "", "dept": "", "admin": True}  # CLI·시험은 관리자


def owns(p, token):
    """토큰이 맞고, 계정에 연결된 프로필이면 그 계정(또는 관리자)일 때만."""
    if not secrets.compare_digest(p["token"].encode(), str(token or "").encode()): return False
    a = cur()
    return not p.get("account") or p["account"] == a["uid"] or a["admin"]


def mine(people):
    """지금 계정에 연결된 내 프로필(관리자 'owner' 는 포털 계정이 아니라 없음)."""
    a = cur()
    return None if a["uid"] == "owner" else next((p for p in people if p.get("account") == a["uid"]), None)


def need_linked(me):
    if not me.get("account") and not cur()["admin"]:
        raise PermissionError("계정에 연결되지 않은 예전 등록입니다 — 고치거나 지우는 건 관리자만 할 수 있어요(새로 등록하면 계정에 연결된 프로필이 생깁니다)")


def account_info():
    """화면용: 내 계정 이름·부서 + 계정에 연결된 내 프로필(id·token — 같은 계정만 쓸 수 있으니 다른 기기에서도 이어 쓰기)."""
    a = cur(); p = mine(load())
    return {"name": a["name"], "dept": a["dept"], "admin": a["admin"], "no_dept": NO_DEPT if not a["dept"] else "",
            "mine": {"id": p["id"], "token": p["token"], "alias": p["alias"]} if p else None}


def link_accounts():
    """예전 등록(계정 없음)을 이름+부서가 정확히 한 계정과 같을 때만 연결. 개수만 돌려줌(실명 출력 안 함)."""
    import sqlite3
    c = sqlite3.connect(f"file:{quote(PORTAL_DB)}?mode=ro", uri=True, timeout=5)
    try: users = c.execute("SELECT id, name, dept FROM users WHERE COALESCE(disabled,0)=0 AND deactivated IS NULL").fetchall()
    finally: c.close()
    out = {"linked": 0, "unlinked": 0, "already": 0}
    with LOCK:
        people = load(); taken = {p["account"] for p in people if p.get("account")}
        for p in people:
            if p.get("account"): out["already"] += 1; continue
            hit = [u for u in users if (u[1] or "").strip() == p["name"].strip() and (u[2] or "").strip() == p["dept"].strip()]
            if len(hit) == 1 and hit[0][0] not in taken:
                p["account"] = hit[0][0]; taken.add(hit[0][0]); out["linked"] += 1
            else:
                out["unlinked"] += 1
        save(people)
    return out


def admin_people():
    if not cur()["admin"]: raise PermissionError("관리자만")
    return [{"id": p["id"], "name": p["name"], "dept": p["dept"], "alias": p["alias"], "account": p.get("account"), "created": p.get("created")} for p in load()]


def admin_fix(req):
    """관리자: 프로필 지우기(action=delete) 또는 계정 연결(action=link, account=<포털 아이디>) — 연결하면 이름·부서를 그 계정 것으로."""
    if not cur()["admin"]: raise PermissionError("관리자만")
    with LOCK:
        people = load(); p = find(people, req.get("pid"))
        if not p: raise ValueError("없는 프로필")
        if req.get("action") == "delete":
            return drop(people, p["id"])
        if req.get("action") != "link": raise ValueError("action 은 delete·link")
        uid = str(req.get("account") or "")
        a = account(uid)
        if not a["dept"]: raise ValueError("부서가 정해진 포털 계정이 아닙니다")
        if any(x.get("account") == uid and x is not p for x in people): raise ValueError("그 계정에는 이미 프로필이 있습니다")
        p.update({"account": uid, "name": a["name"], "dept": a["dept"]}); save(people)
    return {"ok": True}


def public(p, reveal=False):
    keys = ["id", "alias", "dept", "age_band", "day_master", "dm_el", "elements", "ten_gods", "strength", "mbti", "zodiac", "blood", "dominant", "lacking", "hobbies", "traits", "gyeok", "yong", "power"]
    d = {k: p.get(k) for k in keys}
    if reveal: d["name"] = p["name"]
    return d


AXES = ["에너지", "말", "계획", "주도", "새로움", "인원", "승부", "유머", "술", "일얘기"]
AXIS_LABEL = {"에너지": ("활발·시끌", "차분·조용"), "말": ("수다 담당", "듣는 담당"), "계획": ("즉흥", "계획대로"),
              "주도": ("이끄는 편", "따라가는 편"), "새로움": ("새 시도", "익숙한 곳"), "인원": ("소수 정예", "많을수록"),
              "승부": ("이기고 싶음", "즐기면 됨"), "유머": ("드립 환영", "진지한 대화"), "술": ("있는 모임", "없는 모임"),
              "일얘기": ("해도 됨", "금지")}
HOBBIES = "볼링 등산 러닝 보드게임 당구 맛집 카페 영화 독서 사진 자전거 낚시 골프 테니스 배드민턴 풋살 탁구 노래방".split()


def prefs(req):
    """취미 태그 + 성향(-1 왼쪽 / 0 상관없음 / 1 오른쪽) + 원하는 상대 성향."""
    hob = [h.strip()[:12] for h in (req.get("hobbies") or []) if h.strip()][:15]
    ax = lambda d: {a: max(-1, min(1, int((d or {}).get(a, 0) or 0))) for a in AXES}
    return {"hobbies": hob, "traits": ax(req.get("traits")), "wants": ax(req.get("wants"))}


def update_prefs(req):
    with LOCK:
        people = load(); me = find(people, req.get("id"))
        if not me or not owns(me, req.get("token")): raise ValueError("권한 없음")
        need_linked(me)
        me.update(prefs(req)); save(people)
    return {"ok": True, **prefs(req)}


def fits(viewer, host):
    """양방향: 상대가 원하는 성향과 내 성향이 반대면 탈락. 0(상관없음)은 통과."""
    return all(host["wants"][a] * viewer["traits"][a] >= 0 and viewer["wants"][a] * host["traits"][a] >= 0 for a in AXES)


# ── 번개 ─────────────────────────────────────────────────────────────────
BUNGAE = os.path.join(DATA, "bungae.json")


def load_b():
    try:
        with open(BUNGAE, encoding="utf-8") as f: return json.load(f)
    except FileNotFoundError:
        return []


def save_b(items):
    os.makedirs(DATA, exist_ok=True)
    with open(BUNGAE + ".tmp", "w", encoding="utf-8") as f: json.dump(items, f, ensure_ascii=False, indent=1)
    os.replace(BUNGAE + ".tmp", BUNGAE)


def now_kst():
    return datetime.utcnow() + timedelta(hours=9)


def create_bungae(req):
    people = load(); host = find(people, req.get("id"))
    if not host or not owns(host, req.get("token")): raise ValueError("권한 없음")
    title, place = (req.get("title") or "").strip()[:40], (req.get("place") or "").strip()[:40]
    hobby = (req.get("hobby") or "").strip()[:12]
    if not (title and place and hobby): raise ValueError("제목·장소·취미 태그는 필수")
    mins = int(req.get("minutes") or 60)
    if not 5 <= mins <= 60 * 24 * 7: raise ValueError("시간은 5분~7일")
    b = {"id": secrets.token_hex(3), "host": host["id"], "title": title, "place": place, "hobby": hobby,
         "at": (now_kst() + timedelta(minutes=mins)).isoformat(timespec="minutes"),
         "cap": max(2, min(30, int(req.get("cap") or 4))), "members": [host["id"]]}
    with LOCK:
        items = load_b(); items.append(b); save_b(items)
    return b


def list_bungae(pid, token):
    people, me = auth(pid, token)
    byid = {p["id"]: p for p in people}
    cutoff = (now_kst() - timedelta(hours=3)).isoformat(timespec="minutes")
    out = []
    for b in load_b():
        host = byid.get(b["host"])
        if not host or b["at"] < cutoff: continue
        joined = pid in b["members"]
        if not joined:  # ponytail: 취미 태그 일치 + 양방향 성향 필터. 안 맞으면 목록에 아예 안 뜸
            if b["hobby"] not in me["hobbies"] or not fits(me, host) or len(b["members"]) >= b["cap"]: continue
        score, why = compat(me, host) if host["id"] != pid else (100, [])
        reach = sum(1 for p in people if p["id"] != host["id"] and b["hobby"] in p["hobbies"] and fits(p, host)) if host["id"] == pid else None
        out.append({**b, "joined": joined, "mine": host["id"] == pid, "score": score, "why": why, "reach": reach,
                    "host_name": f"{host['alias']} · {host['dept']}",
                    "members": [{"id": m, "name": byid[m]["name"] if joined else byid[m]["alias"], "dept": byid[m]["dept"]}
                                for m in b["members"] if m in byid]})
    out.sort(key=lambda x: (not x["mine"], not x["joined"], -x["score"]))
    return out


def join_bungae(req, leave=False):
    people = load(); me = find(people, req.get("id"))
    if not me or not owns(me, req.get("token")): raise ValueError("권한 없음")
    with LOCK:
        items = load_b(); b = next((x for x in items if x["id"] == req.get("bid")), None)
        if not b: raise ValueError("없는 번개")
        if leave:
            if b["host"] == me["id"]: items.remove(b)
            elif me["id"] in b["members"]: b["members"].remove(me["id"])
        else:
            host = find(people, b["host"])
            if b["hobby"] not in me["hobbies"] or not fits(me, host): raise ValueError("취미·성향 조건이 맞지 않는 번개")
            if len(b["members"]) >= b["cap"]: raise ValueError("정원 마감")
            if me["id"] not in b["members"]: b["members"].append(me["id"])
        save_b(items)
    return {"ok": True}


def register(req):
    a = cur()  # 이름·부서는 포털 계정 것(요청값은 안 씀), 한 계정 = 내 프로필 1건
    if not a["dept"] or a["uid"] == "owner": raise PermissionError(NO_DEPT)
    name, dept = a["name"], a["dept"]
    y, m, d = int(req["year"]), int(req["month"]), int(req["day"])
    if not 1920 <= y <= date.today().year: raise ValueError("연도 범위")
    hh = req.get("hour"); hh = None if hh in (None, "", "unknown") else int(hh)
    mi = int(req.get("minute") or 0)
    if hh is not None and not 0 <= hh <= 23: raise ValueError("시각 범위")
    mbti = (req.get("mbti") or "").upper().strip()
    if mbti and not re.fullmatch(r"[EI][NS][TF][JP]", mbti): raise ValueError("MBTI 형식")
    blood = (req.get("blood") or "").upper().strip()
    if blood and blood not in ("A", "B", "O", "AB"): raise ValueError("혈액형")
    gender = (req.get("gender") or "").upper().strip() or None
    if gender and gender not in ("M", "F"): raise ValueError("성별")
    r = saju.calc(y, m, d, hh, mi)
    pillars = r["pillars"]
    p = saju.analyze(pillars, gender, r["utc"], r["prev_term"], r["next_term"])
    p["pillars"] = [ganzi(x) for x in pillars]
    p["lmt"] = r["lmt"].strftime("%H:%M") if hh is not None else None
    p["birth_year"] = y  # 대운 나이 계산용
    seed = secrets.randbelow(len(ADJ) * len(ANI))
    age = date.today().year - y
    rec = {"id": secrets.token_hex(4), "token": secrets.token_hex(16), "name": name, "dept": dept,
           "age_band": f"{(age // 10) * 10}대", "alias": f"{ADJ[seed % len(ADJ)]} {ANI[seed // len(ADJ)]}",
           "mbti": mbti or None, "blood": blood or None, "zodiac": zodiac(m, d), "hour_known": hh is not None,
           "day_branch": pillars[2][1], "consent_global": bool(req.get("consent_global", True)),
           "created": date.today().isoformat(), **prefs(req), **p}
    # 생년월일시 원본·성별은 저장 안 함. 4주(8자)·분석 결과·출생 연도만 남김 (8자로 생일 역산은 가능 — README 참고)
    rec["account"] = a["uid"]
    with LOCK:
        for old in [p for p in load() if p.get("account") == a["uid"]]:  # 다시 등록 = 내 예전 프로필을 바꿔 끼움
            drop(load(), old["id"])
        people = load(); people.append(rec); save(people)
    return {"id": rec["id"], "token": rec["token"], "alias": rec["alias"],
            "pillars": p["pillars"], "profile": p, "zodiac": rec["zodiac"]}


def find(people, pid):
    return next((p for p in people if p["id"] == pid), None)


def match(pid, token, scope, filters):
    people, me = auth(pid, token)
    cands = [p for p in people if p["id"] != pid and (p.get("account") or cur()["admin"])]  # 미연결 등록은 매칭 후보에서 뺌
    if scope == "dept":
        a = cur()
        if not a["dept"]: raise PermissionError(NO_DEPT)
        if me.get("account") != a["uid"]: raise PermissionError("우리 팀(실명) 매칭은 계정에 연결된 내 프로필로만 볼 수 있어요")
        cands = [p for p in cands if p["dept"] == a["dept"]]
    else: cands = [p for p in cands if p.get("consent_global")]
    for k in ("age_band", "dept", "mbti", "dm_el", "blood"):
        if filters.get(k): cands = [p for p in cands if p.get(k) == filters[k]]
    if scope != "dept" and len(cands) < 3:  # ponytail: k=3. 팀 내는 실명이라 불필요
        raise ValueError("조건에 맞는 사람이 3명 미만이라 익명 보호를 위해 결과를 보여주지 않습니다")
    if not cands: raise ValueError("아직 등록된 팀원이 없습니다")
    out = []
    for p in cands:
        s, why = compat(me, p)
        out.append({**public(p, reveal=scope == "dept"), "score": s, "why": why})
    out.sort(key=lambda x: -x["score"])
    return out[:10]


def graph(dept, viewer=None, owner=False):
    """dept 가 있으면 실명 팀 지도 — 그 부서에 등록한 본인(viewer, id+token 확인됨)이나 owner 만.
    dept 가 없으면 회사 전체 — consent_global 인 사람만 별명으로. depts 목록은 볼 수 있는 부서만."""
    everyone = load(); a = cur()
    if dept and not owner:
        if not a["dept"]: raise PermissionError(NO_DEPT)
        if dept != a["dept"] or not mine(everyone):
            raise PermissionError("부서 지도는 포털 계정 부서의 것만, 그 계정으로 등록한 뒤 볼 수 있습니다")
    shown = everyone if owner else [p for p in everyone if p.get("account")]  # 미연결(주인 없는) 등록은 관리자에게만
    people = [p for p in shown if (p["dept"] == dept if dept else p.get("consent_global"))]
    nodes = [public(p, reveal=bool(dept)) for p in people]
    edges = []
    for i in range(len(people)):
        for j in range(i + 1, len(people)):
            s, why = compat(people[i], people[j])
            edges.append({"a": people[i]["id"], "b": people[j]["id"], "score": s, "why": why})
    balance = {e: sum(p["elements"][e] for p in people) for e in EL}
    depts = sorted({p["dept"] for p in everyone}) if owner else [a["dept"]] if a["dept"] and mine(everyone) else []
    return {"nodes": nodes, "edges": edges, "balance": balance, "depts": depts}


def today(pid, token):
    _, me = auth(pid, token)
    r = today_rule(me)
    cache = os.path.join(DATA, f"today-{r['date']}.json")
    try:
        with open(cache, encoding="utf-8") as f: c = json.load(f)
    except FileNotFoundError:
        c = {}
    if pid not in c:
        out = {"text": FALLBACK[r["theme"]], "research": r["research"], "collab": r["collab"], "menu_why": f"오늘 기운 {r['day_el']}({EL_WORK[r['day_el']]})에 맞춘 메뉴", "llm": False}
        try:
            raw = llm(f"{describe(me)}\n오늘 일진 {r['day']}({r['day_god']}, 12운성 {r['unseong']}), 올해 세운 {r['year']['ganzi']}({r['year']['god']}), 이달 월운 {r['month']['ganzi']}({r['month']['god']}).\n"
                      f"오늘 테마: {r['theme_work']}, 컨디션 {r['stars']}/5, 협업 기운: {r['collab']}, 추천 점심: {r['menu']}.\n"
                      "아래 4줄을 정확히 이 접두어로 시작해서 써라. 각 줄 45자 이내, 연구원 대상, 구체적으로.\n"
                      "팁: (오늘 업무 팁)\n연구: (오늘의 연구 운, 어떤 연구 활동이 잘 풀리는지)\n협업: (오늘의 협업 운)\n점심: (추천 메뉴를 왜 오늘 먹으면 좋은지 한 줄)", timeout=180)
            for line in raw.splitlines():
                k, _, v = line.partition(":")
                k, v = k.strip().lstrip("-•* "), v.strip()
                if not v: continue
                if k == "팁": out["text"] = v
                elif k == "연구": out["research"] = v
                elif k == "협업": out["collab"] = v
                elif k == "점심": out["menu_why"] = v
            out["llm"] = True
        except Exception:
            pass
        c[pid] = out
        if out["llm"]:  # 폴백은 캐시 안 함 → LLM 붙으면 다시 생성
            with LOCK:
                with open(cache, "w", encoding="utf-8") as f: json.dump(c, f, ensure_ascii=False)
    return {**r, **c[pid]}


def reading(pid, token):
    people = load(); me = find(people, pid)
    if not me or not owns(me, token): raise ValueError("권한 없음")
    if not me.get("reading"):
        try:
            work = llm(f"{describe(me)}\n이 사람의 (1) 일하는 스타일 (2) 팀에서 잘 맞는 역할 (3) 주의할 점 (4) 잘 맞는 동료 유형을 "
                       "각각 한두 문장으로, 소제목 없이 문단 4개로. 분포 숫자를 근거로 구체적으로. 총 300자 이내.")
            myeong = llm(f"{describe_myeongri(me)}\n위 원국을 명리 용어를 써서 해설하라. 순서: 일간의 성정과 강약 → 격국의 의미 → 용신·희신·기신과 그 이유 → "
                         "원국 합충형파해와 공망이 주는 영향 → 현재와 다음 대운의 흐름. 단정보다 '~한 경향', 건강·금전·연애 언급 금지, 문단 5개, 총 500자 이내.",
                         system="너는 명리학 해설가다. 정통 자평명리 관점으로 근거를 들어 설명한다. 한국어 존댓말.")
            me["reading"] = work + "\n\n§\n\n" + myeong
        except Exception as e:  # LLM 없으면 규칙 문장, 저장은 안 함 (나중에 LLM 붙으면 다시 생성)
            return {"reading": f"핵심 성향 {EL_WORK[me['dm_el']]}, 주된 역할 {TEN_WORK[max(me['ten_gods'], key=me['ten_gods'].get)]}. (LLM 미연결: {type(e).__name__})"}
        with LOCK:
            people = load(); find(people, pid).update(reading=me["reading"]); save(people)
    return {"reading": me["reading"]}


FORTUNE = os.path.join(DATA, "fortune")  # <id>.json: 사주 풀이 글 캐시 {gender, model, ts, text}
JOBS = {}  # id → {"done": [...], "total": n, "error": str|None}


def auth(pid, token):
    people = load(); me = find(people, pid)
    if not me or not owns(me, token): raise ValueError("권한 없음")
    return people, me


def fortune_cache(pid):
    try:
        with open(os.path.join(FORTUNE, pid + ".json"), encoding="utf-8") as f: return json.load(f)
    except FileNotFoundError:
        return None


def fortune_status(pid, token):
    import report
    _, me = auth(pid, token)
    c, j = fortune_cache(pid), JOBS.get(pid)
    return {"ready": bool(c), "gender": c["gender"] if c else None, "model": c and c.get("model"), "ts": c and c.get("ts"),
            "running": bool(j and j["running"]), "done": len(j["done"]) if j else 0, "total": j["total"] if j else 0,
            "error": j and j.get("error"), "guess_gender": report.guess_gender(me)}


def fortune_start(req):
    """사주 풀이 글을 백그라운드로 쓴다 (섹션 15개, gemma4:31b 기준 2~3분). 같은 성별로 이미 있으면 regen 일 때만 다시."""
    import fortune, report
    pid, gender = req.get("id"), (req.get("gender") or "").upper() or None
    if gender not in (None, "M", "F"): raise ValueError("성별")
    _, me = auth(pid, req.get("token"))
    c = fortune_cache(pid)
    if JOBS.get(pid, {}).get("running") or (c and c["gender"] == gender and not req.get("regen")):
        return fortune_status(pid, req.get("token"))
    keys = [k for k, _, _ in fortune.SECTIONS]
    job = JOBS[pid] = {"done": [], "total": len(keys), "running": True, "error": None}

    def run():
        try:
            text = fortune.write(report.record_view(me, gender), llm, keys, on_done=job["done"].append)
            errs = [v for k, v in text.items() if k.endswith(":error")]
            text = {k: v for k, v in text.items() if not k.endswith(":error")}
            if not text: raise RuntimeError(errs[0] if errs else "LLM 응답 없음")
            os.makedirs(FORTUNE, exist_ok=True)
            with open(os.path.join(FORTUNE, pid + ".json"), "w", encoding="utf-8") as f:
                json.dump({"gender": gender, "model": MODEL, "ts": datetime.now().isoformat(timespec="minutes"), "text": text}, f, ensure_ascii=False)
            if errs: job["error"] = f"{len(errs)}개 섹션 실패: {errs[0]}"
        except Exception as e:
            job["error"] = f"{type(e).__name__}: {e}"
        job["running"] = False

    threading.Thread(target=run, daemon=True).start()
    return fortune_status(pid, req.get("token"))


def report_html(pid, token):
    import report  # report 가 app 을 import 하므로 지연 import
    people, me = auth(pid, token)
    c = fortune_cache(pid) or {}
    return report.from_record(me, [p for p in people if p["dept"] == me["dept"]], c.get("gender"), c.get("text")).encode()


_status = {"t": 0, "v": None}


def status():
    import time
    if time.time() - _status["t"] > 30:
        try:
            names = models_list()
            _status["v"] = {"llm": True, "model": MODEL, "model_found": MODEL in names or any(n.startswith(MODEL) for n in names)}
        except Exception as e:
            _status["v"] = {"llm": False, "model": MODEL, "error": type(e).__name__}
        _status["t"] = time.time()
    return _status["v"]


def models_list():
    hdr = {"Authorization": "Bearer " + API_KEY} if API_KEY else {}
    if LLM_API == "openai":
        with urllib.request.urlopen(urllib.request.Request(BASE + "/models", headers=hdr), timeout=3) as r:
            return [m["id"] for m in json.load(r)["data"]]
    with urllib.request.urlopen(BASE + "/api/tags", timeout=3) as r:
        return [m["name"] for m in json.load(r)["models"]]


def me_info(pid, token):
    p = find(load(), pid)
    if not p or not owns(p, token): raise ValueError("권한 없음")
    full = {k: p[k] for k in ("pillars", "tens", "power", "support_ratio", "deukryeong", "rooted", "gyeok", "gyeok_god", "yong", "hui", "gi",
                              "yong_why", "johu", "gongmang", "gongmang_hit", "relations", "daeun", "unseong_day", "dm_yin", "lmt", "hour_known", "birth_year") if k in p}
    return {**public(p, reveal=True), **full, "wants": p["wants"], "consent_global": p["consent_global"], "linked": bool(p.get("account"))}


def delete(pid, token):
    with LOCK:
        people = load(); me = find(people, pid)
        if not me or not owns(me, token): raise ValueError("권한 없음")
        need_linked(me)
        return drop(people, pid)


def drop(people, pid):
    """프로필 하나와 딸린 것(풀이 캐시·오늘의 운 캐시·번개)을 지움 — LOCK 안에서 부를 것."""
    save([p for p in people if p["id"] != pid])
    try: os.remove(os.path.join(FORTUNE, pid + ".json"))
    except FileNotFoundError: pass
    JOBS.pop(pid, None)
    for cache in glob.glob(os.path.join(DATA, "today-*.json")):  # 오늘의 운 캐시에서도 그 사람 항목을 지운다
        try:
            with open(cache, encoding="utf-8") as f: c = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(c, dict) and pid in c:
            del c[pid]
            with open(cache + ".tmp", "w", encoding="utf-8") as f: json.dump(c, f, ensure_ascii=False)
            os.replace(cache + ".tmp", cache)
    items = [b for b in load_b() if b["host"] != pid]
    for b in items: b["members"] = [m for m in b["members"] if m != pid]
    save_b(items)
    return {"ok": True}


# ── HTTP ─────────────────────────────────────────────────────────────────

# ── 저작권 표기 (LICENSE·NOTICE 참고) ─────────────────────────────────────
_SIG = __import__("base64").b64decode("wqkgMjAyNiBnZ2dnODY1NyDCtyBkb25nanVraW0uZGV2QGdtYWlsLmNvbQ==").decode()
_SIG_A = __import__("base64").b64decode("Z2dnZzg2NTcgPGRvbmdqdWtpbS5kZXZAZ21haWwuY29tPg==").decode()


def signed(html):
    """화면에 저작권 표기를 붙인다. ui.html 에서 지워져도 서버가 내보낼 때 다시 붙는다."""
    name, mail = _SIG.split(" · ")
    if 'name="author"' not in html:
        meta = f'<meta name="author" content="{name[7:]} <{mail}>">'
        html = html.replace("<head>", "<head>" + meta, 1) if "<head>" in html else meta + html
    if "data-sig" not in html:
        tag = (f'<!-- {_SIG} --><div data-sig title="{mail}" style="text-align:center;font-size:11px;color:#9aa0a6;'
               f'opacity:.55;margin:28px 0 8px">{name} · 내부 시험용 · 배포용 아님</div>')
        html = html.replace("</body>", tag + "</body>", 1) if "</body>" in html else html + tag
    return html


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, body, code=200, ctype="application/json", filename=None):
        b = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("X-Author", _SIG_A)
        if filename: self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + quote(filename))
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def _cred(self, body=None):
        """본인 확인용 id·token — 헤더(X-Saju-Id·X-Saju-Token) 또는 POST 본문. URL 쿼리는 받지 않는다(로그·기록·링크로 샘)."""
        body = body or {}
        return (body.get("id") or self.headers.get("X-Saju-Id") or None,
                body.get("token") or self.headers.get("X-Saju-Token") or None)

    def _owner(self):
        return (self.headers.get("X-Agent-User") or "owner").strip() == "owner"

    def _viewer(self):
        pid, token = self._cred()
        if not pid and not token: return None
        try: return auth(pid, token)[1]
        except ValueError: return None  # 틀린 토큰이면 손님(회사 전체 지도만)

    def _report(self, pid, token, download):
        body = report_html(pid, token)
        return self._send(signed(body.decode()).encode(), ctype="text/html", filename=f"사주리포트_{find(load(), pid)['name']}.html" if download else None)

    def do_GET(self):
        CUR.acct = account((self.headers.get("X-Agent-User") or "owner").strip())
        u = urlparse(self.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}
        q.pop("id", None); q.pop("token", None)  # 쿼리의 id·token 은 무시
        try:
            if u.path == "/api/match": return self._send(match(*self._cred(), q.get("scope", "all"), q))
            if u.path == "/api/graph": return self._send(graph(q.get("dept"), self._viewer(), self._owner()))
            if u.path == "/api/today": return self._send(today(*self._cred()))
            if u.path == "/api/reading": return self._send(reading(*self._cred()))
            if u.path == "/api/bungae": return self._send(list_bungae(*self._cred()))
            if u.path == "/api/me": return self._send(me_info(*self._cred()))
            if u.path == "/api/status": return self._send(status())
            if u.path == "/api/account": return self._send(account_info())
            if u.path == "/api/admin/people": return self._send(admin_people())
            if u.path == "/api/fortune": return self._send(fortune_status(*self._cred()))
            if u.path == "/report": return self._report(*self._cred(), q.get("download"))
            if u.path == "/api/meta": return self._send({"axes": AXES, "labels": AXIS_LABEL, "hobbies": HOBBIES})
            with open(os.path.join(ROOT, "ui.html"), encoding="utf-8") as f: return self._send(signed(f.read()).encode(), ctype="text/html")
        except PermissionError as e:
            self._send({"error": str(e)}, 403)
        except ValueError as e:
            self._send({"error": str(e)}, 400)
        except Exception as e:
            self._send({"error": f"{type(e).__name__}: {e}"}, 500)

    def do_POST(self):
        CUR.acct = account((self.headers.get("X-Agent-User") or "owner").strip())
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        try:
            if self.path == "/report":  # 화면이 새 창으로 여는 리포트 — 폼 본문(id·token·download)으로 받는다
                f = {k: v[0] for k, v in parse_qs(raw.decode("utf-8", "replace")).items()}
                return self._report(f.get("id"), f.get("token"), f.get("download"))
            try:
                req = json.loads(raw or b"{}")
            except ValueError:
                return self._send({"error": "잘못된 요청 (JSON 이 아님)"}, 400)
            if not isinstance(req, dict): return self._send({"error": "잘못된 요청 (JSON 객체여야 함)"}, 400)
            pid, token = self._cred(req)
            req = {**req, "id": pid, "token": token}
            if self.path == "/api/register": return self._send(register(req))
            if self.path == "/api/admin/fix": return self._send(admin_fix(req))
            if self.path == "/api/delete": return self._send(delete(req.get("id"), req.get("token")))
            if self.path == "/api/prefs": return self._send(update_prefs(req))
            if self.path == "/api/fortune": return self._send(fortune_start(req))
            if self.path == "/api/bungae": return self._send(create_bungae(req))
            if self.path == "/api/bungae/join": return self._send(join_bungae(req))
            if self.path == "/api/bungae/leave": return self._send(join_bungae(req, leave=True))
            self._send({"error": "no route"}, 404)
        except PermissionError as e:
            self._send({"error": str(e)}, 403)
        except (ValueError, KeyError) as e:
            self._send({"error": f"입력 오류: {e}"}, 400)
        except Exception as e:
            self._send({"error": f"{type(e).__name__}: {e}"}, 500)


if __name__ == "__main__" and sys.argv[1:] == ["--link-accounts"]:  # 예전 등록을 포털 계정에 연결(한 번) — 개수만 출력
    print(json.dumps(link_accounts(), ensure_ascii=False)); sys.exit(0)
if __name__ == "__main__":
    print(f"팀 밸런스 맵 → http://localhost:{PORT}  (api={LLM_API} base={BASE} model={MODEL})  {_SIG}")
    ThreadingHTTPServer((os.environ.get("BIND", "127.0.0.1"), PORT), __import__("portal_auth").install(H, "saju-local")).serve_forever()
