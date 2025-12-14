---
license: cc-by-sa-4.0

configs:
- config_name: mini-interact
  data_files:
  - path: mini_interact.jsonl
    split: dev
viewer: true
tags:
- text-to-sql
- database
---

[🌐 Website](https://bird-interact.github.io) • [📄 Paper](https://arxiv.org/abs/2510.05318) • [💻 GitHub](https://github.com/bird-bench/BIRD-Interact) • [🗄️ bird-interact-lite](https://huggingface.co/datasets/birdsql/bird-interact-lite) • [🗄️ bird-interact-full](https://huggingface.co/datasets/birdsql/bird-interact-full) • [🗄️ LiveSQLBench](https://livesqlbench.ai)

Testing
## 🧸 Overview: Mini-Interact

Mini-Interact is a lightweight version of [BIRD-INTERACT](https://bird-interact.github.io) (**re-imagines Text-to-SQL evaluation via lens of dynamic interactions**), which facilitates the quick development of interactive text-to-SQL methods.

### Unique Features compared to BIRD-INTERACT: 
- **DB Backend**: SQLite instead of PostgreSQL. No need to setup the docker.
- **Ambiguous Business Intelligence (BI) Queries**: 300 tasks, each task features ambiguous business intelligence (BI) user query, decoupled from the follow-up questions. (CRUD operations coming soon!)
- **Ambiguity Type**: Knowledge-Based (Personalized Ambiguities in development)
- **Parallel Evaluation**: Multiple evaluation experiments can be run in parallel, speeding up the evaluation process.

Other Features same as BIRD-INTERACT: The evaluation is interactive, same as BIRD-INTERACT, where the model can interact with the user simulator or database to solve the task. Support two evaluation modes: (1) **Conversational Interaction** and (2) **Agentic Interaction**. 


## 📦 Available Versions

### 1. Knowledge-Based Ambiguity Version 🌐✨
**Status**: ✅ Currently Available

In this version, the system navigates uncertainty and ambiguity stemming from:
- 📚 Incomplete knowledge bases
- ❓ Unclear or underspecified information
- 🔄 Context-dependent interpretations

This release focuses on how AI systems handle ambiguity when knowledge is partial or imprecise.


### 2. Personalized Ambiguity Version 💫🧩
**Status**: 🔜 Coming Soon

The upcoming personalized ambiguity version will tackle a different challenge:
- 👤 **User-Specific Preferences**: Adapts to individual user context
- 🧩 **Contextual Adaptation**: Resolves ambiguity based on user history and preferences


## 🗺️ Roadmap

| Feature | Status |
|---------|--------|
| 🔍 SELECT Queries | ✅ Released |
| ➕ CRUD Operations | 🔜 Coming Soon |
| 🧠 Knowledge-Based Ambiguities | ✅ Released |
| 💫 Personalized Ambiguities | 🔜 Coming Soon |
| 💬 Follow-Up Questions | 🔜 Coming Soon |

## 📦 Dataset Usage and Details

### Dataset Uses

1. Download the task file, DBs, DB metafiles (including schema, HKB, column meaning files) by cloning this entire repo:
```bash
git clone https://huggingface.co/datasets/birdsql/mini-interact
```
❗️NOTE:  If you find that some sqlite databases are not working, you could also download the database metafiles from [the Google Drive](https://drive.google.com/file/d/1HAXSy0rEiPRBvSZTPoOzmZrYq9wv549q/view?usp=sharing).


2. To avoid data leakage by auto-crawling, we do not include GT solution sqls and test cases along with data in `mini_interact.jsonl`.
please email [bird.bench25@gmail.com](mailto:bird.bench25@gmail.com) with the tag `[mini-interact GT&Test Cases]` in title for full set, which will be sent automatically within **30** minutes.

    Then refer to [Combine the Public Data with the Ground Truth and Test Cases](https://github.com/bird-bench/BIRD-Interact?tab=readme-ov-file#combine-the-public-data-with-the-ground-truth-and-test-cases) Section in our Github Repo to integrate the ground truth fields into the public data.

3. Refer to [bird-interact repo](https://github.com/bird-bench/BIRD-Interact/tree/main/mini_interact) for details of Evaluation.


### Dataset Description

**data:** Each data instance contain the following main parts:
   - `selected_database`: The name of the database.  
   - `amb_user_query`: The user query with injected ambiguities.
   - `user_query_ambiguity`: The ambiguities injected into the user query.
   - `non_critical_ambiguity`: The non-critical ambiguities like order, limit, etc.
   - `knowledge_ambiguity`: The ambiguities created by masked external knowledges. 
   - `sol_sql`: The ground truth SQL solution.  
   - `preprocess_sql`: SQL queries to run before executing the solution or prediction.  
   - `clean_up_sql`: SQL queries to run after the test cases to revert any changes made to the database.  
   - `test_cases`: A set of test cases to validate the predicted corrected SQL.
   - `external_knowledge`: The external knowledge related to the specific task.

- **Curated by:** BIRD Team & Google Cloud
- **License:** [cc-by-sa-4.0](https://creativecommons.org/licenses/by-sa/4.0/)


## 📋 Todo Lists

- [x] Release lite version, bird-interact-lite (270).
- [x] Release conversational version, bird-interact-conv.
- [x] Release agent version, bird-interact-agent.
- [x] Release Full bird-interact-full (600).
- [x] Release mini-interact (300).
- [ ] SFT / RL an User Simulator

## Created By:
BIRD Team & Google Cloud
