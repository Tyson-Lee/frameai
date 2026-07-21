# qlc-tlc-bit-cost-calculator

시장에 QLC/TLC 수요가 섞여 있을 때, **"QLC 다이를 그대로 써서 TLC mode로도
돌리는 콤보 라인 하나를 만드는 것"** 과 **"QLC 전용 + TLC 전용 제품을 각각
새로 만드는 것"** 중 어느 쪽이 **bit 생산량 / total cost / bit당 cost**
측면에서 더 유리한지 비교해 주는 계산기 스킬입니다.

두 시나리오는 **동일한 QLC:TLC 비율 `r`(0~100%)을 함께 스윕**하지만, 각
라인은 **자기 자신의 100% 가동 기준 max capa를 독립적으로** 갖습니다 —
분리 생산의 QLC 전용 라인/TLC 전용 라인, 콤보의 QLC 레시피/TLC 레시피 모두
서로 다른 투자·라인이므로 하나의 공유 풀로 나눠 쓰지 않습니다. 비율 `r`
에서 각 라인은 자기 max capa의 `r%`(또는 `(100-r)%`)만큼만 가동합니다 —
분리 생산도 콤보처럼 비율에 따라 결과가 달라지는 진짜 스윕이며, 더 이상
비율과 무관한 고정 기준선이 아닙니다. 핵심 트레이드오프: TLC 수요 비중이
높을 때는 진짜 TLC 레시피를 쓰는 분리 생산이 대개 bit당 더 효율적이고,
TLC 수요 비중이 낮을 때는 투자를 하나로 합친 콤보의 낮은 wafer당 투자비가
대개 유리해지는 지점(crossover)이 있습니다. 이 계산기는 그 crossover 지점을
찾아 줍니다 (이 crossover는 아래 "수율 램프업" 항목에서 설명하는 **성숙
수율(mature yield) 기준**의 월간 스냅샷으로 판정합니다).

`key=value` 형식의 파라미터 텍스트 파일을 입력받아, 콤보/분리 두 시나리오
모두를 QLC 비율 0~100% 로 스윕한 결과표와, 그 결과를 슬라이더로 직접
조작하며 볼 수 있는 인터랙티브 HTML 차트를 만들어 줍니다. 투자비/density/
gross die/수율/wafer capa를 그대로 곱해서 bit 생산량과 cost를 직접
계산합니다 — 튜닝 계수는 1회성 개발비에 들어가는 인력·Mask 환산 계수
2개(`coef_cost_per_headcount`, `coef_cost_per_mask`)뿐입니다.

**실제 fab 파라미터는 파일로 저장하지 않아도 됩니다.** `visualization.html`
은 30개 fab 파라미터를 전부 화면 안 입력창으로 갖고 있는 완전한
클라이언트사이드 계산기입니다. 값을 타이핑하는 즉시 브라우저 안에서만
재계산됩니다 (서버 전송·파일 기록 없음) — 외부로 반출할 수 없는 실제 fab
수치를 다룰 때 이 방식을 쓰면 됩니다.

**단위 표기**: 계산 구조 자체는 그대로 두고, 아래 필드만 입력 단위가
정해져 있습니다 (자세한 내용은 아래 "입력" 표 참고).
- `*_mature_yield`: % 로 입력 (예: `82` = 완전히 램프업된 이후의 82%),
  내부적으로 100으로 나눠 사용 — 특정 시점의 수율이 아니라 **성숙(mature)
  수율**입니다. 아래 "수율 램프업" 참고.
- `*_yield_ramp_coef`: 수율이 성숙 수율까지 도달하는 속도 계수 (1/개월,
  클수록 빨리 도달)
- `*_capex_per_wafer`: **1만(10,000) wafer 당 비용**으로 입력, 내부적으로
  10000으로 나눠 wafer당 단가로 환산 — `cost_mode=direct` 일 때는 무시됨
- `*_density`: `Gb/Wafer` 라벨 — 계산식 자체는 그대로, bit 생산량 결과를
  GB로 보여줄 때만(그래프, report.md) 8로 나눠 GB로 환산 (1 GB = 8 Gb)
- `*_max_capa`: `wafer/월` 라벨 — 계산 방식은 그대로

**수율 램프업 (Normalized Exponential Saturation)**: QLC 전용 라인/TLC
전용 라인/콤보 QLC 레시피/콤보 TLC 레시피, 이 4개는 각각 하나의 `*_yield`
대신 **성숙 수율(`*_mature_yield`)과 램프업 속도 계수(`*_yield_ramp_coef`)
한 쌍**을 입력받습니다:

```
yield_fraction(t) = mature_yield_fraction × (1 - exp(-ramp_coef × t))
```

`t`는 **그 라인/레시피 자신의 생산 시작 시점을 t=0으로 한** 경과 개월수 —
콤보 QLC 레시피, 콤보 TLC 레시피, 분리 QLC 라인, 분리 TLC 라인 각각 자기
자신의 t=0부터 독립적으로 램프업한다고 가정합니다. **기존 "월간(monthly)"
스냅샷 표/그래프와 crossover 판정은 이 변경의 영향을 받지 않습니다** —
여전히 완전히 램프업된 상태(`mature_yield_fraction`을 그대로 사용, 기존
`*_yield`와 동일한 방식)를 가정합니다. **5년 누적 Bit 생산량** 그래프만
실제로 이 램프업 곡선을 개월 단위로 반영합니다 (아래 "여섯 개 그래프"
참고). `*_mature_yield`/`*_yield_ramp_coef` 값을 눈으로 튜닝할 수 있도록
**QLC 수율 램프업**/**TLC 수율 램프업**, 이 두 개의 고정 참고용 그래프도
새로 추가되었습니다 (역시 아래 "여섯 개 그래프" 참고).

**ER(엔지니어링 런) 기간과 t95, 판매용/총량 bit 분리**: QLC 전용/TLC 전용/
콤보 QLC 레시피/콤보 TLC 레시피, 이 4개는 각각 **자기 자신의**
`*_yield_ramp_coef` 만으로 결정되는 시점 `t95 = ln(20) / yield_ramp_coef`
에 자기 성숙수율의 95%에 도달합니다(`*_mature_yield` 값과는 무관 —
95%라는 정의 자체가 성숙수율을 약분시켜 버리기 때문). `t=0..t95`(그
라인/레시피 자신의 생산 시작을 0으로 한 경과 개월)가 그 라인/레시피의
**ER(엔지니어링 런)/품질인증 기간**입니다. `er_wafer_combo` /
`er_wafer_dedicated`는 이제 1회성 총량이 아니라 **월간 ER wafer 소모
RATE**(wafer/월)이고, wafer_total(비율에 따라 스윕되는 그 라인/레시피의
정상 wafer 물량, 변경 없음) 위에 추가로 더 생산되는 게 아니라 그 안에서
**깎여 나가는** 방식입니다: ER 기간 동안 매달
`min(er_wafer_rate, wafer_total)` 만큼이 ER로 쓰이고 나머지가 판매용,
ER 기간이 지나면 100%가 판매용입니다. `er_wafer_combo`는 콤보 QLC
레시피·TLC 레시피 양쪽에 **50:50으로 나누지 않고 각각 그대로(풀레이트)**
독립적으로 적용되고, `er_wafer_dedicated`도 분리 QLC 라인·TLC 라인
양쪽에 동일하게 적용됩니다(`calc.ER_WAFER_RATE_ASSUMPTION`) —
`combo_headcount`/`dedicated_headcount`가 시나리오당 단일 값을 그대로
쓰는 것과 같은 취급입니다. **총 bit 생산량 공식은 전혀 바뀌지 않습니다**
(wafer_total × 그 달 수율 — ER wafer도 이미 포함된 셈). 새로 추가된 건
**판매용 bit 생산량**(= wafer_total에서 ER로 깎인 만큼을 뺀 판매용
wafer × 그 달 수율)이며, 1년/5년 누적 계산에만 반영됩니다(아래 "1년·5년
누적" 참고) — 기존 월간(monthly) 스냅샷/crossover는 이 분리와 무관하게
그대로입니다.

**원가 계산 모드 (`cost_mode`)**: bit 생산량은 이 설정과 무관하게 항상
물리 모델(density/gross_die/수율 램프업/max_capa/ER 분리)로 계산됩니다 —
이 토글은 **원가 계산에만** 영향을 줍니다.
- `model` (기본값): 기존과 동일한 투자비 + 개발비(인력+Mask만) 모델.
- `direct`: 투자비/개발비 모델 전체를 무시하고, `combo_direct_cost_per_gb`
  / `dedicated_direct_cost_per_gb` — **cent/GB 단위로 직접 입력**하는 두
  값을 비율과 무관한 고정값으로 Cost/GB 그래프(월간·누적 모두)에
  사용합니다. `visualization.html`에는 "원가 계산 모드" 라디오 버튼이 있고,
  "GB당 원가 직접 입력"을 고르면 투자비/개발비 관련 입력 필드들이 전부
  비활성화(회색 처리)되고 필수값 검증에서도 제외됩니다 — 입력해도 계산에
  반영되지 않습니다. **`er_wafer_combo`/`er_wafer_dedicated`는 이 목록에서
  제외**되어 있어 두 모드 모두에서 계속 활성화·필수 입력 상태입니다 — bit
  생산량(판매용/총량 분리 포함)에 영향을 주는 값이라 원가 계산 모드와
  무관하게 항상 필요하기 때문입니다. 이 모드에서는 표의 Total cost/Cost
  per bit 칸과 1회성 개발비/전체 투자비용 텍스트가 "—"(해당 없음)로
  표시됩니다.

## 한 줄 사용법

### A. 브라우저에서 직접 입력 (완전히 빈 화면, 반출 불가 fab 수치용)

```bash
python3 skills/qlc-tlc-bit-cost-calculator/helpers/render_html.py --blank visualization.html
```

`visualization.html` 을 열면 30개 fab 파라미터 입력창이 전부 빈 채로 뜹니다.
값을 타이핑하면 그 자리에서 슬라이더·차트·crossover가 갱신됩니다 — 값은
브라우저 밖으로 전송되지 않습니다. 이미 샘플로 채워진 화면에서도 **"전체
비우기"** 버튼으로 언제든 같은 빈 상태로 전환할 수 있습니다.

### B. CLI 배치 (`frame run`)

```bash
./frame run qlc-tlc-bit-cost-calculator \
  --in automations/qlc-tlc-bit-cost-calculator/samples/sample-1.txt \
  "QLC TLC 비교 계산해줘"
```

`--in` 없이 호출하면 A 방식의 빈 화면 대신, 내장된
`samples/sample-1.txt` 값으로 미리 채워진(샘플 배너 표시) 계산기를
생성합니다. 완전히 빈 화면이 필요하면 자유 텍스트에 "blank" 등을 포함해
요청하세요.

### C. Claude Code 채팅에서

```
/qlc-tlc-bit-cost-calculator
```

라고 적고 파라미터 파일을 채팅에 드래그하거나, `key=value` 값을 채팅에
직접 붙여넣으면 됩니다. 아무것도 주지 않으면 샘플로 미리 채워진 계산기를
생성합니다("blank로 줘"라고 하면 완전히 빈 화면). 스킬이
`automations/qlc-tlc-bit-cost-calculator/runs/<UTC-ts>/` 아래에 archive
폴더를 만들고 같은 출력을 생성합니다.

## 입력

| 종류 | 필수 | 비고 |
|---|---|---|
| `key=value` 파라미터 텍스트 (`.txt`) | ⛔ | 선택 — 있으면 화면을 미리 채움. 없으면 샘플로 미리 채운 계산기 생성(배너 표시), 필수 30개 키는 브라우저에서 직접 입력·수정 가능 |
| 자유 텍스트 인자 | ⛔ | 강조하고 싶은 맥락, 또는 "blank"로 완전히 빈 화면 요청 |

| 파라미터 접두사 | 의미 | 포함 필드 |
|---|---|---|
| `qlc_*` | QLC 전용 라인 (분리 생산, 독립 다이) | `capex_per_wafer` (1만 wafer당 비용, direct 모드에서 무시), `density` (Gb/Wafer), `gross_die`, `mature_yield` (%, 성숙 수율), `yield_ramp_coef` (1/개월), `max_capa` (QLC 전용 라인 100% 가동시 max capa, wafer/월, 독립 값) |
| `tlc_*` | TLC 전용 라인 (분리 생산, 독립 다이) | 위와 동일 필드 (`tlc_max_capa` 는 QLC 전용 라인과 별개 투자이므로 다른 값일 수 있음) |
| `combo_capex_per_wafer` / `combo_gross_die` | 콤보 라인 공통 (하나의 물리적 라인·다이이므로 두 레시피가 공유) | `capex_per_wafer` 도 1만 wafer당 비용, direct 모드에서 무시 |
| `combo_qlc_*` | 콤보 라인이 QLC 레시피로 돌 때 | `density` (Gb/Wafer), `mature_yield` (%), `yield_ramp_coef` (1/개월), `max_capa` (콤보가 QLC 레시피로 100% 가동시 max capa, wafer/월) |
| `combo_tlc_*` | 콤보 라인이 TLC 레시피로 돌 때 (QLC 다이를 TLC mode로 강제 운용) | `density`, `mature_yield`, `yield_ramp_coef`, `max_capa` (콤보가 TLC 레시피로 100% 가동시 max capa — 같은 물리 라인이라 보통 combo_qlc_max_capa와 비슷하지만, 레시피별로 다를 수 있어 별도 입력) |
| `er_wafer_combo` | **월간** ER(엔지니어링 런/품질인증) wafer 소모 RATE (wafer/월) — 콤보 QLC·TLC 레시피 각각 자기 ER 기간(t95) 동안 독립적으로(50:50 분할 아님) 소모. bit 생산량에 영향을 주므로 **direct 모드에서도 계속 사용됨** | — |
| `er_wafer_dedicated` | **월간** ER wafer 소모 RATE (wafer/월) — 분리 QLC·TLC 라인 각각 독립적으로 소모 (보통 콤보보다 큼: 두 신제품을 각각 개발). **direct 모드에서도 계속 사용됨** | — |
| `combo_headcount` / `dedicated_headcount` | 1회성 개발에 필요한 인력 명 수 (시나리오별 독립, direct 모드에서 무시) | — |
| `combo_mask_count` / `dedicated_mask_count` | 1회성 개발에 소모되는 Mask 매수 (시나리오별 독립, direct 모드에서 무시) | — |
| `coef_cost_per_headcount` | 인력 1명당 환산 비용 — 콤보·분리 **공통** 계수 (currency_unit/명, direct 모드에서 무시) | — |
| `coef_cost_per_mask` | Mask 1매당 환산 비용 — 콤보·분리 **공통** 계수 (currency_unit/매, direct 모드에서 무시) | — |
| `currency_unit`, `bit_unit` | 표시용 단위 라벨 (선택, 기본값 있음) | — |
| `ratio_step` | 슬라이더 스윕 간격 %, 선택 (기본 5) | — |
| `exchange_rate_krw_per_usd` | 환율 (원/달러), 선택 (기본 1300) — **Cost 그래프의 cent/GB 축 환산에만 쓰임 (cost_mode=model 일 때만)**, 다른 출력엔 영향 없음 | — |
| `cost_mode` | 원가 계산 모드, 선택 (기본 `model`) — `model` 또는 `direct` | — |
| `combo_direct_cost_per_gb` / `dedicated_direct_cost_per_gb` | GB당 원가 직접 입력값 (cent/GB), 선택 (기본 0) — `cost_mode=direct` 일 때만 사용 | — |

전체 예시는 `samples/sample-1.txt`, `samples/sample-2.txt` 참고. 단위는
위 변환 규칙(성숙 수율 %, 램프업 계수, capex 1만wafer당, density Gb/Wafer,
max_capa wafer/월)을 제외하면 사용자가 일관되게만 입력하면 됩니다 — 그 외
필드는 계산기가 단위 변환을 하지 않습니다.

**왜 콤보는 `capex_per_wafer`/`gross_die` 를 공유하고 분리 생산은
별개인가**: 콤보 라인은 물리적으로 하나의 라인·하나의 다이 설계이므로
wafer당 투자비와 wafer당 다이 수는 레시피와 무관하게 동일합니다. 셀당 몇
bit를 저장하는지(density)와 그 density에서의 수율(및 그 수율에 도달하는
속도)만 레시피별로 달라집니다. 반면 분리 생산은 QLC/TLC가 애초에 서로 다른
다이 설계이므로 모든 파라미터가 완전히 독립적입니다.

**왜 max_capa 필드가 4개(`qlc_max_capa`/`tlc_max_capa`/
`combo_qlc_max_capa`/`combo_tlc_max_capa`)로 나뉘어 있고 팹 공유 값이 아닌가**:
분리 생산의 QLC 전용 라인·TLC 전용 라인, 콤보의 QLC 레시피·TLC 레시피 모두
서로 다른 투자·라인이므로, 100% 가동시 max capa가 서로 다를 수 있습니다 —
하나의 공유 풀을 나눠 쓰는 게 아닙니다. 시장이 원하는 QLC:TLC 비율 `r`
에서, 분리 생산의 QLC 전용 라인은 **자기 자신의** `qlc_max_capa` 의 `r%`
만큼만 가동하고, TLC 전용 라인은 **자기 자신의** `tlc_max_capa` 의
`(100-r)%` 만큼만 가동합니다. 콤보는 물리적으로 하나의 라인이라 항상 100%
가동(레시피 간 시간분할, 노는 시간 없음)이지만, QLC 레시피로 돌 때와 TLC
레시피로 돌 때의 max capa(`combo_qlc_max_capa` / `combo_tlc_max_capa`)는
레시피별로 살짝 다를 수 있어 별도로 입력받습니다.

## 계산 모델 (요약)

```
bit_per_wafer (월간 스냅샷) = density_per_die × grossdie_per_wafer × (mature_yield% / 100)
cost(line)                  = (capex_per_wafer_입력값 / 10000) × wafer_count   [cost_mode=model]
```

`mature_yield` 는 %로 입력(예: 82=82%, 완전히 램프업된 이후)하고 내부적으로
100으로 나눠 사용합니다. `capex_per_wafer` 는 **1만 wafer당 비용**으로
입력하고, 실제 계산에서는 `입력값 / 10000` 을 wafer당 단가로 씁니다
(콤보/QLC/TLC 모두 동일 규칙, `cost_mode=direct` 일 때는 무시).

- 비율 `r` (QLC %) 에서 각 라인은 **자기 자신의** max capa를 기준으로
  `r%`(또는 `(100-r)%`) 만큼만 가동합니다 — 하나의 공유 풀을 나눠 쓰지
  않습니다:
  - 분리 생산: `wafer_qlc_dedicated = qlc_max_capa × r/100`,
    `wafer_tlc_dedicated = tlc_max_capa × (100-r)/100`
  - 콤보: `wafer_qlc_combo = combo_qlc_max_capa × r/100`,
    `wafer_tlc_combo = combo_tlc_max_capa × (100-r)/100`
- **콤보**: `bit_total = wafer_qlc_combo × combo_qlc.bpw + wafer_tlc_combo ×
  combo_tlc.bpw`, `cost_total = (combo_capex_per_wafer/10000) ×
  (wafer_qlc_combo + wafer_tlc_combo) + dev_cost(combo)`. `combo_qlc_max_capa`
  와 `combo_tlc_max_capa` 가 다르면 cost_total도 비율에 따라 달라집니다.
- **분리 생산**: `bit_total = wafer_qlc_dedicated × qlc.bpw +
  wafer_tlc_dedicated × tlc.bpw`, `cost_total = (qlc_capex_per_wafer/10000) ×
  wafer_qlc_dedicated + (tlc_capex_per_wafer/10000) × wafer_tlc_dedicated +
  dev_cost(dedicated)`.
- **1회성 개발비 (`cost_mode=model` 일 때만, 인력 + Mask 환산만)**:
  ```
  dev_cost(combo)     = combo_headcount × coef_cost_per_headcount
                       + combo_mask_count × coef_cost_per_mask
  dev_cost(dedicated) = dedicated_headcount × coef_cost_per_headcount
                       + dedicated_mask_count × coef_cost_per_mask
  ```
  **ER wafer는 더 이상 별도의 1회성 비용 항목이 아닙니다** —
  `wafer_total × capex_rate_per_wafer` (변경 없음)가 이미 ER이든 판매용이든
  처리한 모든 wafer 비용을 지불하므로, 별도의 "ER wafer 수 × capex" 항목은
  중복 계상이었습니다. ER wafer는 이제 원가가 아니라 **bit 생산량**(판매용/
  총량 분리)에 반영됩니다 — 아래 "ER 기간과 t95" 참고.
- 두 시나리오 모두 `cost_per_bit = cost_total / bit_total` 을 핵심 비교
  지표로 사용합니다 (낮을수록 유리, 월간 스냅샷은 성숙 수율 기준). `crossover`
  는 QLC 비율 0%부터 스캔했을 때 콤보의 cost_per_bit 가 분리 생산의
  cost_per_bit 이하로 처음 내려가는 지점입니다.
- **GB 환산 (표시 전용)**: `density` 필드는 `Gb/Wafer` 라벨이므로
  `bit_per_wafer` 계산 결과(원시값)는 Gb 기준입니다. 그래프와 report.md의
  GB 관련 수치는 이 원시값을 8로 나눠(1 GB = 8 Gb) 만듭니다.
- **Cost 그래프 y축은 cent/GB 고정**: `cost_mode=model` 일 때는 기존처럼
  `exchange_rate_krw_per_usd` 로 환산(`calc.cost_per_gb_eokwon_to_cent`);
  `cost_mode=direct` 일 때는 `combo_direct_cost_per_gb`/
  `dedicated_direct_cost_per_gb` 값을 환산 없이 그대로 사용합니다(이미
  cent/GB 단위로 입력받으므로).

## 수율 램프업 (Normalized Exponential Saturation)

QLC 전용 라인 / TLC 전용 라인 / 콤보 QLC 레시피 / 콤보 TLC 레시피, 이
4개의 라인·레시피는 각각 아래 공식으로 수율이 시간에 따라 램프업한다고
가정합니다:

```
yield_fraction(t) = mature_yield_fraction × (1 - exp(-ramp_coef × t))
```

- `mature_yield_fraction` = `*_mature_yield` / 100 (완전히 램프업된 이후의
  최종 수율)
- `ramp_coef` = `*_yield_ramp_coef` (1/개월, 클수록 빨리 성숙 수율에 도달)
- `t` = **그 라인/레시피 자신의** 생산 시작 시점을 0으로 하는 경과 개월수
  — 콤보 QLC 레시피, 콤보 TLC 레시피, 분리 QLC 라인, 분리 TLC 라인이 각자
  독립적으로 자기 t=0(= 생산 1개월차)부터 램프업합니다.

**월간(monthly) 스냅샷 표/그래프와 crossover 판정은 이 램프업의 영향을
받지 않습니다** — 계속 `mature_yield_fraction`을 그대로 사용해 "완전히
램프업된 라인"을 가정합니다 (기존 `*_yield` 필드와 동일한 취급). **오직
1년/5년 누적 Bit 생산량 그래프·수치만** 이 공식을 실제로 개월 단위
반복문으로 적용합니다 — 아래 "여섯 개 그래프" 및 "1년·5년 누적" 참고.

## ER 기간(t95)과 판매용/총량 bit 분리

QLC 전용/TLC 전용/콤보 QLC 레시피/콤보 TLC 레시피, 이 4개는 각각 **자기
자신의** `*_yield_ramp_coef` 값만으로 결정되는 시점에 자기 성숙수율의
95%에 도달합니다:

```
t95 = ln(20) / yield_ramp_coef
```

(`*_mature_yield` 값과는 무관 — 95%라는 정의 자체에서 성숙수율이
약분되어 사라지기 때문. `calc.yield_ramp_t95()`, `render_html.py`의
`yieldRampT95()`로 미러링). `t=0..t95`(그 라인/레시피 자신의 생산
시작월을 0으로 한 경과 개월)가 그 라인/레시피의 **ER(엔지니어링
런)/품질인증 기간**입니다.

`er_wafer_combo` / `er_wafer_dedicated`는 **1회성 총량이 아니라 월간 ER
wafer 소모 RATE**(wafer/월)입니다. `wafer_total`(비율에 따라 스윕되는 그
라인/레시피의 정상 wafer 물량, `qlc_max_capa × r/100` 등 — 변경 없음)은
ER wafer 때문에 늘어나지 않습니다 — ER wafer는 그 위에 **추가로** 생산되는
게 아니라 그 **안에서 깎여 나가는** 것뿐입니다. ER 기간 안의 매달, 그 달
wafer_total 중 `min(er_wafer_rate, wafer_total)` 만큼이 ER로 쓰이고
나머지가 판매용입니다. ER 기간이 지나면 100%가 판매용입니다:

```
판매용_wafer(t) = wafer_total - (ER 기간(t <= t95)이면 min(er_wafer_rate, wafer_total), 아니면 0)
```

`er_wafer_combo`는 콤보 QLC 레시피·TLC 레시피 **양쪽에 50:50으로 나누지
않고 각각 그대로(풀레이트)** 독립적으로 적용되고, `er_wafer_dedicated`도
분리 QLC 라인·TLC 라인 양쪽에 동일하게 적용됩니다
(`calc.ER_WAFER_RATE_ASSUMPTION`) — `combo_headcount`/
`dedicated_headcount`가 시나리오당 단일 값을 두 라인/레시피 모두에 그대로
쓰는 것과 같은 취급입니다.

**총 bit 생산량 공식은 전혀 바뀌지 않습니다** — `wafer_total × density ×
grossdie × yield_fraction(t)`(ER wafer도 이미 포함된 셈이라 수식 자체는
그대로). 새로 추가된 건 **판매용 bit 생산량**입니다:

```
판매용_bit(t) = 판매용_wafer(t) × density × grossdie × yield_fraction(t)
```

두 값 모두 1년/5년 누적 창에서 매달 합산됩니다(아래 참고) —
월간(monthly) 스냅샷/crossover는 이 분리와 무관하게 그대로입니다.

## 여섯 개 그래프 (`visualization.html`)

기존 2개 그래프(월간 Bit 생산량 vs QLC비율, 월간 Cost/GB vs QLC비율)에 더해,
아래 4개 그래프가 있습니다. **이 2개 그래프만** 아래 "기준 시점 토글"의
영향을 받습니다 — 나머지 4개는 이 토글과 무관하게 항상 성숙 수율 기준입니다.

**기준 시점 토글 (`visualization.html` 좌측 패널, 슬라이더 바로 아래)**: 첫
두 그래프("Bit 생산량 vs QLC 비율", "Cost/GB vs QLC 비율")와 그 위 표에 나오는
콤보/분리 생산의 **Bit 생산량**·**Cost / bit** 수치는 기본적으로 지금까지처럼
**성숙 수율(mature yield) 기준**으로 계산되지만, 라디오 버튼으로 **"특정 개월
기준"**을 고르면 QLC:TLC 비율 슬라이더와 똑같이 조작 가능한 **1~60개월 슬라이더**가
활성화됩니다. 이 슬라이더로 개월 수 `t`를 고르면, 4개 라인/레시피(`qlc`/`tlc`/
`combo_qlc`/`combo_tlc`) 각각 **자기 자신의** 수율 램프업 공식
(`yield_fraction(t) = mature_yield × (1 - exp(-ramp_coef × t))`)으로 계산한
그 시점의 실제 수율을 사용해 Bit 생산량/Cost per bit를 다시 계산합니다 —
Total cost는 수율과 무관하므로(처리한 wafer 수에만 비례) 이 토글로 바뀌지
않고, Bit 생산량과 그로부터 파생되는 Cost/bit·Cost/GB만 바뀝니다. 화면에는
고른 개월 수와, 그 시점에 각 라인/레시피가 자기 성숙 수율 대비 몇 %까지
도달했는지(참고용 텍스트, `mature_yield` 값과 무관하게 `ramp_coef`만으로 결정)도
함께 표시됩니다.

**이 토글이 절대 건드리지 않는 것**: 5년/1년 누적 Bit 생산량(아래 3, 4번
그래프 + 표의 1년·5년 행), 수율 램프업 참고 그래프 2개(아래 5, 6번), 판정
문구("현재 비율에서는 ~가 유리합니다")와 `sweep.json`/`report.md`의 crossover
서술은 전부 이 토글과 무관하게 항상 성숙 수율 기준으로 고정됩니다 — 순수하게
`visualization.html`의 화면 표시 레이어일 뿐이라 params 파일이나 `sweep.json`
자체에는 반영되지 않습니다 (파일을 새로고침해도 처음 값은 "성숙 수율
기준"으로 돌아옵니다).

**3) 5년 누적 Bit 생산량 vs QLC 비율 (억GB)** — 콤보/분리 각 시나리오가
5년(60개월) 동안 그 비율로 계속 생산했을 때의 누적 **총** bit 생산량.
**더 이상 개발/품질인증 기간을 건너뛰지 않고 1개월차부터 바로** 60개월
전부, 콤보의 QLC/TLC 레시피·분리의 QLC/TLC 라인 각각 자기 자신의 생산
시작월(t=0)부터 독립적으로 램프업하는 실제 수율 곡선을 매달 적용해 그
달의 bit 생산량을 계산하고 전부 합산합니다:

```
5년 누적 총 bit(라인) = wafer_count(라인) × Σ[t=1..60] density × grossdie × yield_fraction(t)
```

(`calc.cumulative_ramp_bit_per_wafer`, `render_html.py`의
`cumulativeRampBitPerWafer()`로 미러링). 콤보 총 bit은 QLC 레시피 기여분 +
TLC 레시피 기여분, 분리 총 bit도 QLC 라인 기여분 + TLC 라인 기여분입니다.
같은 방식으로 **1년(12개월) 누적**도 나란히 계산됩니다(차트로 그려지진
않지만 결과 표와 "동적 인트로 수치"에 표시 — 아래 참고). 두 누적 창 모두
`*_sale_bit_total` 필드로 **판매용** bit 생산량도 함께 제공됩니다(총량에서
ER로 깎인 만큼을 뺀 값, 위 "ER 기간과 t95" 참고).

**4) 5년 누적 Cost/GB vs QLC 비율 (cent/GB)** — cost는 수율과 무관합니다
(양품 bit이 아니라 처리한 wafer 수만큼 비용이 발생하므로) — 그래서 이
그래프의 공식은 (개발 기간 건너뛰기가 없어진 것 외에는) 기존과
**동일합니다**: "월간 wafer 원가(1회성 개발비 제외) × 60"에 해당
시나리오의 1회성 개발비를 **한 번만** 더합니다 (`cost_mode=model` 일
때). `cost_mode=direct` 일 때는 `combo_direct_cost_per_gb`/
`dedicated_direct_cost_per_gb` 를 비율·시점과 무관한 고정값으로 그대로
사용합니다.

```
5년 누적 cost = 월간 wafer 원가(dev cost 제외) × 60 + dev_cost   [model 모드]
1년 누적 cost = 월간 wafer 원가(dev cost 제외) × 12 + dev_cost   [model 모드]
N년 누적 cost/bit = N년 누적 cost / N년 누적 총 bit
```

**동적 인트로 수치**: 페이지 상단 소개 문단(`#introStats`)에 현재
슬라이더 비율 기준 네 수치 — 콤보 생산 1년/5년간 총 bit 생산량, 분리
생산 1년/5년간 총 bit 생산량(모두 억GB) — 가 실시간으로 표시되고,
슬라이더를 움직이면 즉시 갱신됩니다.

**5) QLC 수율 램프업 (%, x축 = 생산 시작 후 경과 개월 0~36)** — 분리
생산의 QLC 전용 라인(`qlc_mature_yield`/`qlc_yield_ramp_coef`)과 콤보의
QLC 레시피(`combo_qlc_mature_yield`/`combo_qlc_yield_ramp_coef`) 두 곡선을
비교합니다. **QLC:TLC 비율 슬라이더와 무관하게 항상 고정으로 표시되는
참고용 그래프**입니다(비율 스윕 대상이 아니므로 현재 비율을 나타내는 점선도
그려지지 않음) — 수율 램프업 파라미터를 눈으로 확인하며 튜닝하기 위한
용도입니다.

**6) TLC 수율 램프업 (%, x축 = 생산 시작 후 경과 개월 0~36)** — 분리
생산의 TLC 전용 라인과 콤보의 TLC 레시피를 같은 방식으로 비교합니다.

## 전체 투자비용 (Max capa 풀 빌드아웃 기준) — 텍스트로만 표시

실제 가동 비율 `r`과 무관하게, 각 시나리오가 자기 라인들을 **Max capa까지
전부 지어서 투자**한다고 가정했을 때의 총 투자비용입니다. 비율과 무관한
고정값 두 개뿐이므로 그래프가 아니라 **왼쪽 정보 패널에 텍스트 한 줄로만
표시**합니다 (예: `전체 투자비용 (Max capa 풀 빌드아웃 기준): 콤보 XX /
분리 YY`). 계산 로직 자체는 이전과 동일합니다:

```
전체 투자비용(분리 생산) = qlc_capex_rate × qlc_max_capa
                        + tlc_capex_rate × tlc_max_capa
                        + dedicated_dev_cost
전체 투자비용(콤보)     = combo_capex_rate × combo_qlc_max_capa + combo_dev_cost
```

분리 생산은 QLC 전용/TLC 전용이 완전히 별개 라인이므로 두 라인의 빌드아웃
비용을 그대로 더하면 됩니다. **콤보는 물리적으로 하나의 라인**이라 빌드아웃
크기가 하나뿐이어야 하는데, `combo_qlc_max_capa`와 `combo_tlc_max_capa` 두
값을 갖고 있습니다 — 이 계산기는 **`combo_qlc_max_capa`를 대표 capa로
사용**합니다(근거: `calc.COMBO_FULL_CAPEX_ASSUMPTION`, 콤보 라인은 QLC 다이
설계를 기준으로 지어진 하나의 물리적 라인이기 때문). 이는 계산기가 임의로
정한 모델링 가정이지, 파라미터로 주어진 숫자가 아닙니다 — 실제 fab
상황에 더 잘 맞는 기준이 있다면 `helpers/calc.py`의 `full_buildout()`(및
`render_html.py`의 JS 미러 `fullBuildout()`)을 직접 수정해야 합니다.

**이 텍스트는 `cost_mode=model` 일 때만 표시됩니다** — `cost_mode=direct`
에서는 투자비 모델 자체를 쓰지 않으므로 "해당 없음"으로 표시됩니다.

## 출력 (`runs/<UTC-ts>/outputs/` 아래)

| 파일 | 내용 |
|---|---|
| `sweep.csv` / `sweep.json` | 콤보·분리 생산 두 시나리오를 QLC 비율 0~100% 로 함께 스윕한 표 (wafer/bit/cost/cost-per-bit, 1년·5년 누적 총량/판매용 bit 포함, 시나리오별) + `full_buildout`/`yield_ramp_curves`/`t95_months`/`er_wafer_rate_assumption`/`cost_mode`/`direct_cost_per_gb` |
| `visualization.html` | 슬라이더로 QLC:TLC 비율을 조절하며 두 시나리오를 나란히 보는 인터랙티브 차트 6개(월간 Bit 생산량, 월간 Cost/GB, 5년 누적 Bit 생산량, 5년 누적 Cost/GB, QLC 수율 램프업, TLC 수율 램프업) + 전체 투자비용/ER 기간 텍스트 + 1년·5년 누적 총량/판매용 bit 표 + 동적 인트로 수치 + 원가 계산 모드(model/direct) 토글 + 월간 Bit/Cost 그래프 2개 전용 "기준 시점"(성숙 수율/특정 개월) 토글. 외부 CDN 의존 없이 단독으로 열림. params 없이 생성됐다면 상단에 샘플 데이터 배너 표시 |
| `summary.json` | 리포트 작성용 헤드라인 수치 (크로스오버 비율, 시나리오별 최적 비율, 1회성 개발비, 전체 투자비용, t95, ER wafer rate 가정, 원가 계산 모드) |
| `report.md` | 콤보 vs 분리 생산 요약, 크로스오버 지점, 개발비(인력+Mask만)와 ER wafer rate 가정(model 모드) 또는 GB당 원가 직접 입력값(direct 모드), 1년·5년 누적 총량/판매용 bit, 각 라인/레시피의 t95, 수율 램프업 파라미터, 추천 문단 (입력 언어에 맞춰 한국어/영어 자동 전환) |

## 샘플로 한 번에 검증

```bash
./frame run qlc-tlc-bit-cost-calculator \
  --in automations/qlc-tlc-bit-cost-calculator/samples/sample-1.txt \
  "테스트 실행"
```

`sample-1.txt` (억원/Gb 단위) 는 QLC 비율이 약 60% 를 넘으면(=TLC 수요가
약 40% 미만이면) 콤보가 분리 생산보다 유리해지기 시작하는, 중간 지점
크로스오버가 있는 케이스입니다(월간 스냅샷, 성숙 수율 기준) — 콤보 라인에
QLC 다이를 억지로 TLC 모드로 돌리면(`combo_tlc_density=20`,
`combo_tlc_mature_yield=78`) 진짜 TLC 전용 설계(`tlc_density=32`,
`tlc_mature_yield=88`) 대비 bit 효율이 크게 떨어지므로, QLC 수요가 확실히
우세해질 때까지는 분리 생산이 계속 유리합니다.
`sample-2.txt` ($M/TB 단위, 소규모 엔터프라이즈 SSD 스케일)는 콤보의
투자비 이점이 크지 않아 QLC 비율이 약 75% 를 넘어야만(=TLC 수요가 적을
때만) 콤보가 이기는, 분리 생산이 대부분의 구간에서 유리한 케이스입니다.
두 샘플 모두 `cost_mode=model`, 각 라인/레시피에 합리적인
`*_yield_ramp_coef` 기본값(콤보 QLC가 가장 빠르게 램프업, 콤보 TLC가 가장
느리게 램프업)이 채워져 있습니다.
`qlc_max_capa`/`tlc_max_capa`/`combo_qlc_max_capa`/`combo_tlc_max_capa` 나
`*_headcount`/`*_mask_count` 를 조정하면 크로스오버 지점이 어떻게
이동하는지 `visualization.html` 의 입력창에서 바로 확인할 수 있습니다
(`er_wafer_*`는 더 이상 크로스오버나 개발비에 영향을 주지 않습니다 — 이제
1년·5년 누적 판매용/총량 bit 분리에만 영향을 줍니다). 둘 다 순수 합성
데이터입니다. (참고: `capex_per_wafer` 는 1만 wafer당 비용, `mature_yield`
는 % 단위로 입력합니다 — 두 샘플 모두 이 단위 스케일 기준입니다.)

## Limits (정직)

- **`visualization.html` 값은 브라우저 밖으로 나가지 않음**: 화면에 직접
  입력한 fab 파라미터는 어떤 params 파일이나 archive에도 자동 저장되지
  않습니다 — 탭을 닫으면 사라집니다.
- **params 없을 때의 기본값은 샘플이지 실제 결과가 아님**: 화면 상단
  배너와 report.md 첫 줄에 명시하긴 하지만, 배너를 놓치면 실제 fab 결과로
  오인할 수 있습니다.
- **투자비/wafer 모델만 비교 (model 모드)**: `cost(line) =
  (capex_per_wafer_입력값/10000) × wafer_count` (+ 1회성 개발비, 인력+Mask만).
  웨이퍼당 운영비(재료비/인건비/유틸리티)는 모델링하지 않습니다.
- **direct 모드는 비율과 무관한 고정 입력값일 뿐, 재계산이 아님**:
  `combo_direct_cost_per_gb`/`dedicated_direct_cost_per_gb` 는 모든
  QLC:TLC 비율에서 동일하게 적용됩니다 — 실제로 비율에 따라 GB당 원가가
  달라지는 상황(예: 규모의 경제)은 이 모드로 표현할 수 없습니다. 그런
  경우 model 모드로 투자비/개발비 파라미터를 조정해야 합니다.
- **수율 램프업은 하나의 함수 형태(Normalized Exponential Saturation)로
  4개 라인/레시피 전부에 동일하게 적용**: 실제 램프업 곡선이 S자형이거나
  중간에 정체 구간이 있는 등 이 공식과 다른 형태라면 표현할 수 없습니다 —
  그 경우 `calc.py`의 `yield_ramp_fraction()`(및 `render_html.py`의 JS
  미러)을 직접 수정해야 합니다.
- **1년/5년 누적 계산은 두 창 모두 1개월차부터 바로 생산이 시작되고, 그
  기간 내내 그 비율의 wafer 물량이 일정하다고 가정**합니다(수율만
  램프업하고 wafer 투입량은 램프업하지 않음) — 실제로는 wafer 투입량
  자체도 서서히 늘어나는 경우가 있는데 이는 반영하지 않습니다.
- **ER wafer 소모 RATE는 시나리오당 단일 값을 두 라인/레시피 모두에
  분할 없이 그대로 적용 (가정)**: `er_wafer_combo`/`er_wafer_dedicated`
  는 각각 콤보 QLC·TLC 레시피, 분리 QLC·TLC 라인 양쪽에 50:50으로 나누지
  않고 풀레이트로 독립 적용됩니다(`calc.ER_WAFER_RATE_ASSUMPTION`) —
  실제로 두 라인/레시피가 하나의 제한된 ER 예산을 나눠 쓰는 경우라면 이
  모델로는 표현할 수 없습니다.
- **ER wafer는 더 이상 별도의 1회성 비용 항목이 아님**: 기존 "ER wafer 수
  × capex_per_wafer" 항목은 완전히 제거되었습니다 —
  `wafer_total × capex_rate_per_wafer`(변경 없음)가 이미 ER이든 판매용이든
  모든 wafer 처리 비용을 지불하기 때문입니다. 실제로 ER wafer 처리가 일반
  생산 wafer보다 wafer당 비용이 더 든다면(추가 특성평가 공정 등) 이 모델로는
  표현할 수 없습니다.
- **인력/Mask 환산 계수는 콤보·분리 공통, 고정값 (model 모드)**:
  `coef_cost_per_headcount`/`coef_cost_per_mask` 는 시나리오에 상관없이
  동일한 비율을 씁니다.
- **GB 환산은 표시 레이어일 뿐, 재계산이 아님**: `*_bit_total_gb`/
  `*_cost_per_gb` 는 원시 Gb 계산 결과를 8로 나눈 값입니다.
- **개발비는 물량에 비례하지 않는 고정값 (model 모드)**: `dev_cost.combo` /
  `dev_cost.dedicated` 는 비율과 무관하게 매 스윕 지점의 총원가에 한 번만
  더해집니다.
- **콤보/분리 모두 가동률 100% 가정**: 레시피 전환(QLC↔TLC) 또는 별도
  라인 신설 시 발생하는 셋업/전환 시간은 반영하지 않습니다.
- **콤보의 capex/gross_die 공유 가정**: 콤보 라인의 QLC mode와 TLC
  mode가 투자비·wafer당 다이 수까지 실제로 다르다면 이 모델로는 표현할
  수 없습니다.
- **전체 투자비용(빌드아웃) 텍스트의 콤보 대표 capa는 가정 (model
  모드에서만 표시)**: 콤보의 두 max capa 중 `combo_qlc_max_capa`를
  대표값으로 씁니다 — 실제로는 `combo_tlc_max_capa`나 둘 중 큰 값이 더
  맞는 fab도 있을 수 있습니다.
- **t95(ER 기간)는 `*_yield_ramp_coef`에만 좌우되고 `*_mature_yield`와
  무관**: 95%-of-mature 정의 자체에서 성숙수율이 약분되어 사라지기
  때문입니다 — 성숙수율이 낮다고 해서 ER 기간이 그 이유만으로 짧아지거나
  길어지지 않습니다. 단순화를 위한 선택이 아니라 정의상 그런 것입니다.
- **"기준 시점" 토글은 순수 화면 표시 레이어일 뿐, params/출력 파일에는
  저장되지 않음**: `visualization.html`에서 "특정 개월 기준"을 골라 첫 두
  그래프/표의 Bit 생산량·Cost per bit 수치를 특정 개월 시점의 수율로 다시
  본다 해도, `sweep.csv`/`sweep.json`/`report.md`나 crossover 판정에는
  전혀 반영되지 않습니다 — 그 값들은 항상 성숙 수율 기준입니다. 페이지를
  새로고침하면 이 토글은 "성숙 수율 기준"(기본값)으로 돌아갑니다.
- **공정 시뮬레이터 아님**: 팹 스케줄링/공정 통합 모델이 아닌 1차
  전략 비교용 선형 계산기입니다. 실제 투자 의사결정에는 공정/재무팀
  검토가 별도로 필요합니다.
- **로컬 파일 시스템 한정**: 출력은 작업 트리 안에만 기록, 외부 네트워크
  호출 없음.

## 디렉토리 구조

```
automations/qlc-tlc-bit-cost-calculator/
├── input.md            # 사용자가 처음 적은 자연어 (수정 금지)
├── README.md           # 이 파일
├── before_after.md     # 수동 vs 자동 시간 비교
├── CHANGELOG.md         # 스킬 refine 이력
├── samples/
│   ├── sample-1.txt    # 억원/Gb 단위, QLC 60% 부근 중간 크로스오버
│   └── sample-2.txt    # $M/TB 단위, QLC 75% 부근 → 분리 생산이 대부분 우위
└── runs/<UTC-ts>/      # frame run / 채팅 호출마다 1개씩 생성
    ├── inputs/
    └── outputs/
        ├── sweep.csv
        ├── sweep.json
        ├── summary.json
        ├── visualization.html
        └── report.md
```
