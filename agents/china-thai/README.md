# Agent: China-Thai Freight Calculator

**GO Corporation Co., Ltd.**
Route: China (Foshan / Guangzhou) → Bangkok, Thailand
Last updated: 2026-04-02

---

## What This Agent Does

Calculates the full **landed cost** of importing goods from a Chinese supplier (EXW terms) to a Bangkok delivery address. Covers both **sea LCL** and **air LCL** modes.

All rates and formulas are derived from actual GO Corporation shipment data.

---

## Files

| File | Purpose |
|---|---|
| `freight_calculator.py` | Runnable Python script — edit INPUT block, run to get landed cost |
| `freight-calculation-guide.md` | Full reference guide: rates, contacts, HS codes, formulas |

---

## Quick Start

```bash
# Edit the INPUT block in freight_calculator.py
# Set: EXW_PRICE_THB, dimensions, weight, HS code, mode
python agents/china-thai/freight_calculator.py
```

---

## Freight Route

```
Factory (Foshan/GZ)
    ↓ land truck 1-4 days
Guangzhou Consolidation Warehouse
广州市白云区太和镇和龙村云美西街2号
    ↓ sea 7-10 days  (TA-xxxx tracking)
    ↓ or land 3-5 days (TB-xxxx tracking)
Bangkok Port + Customs Clearance
    ↓ last-mile 1-3 days
Project Site / Warehouse
```

**Total EXW → Bangkok door: ~14–21 days (sea)**

---

## Key Agent: Gift Somlak (Murazame / Profreight)

Internal Slack channel: **#shipping-china-thai**
China warehouse contact: 姜琼玉 — +86 137 9881 9454

---

## Algorithm Summary

```
1. Chargeable weight
   Air:  CW = max(actual_kg, L×W×H÷6000)
   Sea:  RT = max(CBM, actual_kg÷1000)  where CBM = L×W×H÷1,000,000

2. Freight cost
   Air:  freight = CW × rate_per_kg
   Sea:  freight = CBM × rate_per_cbm

3. CIF value
   CIF = EXW + freight + insurance

4. Insurance (Chubb, via Logimark)
   insured_value = CIF × 110%
   premium = max(insured_value × 0.45%, USD 40)
   total = premium + stamp(4) + duplicate(1) + VAT(7%)

5. Import duty + VAT (Thailand)
   duty = CIF × hs_duty_rate
   VAT  = (CIF + duty) × 7%

6. Landed cost
   landed = EXW + freight + insurance + duty + VAT
          + clearance_service_fee + last_mile

7. Minimum selling price
   sell = landed ÷ (1 - margin%)   e.g. ÷0.80 for 20% GM
```

---

## Confirmed HS Codes (from GO Corp actual clearances)

| HS | Product | Duty |
|---|---|---|
| 9403 | Furniture | 20% |
| 7610 | Aluminum windows/doors/frames | ~10% |

---

## Data Sources

- **Air rate:** Logimark International, PO.1254 (Glas Italia FOU03, MXP→BKK, March 2026)
- **Sea rate:** Profreight / Gift Somlak, China→BKK (Slack #shipping-china-thai)
- **Insurance:** Chubb cargo via Logimark, actual invoice PO.1254
- **HS 9403, 20% duty:** Confirmed Logimark, March 2026
- **Last-mile THB 3,500:** Confirmed from Slack #shipping-china-thai, oversized 6-wheel truck
