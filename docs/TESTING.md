# Evaluation of SQL Model Outputs (Questions 1–10)

This document describes how the current SQL generation model behaves for each evaluation question compared to the reference (correct) answers.  
The analysis focuses on **identifier usage, aggregation level, and semantic correctness**, not only numeric accuracy.

A critical discovery is that the dataset uses **two identifiers per person**:

- **CU** = Customer ID  
- **CS** = Core Registry ID  

Both refer to the same real person but appear in different tables. Many observed errors originate from mixing these two incorrectly.

---

## Question 1 – Top 10 Wealthiest Customers

**Reference behavior**

The correct answer returns:
- `customer_id` in **CS format** (e.g., `CS239090`)
- `total_assets`
- `total_liabilities`
- `computed_net_worth`
- `wealth_rank`

It returns the **10 wealthiest individuals**.

**Model behavior**

The model returns:
- Correct financial values and ranking
- But uses **CU identifiers** (e.g., `CU154870`) instead of CS

**Assessment**

The **numerical output is correct**, but the **identifier type is wrong**.

---

## Question 2 – Filtered Customer Set

**Reference behavior**

Only customers with **CS identifiers** are returned.

**Model behavior**

Only **CU identifiers** are returned. The CU–CS mapping does not align.

**Assessment**

The **filtering logic is correct**, but the **wrong identity domain** is used.

---

## Question 3 – Same Issue as Question 2

All values and ordering are correct, but the model again uses **CU instead of CS**.

---

## Question 4 – Credit Category Aggregation

**Reference behavior**

The correct output is aggregated by category:

| credit_category | count | avg_score |
|----------------|-------|-----------|
| Excellent | 102 | 826.90 |
| Fair | 160 | 625.57 |
| Good | 128 | 706.97 |
| Poor | 496 | 432.46 |
| Very Good | 114 | 767.51 |

**Model behavior**

The model returns **individual customers**, each with a credit category.

**Assessment**

This is a **semantic error**: the model should use **GROUP BY + aggregation** but returned row-level data.

---

## Question 5 – Identifier Mismatch

Both answers return the correct columns, but:

- Reference uses **CS**
- Model uses **CU**

This is explained by the dual-ID system: one person has both identifiers, but the model joins the wrong one.

---

## Question 6 – Financial Stress Indicator (FSI)

**Reference behavior**

Returns only:
- `CU` (clientref)
- `net_worth`
- `fsi`  
Only customers where `fsi = 1`

**Model behavior**

- Returns many unrelated columns
- Does **not** include `fsi`
- Does **not** filter to `fsi = 1`

**Assessment**

This is the **first fully incorrect query**:
- Wrong column set
- Missing business rule
- Missing filter condition

---

## Question 7 – Cohort Analysis

**Model behavior**

- Produces output in the UI
- SQL fails when run in SQLite
- Returns complex time-series columns:
- cohort_quarter, tenure_cohort, is_digital_native,
- cohort_size, engagement_score,
- pct_high_engagement_in_cohort,
- pct_high_engagement_by_digital_native_status
- Outputs quarterly data (2022–2023)

**Reference behavior**

Returns a **binary cohort comparison**:

| is_digital_native | cohort_size | avg_engagement | pct_high_engagement |
|------------------|-------------|----------------|--------------------|
| 1 | 285 | 0.5427 | 0.1684 |
| 0 | 715 | 0.5466 | 0.2112 |

**Assessment**

The model:
- Misinterpreted the task
- Built a time-series instead of a cohort comparison
- Generated **invalid SQL**

---

## Question 8 – Almost Correct

The model returns the correct rows but:
- Includes extra fields
- Omits `median_dti` and `avg_tsdr`

This is a **partial column selection error**.

---

## Question 9 – Likely Correct

The only difference is **CU vs CS**.  
All other columns and values appear consistent.

---

## Question 10 – High-Risk Customers

**Reference output**
CU456680 0.742022588 -589973.0 5 10
CU582141 0.781790236 -320071.0 2 14

**Model output**
CU969131 0.712508251 -30531.0 6 3
CU582141 0.781790236 -363816.0 2 14
CU609851 0.728122397 -228468.0 1 19

**Assessment**

The model:
- Uses the correct ID type (CU)
- But selects **different customers**
- Indicates a **logic mismatch in scoring or filtering**

---

# Overall Diagnosis

The system exhibits three main failure modes:

| Category | Description |
|--------|-------------|
| **Identity leakage** | CU and CS are mixed incorrectly |
| **Aggregation failure** | GROUP BY logic is missing |
| **Semantic drift** | Business rules (FSI, cohorts, risk) are misinterpreted |

---

# Recommended Fixes (Without Using Reference Answers)

Because the reference SQL cannot be exposed, corrections must be done at the **logic layer**.

## 1. Identity Control
Add a rule:
> If a query refers to people or customers, determine whether CU or CS is required based on the involved tables. Never mix them.

## 2. Aggregation Detection
Classify every question as:
- **Row-level**
- **Aggregate**

Then enforce:
- `GROUP BY` when categories or metrics are requested

## 3. Semantic Guardrails
Add hard rules:
- If FSI is mentioned → must include `fsi` and `fsi = 1`
- If cohort comparison → must aggregate, not time-series

---

# Conclusion

The SQL generator is technically capable but lacks:
- Identity awareness
- Aggregation intent
- Business-rule enforcement

Fixing these three layers will dramatically improve accuracy without revealing the correct answers.
