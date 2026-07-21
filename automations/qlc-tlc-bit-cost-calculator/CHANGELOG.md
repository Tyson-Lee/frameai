# qlc-tlc-bit-cost-calculator — 변경 이력

## 2026-07-06 (11차 리파인 — 첫 두 그래프(월간 Bit 생산량/Cost per GB) 전용 "기준 시점" 토글 추가)

첫 두 그래프("월간 Bit 생산량 vs QLC 비율", "Cost/GB vs QLC 비율")와 그 위
표의 콤보/분리 생산 Bit 생산량·Cost/bit 수치가 지금까지 항상 성숙 수율
(mature_yield) 기준으로만 계산되던 것을, 사용자가 화면에서 직접 고를 수
있는 "기준 시점" 토글로 확장.

- **"기준 시점" 라디오 토글 신설 (QLC:TLC 비율 슬라이더 바로 아래)**:
  (a) "성숙 수율 기준"(기본값, 기존과 완전히 동일하게 mature_yield 그대로
  사용) / (b) "특정 개월 기준" — 고르면 QLC:TLC 비율 슬라이더와 동일한
  방식으로 조작하는 **1~60개월 슬라이더**가 활성화되고, 고른 개월수 `t`에서
  4개 라인/레시피(`qlc`/`tlc`/`combo_qlc`/`combo_tlc`) 각각 **자기 자신의**
  기존 수율 램프업 공식(`yield_fraction(t) = mature_yield × (1 -
  exp(-ramp_coef × t))`)으로 계산한 실제 수율을 사용해 Bit 생산량/Cost per
  bit/Cost per GB를 다시 계산. Total cost는 수율과 무관(wafer 처리량에만
  비례)하므로 이 토글로 바뀌지 않음.
- **영향 범위를 엄격히 제한**: 이 토글은 딱 두 그래프(1, 2번)와 그 위 표의
  콤보/분리 생산 "Bit 생산량"/"Cost / bit" 셀에만 영향. 5년/1년 누적
  그래프·표 행, 수율 램프업 참고 그래프 2개(5, 6번), 실시간 판정 문구
  (`verdict`), `sweep.json`/`report.md`의 crossover 서술은 전부 이 토글과
  무관하게 항상 성숙 수율 기준 그대로 — 순수 `visualization.html`의 표시
  레이어일 뿐이라 params 파일/`sweep.csv`/`sweep.json`에는 전혀 저장되지
  않고, 새로고침하면 항상 "성숙 수율 기준"으로 돌아감.
- **참고용 텍스트 추가**: "특정 개월 기준"을 고르면, 고른 개월수와 그
  시점에 각 라인/레시피가 자기 성숙 수율 대비 몇 %까지 도달했는지
  (`mature_yield` 값과 무관하게 `ramp_coef`만으로 결정 — t95와 같은 약분
  성질)를 화면에 표시.
- `calc.py`: `yield_ramp_progress_pct(ramp_coef, t)` 헬퍼 신설
  (`yield_ramp_fraction(100, ramp_coef, t) * 100` — mature_yield와 무관한
  성숙수율 대비 도달 비율을 %로 반환, "기준 시점" 토글의 참고용 텍스트 계산
  근거이자 JS `rampProgressPct`의 미러 소스). `sweep()`/`report.md` 경로
  자체는 호출하지 않음 — 순수 표시 레이어용 헬퍼이므로 계산 모델에는 아무
  영향 없음.
- `render_html.py`: 새 subpanel(`yieldBasisPanel`, 라디오 2개 + 1~60 범위
  `basisMonth` 슬라이더 + 참고 텍스트 `basisYieldNote`/`basisMonthReadout`)를
  비율 슬라이더 바로 아래에 추가. JS에 `yieldFractionAtBasis()`(mature 또는
  특정 개월의 실제 수율 선택), `computeDisplaySweep()`(wafer_qlc_*/wafer_tlc_*
  와 cost_total은 base `sweep`에서 그대로 재사용하고 bit/cost-per-bit/
  cost-per-gb만 재계산하는 별도 "display sweep"), `displayChartPointsFromSweep()`
  (차트 1-2 전용, five_year 필드는 절대 다루지 않음), `rampProgressPct()`
  (calc.yield_ramp_progress_pct 미러) 신설. `render()`이 이제 base `sweep`의
  `row`(wafer/월, 1년·5년 누적, 판정 문구, dev-cost/ER/전체 투자비용 텍스트용
  — 전부 불변)와 basis 토글이 반영된 `displayRow`(표의 Bit 생산량/Cost per
  bit 셀 전용)를 함께 사용하도록 갱신, `nearestRow()`를 `nearestRowIndex()`로
  교체(두 배열이 같은 순서/길이를 공유하므로 인덱스로 함께 조회). 차트
  1-2는 `monthlyChartPoints`(`displayChartPointsFromSweep(displaySweep, ...)`),
  차트 3-4(5년 누적)는 기존과 동일하게 `fiveYearChartPoints`
  (`chartPointsFromSweep(sweep, ...)`)를 쓰도록 `charts` 배열에 `points`
  필드 추가. `chartBitTitle`/`chartCostTitle`이 현재 기준 시점을 문구로
  반영하도록 갱신(예: "... (성숙 수율 기준)" / "... (12개월차 기준)").
  라디오/슬라이더 변경은 `recomputeAndRender()`가 아니라 가벼운 `render()`만
  호출(params 자체는 안 바뀌므로 전체 재계산 불필요).
- `tests/test_qlc_tlc_bit_cost_calculator.py`: `TestYieldRampProgressPct`
  (calc.yield_ramp_progress_pct 공식·t=0에서 0·mature_yield 무관성 검증),
  `TestYieldBasisToggle`(라디오/슬라이더 존재 및 기본값, `computeDisplaySweep`/
  `displayChartPointsFromSweep`/`yieldFractionAtBasis`/`rampProgressPct` 존재,
  차트 1-2가 `monthlyChartPoints`를, 차트 3-4가 `fiveYearChartPoints`를 쓰는지,
  표의 Bit 생산량/Cost per bit 셀이 `displayRow`를, Total cost 셀이 `row`를
  쓰는지, 판정 문구·1년/5년 누적 셀이 `displayRow`를 전혀 참조하지 않는지,
  `computeDisplaySweep`이 wafer/cost_total을 base row에서 재사용하는지,
  라디오/슬라이더 리스너가 `recomputeAndRender`가 아닌 `render()`만 호출하는지)
  신설. `python3 -m pytest -q` 114개 전체 통과 확인(기존 100개 + 신규 14개).
- `automations/qlc-tlc-bit-cost-calculator/README.md`,
  `skills/qlc-tlc-bit-cost-calculator/SKILL.md.tmpl`을 위 내용 기준으로
  갱신(`gen_skills.py`로 `SKILL.md` 재생성).
- 크로스오버·5년/1년 누적·수율 램프업 참고 그래프·판정 문구는 이 변경과
  완전히 무관 — 계산 로직 자체(=`calc.py`, `computeSweep`)는 단 한 줄도
  바뀌지 않았고, 새 `computeDisplaySweep`은 그 위에 얹힌 별도 레이어일 뿐.
  기존 `runs/` 아카이브는 이전 스키마 그대로 보존 — 재작성하지 않음(이번
  변경은 애초에 `sweep.json`/`report.md` 스키마에 아무 필드도 추가하지
  않는 순수 클라이언트 표시 레이어이므로 아카이브 스키마 자체가 변하지
  않음).

## 2026-07-06 (10차 리파인 — ER wafer 모델 근본 재설계: dev_ramp_months 제거, t95 기반 ER 기간·판매용/총량 bit 분리, 1년 누적 신설)

ER wafer 관련 모델을 근본적으로 다시 설계. 6가지 변경 사항:

1. **`dev_ramp_months` 파라미터 완전 삭제** (UI/계산/문서 전부). 대신 각
   라인/레시피(`qlc`/`tlc`/`combo_qlc`/`combo_tlc`)마다 **자기 자신의**
   `*_yield_ramp_coef`만으로 결정되는 `t95 = ln(20) / yield_ramp_coef`
   (성숙수율의 95%에 도달하는 시점 — `*_mature_yield` 값과는 무관, 정의상
   약분되어 사라짐)를 계산하고, `t=0..t95`를 그 라인/레시피의 **ER(엔지니어링
   런) 기간**으로 정의 (`calc.yield_ramp_t95()` 신설).
2. **`er_wafer_combo`/`er_wafer_dedicated`의 의미를 '1회성 총량' → '월간 ER
   wafer 소모 RATE'(wafer/월)로 변경**. 인력(headcount)/Mask(mask_count)는
   변경 없이 그대로 1회성 비용.
3. **ER wafer가 wafer_total 위에 추가로 더 생산되던 잘못된 가정을
   제거** — wafer_total(=max_capa × 비율, 변경 없음) 자체는 그대로 두고,
   그 ER 기간(`t <= t95`) 동안 매달 `min(er_wafer_rate, wafer_total)`
   만큼만 ER로, 나머지가 판매용으로 나뉜다고 재정의. 총 bit 생산량 공식은
   불변(`wafer_total × bit_per_wafer`, ER도 이미 포함된 셈); 새 필드
   `*_sale_bit_total`(판매용 bit 생산량 = 판매용_wafer × 그 달 수율)을
   1년/5년 누적 양쪽에 추가. 원가 계산에서 기존 "ER wafer 수 ×
   capex_rate" 1회성 개발비 항목은 완전히 제거(중복 계상이었음 —
   `wafer_total × capex_rate`에 이미 포함) — 이제 1회성 개발비는
   인력비+Mask비만. `DEDICATED_ER_ASSUMPTION`(50/50 블렌드 가정)도 그
   비용 항목과 함께 제거, 새 `ER_WAFER_RATE_ASSUMPTION`(월간 rate를
   50:50 분할 없이 두 라인/레시피 각각에 풀레이트로 적용한다는 가정)으로
   대체.
4. **`dev_ramp_months`가 없어졌으므로 5년(60개월) 누적이 이제 생산
   1개월차부터 바로(개발 기간 스킵 없이) 60개월 전부 매달 그 달의
   ramp된 수율을 적용해 합산**. 같은 방식으로 **1년(12개월) 누적**을
   신설해 5년 누적과 나란히 제공(`calc.ONE_YEAR_MONTHS`, `one_year_*`
   필드 — bit 총량/판매용/cost/cost-per-bit/cost-per-gb 전부).
5. **`cost_mode=direct` 모드에서도 `er_wafer_combo`/`er_wafer_dedicated`
   입력 필드는 계속 활성화** — `calc.COST_MODEL_ONLY_KEYS`에서 두 키
   제거(bit 생산량 계산에 관여하므로 원가 계산 모드와 무관하게 항상 필요).
   capex/개발비/헤드카운트/마스크/계수 등 나머지 원가 전용 필드만
   direct 모드에서 그대로 비활성화.
6. **페이지 상단 소개 문단(`#introStats`)에 콤보/분리 생산 각각의 현재
   비율 기준 1년간/5년간 총 bit 생산량 네 수치를 동적으로 표시**, 슬라이더
   이동 시 실시간 갱신.

크로스오버(월간 스냅샷, 성숙수율 기준)는 이 변경들과 완전히 무관 — 월간
bit/cost 공식이 전혀 바뀌지 않았으므로 `calc.py`로 직접 실행해 확인한 결과
sample-1 QLC 60%, sample-2 QLC 75%로 **변화 없음**.

- `calc.py`: `OPTIONAL_STR_DEFAULTS`에서 `dev_ramp_months` 제거,
  `active_production_months()` 삭제. `yield_ramp_t95()`,
  `line_ramp_stats()`(t95 + 1년/5년 양쪽 창의 누적 bit-per-wafer, 전체
  기간·ER 기간만 두 버전) 신설. `combo_dev_cost()`/`dedicated_dev_cost()`
  에서 ER wafer 항 제거(헤드카운트+마스크만). `sweep()`이
  `dev_ramp_months` 인자를 받지 않도록 시그니처 변경
  (`sweep(p, ratio_step)`), `window_totals()` 클로저로 각 시나리오의
  1년/5년 총량·판매용 bit을 계산. `ONE_YEAR_MONTHS`(12) 상수 신설,
  `FIVE_YEAR_MONTHS`(60)는 유지하되 더 이상 개발기간을 빼지 않고 그대로
  사용. `DEDICATED_ER_ASSUMPTION` 삭제, `ER_WAFER_RATE_ASSUMPTION` 신설.
  `t95_months()` 헬퍼 신설, `run()`의 payload/summary에 `t95_months`/
  `er_wafer_rate_assumption` 추가, `dev_cost` 딕셔너리에서
  `dedicated_assumption` 키 제거.
- `render_html.py`: JS `activeProductionMonths()`/`readDevRampMonths()`
  삭제, `ONE_YEAR_MONTHS`/`FIVE_YEAR_MONTHS` 상수화. `yieldRampT95()`/
  `lineRampStats()`/`windowTotals()` 신설(calc.py 미러),
  `comboDevCost()`/`dedicatedDevCost()`에서 ER 항 제거. `computeSweep()`
  시그니처에서 `devRampMonths` 제거, 1년/5년 총량·판매용 bit 필드 전부
  계산하도록 갱신. `PARAM_GROUPS`에서 ER wafer 필드를 기존 "1회성 개발비"
  그룹에서 분리해 새 "er-wafer" 그룹으로 이동(라벨 갱신: 월간 소모
  RATE·direct 모드에서도 활성). `COST_MODEL_ONLY_KEYS`에서
  `er_wafer_combo`/`er_wafer_dedicated` 제거. `OPTIONAL_PARAM_LABELS`에서
  `dev_ramp_months` 제거. `devRampMonthsInput` 필드/리스너 전부 삭제.
  결과 표에 1년/5년 누적 Bit 생산량(총량/판매용) 행 4개(콤보 2 + 분리 2)
  신설, `devCostNote` 텍스트를 인력+Mask만 반영하도록 갱신, 새
  `erInfoNote`(각 라인/레시피 t95 + 월간 소모량 표시) 신설. 페이지 상단
  `<p class="sub" id="introStats">` 신설, `render()`이 매 호출마다 콤보/
  분리 1년·5년 총 bit 생산량(억GB)을 문장으로 채워 넣도록 갱신.
- `samples/sample-1.txt`, `samples/sample-2.txt`: `er_wafer_combo`/
  `er_wafer_dedicated`를 월간 소모량 스케일로 재조정
  (sample-1: 400/900 → 40/60, sample-2: 150/200 → 15/20 — wafer_total이
  수만 단위이므로 ER이 그중 작은 비율만 차지하는 현실적인 스케일),
  `dev_ramp_months` 행 삭제. `calc.py`로 직접 실행해 확인: 두 샘플 모두
  크로스오버 변화 없음(60%/75%), 1년/5년 누적 판매용 bit이 총량보다 소폭
  작게 나옴(ER 기간 동안의 소모분만큼, 예상된 동작).
- `tests/test_qlc_tlc_bit_cost_calculator.py`: `calc.sweep()` 호출
  전부에서 `dev_ramp_months=` 인자 제거. `TestYieldRampT95`(t95 공식·
  95% 도달·mature_yield 무관성 검증) 신설. `TestDevCost`를 헤드카운트+
  마스크만 반영하도록 갱신, ER wafer rate 변경이 dev cost에 영향 없음을
  검증하는 테스트와 `DEDICATED_ER_ASSUMPTION` 제거/`ER_WAFER_RATE_ASSUMPTION`
  존재 검증 테스트 추가. `TestFiveYearCumulative`를
  `TestCumulativeWindows`로 교체(1년/5년 나란히 검증, `active_production_months`
  삭제 확인). `TestErWaferSaleSplit`(판매용 ≤ 총량, ER rate 0이면 판매용=
  총량, 총량이 ER rate와 무관, rate가 두 라인/레시피에 각각 풀로 적용됨을
  재구성해 검증) 신설. `TestCostMode`에 ER wafer 필드가
  `COST_MODEL_ONLY_KEYS`에서 빠졌는지, direct 모드에서도 ER 분리가
  작동하는지 검증하는 테스트 추가. `TestChartYAxisUnitLabels`/
  `TestPayloadPlainTextEditable`에서 `devRampMonthsInput`/`dev_ramp_months`
  참조 제거, 1년 누적 필드 존재 검증 추가. `python3 -m pytest -q` 100개
  전체 통과 확인(신규 테스트 다수 추가로 이전 대비 개수 증가).
- `automations/qlc-tlc-bit-cost-calculator/README.md`,
  `skills/qlc-tlc-bit-cost-calculator/SKILL.md.tmpl`을 위 6가지 변경
  기준으로 전면 갱신(`gen_skills.py`로 `SKILL.md` 재생성).
- 기존 `runs/` 아카이브는 이전 스키마(`dev_ramp_months` 있음, ER wafer가
  1회성 총량, 판매용 bit 필드 없음) 그대로 보존 — 재작성하지 않음.

## 2026-07-06 (9차 리파인 — 전체 투자비용 그래프 제거(텍스트화), 수율 램프업 그래프 2개 추가, 수율 램프업 공식 도입, 원가 계산 모드 토글)

- **"전체 투자비용 (Max capa 풀 빌드아웃 기준)" 그래프 제거, 계산 로직은
  그대로 유지하고 왼쪽 정보 패널에 텍스트 한 줄로만 표시**: `calc.py`의
  `full_buildout()` 함수(및 `combo_qlc_max_capa`를 대표값으로 쓰는 기존
  가정, `COMBO_FULL_CAPEX_ASSUMPTION`)는 전혀 바뀌지 않음 — `render_html.py`
  에서 6번째 SVG 차트(`chartFullBuildout`)와 그 legend를 제거하고, 대신
  `fullBuildoutNote` div에 "전체 투자비용 (Max capa 풀 빌드아웃 기준): 콤보
  XX / 분리 YY" 형태로 텍스트만 출력하도록 변경.
- **새 그래프 2개 추가 — QLC 수율 램프업 / TLC 수율 램프업**: x축은
  QLC:TLC 비율이 아니라 **생산 시작 후 경과 개월수(0~36개월)**, y축은
  수율(%). QLC 수율 램프업 그래프는 분리생산 QLC 전용 라인과 콤보 QLC
  레시피의 수율 램프업 곡선 두 개를 비교, TLC 수율 램프업 그래프는 분리
  TLC 전용 라인과 콤보 TLC 레시피를 비교. **두 그래프 모두 QLC:TLC 비율
  슬라이더와 무관하게 항상 고정으로 표시**(비율 표시용 점선도 그리지
  않음) — 수율 계수를 눈으로 보고 튜닝하기 위한 참고용 그래프.
  `calc.yield_ramp_curve()`/`calc.yield_ramp_curves()` 신설,
  `render_html.py`의 `combinedRampPoints()`로 미러링. 결과: 차트 개수
  5개 → 6개(전체 투자비용 차트 -1, 수율 램프업 차트 +2).
- **수율 램프업 공식 도입 (Normalized Exponential Saturation)**:
  `yield_fraction(t) = mature_yield_fraction × (1 - exp(-ramp_coef × t))`,
  `t`는 그 라인/레시피 자신의 생산 시작 시점(t=0)부터 경과한 개월수.
  기존 단일 `*_yield` 파라미터 4개(`qlc_yield`/`tlc_yield`/
  `combo_qlc_yield`/`combo_tlc_yield`)를 성숙수율+램프업계수 쌍 8개로 교체:
  `qlc_mature_yield`/`qlc_yield_ramp_coef`,
  `tlc_mature_yield`/`tlc_yield_ramp_coef`,
  `combo_qlc_mature_yield`/`combo_qlc_yield_ramp_coef`,
  `combo_tlc_mature_yield`/`combo_tlc_yield_ramp_coef`. 필수 키 26개 →
  30개. **월간(monthly) 스냅샷 표/그래프와 crossover 판정은 전혀 영향받지
  않음** — 계속 `mature_yield_fraction`을 그대로 사용(기존 `*_yield`와
  동일한 취급). **5년 누적 Bit 생산량 그래프만** 실제로 개월 단위
  반복문으로 이 수율 곡선을 적용하도록 변경(`monthly_bit × active_months`
  단순 곱셈에서, `calc.cumulative_ramp_bit_per_wafer()`가 각 생산월
  t=1..활성개월수마다 그 달의 실제 수율로 bit_per_wafer를 계산해 합산하는
  방식으로). 콤보 QLC/TLC 레시피, 분리 QLC/TLC 라인 각각 자기 자신의 t=0
  부터 독립적으로 램프업. **5년 누적 Cost/GB는 공식이 바뀌지 않음** — cost
  는 양품 bit이 아니라 처리한 wafer 수에 비례하므로 수율과 무관, 기존처럼
  `월간 wafer 원가 × 활성개월수 + dev_cost` 그대로 유지.
- **원가 계산 모드 (`cost_mode`) 토글 추가**: `model`(기본, 기존 투자비/
  density/수율/개발비/오버헤드 모델 그대로) 과 `direct`(GB당 원가를
  `combo_direct_cost_per_gb`/`dedicated_direct_cost_per_gb`로 **cent/GB
  단위로 직접 입력**, 투자비/개발비 모델 전체 무시) 중 선택. **bit
  생산량 계산(및 그 그래프)은 이 토글과 무관하게 항상 기존 물리 모델
  그대로** — cost_mode는 원가 계산에만 영향. `visualization.html`에 "원가
  계산 모드" 라디오 버튼 신설, `direct` 선택시 투자비/개발비 입력 필드
  11개(`qlc_capex_per_wafer`/`tlc_capex_per_wafer`/`combo_capex_per_wafer`/
  `er_wafer_combo`/`er_wafer_dedicated`/`combo_headcount`/
  `dedicated_headcount`/`combo_mask_count`/`dedicated_mask_count`/
  `coef_cost_per_headcount`/`coef_cost_per_mask`, `calc.COST_MODEL_ONLY_KEYS`)
  이 비활성화(회색 처리)되고 필수값 검증에서도 제외됨 — 입력해도 무시.
  `direct` 모드에서는 표의 Total cost/Cost per bit 칸과 1회성 개발비/전체
  투자비용 텍스트가 "—"(해당 없음)로 표시되고, Cost/GB 그래프(월간·5년
  누적 모두)는 직접 입력값을 비율과 무관한 고정값으로 사용(eokwon→cent
  환산 없이 그대로, 이미 cent/GB 단위이므로).
- `calc.py`: `REQUIRED_KEYS`의 4개 `*_yield` → 8개 `*_mature_yield`/
  `*_yield_ramp_coef`로 교체, `COST_MODEL_ONLY_KEYS`(투자비/개발비 전용
  11개 키) 신설, `OPTIONAL_STR_DEFAULTS`에 `cost_mode`(기본 `"model"`)/
  `combo_direct_cost_per_gb`/`dedicated_direct_cost_per_gb`(기본 `"0"`)
  추가, `RAMP_CHART_MONTHS`(36) 상수, `yield_ramp_fraction()`/
  `yield_ramp_curve()`/`yield_ramp_curves()`/
  `cumulative_ramp_bit_per_wafer()` 신설. `sweep()`이 월간 bit는 여전히
  mature yield로, 5년 누적 bit는 `cumulative_ramp_bit_per_wafer()`로
  계산하도록 변경(5년 누적 cost 공식은 불변). `run()`이 `cost_mode`/
  `direct_cost_per_gb`/`yield_ramp_curves`를 payload/summary에 추가.
  `full_buildout()`은 전혀 변경 없음(계산 로직 유지, 표시 방식만 변경).
- `render_html.py`: `PARAM_GROUPS`의 yield 필드를 mature_yield/
  yield_ramp_coef 쌍으로 교체, "원가 계산 모드" 서브패널(라디오 버튼 +
  `comboDirectCostInput`/`dedicatedDirectCostInput`) 신설, `chartFullBuildout`
  SVG/legend 제거하고 `fullBuildoutNote` div로 교체, `chartYieldRampQlc`/
  `chartYieldRampTlc` SVG/legend 신설. JS에 `yieldRampFraction()`/
  `cumulativeRampBitPerWafer()`/`combinedRampPoints()` 신설,
  `lineChart()`가 x축을 일반화(`xOpts` — 기본은 기존 qlc_ratio 0~100%,
  램프업 차트는 month 0~36)하도록 변경. `computeSweep()`이 새 8개 yield
  파라미터와 `cumulativeRampBitPerWafer()`로 5년 누적 bit를 계산하도록
  갱신. `readRequiredParams()`/`updateCostModeUI()` 신설 —
  `cost_mode=direct`일 때 `COST_MODEL_ONLY_KEYS` 11개 필드를
  disabled+필수값 검증 제외 처리. `chartPointsFromSweep()`이 `cost_mode`에
  따라 model 환산값 또는 direct 고정값을 분기해서 Cost 차트에 공급하도록
  변경. `render()`의 Total cost/Cost per bit 표시, `devCostNote`,
  `fullBuildoutNote`가 모두 `cost_mode`에 따라 분기(direct 모드에서는
  "—"/해당없음 텍스트).
- `samples/sample-1.txt`, `samples/sample-2.txt`: 4개 `*_yield` → 8개
  `*_mature_yield`/`*_yield_ramp_coef`로 재작성(mature 값은 기존 yield
  값 그대로 유지, ramp_coef는 합리적인 기본값 — 콤보 QLC가 가장 빠르게
  0.2, 분리 QLC/TLC가 0.15, 콤보 TLC(QLC 다이를 TLC로 강제 운용)가 가장
  느리게 0.1). `cost_mode=model`/`combo_direct_cost_per_gb=0`/
  `dedicated_direct_cost_per_gb=0` 명시적으로 추가(기존과 동일하게 동작).
  `calc.py`로 직접 실행해 확인한 결과: **크로스오버는 두 샘플 모두 변화
  없음**(sample-1 QLC 60%, sample-2 QLC 75%) — 월간 스냅샷이 여전히
  mature yield 기준이므로. 5년 누적 bit는 이제 램프업 반영으로 기존
  `monthly×54` 단순 곱셈보다 작게 나옴(sample-1 QLC 60%에서 약 10% 감소)
  — 예상된 동작.
- `tests/test_qlc_tlc_bit_cost_calculator.py`: yield 필드명 전체 갱신,
  `TestYieldRamp`(`yield_ramp_fraction`/`yield_ramp_curve` 공식 검증),
  `TestCostMode`(`direct` 모드에서 Cost 차트/표시가 직접 입력값을 쓰는지,
  `COST_MODEL_ONLY_KEYS`가 비활성화되는지) 신설.
  `TestFiveYearCumulative`를 실제 램프업 합산 결과 기준으로 갱신(기존
  `monthly × active_months` 단순 곱셈 가정 테스트는 더 이상 성립하지
  않으므로 교체). `TestFullBuildout`은 계산 로직 자체는 그대로이므로
  대부분 유지, 차트 관련 검증만 텍스트 존재 검증으로 교체.
  `test_no_leftover_placeholders_and_valid_json_payload`의
  `html.count("<svg") == 5`를 `== 6`으로 갱신. `python3 -m pytest -q`
  전체 통과 확인.
- `automations/qlc-tlc-bit-cost-calculator/README.md`,
  `skills/qlc-tlc-bit-cost-calculator/SKILL.md.tmpl`을 네 가지 변경 사항
  기준으로 전면 갱신(`gen_skills.py`로 `SKILL.md` 재생성).
- 기존 `runs/` 아카이브는 이전 스키마(구 `*_yield` 필드, 전체 투자비용
  차트, cost_mode 없음) 그대로 보존 — 재작성하지 않음.

## 2026-07-03 (8차 리파인 — 그래프 2개 → 5개, 5년 누적 + 전체 투자비용 빌드아웃 추가)

- **기존 2개 그래프(월간 Bit 생산량, 월간 Cost/GB)는 공식 변경 없이 그대로
  유지**, 아래 3개 그래프를 새로 추가:
  1. **5년 누적 Bit 생산량 vs QLC 비율 (억GB)**: 60개월 동안 그 비율로 계속
     생산했을 때의 콤보/분리 누적 bit 생산량. 새 공유 파라미터
     `dev_ramp_months`(콤보·분리 공통, 기본 6)로 "60개월 중 최초 몇 개월을
     개발/품질인증 기간(생산량 0)으로 볼지"를 입력받고, 나머지
     `(60 - dev_ramp_months)` 개월만 월간 생산량으로 실제 생산한다고 계산:
     `5년 누적 bit = 월간 bit 생산량 × (60 - dev_ramp_months)`.
  2. **5년 누적 Cost/GB vs QLC 비율 (cent/GB)**: 같은 논리로
     `5년 누적 cost = 월간 wafer 원가(dev cost 제외) × (60 - dev_ramp_months)
     + dev_cost`(1회성 개발비는 한 번만 더함), `5년 누적 cost/bit = 5년 누적
     cost / 5년 누적 bit`. 단위는 기존 Cost 그래프와 동일하게 cent/GB (같은
     `exchange_rate_krw_per_usd` 재사용).
  3. **전체 투자비용 (Max capa 풀 빌드아웃 기준)**: 실제 가동 비율과 무관하게
     각 시나리오가 자기 라인들을 Max capa까지 전부 지어서 투자한다고
     가정했을 때의 총 투자비용 — 비율-불변 고정값이라 수평선 2개(콤보/분리)로
     표시. 분리는 `qlc_capex_rate×qlc_max_capa + tlc_capex_rate×tlc_max_capa
     + dedicated_dev_cost`. 콤보는 물리적으로 하나의 라인이라 대표 capa
     하나가 필요한데, `combo_qlc_max_capa`와 `combo_tlc_max_capa` 중
     **`combo_qlc_max_capa`를 대표값으로 채택** — 콤보 라인이 QLC 다이
     설계를 기준으로 지어진 하나의 물리적 라인이기 때문(`combo_capex_per_wafer`/
     `combo_gross_die`가 이미 두 레시피 간 공유되는 것과 같은 근거). 이는
     계산기가 임의로 정한 모델링 가정이며 `calc.COMBO_FULL_CAPEX_ASSUMPTION`
     문자열로 코드에 명시, `report.md`/README에도 그대로 restate. y축 단위는
     cent 변환 없이 `currency_unit` 그대로(다른 4개 그래프와 달리 GB당이
     아니라 총 투자비용이므로 cent/GB 변환을 적용하지 않음).
- `calc.py`: `OPTIONAL_STR_DEFAULTS`에 `dev_ramp_months` 기본값 `"6"` 추가,
  `FIVE_YEAR_MONTHS`(60) 상수, `active_production_months()` 헬퍼,
  `COMBO_FULL_CAPEX_ASSUMPTION` 문자열, `full_buildout()` 함수 신설.
  `sweep()`이 `dev_ramp_months` 인자를 받아 각 row에
  `five_year_{combo,dedicated}_{bit_total,bit_total_gb,cost_total,
  cost_per_bit,cost_per_gb}` 10개 필드 추가 (기존 monthly 필드는 전혀 변경
  없음). `run()`이 `dev_ramp_months`를 params에서 읽어 `sweep()`에 전달하고,
  `full_buildout(p)` 결과를 `sweep.json`/`summary.json`의 `full_buildout`
  키로 추가. CLI stdout 다이제스트에도 `full_buildout` 포함.
- `render_html.py`: `OPTIONAL_PARAM_LABELS`에 `dev_ramp_months` 라벨 추가,
  "표시 설정" 패널에 개발 Ramp 기간 입력 필드(`devRampMonthsInput`) 신설
  (currency_unit/bit_unit/ratio_step/exchange_rate와 동일하게 "전체
  비우기"로는 지워지지 않음). JS에 `activeProductionMonths()`/
  `fullBuildout()` 신설, `computeSweep()`이 `devRampMonths` 인자를 받아
  calc.py와 동일한 10개 five_year 필드를 계산하도록 변경.
  `chartPointsFromSweep()`이 five_year GB/cent 필드와 (비율과 무관하게 모든
  포인트에 동일 값을 반복하는) `full_buildout_{combo,dedicated}` 필드를
  추가로 계산. HTML에 SVG 차트 3개(`chartFiveYearBit`/`chartFiveYearCost`/
  `chartFullBuildout`) 및 각 legend 신설, `render()`이 `chartsInfo` 배열을
  5개 차트로 확장해 그리도록 변경. `currencyUnitInput`의 input 리스너가
  이제 `updateUnitLabels()`에 더해 `render()`도 호출하도록 변경 — 전체
  투자비용 그래프의 y축 라벨이 `currency_unit` 그대로이므로(cent 변환 없음)
  값을 타이핑하면 그 축 라벨도 즉시 갱신되어야 함(`bitUnitInput`은 여전히
  `updateUnitLabels()`만 호출). `.charts`의 CSS grid를
  `repeat(auto-fit, minmax(460px, 1fr))`로 변경해 5개 차트가 넓은 화면에서
  2열로, 좁은 화면에서 1열로 배치되도록 레이아웃 정리(전체 투자비용 차트는
  `.chart-full-width`로 항상 전체 폭 차지).
- `samples/sample-1.txt`, `samples/sample-2.txt`에 `dev_ramp_months=6`
  추가(다른 필드는 변경 없음 — 기존 crossover 지점에 영향 없음, 5년 누적/
  빌드아웃 그래프는 새 그래프이므로 crossover 판정 자체와 무관).
- `tests/test_qlc_tlc_bit_cost_calculator.py`: `TestFiveYearCumulative`
  (`active_production_months`/`five_year_*` 필드가 monthly 필드 ×
  active_months + dev_cost 관계를 만족하는지, dev_ramp_months=0일 때 60개월
  전부 생산하는지 등), `TestFullBuildout`(`full_buildout()`이
  `combo_qlc_max_capa`를 쓰는지, 비율과 무관한 고정값인지, dev_cost 포함
  여부) 신설. `TestRenderHtml`/`TestChartYAxisUnitLabels`에 5개 SVG 존재,
  `chartFiveYearBit`/`chartFiveYearCost`/`chartFullBuildout` id 존재,
  `devRampMonthsInput` 필드 존재 검증 추가.
  `test_no_leftover_placeholders_and_valid_json_payload`의
  `html.count("<svg") == 2` 를 `== 5`로 갱신.
  `test_currency_unit_input_only_updates_labels_not_chart`를
  `test_currency_unit_input_also_redraws_chart_for_buildout_axis`로 교체
  (동작이 실제로 바뀌었으므로). `python3 -m pytest -q` 전체 통과 확인.
- `automations/qlc-tlc-bit-cost-calculator/README.md`에 "그래프 5개" 섹션
  신설(3개 새 그래프의 공식과 콤보 대표 capa 가정 근거 전문 서술) +
  파라미터 표에 `dev_ramp_months` 행 + Limits에 콤보 대표 capa 가정/
  dev_ramp_months 공통 가정 bullet 2개 추가.
  `skills/qlc-tlc-bit-cost-calculator/SKILL.md.tmpl`도 동일 내용 기준으로
  갱신 후 `gen_skills.py`로 `SKILL.md` 재생성.
- 기존 2개 그래프의 계산 로직(월간 bit/cost 공식, crossover 판정)은 전혀
  바뀌지 않음 — 순수 추가. 기존 `runs/` 아카이브는 이전 스키마(five_year_*/
  full_buildout 필드 없음) 그대로 보존 — 재작성하지 않음.

## 2026-07-03 (7차 리파인 — Cost 그래프 y축 cent/GB 고정 + 샘플 크로스오버 재조정)

- **Cost 그래프 y축을 cent/GB로 고정 환산**: `currency_unit`이 억원(큰
  단위)일 때 `cost_per_gb` 값이 소수점 이하로 아주 작아져(예: 0.0003억원/GB)
  y축이 전부 0으로 뭉개져 보이는 문제를 해결. 표시 설정 파라미터 그룹에
  새 선택 파라미터 `exchange_rate_krw_per_usd`(환율, 원/달러, 기본값
  `1300`)를 추가하고, Cost 그래프에서만 다음 공식을 적용:
  `cent/GB = (cost_per_gb_억원값 × 100,000,000 ÷ exchange_rate_krw_per_usd) × 100`
  (억원→원 환산 후 환율로 나눠 달러, 다시 100을 곱해 cent). 표의
  Cost/Cost-per-bit 행과 `report.md`는 그대로 `{currency_unit}/GB`를
  보여줌 — 이번 변경은 Cost 그래프의 y축 표기에만 적용됨. Bit 생산량
  그래프의 억GB 고정 축은 변경 없음.
- `calc.py`: `OPTIONAL_STR_DEFAULTS`에 `exchange_rate_krw_per_usd` 기본값
  `"1300"` 추가, `WON_PER_EOKWON`(1억원=100,000,000원)/`CENT_PER_USD`(100)
  상수와 `cost_per_gb_eokwon_to_cent()` 헬퍼 신설 (Cost 차트가 미러링하는
  단일 소스; `calc.py`의 sweep/report 경로 자체는 호출하지 않음 — 이
  변환은 순수 표시 레이어이므로 sweep.csv/report.md에는 새 필드를 추가하지
  않음).
- `render_html.py`: `OPTIONAL_PARAM_LABELS`에 `exchange_rate_krw_per_usd`
  라벨 추가, "표시 설정" 패널에 환율 입력 필드(`exchangeRateInput`) 신설
  (`resetAllInputs()`가 `initialParams.exchange_rate_krw_per_usd`로 초기화,
  "전체 비우기"로는 지워지지 않음 — currency_unit/bit_unit/ratio_step과
  동일한 취급). JS에 `costPerGbEokwonToCent()`/`readExchangeRate()` 신설,
  `chartPointsFromSweep()`이 `combo_cost_per_gb_cent`/
  `dedicated_cost_per_gb_cent` 필드를 계산해 Cost 차트에 넘기도록 변경
  (y축 유닛 인자도 동적 `currencyUnit + "/GB"`에서 고정 `"cent/GB"`로
  변경). `chartCostTitle`도 고정 문구로 변경. `exchangeRateInput`의 input
  이벤트가 (currency_unit/bit_unit처럼 라벨만 갱신하는 게 아니라) 차트를
  다시 그리도록 `render()` 호출 — 반대로 currencyUnitInput/bitUnitInput은
  더 이상 어떤 차트에도 영향을 주지 않으므로 `updateUnitLabels()`만 호출하도록
  단순화.
- **샘플 크로스오버를 QLC 15% 부근에서 60% 부근으로 재조정**:
  `samples/sample-1.txt`의 콤보 TLC 레시피 효율을 낮춰(`combo_tlc_density`
  27→20, `combo_tlc_yield` 86→78 — 진짜 TLC 전용 설계`tlc_density=32`/
  `tlc_yield=88` 대비 QLC 다이를 억지로 TLC로 돌릴 때의 효율 저하를 더
  뚜렷하게 반영) 분리 생산이 QLC 수요가 뚜렷이 우세해질 때까지 계속
  유리하도록 재설계. `sample-1.txt`에 `exchange_rate_krw_per_usd=1300`도
  명시적으로 추가. `helpers/calc.py`로 직접 실행해 확인한 결과:
  crossover는 정확히 QLC 60% (요청 범위 50~70% 이내). 다른 필드(투자비,
  max_capa, 개발비 등)는 그대로 유지 — 여전히 순수 합성 데이터이며 실제
  fab 값이 아님.
- `tests/test_qlc_tlc_bit_cost_calculator.py`: `test_crossover_exists_between_extremes`
  가 이제 `qlc_ratio == 60`(50~70 범위 포함)을 검증하도록 갱신.
  `test_cost_per_gb_eokwon_to_cent_matches_formula`/
  `test_cost_per_gb_eokwon_to_cent_scales_inversely_with_exchange_rate`
  신설. `test_display_settings_default_when_absent`에
  `exchange_rate_krw_per_usd == "1300"` 검증 추가.
  `test_optional_display_keys_also_commented`에 새 키 포함.
  `test_cost_chart_axis_unit_is_dynamic_currency_unit_per_gb`를
  `test_cost_chart_axis_unit_is_fixed_cent_per_gb`로 교체 (고정 `cent/GB`
  문자열 + `costPerGbEokwonToCent`/`exchangeRateInput` 존재 확인),
  `test_currency_unit_input_redraws_chart_not_just_title`를
  `test_currency_unit_input_only_updates_labels_not_chart`로 교체, 새
  `test_exchange_rate_input_redraws_chart` 추가. `python3 -m pytest -q`
  전체 통과 확인.
- `automations/qlc-tlc-bit-cost-calculator/README.md`,
  `skills/qlc-tlc-bit-cost-calculator/SKILL.md.tmpl` 를 두 변경 사항
  기준으로 갱신 (`gen_skills.py`로 `SKILL.md` 재생성).
- 계산 모델(bit/cost 공식, crossover 판정 로직 자체)은 바뀌지 않음 — Cost
  그래프의 표시 레이어와 샘플 파라미터 값만 변경. 기존 `runs/` 아카이브는
  이전 스키마(고정 currency_unit/GB 축, 옛 crossover 15%) 그대로 보존 —
  재작성하지 않음.

## 2026-07-03 (6차 리파인 — 그래프 y축 단위 표시 + 순수 텍스트 편집 가능한 초기값)

- **그래프 y축 자체에 실제 단위 표시**: 지금까지는 차트 제목에만 괄호로
  단위(억GB, `{currency_unit}/GB`)가 적혀 있고 y축 눈금에는 숫자만
  있었음 — 축만 보면 arbitrary unit처럼 보인다는 지적을 반영. 두 SVG
  차트(`render_html.py`의 `lineChart()`) 모두 y축에 (1) 세로로 회전된
  단위 라벨 텍스트(`axis-unit-label` 클래스, `transform="rotate(-90 ...)"`)
  와 (2) 실제 눈금 값(`fmtAxisTick()`으로 스케일에 맞게 포맷된 숫자 +
  옅은 가로 그리드라인, 4등분)을 추가로 그리도록 변경. Bit 생산량 차트는
  고정 **"억GB"**, Cost 차트는 **`currencyUnit + "/GB"`** — currency_unit
  입력창 값이 바뀌면 즉시 축 라벨도 다시 그려짐 (`currencyUnitInput`/
  `bitUnitInput`의 `input` 리스너가 `updateUnitLabels()`에 더해
  `sweep.length > 0`일 때 `render()`도 호출하도록 변경). y축 라벨 공간
  확보를 위해 차트 왼쪽 여백(`padL`)을 46px → 58px로 확대. 사용자가
  타이핑한 currency_unit 텍스트는 `escapeXml()`로 이스케이프한 뒤 SVG에
  삽입 (특수문자로 인한 마크업 깨짐 방지).
- **`visualization.html` 초기값을 순수 텍스트 에디터로 찾고 고칠 수 있게
  변경**: 기존엔 초기 payload가 `<script type="application/json">` 안에
  압축된 한 줄 JSON으로 들어가 있어 메모장으로 찾기/수정하기 어려웠음.
  이제 `<script id="payload">`
  안에 `var INITIAL_PAYLOAD = {...};` 형태의, 사람이 읽기 쉽게
  들여쓰기된(pretty-printed) JS 객체 리터럴로 바뀜
  (`render_html._payload_js_literal()`, `json.dumps(indent=2)` 기반) —
  JSON과 달리 JS 객체 리터럴은 `//` 주석을 허용하므로, `params` 안의 모든
  키(26개 필수 fab 파라미터 + `currency_unit`/`bit_unit`/`ratio_step`)
  옆에 그 뜻과 단위를 적은 `// 설명` 주석을 자동으로 붙임
  (`OPTIONAL_PARAM_LABELS` 신설, 기존 `PARAM_LABELS`와 병합). 스크립트
  바로 위에는 "숫자를 고치고 저장한 뒤 다시 열면 그 값이 초기값으로
  반영된다"는 안내와, `params` 아래의 `sweep`/`crossover`/`dev_cost`/
  `best_*` 항목은 참고용 기록일 뿐 계산기가 다시 읽지 않는다는 설명을
  HTML 주석으로 추가. 메인 스크립트는 더 이상
  `JSON.parse(document.getElementById("payload").textContent)`를 쓰지
  않고 `var data = INITIAL_PAYLOAD;`로 직접 참조 (부수 효과로, sweep
  결과에 `Infinity`가 섞여도 — 순수 JSON으로는 파싱 불가능했던 값도 —
  JS 리터럴에서는 전역 `Infinity`로 정상 평가됨).
- `render_html.py`: `_payload_js_literal()` / `OPTIONAL_PARAM_LABELS` /
  `_PAYLOAD_LINE_RE` 신설, CSS에 `.axis-unit-label` 추가, `lineChart()`에
  `yAxisUnit` 매개변수 + `escapeXml()`/`fmtAxisTick()` 헬퍼 + y축 그리드/
  눈금/라벨 렌더링 추가, 모듈 docstring 갱신.
- `tests/test_qlc_tlc_bit_cost_calculator.py`: `_extract_initial_payload()`
  헬퍼(주석 제거 후 JSON 파싱) 추가하고 기존
  `test_no_leftover_placeholders_and_valid_json_payload`가 이를 쓰도록
  갱신, `TestChartYAxisUnitLabels`(축 라벨 클래스·고정 억GB·동적
  currency_unit·회전 라벨·currency 입력시 재렌더)와
  `TestPayloadPlainTextEditable`(JSON.parse 미사용·pretty-print·안내
  주석·전체 필수 키 인라인 주석·값 수정 후 재파싱 반영·blank scaffold도
  동일 메커니즘) 신설. `python3 -m pytest -q
  tests/test_qlc_tlc_bit_cost_calculator.py` 48개 전체 통과 확인.
- `automations/qlc-tlc-bit-cost-calculator/README.md`,
  `skills/qlc-tlc-bit-cost-calculator/SKILL.md.tmpl` 를 두 변경 사항
  기준으로 갱신 (`gen_skills.py`로 `SKILL.md` 재생성).
- 계산 모델(공식/파라미터/단위 변환)은 전혀 바뀌지 않음 — 표시 레이어만
  변경. 기존 `runs/` 아카이브는 이전 스키마(compact JSON payload, 축
  단위 없음) 그대로 보존 — 재작성하지 않음.

## 2026-07-03 (5차 리파인 — 인력/Mask 개발비 추가 + 단위 표기 정비)

- **1회성 개발비에 인력·Mask 항목 추가**: 기존 ER wafer 환산에 더해
  `combo_headcount`/`dedicated_headcount`(필요 인력 명 수)와
  `combo_mask_count`/`dedicated_mask_count`(소모 Mask 매수)를 콤보/분리
  각각 독립적으로 입력받고, 공통 계수 `coef_cost_per_headcount`(인력
  1명당 환산 비용)와 `coef_cost_per_mask`(Mask 1매당 환산 비용) — 이
  둘은 콤보/분리로 나뉘지 않는 단일 공유 값 — 으로 비용 환산해
  `dev_cost`에 더함:
  `dev_cost(combo) = er_wafer_combo×(combo_capex_per_wafer/10000) +
  combo_headcount×coef_cost_per_headcount +
  combo_mask_count×coef_cost_per_mask` (dedicated도 동일 구조, ER wafer
  블렌디드 가정은 그대로 유지). 필수 키 20개 → 26개.
- **capex_per_wafer 입력 단위를 "1만(10,000) wafer당 비용"으로 변경**:
  기존엔 wafer 1장당 비용을 직접 입력했지만, 이제 사용자는 "1만장 생산시
  드는 투자비"를 입력하고 계산기가 내부적으로 `입력값/10000`으로 환산해
  기존과 동일한 wafer당 단가를 씀 (`calc.capex_rate_per_wafer`). 콤보/QLC/
  TLC capex 필드 전부 동일 규칙 적용 — wafer 원가 계산과 ER-wafer
  dev-cost 환산 양쪽 모두에 적용.
- **수율(yield) 입력을 %로 변경**: 기존엔 0~1 소수를 입력했지만, 이제
  `82`처럼 %로 입력하고 계산기가 내부적으로 100으로 나눠 기존과 동일하게
  사용 (`calc.yield_fraction`). 계산 결과 자체는 바뀌지 않음 — 입력
  방식·라벨만 변경.
- **Density 필드 라벨을 `Gb/Wafer`로 명시**: 계산식 구조
  (`density × grossdie_per_wafer × yield`)는 그대로 두고 라벨만 정정.
  대신 bit 생산량을 GB로 보여줘야 하는 곳(그래프, report.md)에서는 원시
  Gb 결과를 8로 나눠(1 GB = 8 Gb) GB로 환산하는 표시 레이어를 추가
  (`calc.bit_total_gb`, 각 sweep row의 `*_bit_total_gb`/`*_cost_per_gb`
  필드). crossover 판정은 원시 Gb 값 그대로 사용 — 양쪽 시나리오에 동일
  배율을 곱하는 변환이므로 대소 비교에 영향 없음(테스트로 확인).
- **그래프 단위 명시**: `visualization.html`의 Bit 생산량 그래프 y축을
  **억GB**(10^8 GB)로 고정, Cost/Cost-per-bit 그래프 y축을
  **`{currency_unit}/GB`**(사용자가 자유롭게 정하는 통화 단위는 유지하되
  분모를 GB로 통일)로 변경. 표 안의 "Bit 생산량"/"Cost / bit" 행은 기존과
  동일하게 `bit_unit` 라벨 기준 원시값을 계속 표시(그래프만 GB 환산).
- **Max Wafer capa 필드에 단위 라벨(`wafer/월`) 추가**: 계산 방식은
  변경 없음, 표시만 명시.
- `calc.py`: `REQUIRED_KEYS`에 6개 키 추가, `yield_fraction`/
  `capex_rate_per_wafer`/`bit_total_gb` 헬퍼 추가, `combo_dev_cost`/
  `dedicated_dev_cost`/`sweep()`이 이 헬퍼들을 통해 계산하도록 갱신,
  각 sweep row에 `combo_bit_total_gb`/`dedicated_bit_total_gb`/
  `combo_cost_per_gb`/`dedicated_cost_per_gb` 필드 추가.
- `render_html.py`: PARAM_GROUPS에 새 8개 필드(`dev-cost` 그룹, 기존
  `er-wafer` 그룹을 대체) 추가 + 기존 필드 라벨 전체 갱신(Gb/Wafer, %,
  1만 Wafer, wafer/월). JS `computeSweep()`이 `yieldFraction`/
  `capexRatePerWafer`/`bitTotalGb`를 동일하게 미러링, 두 차트가
  `combo_bit_100m_gb`/`combo_cost_per_gb` 등 GB 환산 시리즈를 그리도록
  변경, Cost 차트 제목이 `currency_unit` 입력값에 따라 동적으로
  "{currency_unit}/GB"로 갱신되도록 `updateUnitLabels()`에 로직 추가.
- `samples/sample-1.txt`, `samples/sample-2.txt` 를 새 단위 스케일로
  재작성 (capex ×10000, yield ×100, 인력/Mask/계수 필드 추가) — capex를
  10000으로 나누고 다시 곱하는 왕복 변환이 상쇄되므로 wafer당 유효
  단가는 이전과 동일, 인력/Mask 개발비 추가분은 total cost 대비 1% 미만
  수준으로 작게 설정해 crossover 지점에 실질적 영향이 없도록 함.
  `calc.py` 로 직접 실행해 확인한 결과: sample-1 crossover는 여전히
  QLC 15% (변화 없음), sample-2는 여전히 QLC 75% (변화 없음).
- `tests/test_qlc_tlc_bit_cost_calculator.py`: capex/yield 변환을 반영해
  `test_sweep_endpoints_match_single_recipe_capacity`/
  `test_dev_cost_applied_at_every_ratio_not_just_once` 갱신, dev-cost
  테스트에 헤드카운트/Mask 항목 반영, `calc.capex_rate_per_wafer`/
  `calc.yield_fraction`/`calc.bit_total_gb` 단위 변환 유닛 테스트 추가,
  GB 표시 변환이 crossover 판정을 바꾸지 않음을 검증하는
  `TestGbDisplayConversion` 클래스 신설. 기존
  `test_no_coefficient_keys_in_required`는 이제 유효하지 않은 전제(계수
  0개)를 검증하고 있어 `test_only_the_two_shared_dev_cost_coefficients_remain`
  로 교체(옛 step 기반 계수들은 여전히 없고, 새 헤드카운트/Mask 계수 2개만
  있음을 확인). `render_html.py` 쪽 동일 취지 테스트
  (`test_only_the_two_shared_dev_cost_coefficients_appear`)도 교체.
- `automations/qlc-tlc-bit-cost-calculator/README.md` 를 새 단위 규칙·
  새 필수 키 26개·GB 그래프 단위 기준으로 갱신.
- 기존 `runs/` 아카이브는 이전 스키마(구 capex/yield 단위, `er-wafer`
  그룹, GB 미변환 그래프) 그대로 보존 — 재작성하지 않음.

## 2026-07-02 (4차 리파인 — 공유 wafer capa 풀 가정 되돌림)

- **`max_wafer_capa_per_fab` 하나로 통합했던 3차 리파인의 가정을 되돌림**:
  근거 — 분리 생산의 QLC 전용 라인·TLC 전용 라인, 콤보의 QLC 레시피·TLC
  레시피는 전부 서로 다른 투자/라인이므로, 100% 가동시 max capa가 반드시
  같을 필요가 없음. 하나의 공유 풀을 나눠 쓴다는 가정은 잘못된 단순화였음.
- **4개의 독립적인 max_capa 파라미터로 복귀**: `qlc_max_capa` (QLC 전용
  라인), `tlc_max_capa` (TLC 전용 라인), `combo_qlc_max_capa` (콤보가
  QLC 레시피로 100% 가동시), `combo_tlc_max_capa` (콤보가 TLC 레시피로
  100% 가동시) — `max_wafer_capa_per_fab` 필드는 완전히 제거. 필수 키
  17개 → 20개.
- **비율에 따라 실제 반영 capa가 달라지는 3차 리파인의 성질은 유지**:
  분리 생산은 `wafer_qlc_dedicated = qlc_max_capa × r/100`,
  `wafer_tlc_dedicated = tlc_max_capa × (100-r)/100` 로, 각 라인이 **자기
  자신의** max capa 기준으로 비율만큼만 가동 (공유 총량을 나누는 게
  아님). 콤보는 `wafer_qlc_combo = combo_qlc_max_capa × r/100`,
  `wafer_tlc_combo = combo_tlc_max_capa × (100-r)/100` 로 기존과 동일한
  방식 유지 (콤보는 물리적으로 하나의 라인이라 항상 100% 가동, 레시피
  간 시간분할).
- `calc.py`의 `sweep()` 출력 필드명을 `wafer_qlc`/`wafer_tlc` (공유
  개념) 에서 시나리오별 `wafer_qlc_dedicated`/`wafer_tlc_dedicated`/
  `wafer_qlc_combo`/`wafer_tlc_combo` 로 분리 — 두 시나리오가 이제 서로
  다른 wafer 물량을 가질 수 있으므로 필드도 분리해야 함.
- `render_html.py`: `visualization.html`의 max capa 입력 필드를
  4개로 분리 (`fab-shared` 그룹 제거, 각 라인/레시피 그룹에 자기
  `max_capa` 필드 추가). 표시 테이블도 콤보/분리 생산 섹션 아래에 각각
  자기 wafer/월 값을 보여주도록 재배치 (예전엔 상단에 공유 wafer_qlc/
  wafer_tlc 한 쌍만 있었음). JS의 `computeSweep()` 미러도 동일하게 갱신.
- `samples/sample-1.txt`, `samples/sample-2.txt` 를 4-파라미터 스키마로
  갱신 — 의도적으로 4개 값을 서로 다르게 설정해 독립 capa 동작을
  보여줌 (예: sample-1 은 `qlc_max_capa=85000`/`tlc_max_capa=75000`/
  `combo_qlc_max_capa=80000`/`combo_tlc_max_capa=78000`). 실제 계산
  결과 crossover 지점은 두 샘플 모두 3차 리파인 때와 동일 (sample-1 QLC
  15%, sample-2 QLC 75%) — 미세한 capa 차이가 그 지점을 옮기지 않음을
  `calc.py` 실행으로 직접 확인.
- `tests/test_qlc_tlc_bit_cost_calculator.py`: `wafer_qlc`/`wafer_tlc`
  참조를 새 필드명으로 갱신, 공유-풀 가정을 검증하던
  `test_wafer_capacity_split_shared_by_both_scenarios` 를 독립 capa를
  검증하는 `test_each_line_sweeps_its_own_independent_max_capa` /
  `test_independent_max_capa_values_need_not_match` 로 교체, 콤보
  cost_total이 더 이상 비율-불변 고정값이 아님을 확인하는
  `test_combo_cost_total_varies_with_ratio` 추가 (combo_qlc_max_capa !=
  combo_tlc_max_capa 인 SAMPLE 기준). `python3 -m pytest -q
  tests/test_qlc_tlc_bit_cost_calculator.py` 30개 전체 통과 확인.
- `automations/qlc-tlc-bit-cost-calculator/README.md` 를 4-파라미터
  모델·새 계산식 기준으로 갱신.
- 기존 `runs/` 아카이브는 3차 리파인 스키마(`max_wafer_capa_per_fab`,
  공유 `wafer_qlc`/`wafer_tlc`) 그대로 보존 — 재작성하지 않음.

## 2026-07-02 (3차 리파인 — 모델 재설계)

- **분리 생산을 비율-스윕으로 전환**: 지금까지 비율과 무관한 고정 점선
  기준선이었던 "분리 생산"을, 콤보와 동일하게 QLC:TLC 비율(0~100%)에
  대한 완전한 스윕 결과로 바꿈. 근거: 분리 생산도 결국 같은 팹 안에서
  투자와 공간(wafer capa)을 QLC 라인/TLC 라인이 나눠 쓰는 것이므로, 새
  공유 파라미터 `max_wafer_capa_per_fab` (팹 전체 wafer capa, 콤보·분리가
  동일 값 공유) 를 도입해 두 시나리오 모두 비율 `r` 에서
  `wafer_qlc = capa × r/100`, `wafer_tlc = capa × (100-r)/100` 을 사용하게
  함. 결과: 두 그래프(Bit 생산량 vs QLC비율, Cost/Bit vs QLC비율) 모두
  콤보·분리 생산이 실선 두 줄로 나란히 그려짐 — 더 이상 점선 기준선 없음.
- **Step 관련 필드 전부 제거**: `qlc_step`/`tlc_step`/`combo_step`,
  `coef_step_cost` 삭제. 계수(coefficient) 체계 전체 제거
  (`coef_capex_cost`/`coef_density_bit`/`coef_gross_die_bit`/
  `coef_wafer_bit` 도 삭제) — 파라미터를 직접 곱해서 계산:
  `bit_per_wafer = density_per_die × grossdie_per_wafer × yield`,
  `cost(line) = capex_per_wafer × wafer_count`. 필수 키 21개 → 17개로
  감소 (max_capa 6개 필드가 공유 `max_wafer_capa_per_fab` 1개로 통합된
  영향이 큼).
- **`capex`를 `capex_per_wafer` 로 재정의**: 레시피별(QLC/TLC/콤보)로
  다를 수 있는 wafer당 투자비로 명확화. `dedicated_overhead` (고정 NRE)
  는 제거하고 아래 ER wafer 방식으로 대체.
- **ER(엔지니어링 런/품질인증) wafer 소모량 파라미터 추가**:
  `er_wafer_combo` / `er_wafer_dedicated` 를 새로 추가 — 개발 물량을
  wafer 수로 입력받아 해당 시나리오의 capex_per_wafer로 환산한 1회성
  개발비를 모든 비율의 total cost에 동일하게 더함
  (`dev_cost(combo) = er_wafer_combo × combo_capex_per_wafer`,
  `dev_cost(dedicated) = er_wafer_dedicated × (qlc_capex_per_wafer +
  tlc_capex_per_wafer) / 2`). 분리 생산 쪽의 QLC/TLC capex_per_wafer
  합산 방식은 "50:50 분배, 평균 적용"이라는 가정을 코드
  (`calc.DEDICATED_ER_ASSUMPTION`)·report.md·README에 투명하게 명시.
- **기본 실행이 더 이상 빈 계산기가 아님**: params 파일 없이 `frame run`
  을 호출하거나 채팅에서 아무 값도 주지 않으면, 이제 내장된
  `samples/sample-1.txt` 값으로 미리 채워진 계산기가 열림 (그래프·수치가
  처음부터 보임, 화면 상단에 "샘플 데이터" 배너 표시,
  `calc.py --sample` → `sweep.json`/`summary.json` 의 `is_sample: true`
  로 추적). 완전히 빈 화면(모든 필드 공백) 옵션은 그대로 유지 —
  `render_html.py --blank`, 화면 안의 새 **"전체 비우기"** 버튼, 또는
  채팅에서 "blank"/"빈 화면" 명시적 요청으로 얻을 수 있음
  (`SKILL.md.tmpl` Phase 1 참고).
- `samples/sample-1.txt`, `samples/sample-2.txt` 를 새 스키마로 완전히
  재작성 (크로스오버가 있는 케이스로 유지: sample-1 은 QLC 15% 부근
  저-중간 크로스오버, sample-2 는 QLC 75% 부근 → 분리 생산이 대부분
  구간에서 우위).
- `tests/test_qlc_tlc_bit_cost_calculator.py` 를 새 모델 기준으로 재작성
  (계수 테스트 제거, 공유 capa 분배·비율-종속 분리 원가·개발비·
  is_sample·샘플 배너 테스트 추가). `python3 -m pytest -q` 29개 전체
  통과 확인.
- `automations/qlc-tlc-bit-cost-calculator/README.md` 를 새 모델·새
  기본 동작(샘플 우선) 기준으로 전면 갱신.
- 기존 `runs/` 아카이브는 이전 스키마(구 필드명, 고정 기준선) 그대로
  보존 — 재작성하지 않음.

## 2026-07-02 (2차 리파인)

- **params 파일 없이도 완전히 동작하는 브라우저 계산기로 확장**: 실제 fab
  수치(Step 수, 투자비, density, gross die, 수율, max capa 등 21개 필수
  키)는 외부로 반출할 수 없는 경우가 많아, 계수뿐 아니라 이 21개 파라미터
  전부를 `visualization.html` 의 입력창으로 노출. `render_html.py --blank`
  로 모든 필드가 빈 채로 시작하는 페이지를 생성할 수 있고, `frame run` 을
  `--in` 없이 호출해도(또는 Phase 1에서 params를 못 찾으면) 자동으로 이
  blank 화면으로 폴백함 (`SKILL.md.tmpl` Phase 1 참고).
- 값이 비어 있거나 숫자가 아니면 해당 입력창을 빨간 테두리로 표시하고
  에러 배너에 어떤 키가 문제인지 나열 — 유효하지 않은 값으로 조용히
  계산하지 않음. 계수는 비워두면 `calc.py` 와 동일한 중립 기본값으로
  대체.
- "불러온 초기값으로 전체 재설정" 버튼으로 params 파일이 있었다면 그
  값으로, 없었다면 전부 빈 값으로 되돌릴 수 있음.
- `tests/test_qlc_tlc_bit_cost_calculator.py` 에 `TestRenderHtmlBlank`
  (blank_payload/render_blank) 및 모든 필수 키에 입력창이 존재하는지
  확인하는 테스트 추가. `python3 -m pytest -q` 23개 전체 통과 확인.
- `automations/qlc-tlc-bit-cost-calculator/README.md` 를 새 무-params
  워크플로 기준으로 갱신.

## 2026-07-02

- **계산 모델을 coefficient 기반으로 재설계**: `*_bit_per_wafer` (미리 계산된
  net bit 값)를 입력받던 방식을 폐기하고, `density × gross_die × yield` 로
  bit 생산량을 직접 도출하도록 변경. `cost = capex×coef_capex_cost +
  step×coef_step_cost` 로 원가도 물리 파라미터에서 도출. 각 계수
  (`coef_step_cost`, `coef_capex_cost`, `coef_density_bit`,
  `coef_gross_die_bit`, `coef_wafer_bit`)는 params 파일 또는
  `visualization.html` 의 입력창에서 직접 튜닝 가능 (기본값은 중립: `0` 또는
  `1.0`).
- **`dedicated_overhead` 추가**: 분리 생산(QLC 전용 + TLC 전용 신제품)을
  선택할 때 발생하는 고정 NRE/품질인증 비용을 별도 계수로 반영. 이 비용이
  콤보 대비 분리 생산의 crossover 지점을 만드는 핵심 요인 — TLC 수요 비중이
  낮을 때는 콤보(QLC 다이를 TLC mode로 재사용)가, 높을 때는 오버헤드를 상각할
  수 있는 분리 생산이 유리해지는 실제 의사결정 문제를 반영.
- **콤보 파라미터 구조 변경**: `combo_capex`/`combo_step`/`combo_gross_die`
  를 QLC·TLC 레시피가 공유하는 필드로 통합 (하나의 물리적 라인·다이이므로).
  `density`/`yield`/`max_capa`만 레시피별로 유지. 필수 키 수가 24개 →
  21개로 감소.
- **`visualization.html` 에 계수 입력 패널 추가**: JS가 `calc.py` 의 수식을
  그대로 미러링해, 계수를 바꿀 때마다 서버 재실행 없이 슬라이더·차트·표를
  즉시 재계산. "calc.py 실행 시 값으로 초기화" 버튼으로 원복 가능.
- `samples/sample-1.txt`, `samples/sample-2.txt` 를 새 스키마로 재작성.
  sample-1 은 QLC 55%/TLC 45% 부근 중간 크로스오버, sample-2 는 낮은
  `dedicated_overhead` 로 분리 생산이 대부분 구간에서 우위인 케이스로 대비.
- 기존 `runs/` 아카이브는 이전 스키마(구 필드명) 그대로 보존 — 재작성하지
  않음.

## 2026-07-02 (초기 빌드)

- 최초 빌드: QLC/TLC 분리 생산 vs 콤보 라인(0~100% 비율 슬라이더) bit
  생산량/원가 비교 계산기. `sweep.csv`/`sweep.json`/`visualization.html`
  (인터랙티브 슬라이더 차트)/`report.md` 출력.
