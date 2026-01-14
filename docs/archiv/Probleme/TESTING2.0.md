# Update: Questions 5, 6 and 8 — Detailed Evaluation

This section extends the original *Testing.md* and documents newly observed failure modes for **Question 5, Question 6, and Question 8**.  
In addition to the known CU/CS identity problem, these questions reveal **join drift, projection errors, and a SQL execution bug (parameter binding)**.

---

## Question 5 — Property Leverage (LTV / Mortgage Ratio)

### Intended task
The model should return, for each customer with property data:

- customer_id  
- property_value  
- mortgage_balance  
- property_leverage_ratio = mortgage_balance / property_value  

The result should be **sorted by the ratio (descending)** so that the highest leveraged customers appear first.

---

### Correct logical pattern

The correct logic is:

- Read directly from `expenses_and_assets.propfinancialdata`
- Use the **table-native identifier** `expemplref`
- Compute  
  `ltv = mortgage_balance / property_value`
- Exclude invalid or NULL ratios
- Sort by `ltv DESC`

This ensures:
- No identity mismatch
- No row duplication
- No join-induced distortion

---

### Model behavior

The generated SQL:

- Joins `core_record`, `employment_and_income`, and `expenses_and_assets`
- Uses `cr.clientref` as customer_id
- Does not apply any `ORDER BY`
- Returns values that do not align with the reference output

Even though the formula is mathematically correct, the **rows and IDs are wrong**.

---

### Root cause

This is a **join-drift + identity-leakage problem**.

`expenses_and_assets` is already keyed by `expemplref`.  
By joining via `core_record` and `employment_and_income`, the model introduces:

- 1:n joins
- row duplication or loss
- ID-domain switching (clientref instead of expemplref)

As a result, the same leverage calculation is applied to the wrong people.

---

### Fix rules

**Rule Q5-A — Table-native identity**  
When metrics come from `expenses_and_assets`, use `expemplref` as customer_id unless explicitly requested otherwise.

**Rule Q5-B — No unnecessary joins**  
If all required fields are present in one table, do not join additional tables.

**Rule Q5-C — Sort intent**  
If a ratio or leverage is calculated, the default ordering must be:
```sql
ORDER BY ratio DESC