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

# HTTP: 토큰은 헤더로만(쿼리 무시), 부서 지도는 본인 부서·owner 만, 삭제 시 오늘의 운 캐시에서도 지움 — 임시 폴더에서
import json, tempfile, threading, urllib.request, urllib.error, urllib.parse
_tmp = tempfile.mkdtemp(prefix="saju-selftest-")
app.DATA, app.PEOPLE, app.BUNGAE, app.FORTUNE = _tmp, os.path.join(_tmp, "people.json"), os.path.join(_tmp, "bungae.json"), os.path.join(_tmp, "fortune")
app.llm = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("LLM 없음"))
_srv = app.ThreadingHTTPServer(("127.0.0.1", 0), app.H); threading.Thread(target=_srv.serve_forever, daemon=True).start()
_B = f"http://127.0.0.1:{_srv.server_address[1]}"
def _call(path, body=None, hdr=None, user=None):
    h = {**(hdr or {}), **({"X-Agent-User": user} if user else {})}
    r = urllib.request.Request(_B + path, json.dumps(body).encode() if body is not None else None, h)
    try:
        with urllib.request.urlopen(r) as f: return f.status, f.read()
    except urllib.error.HTTPError as e: return e.code, e.read()
# 포털 계정(가짜 portal.db): 이름·부서는 계정 것, 한 계정 = 프로필 1건, 부서 지도·팀 매칭은 계정 부서로만
import sqlite3
app.PORTAL_DB = os.path.join(_tmp, "portal.db"); _db = sqlite3.connect(app.PORTAL_DB)
_db.execute("CREATE TABLE users(id TEXT PRIMARY KEY, name TEXT, dept TEXT, disabled INTEGER DEFAULT 0, deactivated TEXT)")
_db.executemany("INSERT INTO users(id,name,dept) VALUES(?,?,?)", [("u1", "갑", "시험부서"), ("u2", "을", "다른부서"), ("u3", "병", ""), ("u4", "정", "시험부서")]); _db.commit(); _db.close()
_base = {"year": 1990, "month": 5, "day": 3, "hour": 10}
_a = json.loads(_call("/api/register", {**_base, "name": "사칭", "dept": "다른부서"}, user="u1")[1]); _b = json.loads(_call("/api/register", _base, user="u2")[1])
assert [(p["name"], p["dept"], p["account"]) for p in app.load()] == [("갑", "시험부서", "u1"), ("을", "다른부서", "u2")], "요청의 이름·부서를 쓰면 안 됨"
assert _call("/api/register", _base, user="u3")[0] == 403 and _call("/api/register", _base, user="owner")[0] == 403, "부서 없는 계정 등록"
_ha = {"X-Saju-Id": _a["id"], "X-Saju-Token": _a["token"]}
assert _call("/api/me", hdr=_ha, user="u1")[0] == 200
assert _call("/api/me", hdr=_ha, user="u2")[0] == 400, "다른 계정이 토큰으로 남의 프로필"
assert json.loads(_call("/api/account", user="u1")[1])["mine"]["id"] == _a["id"]
assert _call(f"/api/me?id={_a['id']}&token={_a['token']}", user="u1")[0] == 400, "쿼리 토큰은 받지 않아야 함"
_q = "/api/graph?dept=" + urllib.parse.quote("시험부서")
assert _call(_q, user="u2")[0] == 403 and _call(_q, user="u3")[0] == 403 and _call(_q, user="u4")[0] == 403, "남의 부서·부서 없음·미등록이 부서 지도"
_c, _g = _call(_q, user="u1"); _g = json.loads(_g)
assert _c == 200 and _g["nodes"][0]["name"] == "갑" and _g["depts"] == ["시험부서"], _g
_c, _g = _call(_q, user="owner"); assert _c == 200 and set(json.loads(_g)["depts"]) == {"시험부서", "다른부서"}
_g = json.loads(_call("/api/graph?dept=", user="u3")[1]); assert _g["depts"] == [] and all("name" not in n for n in _g["nodes"])
assert _call("/api/today", hdr=_ha, user="u1")[0] == 200
_tc = os.path.join(_tmp, "today-2000-01-01.json"); json.dump({_a["id"]: {"text": "x"}, "other": {"text": "y"}}, open(_tc, "w"))
os.makedirs(app.FORTUNE, exist_ok=True); open(os.path.join(app.FORTUNE, _a["id"] + ".json"), "w").write("{}")
_a2 = json.loads(_call("/api/register", _base, user="u1")[1])  # 다시 등록 = 바꿔 끼움(계정당 1건)
assert sum(p.get("account") == "u1" for p in app.load()) == 1 and _call("/api/me", hdr=_ha, user="u1")[0] == 400
assert json.load(open(_tc)) == {"other": {"text": "y"}} and not os.path.exists(os.path.join(app.FORTUNE, _a["id"] + ".json"))
_ha = {"X-Saju-Id": _a2["id"], "X-Saju-Token": _a2["token"]}
assert _call("/api/delete", {}, hdr=_ha, user="u1")[0] == 200 and _call("/api/me", hdr=_ha, user="u1")[0] == 400
# 예전 등록(계정 없음): 이름+부서가 한 계정과 정확히 같으면 연결, 아니면 미연결 — 미연결은 관리자만 고치거나 지움
_old = [{**app.load()[0], "id": "0000000" + str(k), "token": "t" * 32, "name": n, "dept": d} for k, (n, d) in enumerate([("정", "시험부서"), ("무", "시험부서"), ("을", "다른부서")])]
for o in _old: o.pop("account", None)
app.save(app.load() + _old)
assert app.link_accounts() == {"linked": 1, "unlinked": 2, "already": 1}
_hu = {"X-Saju-Id": "00000001", "X-Saju-Token": "t" * 32}
assert _call("/api/delete", {}, hdr=_hu, user="u1")[0] == 403 and _call("/api/prefs", {"hobbies": []}, hdr=_hu, user="u1")[0] == 403
assert _call("/api/admin/people", user="u1")[0] == 403 and _call("/api/admin/fix", {"pid": "00000001", "action": "delete"}, user="u1")[0] == 403
assert _call("/api/admin/fix", {"pid": "00000001", "action": "delete"}, user="owner")[0] == 200 and not app.find(app.load(), "00000001")
assert _call("/api/admin/fix", {"pid": "00000002", "action": "link", "account": "u2"}, user="owner")[0] == 400, "이미 프로필 있는 계정에 연결"
try: urllib.request.urlopen(urllib.request.Request(_B + "/api/register", b"not json")); raise AssertionError("잘못된 JSON 통과")
except urllib.error.HTTPError as e: assert e.code == 400
_srv.shutdown(); import shutil; shutil.rmtree(_tmp, ignore_errors=True)

print("selftest ok")
