# BITSians Startup Map PRD

Status: draft, 2026-11-09 · Owners: whyujjwal, Devansh Goel · Living document, edit as you learn

Gap tags used throughout: 🔶 **Assumption** (plausible, not yet checked) · 🔵 **Open Question** (needs discovery or a decision)

## 1. Executive summary

BITSians Startup Map is a public map and directory of companies started by BITS Pilani alumni from the Pilani, Goa, Hyderabad and Dubai campuses. Each founder–company claim on it carries a source and a confidence level. BITS students can use it to find jobs and internships at alumni companies. Alumni and founders can use it to find each other and to be found. Version 1 is live with 306 companies and 388 founders. The next phase makes the dataset **complete enough to trust**, meaning more companies located, more websites and batch years filled in, and a way for listed founders to send corrections. It also makes the site **better at its main jobs**: getting a student to an open role, and getting an alum to a specific person. The goal is for the map to be the place BITSians go to answer "who from BITS started what, and are they hiring?" 🔶 **Assumption:** no other public source answers this today. See §4.

## 2. Problem statement

### Who has this problem?
- BITS students looking for internships and jobs, especially at early-stage companies that don't recruit on campus.
- Alumni who want to find other BITSian founders by sector, city or batch, to hire, raise money, sell or partner.
- BITSian founders who want to be found by students and peers.

### What is the problem?
The information exists, but it is scattered and goes out of date. It sits in a university PDF (*Built by BITSians*), campus magazines, the BITSAA notable-alumni page, Wikipedia, Tracxn's paid lists, press articles and LinkedIn. None of these covers all four campuses, none can be filtered by "hiring now" or by city, and none links a claim to its evidence. Students depend on word of mouth, and that favours people who already have networks.

### Why is it painful?
- **Students:** they miss roles at companies that would favour a BITSian, and cold outreach without a shared-campus hook converts poorly. 🔶 **Assumption**
- **Alumni and founders:** finding "BITSians building in climate in Bengaluru" takes hours of LinkedIn searching. 🔶 **Assumption**
- **The community:** the BITS founder story is told only through a few famous names (Swiggy, redBus, Hotmail). The long tail of 2015–2026 companies stays invisible.

### Evidence
- **Coverage of the sources (observed, from this repo):** the five public sources together produce 306 companies. The official PDF alone lists about 100. No single source covers more than a third of the merged set.
- **Data gaps in v1 (observed, `web/src/data/companies.json`):**
  - 146 of 306 companies (48%) have no map location.
  - Only 124 have a website and 61 a careers page.
  - 195 of 388 founders (50%) have no known campus, and 158 have no batch year.
  - 235 companies (77%) rest on a single source.
- **UX evidence:** `ux-audit-site-2026-11-09.md` found two High-severity issues. Half the companies can't be reached from the map, and unlabelled years make batch years read as founding years.
- 🔵 **Open Question:** no user interviews or analytics exist yet. Section 6 starts measuring, and discovery should begin with 5 to 8 student interviews.

> Before moving on: the problem is about **completeness and trust** as much as **discovery UX**. Every later section should serve one or both.

## 3. Target users & personas

### Primary: Aditi, third-year student hunting for an internship
- **Context:** BITS Goa, CS, looking for a summer internship or a first job. Uses LinkedIn and WhatsApp batch groups. Mostly on her phone.
- **Goals:** get a short list of BITSian-founded companies that are hiring in her field and city, and a name to message.
- **Pain points:** doesn't know which startups are BITSian. Career pages are scattered. Doesn't know who to contact.
- **Job to be done:** "When I'm hunting for an internship, help me find companies where a BITS connection counts, so I can reach out with a reason to be heard."
- **What success looks like:** filter Hiring + sector + city, open a company, and click "View open roles" in under a minute.

### Secondary: Rahul, alum and founder (Pilani '08)
- **Context:** runs a Series A company. Hires, raises money, and likes to give back to BITS.
- **Goals:** be listed correctly, with the right co-founders, batch and careers link. Find other BITSian founders in his space.
- **Pain points:** wrong or missing data about him, and no way to fix it.
- **Job to be done:** "When I'm hiring, make sure BITS students can find us and know we're BITSian."

### Tertiary: community and press
BITSAA chapters, campus clubs (E-Cell, incubators) and journalists who want aggregate numbers ("306 companies, 61 hiring") and a shareable map. 🔶 **Assumption:** this group drives most first visits, through shares.

> Before moving on: Aditi is mobile-first and task-driven, and Rahul is a correction and data source. Requirements need both a fast mobile hiring flow (Aditi) and a correction path (Rahul).

## 4. Strategic context

- **Goal:** become the reference directory of BITSian-founded companies, the one that student groups, BITSAA and the press link to.
- **Market:** about 100,000 or more living BITS alumni across four campuses, plus about 18,000 students at any time. 🔶 **Assumption:** figures to be confirmed with BITSAA or the university. Within that, about 1,000 to 3,000 founders. 🔵 **Open Question:** the true number of BITSian founders. The Coresignal pull suggests the public sources cover a small fraction.
- **Alternatives:**
  - Tracxn and Crunchbase alumni lists are paid, don't name founders reliably, and don't show hiring.
  - The *Built by BITSians* PDF is static, Pilani-centred and published once a year.
  - The BITSAA notable-alumni page is a flat list with no filters.
  - LinkedIn is comprehensive but can't be searched this way without paid tools.
- **Why now:**
  - The official *Built by BITSians* volume (Oct 2026) raised interest.
  - The pipeline and site already exist, so the cost of the next step is mostly data work.
  - Internship season (Dec–Feb) is the best time to reach Aditi. 🔶 **Assumption**
- **Constraints:** no budget for paid data. Coresignal (licensed, LinkedIn-derived) can't be republished without verification or consent. Not affiliated with BITS Pilani, so no official branding.

## 5. Solution overview

The product has two halves that need to improve together.

### A. The dataset (the product's foundation)
1. **Sources → raw rows:** each source becomes a CSV of founder–company rows with a source URL, a note and a confidence level (`data/raw/`).
2. **Merge:** names are normalised and aliased. The highest-confidence row wins, gaps are filled from the other rows, all sources are kept, and campus conflicts are flagged (`scripts/merge.py`).
3. **Enrich:** research batches fill website, careers page, status and HQ (`out_*.csv`). Wikidata fills the rest, but only when a founder or website matches (`wikidata_enrich.py`).
4. **Geocode:** Nominatim, rate-limited and cached, using the address and falling back to the city (`build_companies.py`).
5. **Logos:** site icons are tried first, then favicon services. Generic and placeholder icons are blocked, and sites that refuse are not worked around (`fetch_logos.py`).
6. **Publish:** low-confidence and Coresignal-only rows are dropped, sectors are bucketed, and the JSON is exported (`export_web_data.py`).

**Next phase additions:**
- **Socials enrichment.** For each company: LinkedIn, X and GitHub pages, taken only from the company's own homepage links and `sameAs` structured data, or from Wikidata (P2002 X, P4264 LinkedIn, P2037 GitHub) with the same founder/website match rule. No scraping of LinkedIn itself. Founder profiles are published only with consent.
- **Location backfill.** Every company gets at least a country-level pin, and the remaining 146 get an HQ city where it can be found.
- **Corrections loop.** "Suggest a fix" on every company and "Add a company" in About. Each opens a prefilled GitHub issue (v1) and then turns into a raw-row update with the submitter's source.
- **Verification.** Founders can confirm their own entry, which earns a "verified" mark. That makes it possible to publish consented Coresignal leads.

### B. The site
- **Map:** a night globe, arcs from each campus to the cities its alumni built in, city lights (marigold where companies are hiring), and logo "sunflowers" when zoomed in.
- **List and filters:** Hiring, Sector, Stage, Campus, City, plus search across companies, founders and cities. All filters live in the URL.
- **Detail and company page:** founders with campus and batch, careers CTA, website, sources, and JSON-LD for search engines.

**Next phase UX** (from `ux-audit-site-2026-11-09.md`):
- A batch tag ("Pilani '08" / "Class of '10") everywhere.
- The "N aren't on the map" notice becomes a link to an Unmapped list.
- Campus labels get priority on the map.
- Far-side globe labels are hidden.
- Sources appear in the detail panel.
- The muted-text contrast is fixed.
- Social links appear on company pages once enrichment exists.

> Before moving on: each solution item maps to a gap in §2. Location backfill and Unmapped fix the 48% problem. Batch tags plus campus backfill fix the 50% unknown campus. Corrections and verification fix the 77% single-source problem.

## 6. Success metrics

No analytics are installed yet. The first task is privacy-friendly analytics (Cloudflare Web Analytics, no cookies). 🔵 **Open Question:** the baselines below for usage metrics are unknown until then.

### Primary metric
**Careers clicks per week**: clicks on "View open roles". This is the closest measure of the product's main job, a student reaching a role at a BITSian company.
- Current: unknown (no analytics) · Target: baseline in the first 4 weeks, then +50% by the end of internship season (Feb 2027) 🔶 **Assumption** on the target.

### Secondary metrics (dataset health, measurable today)
| Metric | Now | Target (Q1 2027) |
|---|---|---|
| Companies with a map location | 160 / 306 (52%) | ≥ 90% |
| Founders with known campus | 193 / 388 (50%) | ≥ 75% |
| Companies with 2+ sources | 71 / 306 (23%) | ≥ 40% |
| Companies with a website | 124 / 306 (41%) | ≥ 80% |
| Companies with at least one social link | 0 | ≥ 60% |
| Companies listed | 306 | 600 🔶 **Assumption** |
| Corrections received / merged per month | 0 / 0 | 20 / 15 |

### Usage metrics (after analytics)
Weekly visitors. Share of visits that use a filter. Company-page entries from search. Share of mobile sessions that reach a company detail.

### Guardrails
- **Accuracy:** a public correction or takedown request is resolved within 7 days. Zero claims published without a source.
- **Licensing:** zero Coresignal-only rows published without verification.
- **Performance:** first paint stays instant (static HTML). Filtering stays at about 0.1 ms. No new runtime requests except tiles and logos.

## 7. User stories & requirements

### Epic hypothesis
We believe that **filling the location, campus and source gaps, adding a corrections loop, and fixing the audit's top UX issues** will make BITSians **trust and use the map to find roles and people**. We'll know it worked when careers clicks grow 50% over baseline during internship season and dataset health reaches the §6 targets.

### Stories

**S1 · Batch tag (site)**
As Aditi, I want to see each founder's campus and batch in one clear form, so that I know who to message and why.
- [ ] The tag reads "Pilani '08" when the campus and year are known, "Class of '10" when only the year is known, and is hidden when neither is.
- [ ] The same tag appears in list rows, the detail panel and the company page, in tabular figures.
- [ ] The tag has a title of "BITS Pilani, batch of 2008".

**S2 · Reach unmapped companies (site)**
As Aditi on mobile, I want to see the companies that aren't on the map, so that a missing pin doesn't mean a missing company.
- [ ] The notice "146 aren't on the map yet. Show them" is a button.
- [ ] Clicking it opens the list filtered to unmapped companies (`?unmapped=1`), and the filter can be cleared like any other.
- [ ] The count updates with the other filters.

**S3 · Sources in the panel (site)**
As a visitor, I want to see why a company is listed as BITSian, so that I can trust it.
- [ ] The detail panel lists each source by its domain, linked, under the founders.

**S4 · Suggest a fix (site + process)**
As Rahul, I want to correct my company's entry in under a minute, so that students see accurate data.
- [ ] "Suggest a fix" on the detail panel and company page opens a GitHub issue prefilled with the company id, the current values and a source field.
- [ ] "Add a company" in About opens a prefilled issue for a new company.
- [ ] The README documents how a maintainer turns an issue into a raw-row edit.

**S5 · Location backfill (data)**
As a maintainer, I want every company placed at least at country level, so that the map reflects the whole dataset.
- [ ] The enrichment batch for the unmapped companies finds an HQ city, or failing that a country, each with a source.
- [ ] Country-level pins sit at the country centroid with `precision: "country"`, and the site shows them as a country light, not a fake city.

**S6 · Socials enrichment (data)**
As Aditi, I want a company's LinkedIn, X and GitHub links, so that I can check them out and find people.
- [ ] A new `scripts/socials_enrich.py` reads the company homepage and collects social links from `<a href>` and from JSON-LD `sameAs`. It honours robots.txt and backs off on 403/429, like `fetch_logos.py`.
- [ ] Wikidata P2002, P4264 and P2037 are accepted only for items that pass the existing founder/website match.
- [ ] The output is `data/enrich/socials.csv` (company, platform, url, source), exported as `socials` and shown on the company page and in JSON-LD `sameAs`.
- [ ] No LinkedIn pages are fetched. Founder personal profiles are not published in this phase.

**S7 · Founder verification (data + site)**
As Rahul, I want to confirm my listing, so that it shows as verified.
- [ ] Split before building (story too big): (a) a verification request through an issue, (b) a `verified` column in raw rows, (c) a verified mark on the site, (d) consented Coresignal rows promoted to publishable.

**S8 · Map polish (site)**
- [ ] Campus labels are placed before city labels.
- [ ] DOM labels behind the globe horizon are hidden.
- [ ] `--ink-3` contrast is ≥ 4.5:1 on `--surface`.

**S9 · Analytics (site)**
- [ ] Cookieless page analytics.
- [ ] Events for careers clicks, filter use and company opens.
- [ ] No personal data collected. About says what is measured.

### Constraints & edge cases
- **Static site:** all data is built in at deploy time, so corrections take effect on the next deploy. 🔵 **Open Question:** deploy on every merged correction, or weekly?
- **People data:** names, campus and batch are published only from public sources or with consent. Takedown requests take precedence over completeness.
- **Ambiguous names:** generic company names need a founder or domain match (an existing rule, and socials must follow it too).
- **Rate limits and etiquette:** Nominatim at 1 request per second, Wikidata with a user agent, and no working around site blocks.

## 8. Out of scope

- **Individual founder profile pages and alumni directories.** Privacy risk and a different product. Revisit after verification exists.
- **Scraping LinkedIn or other social networks.** Terms of service and consent.
- **Live job listings** (parsing open roles). Each careers page is different. Linking out is enough for now.
- **Accounts and logins.** GitHub issues cover corrections without them.
- **Light theme.** A design decision in `DESIGN.md`. Revisit only if accessibility feedback calls for it.
- **Funding amounts and valuations.** Hard to source reliably, and they invite disputes.

## 9. Dependencies & risks

### Dependencies
- OpenFreeMap tiles, Nominatim and Wikidata (free public services).
- Cloudflare Workers for hosting and Web Analytics.
- Research-agent time for enrichment batches.
- GitHub issues for the corrections loop.

### Risks & mitigations
| Risk | Mitigation |
|---|---|
| **Publishing a wrong claim about a real person** (wrong batch, someone who isn't a BITSian) | Every row has a source. Low confidence is never published. "Suggest a fix" and a 7-day takedown guardrail. |
| **Licensing:** Coresignal data leaks into the public set | The export excludes Coresignal-only rows by default. Private files stay out of git. Check before each deploy. |
| **Anti-pattern: completeness theatre.** Chasing the "600 companies" number with weak single-source rows | Count only rows with medium confidence and 2+ sources, or high confidence, toward the target. Report single-source share next to the total. |
| **Anti-pattern: building features nobody asked for** (verification, socials) before seeing whether students use the hiring flow | Ship analytics (S9) and the audit fixes (S1–S3, S8) first. Gate S6 and S7 on the baseline. |
| Corrections pile up without maintainers | Issue templates, and a weekly triage slot shared by both owners. 🔵 **Open Question:** who owns triage? |
| Map tiles or the geocoder change terms | The geocode cache is committed. The tile style is generated and can be pointed at another source. |
| Hardcoded paths break the pipeline on other machines (`fetch_logos.py` points at one contributor's home directory) | Make paths relative to the repo root before the next logo refresh. |

## 10. Open questions

- 🔵 How many BITSian founders exist? Can BITSAA or the university share a list, or endorse the project?
- 🔵 Should Coresignal leads be verified through outreach (email or LinkedIn message from a maintainer), and what consent wording?
- 🔵 Deploy cadence for corrections: every merge, or weekly?
- 🔵 Does "Hiring" (careers page exists) need a freshness check, such as "careers page reachable within 30 days"?
- 🔵 Is the company page (search traffic) or the map (shares) the main way in? This decides where polish goes.
- 🔶 Students mostly arrive on mobile through WhatsApp shares. Confirm with analytics.

## Self-assessment

- **Strongest section:** §5 and §7 on the dataset. The pipeline is real, measured and already enforces the trust rules this PRD relies on, so the stories extend working code.
- **Weakest section:** §2 evidence and §6 baselines for usage. There are no interviews and no analytics, so the user pain and the primary-metric target are reasoned, not observed.
- **Top assumptions to validate:**
  1. Students would use a BITS connection to reach out, and it helps them get heard.
  2. Listed founders will send corrections if it takes under a minute.
  3. No existing source already answers "who from BITS started what, and are they hiring".
- **Recommended next step:** ship analytics plus the audit's quick fixes (S1–S3, S8, S9) this week. Run 5 student interviews during internship season. Run `/plan-roadmap` to sequence S4–S7 against what the interviews and the four-week baseline show.
