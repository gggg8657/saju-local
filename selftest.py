import os
#!/usr/bin/env python3
"""python3 selftest.py — 만세력(VSOP87 절기·시간 보정)·명리 분석·궁합·번개 필터 자가검증. LLM 불필요."""
from datetime import datetime, date
import saju, app

# 절기: 알려진 분점·지점·입춘 시각(UTC)과 ±1.5분
for lon, t in [(0, datetime(2024, 3, 20, 3, 6)), (90, datetime(2024, 6, 20, 20, 51)), (180, datetime(2024, 9, 22, 12, 44)),
               (270, datetime(2024, 12, 21, 9, 20)), (0, datetime(2000, 3, 20, 7, 35)), (315, datetime(2024, 2, 4, 8, 27)),
               (270, datetime(1990, 12, 22, 3, 7)), (90, datetime(1975, 6, 22, 0, 26))]:
    got = saju.term_time(lon, t)
    assert abs((got - t).total_seconds()) < 90, (lon, t, got)

# 시간 보정: 1958 여름 = UTC+8:30 + 서머타임 → 14:00 시계 = 13:00 진태양시(미시); 1987 서머타임 23:30 → 22:00 해시, 일주 유지
assert saju.calc(1958, 7, 20, 14, 0)["lmt"].hour == 13
r = saju.calc(1987, 8, 1, 23, 30); assert r["lmt"].hour == 22 and saju.ganzi(r["pillars"][2]) == "임오"
# 진태양시 -30분: 09:00 시계 → 08:30 → 진시
assert saju.ganzi(saju.calc(1990, 3, 15, 9, 0)["pillars"][3]) == "무진"
# 기준점: 2000-01-01 00:30 → 기묘 병자 무오 임자 / 1900-01-01 갑술일 / 입춘 직후·직전
assert [saju.ganzi(p) for p in saju.calc(2000, 1, 1, 0, 30)["pillars"]] == ["기묘", "병자", "무오", "임자"]
assert saju.ganzi(saju.calc(1900, 1, 1)["pillars"][2]) == "갑술"
assert [saju.ganzi(p) for p in saju.calc(2024, 2, 4, 18)["pillars"][:2]] == ["갑진", "병인"]
assert [saju.ganzi(p) for p in saju.calc(2024, 2, 4, 17)["pillars"][:2]] == ["계묘", "을축"]
# 절기 경계 1시간 전 출생: 2003-07-07 20:31 (소서 21:35) → 아직 오월
assert [saju.ganzi(p) for p in saju.calc(2003, 7, 7, 20, 31)["pillars"]] == ["계미", "무오", "신사", "무술"]
assert saju.ganzi(saju.calc(2003, 7, 7, 22, 0)["pillars"][1]) == "기미"
# 23시 이후 다음날 / 야자시 옵션 / 시각 모름
assert saju.calc(2000, 1, 1, 23, 40)["pillars"][2] == saju.calc(2000, 1, 2)["pillars"][2]
assert saju.calc(2000, 1, 1, 23, 40, yajasi=True)["pillars"][2] == saju.calc(2000, 1, 1)["pillars"][2]
assert saju.calc(2000, 1, 1)["pillars"][3] is None

# 분석: 십신 10종·12운성·공망·대운
assert saju.ten_god10(7, 4) == "정인" and saju.ten_god10(7, 5) == "편인" and saju.ten_god10(0, 0) == "비견"
assert saju.unseong(0, 11) == "장생" and saju.unseong(0, 2) == "건록" and saju.unseong(1, 6) == "장생"
r = saju.calc(1990, 3, 15, 9, 0); a = saju.analyze(r["pillars"], "M", r["utc"], r["prev_term"], r["next_term"])
assert a["gongmang"] == ["신", "유"] and a["gyeok"] == "편관격" and a["daeun"]["forward"] and a["daeun"]["start_age"] == 7
assert a["daeun"]["list"][0]["ganzi"] == "경진" and a["strength"] == "신약" and a["yong"] == "화"
r = saju.calc(2003, 7, 7, 20, 31); a = saju.analyze(r["pillars"], "F", r["utc"], r["prev_term"], r["next_term"])
assert a["yong"] == "수" and a["daeun"]["forward"] and a["daeun"]["start_age"] == 1  # 조후 우선, 음남양녀... 계년 음간·여 → 순행
assert "년간 계·월간 무 천간합" in a["relations"] and "년지 미·시지 술 형" in a["relations"]

# 궁합
p = {**a, "day_branch": 5, "mbti": "ISTP", "zodiac": "게", "blood": "O"}
r2 = saju.calc(1990, 3, 15, 9, 0); b = {**saju.analyze(r2["pillars"]), "day_branch": 3, "mbti": "INTJ", "zodiac": "물고기", "blood": "A"}
s, why = app.compat(p, b); assert 0 <= s <= 100 and 1 <= len(why) <= 4, (s, why)
s2, _ = app.compat({**p, "mbti": None, "blood": None}, {**b, "mbti": None, "blood": None}); assert 0 <= s2 <= 100
t = app.today_rule({**p, "id": "x"}, date(2024, 2, 4)); assert t["day"] == "무술" and 1 <= t["stars"] <= 5 and t["year"]["ganzi"] == "계묘"  # 입춘 17:27 전 정오
assert app.today_rule({**p, "id": "x"}, date(2024, 3, 1))["year"]["ganzi"] == "갑진"

# 번개 성향 필터
z = {x: 0 for x in app.AXES}
host = {"traits": {**z, "에너지": -1}, "wants": {**z, "말": -1}}
assert app.fits({"traits": {**z, "말": -1}, "wants": z}, host) and not app.fits({"traits": {**z, "말": 1}, "wants": z}, host)
assert not app.fits({"traits": {**z, "말": -1}, "wants": {**z, "에너지": 1}}, host)
# 저작권 표기: ui.html 에서 지워도 서버가 다시 붙인다 (LICENSE·NOTICE)
import base64 as _b
_h = app.signed(open(os.path.join(app.ROOT, 'ui.html'), encoding='utf-8').read().replace("data-sig", "").replace('name="author"', ""))
assert "data-sig" in _h and 'name="author"' in _h and _b.b64decode("ZG9uZ2p1a2ltLmRldkBnbWFpbC5jb20=").decode() in _h, "저작권 표기 누락"

print("selftest ok")
