#!/usr/bin/env python3
"""명리 계산 모듈 (표준 라이브러리만). 태양 황경은 VSOP87D 지구 절단 급수(Meeus 32.A) + 장동·광행차 → 절기 ±1분.
   시간 보정: 한국 표준시 이력(1954-03-21~1961-08-09 UTC+8:30), 서머타임(1948~51, 55~60, 87~88), 동경 127.5° 진태양시."""
import math
from datetime import date, datetime, timedelta

STEMS, BRANCHES = "갑을병정무기경신임계", "자축인묘진사오미신유술해"
EL = ["목", "화", "토", "금", "수"]
STEM_EL = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]
BR_EL = [4, 2, 0, 0, 2, 1, 1, 2, 3, 3, 2, 4]
TEN = ["비겁", "식상", "재성", "관성", "인성"]
TEN10 = [("비견", "겁재"), ("식신", "상관"), ("편재", "정재"), ("편관", "정관"), ("편인", "정인")]  # (음양 같음, 다름)
# 지장간 (여기, 중기, 정기) 와 일수
HIDDEN = {0: [(8, 10), (9, 20)], 1: [(9, 9), (7, 3), (5, 18)], 2: [(4, 7), (2, 7), (0, 16)], 3: [(0, 10), (1, 20)],
          4: [(1, 9), (9, 3), (4, 18)], 5: [(4, 7), (6, 7), (2, 16)], 6: [(2, 10), (5, 9), (3, 11)], 7: [(3, 9), (1, 3), (5, 18)],
          8: [(4, 7), (8, 7), (6, 16)], 9: [(6, 10), (7, 20)], 10: [(7, 9), (3, 3), (4, 18)], 11: [(4, 7), (0, 7), (8, 16)]}
UNSEONG = "장생 목욕 관대 건록 제왕 쇠 병 사 묘 절 태 양".split()
UNSEONG_START = {0: 11, 1: 6, 2: 2, 3: 9, 4: 2, 5: 9, 6: 5, 7: 0, 8: 8, 9: 3}  # 일간별 장생 지지
LIUHE = {frozenset(p) for p in [(0, 1), (2, 11), (3, 10), (4, 9), (5, 8), (6, 7)]}
PO = {frozenset(p) for p in [(0, 9), (1, 4), (2, 11), (3, 6), (5, 8), (10, 7)]}
HAE = {frozenset(p) for p in [(0, 7), (1, 6), (2, 5), (3, 4), (8, 11), (9, 10)]}
HYEONG = {frozenset(p) for p in [(2, 5), (5, 8), (2, 8), (1, 10), (10, 7), (1, 7), (0, 3)]}
SELF_HYEONG = {4, 6, 9, 11}
BANGHAP = {2: "목", 3: "목", 4: "목", 5: "화", 6: "화", 7: "화", 8: "금", 9: "금", 10: "금", 11: "수", 0: "수", 1: "수"}

# ── 태양 황경 (VSOP87D Earth, Meeus 부록) ────────────────────────────────
_L = [
    [(175347046, 0, 0), (3341656, 4.6692568, 6283.07585), (34894, 4.6261, 12566.1517), (3497, 2.7441, 5753.3849), (3418, 2.8289, 3.5231),
     (3136, 3.6277, 77713.7715), (2676, 4.4181, 7860.4194), (2343, 6.1352, 3930.2097), (1324, 0.7425, 11506.7698), (1273, 2.0371, 529.691),
     (1199, 1.1096, 1577.3435), (990, 5.233, 5884.927), (902, 2.045, 26.298), (857, 3.508, 398.149), (780, 1.179, 5223.694),
     (753, 2.533, 5507.553), (505, 4.583, 18849.228), (492, 4.205, 775.523), (357, 2.92, 0.067), (317, 5.849, 11790.629),
     (284, 1.899, 796.298), (271, 0.315, 10977.079), (243, 0.345, 5486.778), (206, 4.806, 2544.314), (205, 1.869, 5573.143),
     (202, 2.458, 6069.777), (156, 0.833, 213.299), (132, 3.411, 2942.463), (126, 1.083, 20.775), (115, 0.645, 0.98),
     (103, 0.636, 4694.003), (102, 0.976, 15720.839), (102, 4.267, 7.114), (99, 6.21, 2146.17), (98, 0.68, 155.42),
     (86, 5.98, 161000.69), (85, 1.3, 6275.96), (85, 3.67, 71430.7), (80, 1.81, 17260.15), (79, 3.04, 12036.46),
     (75, 1.76, 5088.63), (74, 3.5, 3154.69), (74, 4.68, 801.82), (70, 0.83, 9437.76), (62, 3.98, 8827.39),
     (61, 1.82, 7084.9), (57, 2.78, 6286.6), (56, 4.39, 14143.5), (56, 3.47, 6279.55), (52, 0.19, 12139.55),
     (52, 1.33, 1748.02), (51, 0.28, 5856.48), (49, 0.49, 1194.45), (41, 5.37, 8429.24), (41, 2.4, 19651.05),
     (39, 6.17, 10447.39), (37, 6.04, 10213.29), (37, 2.57, 1059.38), (36, 1.71, 2352.87), (36, 1.78, 6812.77),
     (33, 0.59, 17789.85), (30, 0.44, 83996.85), (30, 2.74, 1349.87), (25, 3.16, 4690.48)],
    [(628331966747, 0, 0), (206059, 2.678235, 6283.07585), (4303, 2.6351, 12566.1517), (425, 1.59, 3.523), (119, 5.796, 26.298),
     (109, 2.966, 1577.344), (93, 2.59, 18849.23), (72, 1.14, 529.69), (68, 1.87, 398.15), (67, 4.41, 5507.55),
     (59, 2.89, 5223.69), (56, 2.17, 155.42), (45, 0.4, 796.3), (36, 0.47, 775.52), (29, 2.65, 7.11),
     (21, 5.34, 0.98), (19, 1.85, 5486.78), (19, 4.97, 213.3), (17, 2.99, 6275.96), (16, 0.03, 2544.31),
     (16, 1.43, 2146.17), (15, 1.21, 10977.08), (12, 2.83, 1748.02), (12, 3.26, 5088.63), (12, 5.27, 1194.45),
     (12, 2.08, 4694.0), (11, 0.77, 553.57), (10, 1.3, 6286.6), (10, 4.24, 1349.87), (9, 2.7, 242.73),
     (9, 5.64, 951.72), (8, 5.3, 2352.87), (6, 2.65, 9437.76), (6, 4.67, 4690.48)],
    [(52919, 0, 0), (8720, 1.0721, 6283.0758), (309, 0.867, 12566.152), (27, 0.05, 3.52), (16, 5.19, 26.3),
     (16, 3.68, 155.42), (10, 0.76, 18849.23), (9, 2.06, 77713.77), (7, 0.83, 775.52), (5, 4.66, 1577.34),
     (4, 1.03, 7.11), (4, 3.44, 5573.14), (3, 5.14, 796.3), (3, 6.05, 5507.55), (3, 1.19, 242.73),
     (3, 6.12, 529.69), (3, 0.31, 398.15), (3, 2.28, 553.57), (2, 4.38, 5223.69), (2, 3.75, 0.98)],
    [(289, 5.844, 6283.076), (35, 0, 0), (17, 5.49, 12566.15), (3, 5.2, 155.42), (1, 4.72, 3.52), (1, 5.3, 18849.23), (1, 5.97, 242.73)],
    [(114, 3.142, 0), (8, 4.13, 6283.08), (1, 3.84, 12566.15)],
    [(1, 3.14, 0)]]


def sun_lon(jd):
    """겉보기 태양 황경(도). jd = 지구시(TT) 율리우스일. ΔT는 호출측에서 더한다."""
    tau = (jd - 2451545.0) / 365250
    L = sum(sum(a * math.cos(b + c * tau) for a, b, c in terms) * tau ** i for i, terms in enumerate(_L)) / 1e8
    lon = math.degrees(L) + 180
    T = tau * 10
    om = math.radians(125.04452 - 1934.136261 * T)
    Ls = math.radians(280.4665 + 36000.7698 * T)
    Lm = math.radians(218.3165 + 481267.8813 * T)
    nut = (-17.2 * math.sin(om) - 1.32 * math.sin(2 * Ls) - 0.23 * math.sin(2 * Lm) + 0.21 * math.sin(2 * om)) / 3600
    return (lon + nut - 20.4898 / 3600) % 360


def delta_t(y):
    """ΔT(초) 근사 (Espenak-Meeus). 1900~2050 정도에서 충분."""
    t = y - 2000
    if y < 1920: t2 = y - 1900; return -2.79 + 1.494119 * t2 - 0.0598939 * t2 ** 2 + 0.0061966 * t2 ** 3 - 0.000197 * t2 ** 4
    if y < 1941: t2 = y - 1920; return 21.20 + 0.84493 * t2 - 0.076100 * t2 ** 2 + 0.0020936 * t2 ** 3
    if y < 1961: t2 = y - 1950; return 29.07 + 0.407 * t2 - t2 ** 2 / 233 + t2 ** 3 / 2547
    if y < 1986: t2 = y - 1975; return 45.45 + 1.067 * t2 - t2 ** 2 / 260 - t2 ** 3 / 718
    if y < 2005: return 63.86 + 0.3345 * t - 0.060374 * t ** 2 + 0.0017275 * t ** 3 + 0.000651814 * t ** 4 + 0.00002373599 * t ** 5
    if y < 2050: return 62.92 + 0.32217 * t + 0.005589 * t ** 2
    return 62.92 + 0.32217 * t + 0.005589 * t ** 2  # ponytail: 2050 이후 외삽


def jd_utc(dt):
    """naive UTC datetime → JD(UT)"""
    return (dt - datetime(2000, 1, 1, 12)).total_seconds() / 86400 + 2451545.0


def dt_utc(jd):
    return datetime(2000, 1, 1, 12) + timedelta(days=jd - 2451545.0)


def lon_at(dt):
    """UTC datetime → 겉보기 황경 (ΔT 적용)"""
    return sun_lon(jd_utc(dt) + delta_t(dt.year + dt.month / 12) / 86400)


def term_time(target, near):
    """황경 target(도)에 도달하는 UTC 시각. near 근처에서 탐색."""
    lo, hi = near - timedelta(days=20), near + timedelta(days=20)
    f = lambda d: ((lon_at(d) - target + 180) % 360) - 180
    for _ in range(40):
        mid = lo + (hi - lo) / 2
        if f(lo) * f(mid) <= 0: hi = mid
        else: lo = mid
    return lo + (hi - lo) / 2


# ── 한국 시간 보정 ─────────────────────────────────────────────────────
DST = [(datetime(1948, 5, 31, 23), datetime(1948, 9, 12, 23)), (datetime(1949, 4, 2, 23), datetime(1949, 9, 10, 23)),
       (datetime(1950, 3, 31, 23), datetime(1950, 9, 9, 23)), (datetime(1951, 5, 5, 23), datetime(1951, 9, 8, 23)),
       (datetime(1955, 5, 4, 23), datetime(1955, 9, 8, 23)), (datetime(1956, 5, 19, 23), datetime(1956, 9, 29, 23)),
       (datetime(1957, 5, 4, 23), datetime(1957, 9, 21, 23)), (datetime(1958, 5, 3, 23), datetime(1958, 9, 20, 23)),
       (datetime(1959, 5, 2, 23), datetime(1959, 9, 19, 23)), (datetime(1960, 4, 30, 23), datetime(1960, 9, 17, 23)),
       (datetime(1987, 5, 10, 2), datetime(1987, 10, 11, 3)), (datetime(1988, 5, 8, 2), datetime(1988, 10, 9, 3))]


def clock_to_utc(local):
    """한국 시계 시각 → UTC. 표준시 이력 + 서머타임 반영."""
    off = timedelta(hours=8, minutes=30) if datetime(1954, 3, 21) <= local < datetime(1961, 8, 10) else timedelta(hours=9)
    if any(a <= local < b for a, b in DST): off += timedelta(hours=1)
    return local - off


# ── 사주 ─────────────────────────────────────────────────────────────────
def ganzi(p):
    return None if p is None else STEMS[p[0]] + BRANCHES[p[1]]


def gz_index(p):  # 60갑자 순번
    return next(i for i in range(60) if i % 10 == p[0] and i % 12 == p[1])


def gz(i):
    return [i % 10, i % 12]


def calc(y, m, d, hh=None, mi=0, lon=127.5, yajasi=False):
    """양력 시계 시각 → 4주 + 절기 정보. 시각 모르면 시주 None, 정오로 계산.
       lon: 출생지 경도(진태양시 보정). yajasi=True면 23시대를 당일 일주로 본다."""
    known = hh is not None
    local = datetime(y, m, d, hh if known else 12, mi)
    utc = clock_to_utc(local)
    lam = lon_at(utc)
    lmt = utc + timedelta(hours=lon / 15)  # 진태양시(평균). ponytail: 균시차 미적용(±15분)
    # 년주: 입춘(315°) 기준
    sy = y - 1 if (m <= 2 and lam < 315) else y
    ys, yb = (sy - 4) % 10, (sy - 4) % 12
    mb = (2 + int(((lam - 315) % 360) // 30)) % 12
    ms = ((ys % 5) * 2 + 2 + (mb - 2) % 12) % 10
    # 일주: 진태양시 23시 이후 다음날 (yajasi면 당일 유지)
    dd = lmt.date()
    if known and lmt.hour >= 23 and not yajasi: dd += timedelta(days=1)
    di = (dd.toordinal() + 1721425 + 49) % 60
    ds, db = di % 10, di % 12
    hour = None
    if known:
        hb = ((lmt.hour + 1) // 2) % 12
        base_ds = (ds + 1) % 10 if (yajasi and lmt.hour >= 23) else ds  # 야자시: 시간은 다음날 일간 기준
        hour = [((base_ds % 5) * 2 + hb) % 10, hb]
    # 절기: 직전/직후 절(節) 시각 (대운수용)
    prev_lon = (int(((lam - 315) % 360) // 30) * 30 + 315) % 360
    prev_t = term_time(prev_lon, utc - timedelta(days=((lam - prev_lon) % 360) / 360 * 365.25))
    next_t = term_time((prev_lon + 30) % 360, utc + timedelta(days=((prev_lon + 30 - lam) % 360) / 360 * 365.25))
    return {"pillars": [[ys, yb], [ms, mb], [ds, db], hour], "utc": utc, "lmt": lmt, "lon": lam,
            "prev_term": prev_t, "next_term": next_t, "hour_known": known}


def ten_god10(dm, s):
    """일간 dm, 천간 s → 십신 10종"""
    rel = (STEM_EL[s] - STEM_EL[dm]) % 5
    return TEN10[rel][0 if (s % 2) == (dm % 2) else 1]


def ten_group(name):
    return next(t for t, pair in zip(TEN, TEN10) if name in pair)


def unseong(dm, b):
    st = UNSEONG_START[dm]
    return UNSEONG[((b - st) if dm % 2 == 0 else (st - b)) % 12]


def analyze(pillars, gender=None, birth_utc=None, prev_term=None, next_term=None):
    ds = pillars[2][0]
    dm_el = STEM_EL[ds]
    P = [p for p in pillars if p]
    names = ["년", "월", "일", "시"]
    # 오행 힘 (위치 가중 + 지장간 분배)
    W_STEM = {0: 1.0, 1: 1.2, 2: 0, 3: 1.2}
    W_BR = {0: 1.0, 1: 3.0, 2: 2.0, 3: 1.2}
    power = [0.0] * 5
    support = drain = 0.0
    for i, p in enumerate(pillars):
        if not p: continue
        if i != 2:
            power[STEM_EL[p[0]]] += W_STEM[i]
            (support, drain) = (support + W_STEM[i], drain) if (STEM_EL[p[0]] - dm_el) % 5 in (0, 4) else (support, drain + W_STEM[i])
        for hs, days in HIDDEN[p[1]]:
            w = W_BR[i] * days / 30
            power[STEM_EL[hs]] += w
            if (STEM_EL[hs] - dm_el) % 5 in (0, 4): support += w
            else: drain += w
    ratio = support / (support + drain)
    strength = "신강" if ratio >= 0.55 else "신약" if ratio <= 0.45 else "중화"
    rooted = [names[i] for i, p in enumerate(pillars) if p and any(STEM_EL[hs] == dm_el for hs, _ in HIDDEN[p[1]])]
    mb = pillars[1][1]
    deukryeong = (STEM_EL[HIDDEN[mb][-1][0]] - dm_el) % 5 in (0, 4)
    # 십신 (천간 + 지지 정기)
    tens = {}
    for i, p in enumerate(pillars):
        if not p: continue
        tens[names[i]] = {"stem": None if i == 2 else ten_god10(ds, p[0]), "branch": ten_god10(ds, HIDDEN[p[1]][-1][0]),
                          "hidden": [(STEMS[hs], ten_god10(ds, hs)) for hs, _ in HIDDEN[p[1]]], "unseong": unseong(ds, p[1])}
    cnt = {t: 0 for t in TEN}
    for i, p in enumerate(pillars):
        if not p: continue
        if i != 2: cnt[ten_group(ten_god10(ds, p[0]))] += 1
        cnt[ten_group(ten_god10(ds, HIDDEN[p[1]][-1][0]))] += 1
    # 격국: 월지 지장간 중 투간한 것 (정기 우선), 없으면 정기
    stems_out = [p[0] for i, p in enumerate(pillars) if p and i != 2]
    gyeok_stem = next((hs for hs, _ in reversed(HIDDEN[mb]) if hs in stems_out), HIDDEN[mb][-1][0])
    g10 = ten_god10(ds, gyeok_stem)
    gyeok = {"비견": "건록격", "겁재": "양인격" if ds % 2 == 0 else "겁재격", "식신": "식신격", "상관": "상관격", "편재": "편재격",
             "정재": "정재격", "편관": "편관격", "정관": "정관격", "편인": "편인격", "정인": "정인격"}[g10]
    # 용신: 억부(신강 원인별) → 조후 우선 적용
    rel_el = lambda k: EL[(dm_el + k) % 5]  # 0 비겁 1 식상 2 재성 3 관성 4 인성
    pw = lambda k: power[(dm_el + k) % 5]
    johu = "화" if mb in (11, 0, 1) else "수" if mb in (5, 6, 7) else None
    if strength == "신강":
        cands = [rel_el(1), rel_el(2), rel_el(3)]
        if pw(4) > pw(0):  # 인다신강: 인성을 극하는 재성 → 없으면 설기하는 식상
            order = [(2, "인성이 많아 신강이므로 인성을 제어하는 재성"), (1, "재성이 없어 기운을 흘려보내는 식상"), (3, "관성")]
        else:              # 비겁 과다: 관성으로 제어 → 식상 설기 → 재성
            order = [(3, "비겁이 많아 신강이므로 일간을 제어하는 관성"), (1, "관성이 없어 설기하는 식상"), (2, "재성")]
        k, why = next(((k, w) for k, w in order if pw(k) >= 0.5), order[-1])
        yong = rel_el(k)
        hui = EL[(EL.index(yong) + 1) % 5]  # 신강: 용신이 생하는 오행으로 흐름을 이음
    elif strength == "신약":
        cands = [rel_el(4), rel_el(0)]
        if pw(2) >= max(pw(3), pw(1)) and pw(2) > 0: yong, why = rel_el(0), "재성이 많아 신약이므로 재를 감당할 비겁"
        else: yong, why = rel_el(4), "관성·식상이 많아 신약이므로 일간을 생하는 인성"
        hui = rel_el(0) if yong == rel_el(4) else rel_el(4)  # 신약: 인성·비겁 중 용신이 아닌 쪽
    else:
        cands = [rel_el(4), rel_el(1)]
        yong, why = (rel_el(4), "중화라 흐름을 잇는 인성") if pw(4) <= pw(1) else (rel_el(1), "중화라 흐름을 잇는 식상")
        hui = EL[(EL.index(yong) - 1) % 5]
    if johu and johu == yong: why += " (조후와 일치)"
    if johu and johu in cands and johu != yong:
        yong, why = johu, f"조후 우선: {'한여름' if johu == '수' else '한겨울'} 출생이라 {johu} 기운이 먼저 필요 (억부로는 {yong})"
        hui = EL[(EL.index(yong) + (1 if strength == "신강" else -1)) % 5]
    gi = EL[(EL.index(yong) + 3) % 5]  # 용신을 극하는 오행
    # 공망
    gm = gz_index(pillars[2]) // 10
    gongmang = [(10 - 2 * gm) % 12, (11 - 2 * gm) % 12]
    gm_hit = [names[i] for i, p in enumerate(pillars) if p and i != 2 and p[1] in gongmang]
    # 원국 합충형파해
    rels = []
    br = [(names[i], p[1]) for i, p in enumerate(pillars) if p]
    for a in range(len(br)):
        for b in range(a + 1, len(br)):
            (na, x), (nb, y) = br[a], br[b]
            pair = frozenset([x, y]); lab = f"{na}지 {BRANCHES[x]}·{nb}지 {BRANCHES[y]}"
            if pair in LIUHE: rels.append(f"{lab} 육합")
            if (x - y) % 12 == 6: rels.append(f"{lab} 충")
            if x != y and x % 4 == y % 4: rels.append(f"{lab} 삼합(반합)")
            if x != y and BANGHAP[x] == BANGHAP[y] and abs(x - y) in (1, 2, 11, 10): rels.append(f"{lab} 방합")
            if pair in HYEONG or (x == y and x in SELF_HYEONG): rels.append(f"{lab} 형")
            if pair in PO: rels.append(f"{lab} 파")
            if pair in HAE: rels.append(f"{lab} 해")
    st = [(names[i], p[0]) for i, p in enumerate(pillars) if p]
    for a in range(len(st)):
        for b in range(a + 1, len(st)):
            (na, x), (nb, y) = st[a], st[b]
            if (x - y) % 10 == 5: rels.append(f"{na}간 {STEMS[x]}·{nb}간 {STEMS[y]} 천간합")
            if (x - y) % 10 in (4, 6) and x % 2 == y % 2 and {STEM_EL[x], STEM_EL[y]} != {2}: rels.append(f"{na}간 {STEMS[x]}·{nb}간 {STEMS[y]} 천간충")
    # 대운
    daeun = None
    if gender in ("M", "F") and birth_utc and prev_term and next_term:
        forward = (pillars[0][0] % 2 == 0) == (gender == "M")  # 양남음녀 순행
        days = ((next_term - birth_utc) if forward else (birth_utc - prev_term)).total_seconds() / 86400
        start = max(1, round(days / 3))
        mi = gz_index(pillars[1])
        daeun = {"forward": forward, "start_age": start, "list": []}
        for k in range(1, 9):
            p = gz(((mi + k) if forward else (mi - k)) % 60)
            daeun["list"].append({"age": start + 10 * (k - 1), "ganzi": ganzi(p), "stem_god": ten_god10(ds, p[0]),
                                  "branch_god": ten_god10(ds, HIDDEN[p[1]][-1][0]), "unseong": unseong(ds, p[1])})
    els = {EL[i]: round(power[i], 1) for i in range(5)}
    return {"day_master": STEMS[ds], "dm_el": EL[dm_el], "dm_yin": ds % 2 == 1, "power": els,
            "elements": {EL[i]: sum(1 for p in P for v in ((STEM_EL[p[0]], BR_EL[p[1]])) if v == i) for i in range(5)},
            "support_ratio": round(ratio, 2), "strength": strength, "deukryeong": deukryeong, "rooted": rooted,
            "ten_gods": cnt, "tens": tens, "gyeok": gyeok, "gyeok_god": g10, "yong": yong, "hui": hui, "gi": gi, "yong_why": why,
            "johu": johu, "gongmang": [BRANCHES[b] for b in gongmang], "gongmang_hit": gm_hit, "relations": rels,
            "lacking": [EL[i] for i in range(5) if power[i] < 0.5], "dominant": EL[max(range(5), key=lambda i: power[i])],
            "daeun": daeun, "unseong_day": unseong(ds, pillars[2][1])}


def pillars_of(dt_local):
    """임의 시각(한국 시계)의 년·월·일 주 — 세운·월운·일진용"""
    r = calc(dt_local.year, dt_local.month, dt_local.day, dt_local.hour, dt_local.minute)
    return r["pillars"]


def branch_rel(a, b):
    """두 지지의 관계 → (이름, 가중치)"""
    if a == b: return ("같음", 0.05) if a not in SELF_HYEONG else ("자형", -0.1)
    pair = frozenset([a, b])
    if pair in LIUHE: return "육합", 0.3
    if (a - b) % 12 == 6: return "충", -0.3
    if a % 4 == b % 4: return "삼합", 0.25
    if pair in HYEONG: return "형", -0.2
    if pair in PO: return "파", -0.1
    if pair in HAE: return "해", -0.1
    if BANGHAP[a] == BANGHAP[b]: return "방합", 0.15
    return None, 0
