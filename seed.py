#!/usr/bin/env python3
"""python3 seed.py [N] — 더미 인원 N명(기본 24) + 번개 몇 개를 data/ 에 넣는다. 기존 데이터는 지운다."""
import os, random, sys
import app

random.seed(7)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 24
for f in (app.PEOPLE, app.BUNGAE):
    if os.path.exists(f): os.remove(f)
SUR = "김 이 박 최 정 강 조 윤 장 임 한 오 서 신 권 황".split()
GIV = "민준 서연 도윤 지우 예준 하은 시우 수아 지호 지민 준서 유진 현우 채원 건우 다은 우진 소율 선우 지아 연우 하린 정우 은서".split()
DEPT = ["연구1팀", "연구2팀", "안전분석팀", "전산실", "기획부"]
MBTI = ["INTJ", "ENFP", "ISTP", "ESFJ", "ENTP", "INFJ", "ISFP", "ESTJ", "", ""]
seen = set()
for i in range(N):
    while (name := random.choice(SUR) + random.choice(GIV)) in seen: pass
    seen.add(name)
    y = random.randint(1970, 2002); m = random.randint(1, 12); d = random.randint(1, 28)
    traits = {a: random.choice([-1, 0, 1]) for a in app.AXES}
    wants = {a: 0 for a in app.AXES}  # 원하는 성향은 1~2개 축만 (실사용 가정)
    for a in random.sample(app.AXES, random.randint(1, 2)): wants[a] = random.choice([-1, 1])
    r = app.register({"name": name, "dept": random.choice(DEPT), "year": y, "month": m, "day": d,
                      "hour": random.choice(["unknown"] + list(range(24))), "mbti": random.choice(MBTI),
                      "blood": random.choice(["A", "B", "O", "AB", ""]), "gender": random.choice(["M", "F", ""]),
                      "hobbies": random.sample(app.HOBBIES, random.randint(2, 5)), "traits": traits, "wants": wants})
    print(f"{name:6} {r['alias']:8} {' '.join(x or '----' for x in r['pillars'])}")
people = app.load()
for title, place, hobby, mins in [("볼링 칠 사람!", "신탄진 볼링장", "볼링", 60), ("점심 맛집 탐방", "회사 정문", "맛집", 180),
                                   ("퇴근 후 보드게임", "전산실 회의실", "보드게임", 300), ("주말 등산 계룡산", "계룡산 입구", "등산", 60 * 24 * 2)]:
    host = random.choice([p for p in people if hobby in p["hobbies"]] or people)
    if hobby not in host["hobbies"]: host["hobbies"].append(hobby); app.save(people)
    app.create_bungae({"id": host["id"], "token": host["token"], "title": title, "place": place, "hobby": hobby, "minutes": mins, "cap": 4})
from urllib.parse import urlencode
print(f"→ {len(people)}명, 번개 {len(app.load_b())}개. 더미 계정으로 들어가기 (또는 UI에서 새로 등록):")
for p in people[:3]:
    print(f"   http://localhost:{app.PORT}/?" + urlencode({k: p[k] for k in ("id", "token", "name", "dept", "alias")}))
