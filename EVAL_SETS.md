# MongoDB Question Generator — Evaluation Sets

Use these eval sets to **demonstrate**, **test**, and **grade** the application.

---

## Eval Set A — Application Smoke Tests

Verify the app itself works end-to-end.

| ID | Test | Steps | Expected result | Pass? |
|----|------|-------|-----------------|-------|
| A1 | Server starts | `python app.py`, open localhost:5000 | UI loads, syllabus banner visible | |
| A2 | Analyze (paste) | Paste 100+ char assignment with "CRUD" and "schema" | Coverage grid shows green topics in ~2 sec | |
| A3 | Analyze (PDF) | Upload a .pdf assignment | Text extracted, analysis returns 200 | |
| A4 | Generate (basic) | Select 1–2 concepts, click Generate | Returns preview + slug within API timeout | |
| A5 | Download ZIP | Click Download after generate | ZIP contains 3 folders | |
| A6 | API key missing | Remove `.env` key, generate | Clear error: API key not set | |
| A7 | Out-of-syllabus | Paste assignment mentioning "JWT authentication" | Analyze flags out-of-syllabus | |

---

## Eval Set B — File Structure Compliance

Verify the generator respects user file specifications.

| ID | Input query | Expected student files | Must NOT include | Pass? |
|----|-------------|------------------------|------------------|-------|
| B1 | "2 models customer and client + routes for them" | `models/customer.js`, `models/client.js`, `routes/customerRoutes.js`, `routes/clientRoutes.js` | `controllers/` | |
| B2 | Same + explicit scaffold: `server.js`, `app.http` | Above + scaffold complete in prefilled | `controllers/` | |
| B3 | "models + controllers + routes for products" | All three layers for products | — | |
| B4 | Explicit implement list in UI textarea | Exactly listed paths only | Anything not listed | |
| B5 | "schema only, 1 Book model" | `models/book.js` only (routes scaffolded or minimal) | Extra models | |

### B1 acceptance checklist
- [ ] `_prefilled/models/*.js` are empty or comment-only  
- [ ] `_prefilled/routes/*.js` are empty or comment-only  
- [ ] `_prefilled/server.js` is complete  
- [ ] No `controllers/` in ZIP manifest  
- [ ] README `<MultiLineNote>` lists correct student vs scaffold files  

---

## Eval Set C — Syllabus Alignment

| ID | Concept selected | Generated question must demonstrate | Fail if |
|----|------------------|-------------------------------------|---------|
| C1 | schema_design | Mongoose schema fields, types, defaults | Uses SQL or Prisma |
| C2 | crud_operations | POST/GET/PUT/DELETE with Mongoose | Missing CRUD endpoints |
| C3 | relationships | 2+ models with `ref` / populate | Single collection only |
| C4 | aggregation_pipeline | `$lookup` or `$group` in solution/tests | Simple find() only |
| C5 | indexing | `index: true` or compound index in schema | No index config |
| C6 | data_validation | required/enum/min/max validators | No validation rules |
| C7 | pagination_and_sorting | skip/limit/sort or query params | No pagination |
| C8 | error_handling | 400/404 responses in routes/tests | No error path tests |

---

## Eval Set D — README Quality Rubric

Score each generated README 0–2 per criterion (max 16).

| # | Criterion | 0 | 1 | 2 |
|---|-----------|---|---|---|
| D1 | Title matches domain | Missing/wrong | Generic | Clear, specific |
| D2 | Database section | Missing | Partial | Correct in-memory MongoDB note |
| D3 | Schema fields | Incomplete | Most fields | All fields with types/constraints |
| D4 | API endpoints | Missing | Listed without examples | Method, path, body, status codes |
| D5 | Folder structure tree | Missing | Wrong paths | Matches actual generated files |
| D6 | MultiLineNote — scaffold | Missing | Incomplete | Lists server.js, db.js, package.json |
| D7 | MultiLineNote — student files | Missing | Wrong list | Matches `student_files` exactly |
| D8 | Consistency with tests | Contradicts tests | Minor gaps | Endpoints match test assertions |

**Pass threshold:** ≥ 12/16

---

## Eval Set E — Test File Quality

| ID | Check | Expected |
|----|-------|----------|
| E1 | Suite tag | `:::NJSCPAxxxxx_TEST_SUITE:::` present |
| E2 | Test IDs | Each `it()` has `:::NJSCPAxxxxx:::` prefix |
| E3 | Unique IDs | No duplicate NJSCPA IDs |
| E4 | MongoMemoryServer | `beforeAll` connects in-memory DB |
| E5 | Schema tests | `.paths`, `.isRequired`, etc. when models are student work |
| E6 | Route tests | Supertest status + response shape |
| E7 | Error tests | 400/404 cases when syllabus includes error_handling |
| E8 | Solution passes | `npm test` in `_tests` folder passes against `_solution` code |

---

## Eval Set F — Sample Input Queries (Demo Script)

Use these live during a presentation.

### F1 — Relationships, routes only (no controllers)
```
Create a MongoDB schema which shows relation between customer and clients,
with exactly 2 models one is customer model and another one is client
and also create routes for them.
```
**Talking point:** App parses query → no controllers → empty student files.

### F2 — CRUD + error handling
```
Build a product inventory API with Mongoose CRUD endpoints.
Include validation on price (min 0) and return 404 when product not found.
```
**Talking point:** Syllabus topics auto-detected; tests include error paths.

### F3 — Aggregation
```
Create an order reporting API that joins orders and customers using
MongoDB aggregation pipeline with $lookup and $group.
```
**Talking point:** May add `services/` layer when aggregation is complex.

### F4 — Out of scope (negative test)
```
Build user login with JWT and refresh tokens using MongoDB.
```
**Talking point:** Analyze flags JWT as out-of-syllabus; generator should refuse or warn.

---

## Eval Set G — Solution Correctness (Technical)

After generation, copy `_solution` + `_tests` and run:

```bash
cd output/{slug}_tests
npm install
npm test
```

| Result | Meaning |
|--------|---------|
| All tests pass | Package is internally consistent |
| Schema tests fail | Model definition doesn't match README/tests |
| Route tests fail | Endpoints or handlers incorrect |
| Timeout | Server/db setup issue in generated code |

---

## Eval Set H — Comparison Matrix (Utility Pitch)

| Manual process | This application |
|----------------|------------------|
| ~4–8 hours per question | ~1–5 minutes |
| README written separately | README auto-generated from same spec |
| Tests written separately | Tests bundled with matching IDs |
| Inconsistent folder layouts | Query-driven structure |
| No syllabus enforcement | 8-topic guardrail + forbidden keywords |

---

## Quick Demo Script (5 minutes)

1. **Show syllabus banner** — explain scope constraint  
2. **Paste F1 query** → Analyze → show green topics  
3. **Leave file boxes empty** — explain auto-parsing  
4. **Generate** → show prefilled empty models/routes  
5. **Switch to solution tab** → show complete code  
6. **Open README** → show Pet Adoption Portal format  
7. **Download ZIP** → show 3-folder structure  
8. **Mention eval sets B + E** — how you quality-check output  

---

## Scoring Summary Template

| Eval set | Weight | Score | Notes |
|----------|--------|-------|-------|
| A — Smoke tests | 20% | /7 | |
| B — File structure | 25% | /5 | |
| C — Syllabus | 20% | /8 | |
| D — README rubric | 15% | /16 | |
| E — Tests | 10% | /8 | |
| G — npm test pass | 10% | pass/fail | |
| **Total** | 100% | | |

**Release-ready:** ≥ 80% overall AND G passes for at least 3 sample queries (F1, F2, F3).
