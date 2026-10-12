# THIRD_PARTY_NOTICES — saju-local

이 저장소는 Python 3.9+ **표준 라이브러리만** 쓰며 제3자 코드·폰트·JS 라이브러리·모델 가중치를 동봉하지 않습니다(외부 패키지·CDN 0).
조사 기준: `*.py` import 문, `ui.html`(외부 스크립트·폰트 없음), git 추적 파일 전체(2026-10-12).

| 이름 | 버전 | 쓰임 | 라이선스 | 링크 | 상업 이용 | 비고 |
|---|---|---|---|---|---|---|
| Python 표준 라이브러리 | 3.9+ | 실행 환경 | PSF-2.0 | https://docs.python.org/3/license.html | 가능 | 동봉 안 함 |
| Ollama | — | 외부 서비스(LLM 서버, 선택) | MIT | https://github.com/ollama/ollama | 가능 | 동봉 안 함, HTTP 로 호출 |
| Google Gemma 4 `gemma4:31b` | — | 외부 서비스의 모델(기본 배포) | Apache-2.0 | https://ai.google.dev/gemma/docs/gemma_4_license | 가능 | `LLM_MODEL` 로 교체. 코드 기본값 `qwen3:8b`(Qwen3, Apache-2.0) |
| VSOP87D 지구 급수(절단표) | — | `saju.py` `_L` 계수 | 과학 데이터(공개) | Bretagnon & Francou 1988; J. Meeus, *Astronomical Algorithms* 부록 | 가능(저위험) | 출처 표기 유지 — [#1](https://github.com/gggg8657/saju-local/issues/1) |
| ΔT 다항식 (Espenak–Meeus) | — | `saju.py` `delta_t()` | 공개 공식 | https://eclipse.gsfc.nasa.gov/SEhelp/deltatpoly2004.html | 가능(저위험) | 출처 표기 유지 |
| 명리 규칙표(지장간·12운성·합충형파해·신살) | — | `saju.py`, `fortune.py` | 전통 지식(사실) | — | 확인 필요 | 문장 출처 기록 — [#1](https://github.com/gggg8657/saju-local/issues/1) |
| 해설 문구 표 | — | `app.py`, `fortune.py`, `report.py` | 저작자 작성(기록 확인 중) | — | 확인 필요 | [#1](https://github.com/gggg8657/saju-local/issues/1) |
| MBTI 명칭·16유형 표기 | — | 화면·점수 입력 | 상표(The Myers-Briggs Company) | https://www.themyersbriggs.com | 확인 필요 | 공식 문항·결과 문장 안 씀 — [#1](https://github.com/gggg8657/saju-local/issues/1) |

## 확인 필요
- **[#1](https://github.com/gggg8657/saju-local/issues/1) 해설 문구·명리 규칙표 출처 / MBTI 상표** — 해설 문장이 직접 쓴 것인지 기록, 대외 이용 시 "MBTI" 상표 표기 확인. 회피: 의심 문장 새로 쓰기, 상표 고지 한 줄(NOTICE 에 있음), 필요 시 "성격유형(4글자)" 로 표기 변경.

## 상업 이용 시 대안
- LLM: `LLM_MODEL` 로 Apache-2.0 모델(Gemma 4, Qwen3 등) 선택. LLM 이 없으면 규칙 문장으로 대체되어 외부 모델 없이도 동작.
