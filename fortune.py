"""사주 풀이(운세) 섹션 — 규칙으로 근거를 뽑고, LLM 이 근거만 가지고 쉬운 말로 길게 풀어 쓴다.
   report.py(HTML 리포트)와 app.py(/api/fortune)가 쓴다. LLM 이 없으면 근거 문장만 보여준다.
   a: saju.analyze 결과 + pillars(간지 문자열)·raw(인덱스)·birth_year·age·gender(M/F/None)·daeun 이 들어 있는 dict."""
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
import saju
from saju import STEMS, BRANCHES, EL, STEM_EL, BR_EL, TEN, ganzi, branch_rel, unseong

EL_PLAIN = {"목": "나무(성장·기획·인자함)", "화": "불(열정·표현·예의)", "토": "흙(안정·신용·중재)", "금": "쇠(결단·원칙·의리)", "수": "물(지혜·유연·소통)"}
TEN_PLAIN = {"비겁": "나와 같은 기운 — 자존심·독립심·친구·형제·경쟁자", "식상": "내가 낳는 기운 — 표현력·재능·아이디어·자녀(여성)",
             "재성": "내가 다스리는 기운 — 돈·현실감각·성과·아버지·아내(남성)", "관성": "나를 다스리는 기운 — 직장·명예·규칙·책임·남편(여성)",
             "인성": "나를 돕는 기운 — 공부·자격증·문서·어머니·후원"}
TEN10_PLAIN = {"비견": "어깨를 나란히 하는 친구, 독립심", "겁재": "경쟁하는 동료, 승부욕·나눠 쓰는 돈", "식신": "느긋하게 즐기며 만드는 재능, 먹을 복",
               "상관": "날카로운 말재주와 반골 기질, 틀을 깨는 재능", "편재": "크게 굴리는 돈, 사업·투자 감각", "정재": "꼬박꼬박 모으는 돈, 월급·성실",
               "편관": "강한 압박과 카리스마, 위기 돌파력", "정관": "바른 직장과 명예, 규칙과 신뢰", "편인": "독특한 직관과 비주류 지식, 눈치",
               "정인": "정통 공부와 자격, 어머니 같은 후원"}
ORGAN = {"목": "간·담낭·눈·근육·힘줄(목·어깨 뭉침)", "화": "심장·소장·혈압·혈액순환·수면", "토": "위장·비장·소화기·피부 트러블",
         "금": "폐·대장·기관지·피부·비염", "수": "신장·방광·허리·뼈·귀·생식기·호르몬"}
JOB_EL = {"목": "교육·출판·기획·디자인·환경·의류·인사", "화": "방송·미디어·IT·전기·에너지·마케팅·공연", "토": "부동산·건설·중개·농업·컨설팅·공무 조정 업무",
          "금": "금융·법률·기계·자동차·군경·의료기기·품질 관리", "수": "무역·유통·물류·연구·학문·상담·여행·수산"}
JOB_TEN = {"비겁": "독립·자영업·프리랜서·스포츠·동업", "식상": "연구·예술·콘텐츠·강의·요리·기술 개발", "재성": "사업·영업·금융·유통·경영 관리",
           "관성": "공직·대기업 조직·법·군경·관리직", "인성": "교육·학계·연구원·의료·자격 기반 전문직·출판"}
LUCK = {"목": dict(색="초록·청록", 방향="동쪽", 숫자="3·8", 계절="봄", 맛="신맛(레몬·식초·매실)", 활동="산책·식물 키우기·새 공부 시작·아침 운동"),
        "화": dict(색="빨강·주황·보라", 방향="남쪽", 숫자="2·7", 계절="여름", 맛="쓴맛(커피·녹차·쑥)", 활동="햇볕 쬐기·발표·공연 관람·사람 만나기"),
        "토": dict(색="노랑·베이지·갈색", 방향="중앙(집 안 정돈)", 숫자="5·10", 계절="환절기", 맛="단맛(고구마·호박·꿀)", 활동="등산·도자기·정리정돈·규칙적인 식사"),
        "금": dict(색="흰색·은색·금색", 방향="서쪽", 숫자="4·9", 계절="가을", 맛="매운맛(생강·무·마늘)", 활동="악기·근력 운동·버릴 것 버리기·계획표 쓰기"),
        "수": dict(색="검정·남색", 방향="북쪽", 숫자="1·6", 계절="겨울", 맛="짠맛(해조류·검은콩)", 활동="수영·물가 산책·독서·명상·충분한 잠")}
UNSEONG_PLAIN = {"장생": "막 태어난 듯 새로 시작하는 힘", "목욕": "들뜨고 꾸미는 시기, 변화·유혹", "관대": "의욕 넘치는 청년기", "건록": "제 힘으로 서는 전성기",
                 "제왕": "힘이 가장 센 정점", "쇠": "노련하지만 힘이 빠지기 시작", "병": "기운이 약해져 쉬어야 할 때", "사": "멈추고 정리하는 때",
                 "묘": "창고에 넣어 두듯 모으고 숨는 때", "절": "끊고 새로 바뀌는 때", "태": "새 씨앗이 생기는 때", "양": "보살핌 속에 자라는 때"}
REL_PLAIN = {"육합": "짝이 맞아 잘 붙는", "삼합": "뜻이 모여 힘을 합치는", "방합": "같은 방향으로 뭉치는", "충": "정면으로 부딪혀 변동이 생기는",
             "형": "마찰·시비가 생기는", "파": "약속이 어긋나는", "해": "오해·서운함이 생기는", "자형": "스스로를 괴롭히는", "같음": "같은 글자가 겹치는"}

# 신살·귀인 (일간 / 일지·년지 삼합 기준)
CHEONEUL = {0: (1, 7), 4: (1, 7), 6: (1, 7), 1: (0, 8), 5: (0, 8), 2: (11, 9), 3: (11, 9), 7: (2, 6), 8: (5, 3), 9: (5, 3)}
MUNCHANG = {0: 5, 1: 6, 2: 8, 3: 9, 4: 8, 5: 9, 6: 11, 7: 0, 8: 2, 9: 3}
HONGYEOM = {0: 6, 1: 6, 2: 2, 3: 7, 4: 4, 5: 4, 6: 10, 7: 9, 8: 0, 9: 8}
YANGIN = {0: 3, 2: 6, 4: 6, 6: 9, 8: 0}
SAMHAP = {8: 0, 0: 0, 4: 0, 2: 1, 6: 1, 10: 1, 5: 2, 9: 2, 1: 2, 11: 3, 3: 3, 7: 3}  # 신자진 / 인오술 / 사유축 / 해묘미
YEOKMA, DOHWA, HWAGAE = (2, 8, 11, 5), (9, 3, 6, 0), (4, 10, 1, 7)
SINSAL_PLAIN = {"천을귀인": "어려울 때 나타나는 도움의 손길, 인덕", "문창귀인": "글·공부·시험 머리", "도화": "사람을 끄는 매력·인기·이성운",
                "역마": "이동·출장·이사·해외와 인연", "화개": "예술·종교·철학·혼자 깊이 파는 기질", "홍염": "끼와 색기, 이성에게 주는 강한 인상",
                "양인": "칼처럼 강한 결단력과 승부욕(과하면 다툼·다침 주의)"}


def raw_of(a):
    return a.get("raw") or [[STEMS.index(g[0]), BRANCHES.index(g[1])] if g else None for g in a["pillars"]]


def ten_power(a):
    dm = EL.index(a["dm_el"]); out = {t: 0.0 for t in TEN}
    for e, v in a["power"].items(): out[TEN[(EL.index(e) - dm) % 5]] += v
    tot = sum(out.values()) or 1
    return {t: round(v / tot * 100) for t, v in out.items()}


def ten10_list(a):
    """원국에 드러난 십신(천간 + 지지 본기)과 숨은 십신(지장간)"""
    shown, hidden = [], []
    for n, t in a["tens"].items():
        if t["stem"]: shown.append((f"{n}간", t["stem"]))
        if t["branch"]: shown.append((f"{n}지", t["branch"]))
        hidden += [(f"{n}지 속", h) for _, h in t["hidden"][:-1]]
    return shown, hidden


def sinsal(a):
    raw = raw_of(a); ds, db, yb = raw[2][0], raw[2][1], raw[0][1]
    brs = [(n, p[1]) for n, p in zip("년월일시", raw) if p]
    out = []
    for n, b in brs:
        if b in CHEONEUL[ds]: out.append(("천을귀인", n))
        if b == MUNCHANG[ds]: out.append(("문창귀인", n))
        if b == HONGYEOM[ds]: out.append(("홍염", n))
        if YANGIN.get(ds) == b: out.append(("양인", n))
        for base in {db, yb}:
            g = SAMHAP[base]
            if b == YEOKMA[g] and n != ("일" if base == db else "년"): out.append(("역마", n))
            if b == DOHWA[g] and n != ("일" if base == db else "년"): out.append(("도화", n))
            if b == HWAGAE[g] and n != ("일" if base == db else "년"): out.append(("화개", n))
    seen, uniq = set(), []
    for k, n in out:
        if (k, n) not in seen: seen.add((k, n)); uniq.append((k, n))
    return uniq


def year_hits(a, br):
    """그해(그달) 지지가 불러오는 신살"""
    raw = raw_of(a); ds, db = raw[2][0], raw[2][1]; g = SAMHAP[db]
    return [k for k, ok in (("천을귀인", br in CHEONEUL[ds]), ("문창귀인", br == MUNCHANG[ds]), ("도화", br == DOHWA[g]),
                            ("역마", br == YEOKMA[g]), ("화개", br == HWAGAE[g]), ("홍염", br == HONGYEOM[ds])) if ok]


def cycle(a, pp, label):
    """세운·월운 한 칸의 근거"""
    raw = raw_of(a); ds, db, yb = raw[2][0], raw[2][1], raw[0][1]
    s, b = pp
    sg, bg = saju.ten_god10(ds, s), saju.ten_god10(ds, saju.HIDDEN[b][-1][0])
    rel = branch_rel(db, b)[0]; rel_y = branch_rel(yb, b)[0]
    el_s, el_b = EL[STEM_EL[s]], EL[BR_EL[b]]
    tags = []
    for e, where in ((el_s, "천간"), (el_b, "지지")):
        if e == a["yong"]: tags.append(f"{where}에 용신 {e}(나에게 필요한 기운)")
        elif e == a.get("hui"): tags.append(f"{where}에 희신 {e}(돕는 기운)")
        elif e == a["gi"]: tags.append(f"{where}에 기신 {e}(부담 되는 기운)")
    hits = year_hits(a, b)
    return (f"{label} {ganzi(pp)}: 천간 {sg}({TEN10_PLAIN[sg]}), 지지 {bg}({TEN10_PLAIN[bg]}), 내 기운의 상태 12운성 {unseong(ds, b)}({UNSEONG_PLAIN[unseong(ds, b)]})"
            + (f", 배우자 자리(일지)와 {rel}({REL_PLAIN.get(rel, '')})" if rel else "") + (f", 띠(년지)와 {rel_y}" if rel_y else "")
            + (", " + ", ".join(tags) if tags else "") + (", 신살 " + "·".join(hits) if hits else ""))


def cur_daeun(a, age=None):
    d = a.get("daeun"); age = a["age"] if age is None else age
    if not d: return None
    return next((x for x in d["list"] if x["age"] <= age < x["age"] + 10), None)


def love_facts(a):
    import report  # love() 는 report.py 에 있다
    lv = report.love(a)
    if not lv: return ["성별 정보가 없어 배우자별(남성은 재성, 여성은 관성)로 보는 정밀 분석은 생략했다. 일지(배우자 자리)·도화·홍염 중심으로만 본다."], None
    return report.love_text(a, lv) + [f"원국 배우자별 개수 {lv['count']}개", f"해별 연애 점수(2025~2040): " + ", ".join(f"{y} {sc}" for y, gz, age, sc, why in lv["years"])], lv


def facts(a, today=None):
    """섹션 키 → 근거 문장 리스트"""
    today = today or date.today(); Y = today.year
    raw = raw_of(a); ds, db = raw[2][0], raw[2][1]
    tp = ten_power(a); shown, hidden = ten10_list(a); ss = sinsal(a)
    strong = sorted(tp, key=tp.get, reverse=True)
    over = [e for e, v in a["power"].items() if v >= max(a["power"].values()) * 0.85 and v >= 2.5]
    weak = [e for e, v in a["power"].items() if v <= 0.8]
    ss_txt = [f"{k}({n}지) — {SINSAL_PLAIN[k]}" for k, n in ss] or ["원국에 두드러진 신살 없음"]
    ilji = a["tens"]["일"]
    base = [f"원국(태어난 해·달·날·시의 여덟 글자): {' · '.join(x or '시 모름' for x in a['pillars'])}",
            f"일간(나 자신): {a['day_master']}{a['dm_el']} — {EL_PLAIN[a['dm_el']]}, {'음' if a['dm_yin'] else '양'}의 기운",
            f"신강·신약(내 기운의 세기): {a['strength']} (나를 돕는 기운 비율 {a['support_ratio']}), 계절의 힘(득령) {'얻음' if a['deukryeong'] else '못 얻음'}, 뿌리(통근) {'·'.join(a['rooted']) + '지' if a['rooted'] else '없음'}",
            f"격국(타고난 그릇): {a['gyeok']}", f"용신(가장 필요한 기운) {a['yong']}, 희신(돕는 기운) {a['hui']}, 기신(부담 되는 기운) {a['gi']} — {a['yong_why']}",
            "오행 힘: " + ", ".join(f"{e} {v}" for e, v in a["power"].items()),
            "십신 세력(%): " + ", ".join(f"{t} {tp[t]}" for t in strong), f"나이 {a['age']}세" + (f", 성별 {'남성' if a.get('gender') == 'M' else '여성'}" if a.get("gender") else "")]
    cd = cur_daeun(a)
    if cd: base.append(f"현재 대운(10년 운) {cd['ganzi']} ({cd['age']}~{cd['age'] + 9}세): 천간 {cd['stem_god']}, 지지 {cd['branch_god']}, 12운성 {cd['unseong']}")
    lf, lv = love_facts(a)
    F = {}
    F["summary"] = base + ss_txt + [f"원국 관계: {', '.join(a['relations']) or '특별한 합충 없음'}"]
    F["nature"] = [f"일간 {a['day_master']}{a['dm_el']}: {EL_PLAIN[a['dm_el']]}", f"격국 {a['gyeok']} ({a['gyeok_god']})",
                   "드러난 십신: " + ", ".join(f"{w} {t}({TEN10_PLAIN[t]})" for w, t in shown),
                   f"가장 센 십신 무리: {strong[0]}({TEN_PLAIN[strong[0]]}) {tp[strong[0]]}%, 가장 약한 무리: {strong[-1]}({TEN_PLAIN[strong[-1]]}) {tp[strong[-1]]}%",
                   f"일지(속마음·배우자 자리) {BRANCHES[db]}: {ilji['branch']}, 12운성 {ilji['unseong']}({UNSEONG_PLAIN[ilji['unseong']]})", f"신강약: {a['strength']}"] + ss_txt
    F["elements"] = ["오행 힘: " + ", ".join(f"{e}({EL_PLAIN[e]}) {v}" for e, v in a["power"].items()),
                     f"넘치는 오행: {', '.join(over) or '없음'}", f"부족한 오행: {', '.join(weak) or '없음'}" + (f", 아예 없는 오행: {', '.join(a['lacking'])}" if a["lacking"] else ""),
                     f"용신 {a['yong']} · 희신 {a['hui']} · 기신 {a['gi']} — {a['yong_why']}"] + ([f"조후(계절 온도 조절)로 {a['johu']} 기운이 먼저 필요"] if a.get("johu") else [])
    F["career"] = [f"격국 {a['gyeok']}", "십신 세력(%): " + ", ".join(f"{t} {tp[t]}" for t in strong),
                   f"강한 십신이 가리키는 일: {strong[0]} → {JOB_TEN[strong[0]]}; {strong[1]} → {JOB_TEN[strong[1]]}",
                   f"용신 {a['yong']} 분야: {JOB_EL[a['yong']]}", f"희신 {a['hui']} 분야: {JOB_EL[a['hui']]}", f"기신 {a['gi']} 분야(맞지 않을 수 있음): {JOB_EL[a['gi']]}",
                   f"관성(직장·조직) {tp['관성']}%, 식상(재능·표현) {tp['식상']}%, 인성(자격·학문) {tp['인성']}%", f"신강약 {a['strength']}"] + [x for x in ss_txt if "역마" in x or "화개" in x or "문창" in x]
    jae = [f"{w} {t}" for w, t in shown if t in ("정재", "편재")]; jae_h = [f"{w} {t}" for w, t in hidden if t in ("정재", "편재")]
    F["money"] = [f"재성(돈) 세력 {tp['재성']}%, 드러난 재성: {', '.join(jae) or '없음'}, 숨은 재성: {', '.join(jae_h) or '없음'}",
                  f"식상(돈을 만드는 재능) {tp['식상']}% — 식상이 재성을 낳으면(식상생재) 재능으로 버는 구조",
                  f"비겁(돈을 나눠 갖는 경쟁자) {tp['비겁']}% — 비겁이 많으면 돈이 들어와도 나가기 쉬움(군겁쟁재)",
                  f"신강약 {a['strength']} — 신강하면 큰돈을 감당하고, 신약하면 재성이 많을수록 버겁다(재다신약)"]
    mun = [x for x in ss_txt if "문창" in x or "화개" in x]
    F["study"] = [f"인성(공부·자격·문서) {tp['인성']}%, 식상(이해·표현·응용) {tp['식상']}%, 관성(시험·합격·직위) {tp['관성']}%",
                  "드러난 인성: " + (", ".join(f"{w} {t}" for w, t in shown if t in ("정인", "편인")) or "없음"),
                  ("관성과 인성이 함께 있어 관인상생(시험·승진에 유리한 흐름) 가능" if tp["관성"] >= 12 and tp["인성"] >= 12 else "관인상생 구조는 약함")] + (mun or ["문창귀인·화개 없음"]) + \
                 ["앞으로 5년 세운: " + "; ".join(f"{y}년 {ganzi([(y - 4) % 10, (y - 4) % 12])} 천간 {saju.ten_god10(ds, (y - 4) % 10)}" for y in range(Y, Y + 5))]
    F["love"] = lf + [f"일지(배우자 자리) {BRANCHES[db]} {ilji['branch']}, 12운성 {ilji['unseong']}"] + [x for x in ss_txt if any(k in x for k in ("도화", "홍염"))]
    F["marriage"] = lf + [f"일지 관계: {', '.join(r for r in a['relations'] if '일지' in r) or '일지에 합충 없음'}"]
    F["health"] = [f"넘치는 오행 {', '.join(over) or '없음'} → 관련 부위: " + ("; ".join(f"{e}: {ORGAN[e]}" for e in over) or "-"),
                   f"부족한 오행 {', '.join(weak) or '없음'} → 관련 부위: " + ("; ".join(f"{e}: {ORGAN[e]}" for e in weak) or "-"),
                   f"일간 {a['dm_el']} 기본 체질 부위: {ORGAN[a['dm_el']]}", f"기신 {a['gi']}이 강해지는 해에 관련 부위 관리 필요: {ORGAN[a['gi']]}",
                   f"원국 충·형: {', '.join(r for r in a['relations'] if '충' in r or '형' in r) or '없음'}"] + [x for x in ss_txt if "양인" in x]
    F["people"] = [f"비겁(친구·형제·동료) {tp['비겁']}%, 관성(윗사람·조직) {tp['관성']}%, 인성(후원자·어른) {tp['인성']}%, 식상(후배·아랫사람) {tp['식상']}%",
                   f"원국 관계: {', '.join(a['relations']) or '없음'}", f"공망(힘이 비는 자리): {''.join(a['gongmang'])}" + (f", {'·'.join(a['gongmang_hit'])}지가 공망" if a["gongmang_hit"] else "")] + ss_txt + \
                  [f"용신 {a['yong']} 기운이 강한 사람({EL_PLAIN[a['yong']]})이 귀인, 기신 {a['gi']} 기운이 강한 사람은 소모가 클 수 있음"]
    d = a.get("daeun")
    F["daeun"] = ([f"대운 {'순행' if d['forward'] else '역행'}, {d['start_age']}세 시작"] + [f"{x['age']}~{x['age'] + 9}세 {x['ganzi']}: 천간 {x['stem_god']}, 지지 {x['branch_god']}, 12운성 {x['unseong']}"
                  + (" ← 현재" if cd and x is not None and x["age"] == cd["age"] else "") for x in d["list"]]) if d else ["대운 정보 없음(등록 때 성별을 넣지 않음). 세운 중심으로만 본다."]
    for key, y in (("year", Y), ("next_year", Y + 1)):
        cdy = cur_daeun(a, y - a["birth_year"])
        F[key] = [cycle(a, [(y - 4) % 10, (y - 4) % 12], f"{y}년 세운")] + ([f"이 해의 대운 {cdy['ganzi']}(천간 {cdy['stem_god']}, 지지 {cdy['branch_god']})"] if cdy else []) + \
                 [f"용신 {a['yong']} · 기신 {a['gi']}", f"신강약 {a['strength']}"]
        if lv: F[key].append(f"{y}년 연애 점수 " + next((f"{sc} ({' · '.join(why) or '평이'})" for yy, gz, age, sc, why in lv["years"] if yy == y), "-"))
    F["monthly"] = [cycle(a, saju.pillars_of(datetime(Y, m, 20, 12))[1], f"양력 {m}월(절기 기준 대략 {m}월 6일경~다음 달 5일경) 월운") for m in range(1, 13)]
    F["luck"] = [f"용신 {a['yong']}: " + ", ".join(f"{k} {v}" for k, v in LUCK[a["yong"]].items()), f"희신 {a['hui']}: " + ", ".join(f"{k} {v}" for k, v in LUCK[a["hui"]].items()),
                 f"기신 {a['gi']}(줄일 것): 색 {LUCK[a['gi']]['색']}, 방향 {LUCK[a['gi']]['방향']}"] + ([f"조후로 {a['johu']} 보충 우선"] if a.get("johu") else [])
    return F, lv


Y0 = date.today().year
# (키, 제목, 쓰는 법) — 순서가 곧 목차
SECTIONS = [
    ("summary", "한눈에 보는 내 사주", "이 사람의 사주 전체를 처음 보는 사람도 이해하게 요약한다. 소제목: '나는 어떤 사람인가', '내 사주의 강점', '조심할 점', '인생 전체 흐름 한 줄'. 1000~1300자."),
    ("nature", "타고난 성격과 기질", "일간·격국·십신·일지·신살을 근거로 겉으로 보이는 모습과 속마음, 장점과 단점, 스트레스 받을 때 모습, 다른 사람이 보는 나를 풀어 쓴다. 생활 속 예시를 든다. 1300~1700자."),
    ("elements", "오행 균형 — 넘치는 것과 모자란 것", "다섯 기운의 균형을 설명하고, 넘치는 기운·모자란 기운이 생활에서 어떻게 나타나는지, 용신을 어떻게 채우면 좋은지 쓴다. 1000~1300자."),
    ("career", "직업운 · 적성", "잘 맞는 일하는 방식, 추천 직업·분야 5개 이상과 이유, 조직형인지 독립형인지, 승진·이직 시기 감각, 피하면 좋은 업무 환경을 쓴다. 1300~1700자."),
    ("money", "재물운", "돈을 버는 방식(월급형·사업형·재능형), 돈이 새는 패턴, 투자 성향과 주의점, 재물이 모이기 좋은 시기(대운·세운 근거), 실천 팁을 쓴다. 1200~1600자."),
    ("study", "학업운 · 시험운", "공부 스타일(암기·이해·실전형), 잘 맞는 공부법, 자격증·시험·승진시험 운, 앞으로 5년 중 시험에 유리한 해와 이유를 쓴다. 1000~1400자."),
    ("love", "연애운", "연애 스타일, 끌리는 이성 유형, 나에게 잘 맞는 이성 유형, 연애에서 반복되는 패턴과 주의점, 연애운이 들어오는 해를 근거와 함께 쓴다. 1200~1600자."),
    ("marriage", "결혼운 · 배우자", "배우자 자리(일지)로 본 배우자 성향, 결혼 생활의 모습, 결혼 인연이 열리는 시기, 부부 사이 좋게 지내는 법을 쓴다. 1100~1500자."),
    ("health", "건강운", "오행 균형으로 본 약해지기 쉬운 부위와 생활 습관, 계절별·나이대별 관리 포인트, 추천 운동·음식을 쓴다. 첫 문단에 '의학적 진단이 아니며 몸이 불편하면 병원 진료가 먼저'라고 분명히 쓴다. 1000~1300자."),
    ("people", "인간관계 · 귀인", "친구·동료·윗사람·아랫사람과의 관계 패턴, 나를 돕는 귀인 유형, 조심할 사람 유형, 공망·신살의 의미를 쓴다. 1000~1300자."),
    ("daeun", "대운 — 10년 단위 인생 흐름", "대운 하나하나를 '○○~○○세 (간지)' 소제목으로 나눠 각각 3~4문장으로 그 시기의 분위기, 좋은 점, 조심할 점을 쓴다. 현재 대운은 더 자세히. 1600~2200자."),
    ("year", f"{Y0}년 올해 운세", "올해 전체 흐름, 일·직장, 돈, 연애·가족, 건강, 올해 꼭 할 일과 피할 일을 소제목으로 나눠 쓴다. 1300~1700자."),
    ("next_year", f"{Y0 + 1}년 내년 운세", "내년 전체 흐름, 일·직장, 돈, 연애·가족, 건강, 준비할 일을 소제목으로 나눠 쓴다. 1100~1500자."),
    ("monthly", f"{Y0}년 월별 운세", "1월부터 12월까지 '### N월' 소제목 12개로 나눠 각 달 2~3문장(분위기·좋은 일·조심할 일)과 한 줄 팁을 쓴다. 1800~2400자."),
    ("luck", "개운법 — 운을 높이는 생활 습관", "용신·희신을 채우는 색·방향·숫자·음식·활동·인테리어·사람을 구체적으로 추천하고, 기신을 줄이는 방법도 쓴다. 900~1200자."),
]
SYSTEM = ("너는 친절하고 경험 많은 사주 상담가다. 명리 지식이 전혀 없는 사람도 이해하도록 쉬운 말로 풀어서, 옆에서 이야기해 주듯 따뜻하고 자세하게 쓴다. "
          "명리 용어(일간·용신·십신·대운 등)를 쓸 때는 바로 뒤 괄호에 쉬운 뜻을 붙인다. 반드시 주어진 근거 안에서만 해석하고 근거에 없는 사실(글자·나이·사건)을 지어내지 않는다. "
          "'반드시' 같은 단정 대신 '~한 경향', '~하기 쉬워요'처럼 쓴다. 겁주는 말 대신 대처법을 함께 준다. 한국어 존댓말(~해요체). "
          "형식: 마크다운. '### 소제목'으로 나누고, 문단은 3~5문장, 필요한 곳에 '- ' 목록. 머리말·맺음말·제목 반복 없이 본문만.")


def prompt(key, a, F):
    title, how = next((t, h) for k, t, h in SECTIONS if k == key)
    common = "\n".join("- " + x for x in F["summary"][:9])
    return (f"[이 사람의 사주 기본 정보]\n{common}\n\n[이번 주제: {title}]\n[주제 근거]\n" + "\n".join("- " + x for x in F[key])
            + f"\n\n위 근거로 '{title}' 풀이를 써라. {how}")


def write(a, llm, keys=None, workers=3, on_done=None):
    """섹션별 LLM 풀이. llm(user, system=, timeout=) → str. 반환 {key: markdown}. 실패한 섹션은 빠진다."""
    F, _ = facts(a); keys = keys or [k for k, _, _ in SECTIONS]; out = {}

    def one(k):
        try:
            txt = llm(prompt(k, a, F), system=SYSTEM, timeout=600)
            txt = re.sub(r"^\s*#{1,2}\s.*\n", "", txt.strip())  # 모델이 붙인 큰 제목 제거
            out[k] = txt.strip()
        except Exception as e:
            out[k + ":error"] = f"{type(e).__name__}: {e}"
        if on_done: on_done(k)

    with ThreadPoolExecutor(workers) as ex: list(ex.map(one, keys))
    return out


def md_html(md):
    """### 소제목 / - 목록 / **굵게** / 문단 만 지원하는 작은 변환기"""
    import html as H
    out, ul = [], False
    for line in md.splitlines():
        s = line.strip()
        t = H.escape(s); t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        if re.match(r"^[-*•]\s+", s):
            if not ul: out.append("<ul>"); ul = True
            out.append("<li>" + re.sub(r"^[-*•]\s+", "", t) + "</li>"); continue
        if ul: out.append("</ul>"); ul = False
        if not s: continue
        m = re.match(r"^#{3,6}\s*(.+)", t)
        out.append(f"<h3>{m.group(1)}</h3>" if m else f"<p>{t}</p>")
    if ul: out.append("</ul>")
    return "".join(out)
