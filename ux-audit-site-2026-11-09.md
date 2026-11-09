# UX audit — BITSians Startup Map (web)

The map home page, list, filters, company detail and company page, reviewed on 2026-11-09 from the local dev server and the source in `web/src`.

## 1. Scope & evidence base

**Audited:** the home page (map with hero, list, filter chips and popovers, sort), the company detail panel and mobile sheet, the mobile filter sheet (code only), the company page `/c/[id]`, and the 404 page (code only).
**Platform:** a responsive web app. Desktop is a panel plus map; mobile is a map/list toggle with bottom sheets.
**Audience:** mixed, mostly mainstream. BITS students looking for jobs, alumni looking each other up, founders hiring (`web/DESIGN.md`). Startup terms like "Unicorn" or "Series B" are fine for these readers. Data abbreviations need explaining.
**Evidence:** rendered at 1440×900 and 390×844 in headless Chromium with software WebGL (`ux-audit-site-2026-11-09-evidence/`). The source was read at commit `f0fe5b6`. Contrast was computed from the CSS tokens with `contrast-check.py`.
**Stakes:** low. The data is public and nothing is irreversible. The one sensitive area is publishing claims about named people, which is covered under trust.

**Not audited, and why:**
- Hover, keyboard and screen-reader flows were read in code, not driven. Focus styles exist in CSS but were not seen rendered.
- Map performance on real GPUs. The screenshots used software rendering, so rendered pixels on the map may differ slightly from a real device.
- The production site at `bitsians-map.whyujjwalraj.workers.dev`. It is assumed to match this commit.

No conformance claim is made for accessibility; this is a sampled review.

## 2. Executive summary

The site is well built. Its concept (the world at night, lit by companies, with light flowing from the four campuses) holds together, and the chrome is mostly quiet enough to let the map lead. Three things cost users the most. First, **almost half the dataset is missing from the map**: 146 of 306 companies have no location. The only sign of this is a pill that can't be clicked, so the map undersells the product it exists to show. Second, **founder lines use bare years with no label** ("Sid Pardeshi 2016", "Co-founder 2010"). Readers can't tell a batch year from a founding year, and the batch year is the most BITS-specific fact on the screen. Third, **the default globe view gets the campus story slightly wrong**. Pilani, the campus nearly every arc starts from, has no label, while half-hidden US city labels pile up at the top edge from the far side of the globe. Smaller issues: the muted text colour fails AA on the panel, the detail panel hides the sources that make each claim believable, and there is no way to suggest a correction to a dataset that openly rates its own confidence. Visually this is light polish, not a rebuild. Spacing is off the 4px grid in places, chrome weights run heavy, and each list row has two coloured labels competing.

## 3. Quick wins

| ID | Finding | Dimension | Severity | Effort |
|---|---|---|---|---|
| DATA-01 | Bare years on founder lines are ambiguous | Data display | High | S |
| A11Y-01 | `--ink-3` text fails AA on the panel surface | Accessibility | Medium | S |
| NAV-01 | "146 of these aren't on the map yet" is a dead end | Navigation | High | S |
| MAP-01 | Pilani campus is unlabeled at the default view | Visual hierarchy | Medium | S |
| COPY-01 | Empty state says "filters" when the cause is a search | Content | Low | S |

## 4. Findings

### 4.1 Information architecture & navigation — 2 findings

#### NAV-01 · Almost half the companies can't be reached from the map, and the notice offers no way to see them

| | |
|---|---|
| **Dimension** | Navigation (D2); touches System status (D5) |
| **Severity** | High |
| **Confidence** | Observed (rendered + code) |
| **Effort** | S |
| **Location** | `App.svelte:244-246`, `.offmap` |

**Evidence.** At the default view the map reads "146 of these aren't on the map yet" (`desk.png`, `mob.png`). This is 48% of the 306 companies. The notice is a `<p>` element, not a button, and the list has no "location unknown" filter.

**Why it matters.** The map is the first and largest thing a visitor sees, and it is the product's pitch. Someone who searches the map for their batchmate's company and doesn't find it will conclude the company isn't listed. Mobile users start on the map and have to find the List pill on their own.

**Recommendation.** Make the notice a button: **"146 aren't on the map yet. Show them"**. It should switch to the list with an "Unmapped" filter (`f.unmapped`, written to the URL like the other filters). Longer term, the enrichment pipeline should fill in HQ cities. Even a country-level pin beats none, and `geo_precision` already handles this.

#### NAV-02 · No way to suggest a correction or add a company

| | |
|---|---|
| **Dimension** | Navigation (D2); touches Trust (D15) |
| **Severity** | Medium |
| **Confidence** | Observed (code) |
| **Effort** | S |
| **Location** | About popover `App.svelte:164-170`; company page footer |

**Evidence.** The About popover contains two sentences and no link. The company page has no "report an error" link. The dataset itself marks rows `needs_review` and rates confidence, and `verified: false` is on every exported record checked.

**Why it matters.** The people listed are the people most likely to visit, and they will notice a wrong batch year or a missing co-founder. With nowhere to send a fix, they leave annoyed, and the dataset's most motivated editors are lost.

**Recommendation.** Add **"Suggest a fix"** to each company detail and page, opening a prefilled GitHub issue or form with the company id. Add **"Add a company"** to About.

### 4.2 Data display — 2 findings

#### DATA-01 · Founder years have no label, so batch year and founding year can't be told apart

| | |
|---|---|
| **Dimension** | Data display (D11); touches Content (D8) |
| **Severity** | High |
| **Confidence** | Observed (rendered) |
| **Effort** | S |
| **Location** | `CompanyRow.svelte` `.rcy`; `CompanyDetail.svelte` `.fcy`; `c/[id].astro` founders list |

**Evidence.** List rows read "Raj Neervannan  Pilani 1988" next to "Sid Pardeshi  2016" (`desk.png`). In the detail panel, Swiggy shows "Co-founder  Pilani, 2008" and "Co-founder  2010" (`detail.png`). On the same screen, "Founded 2013" carries a label.

**Why it matters.** "2016" on a startup row reads as the founding year, so Blitzy looks like a 2016 company. The batch year is the fact that makes this a BITSian directory, and it is the one left unlabeled.

**Recommendation.** Use one batch tag everywhere: **"Pilani '08"** when the campus is known and **"Class of '10"** when only the year is. Use tabular figures, and the same form in rows, the detail panel and the company page. Add a `title` attribute with "BITS Pilani, batch of 2008".

#### DATA-02 · Two coloured labels on one row compete, and "Unicorn" takes the brand colour

| | |
|---|---|
| **Dimension** | Data display (D11); touches Visual hierarchy (D9) |
| **Severity** | Low |
| **Confidence** | Observed (rendered) |
| **Effort** | S |
| **Location** | `.rstage.peacock`, `.hirepill` |

**Evidence.** Under the default "Notable" sort, the first eight rows each show a marigold "Hiring" pill and a peacock "Unicorn" label (`moblist.png`). Peacock is the colour of selection, links and focus.

**Why it matters.** The spec says hiring should be the loudest thing on screen. With a second coloured label on every row, hiring stops standing out, and the peacock "Unicorn" looks like a link.

**Recommendation.** Show stage in `--ink-2` at weight 500 for every stage, Unicorn included. Keep marigold for Hiring only.

### 4.3 Visual hierarchy & layout (map) — 2 findings

#### MAP-01 · Pilani, the campus most arcs start from, has no label at the default view

| | |
|---|---|
| **Dimension** | Visual hierarchy (D9) |
| **Severity** | Medium |
| **Confidence** | Observed (rendered + code) |
| **Effort** | S |
| **Location** | `Map.svelte` `declutter()` lines 271-312 |

**Evidence.** At 1440×900, "Dubai campus" and "Goa campus" are labelled, but no "Pilani campus" label appears. The arc bundle converges on an unlabelled point between Gurugram and Delhi (`desk.png`). The code places campus labels only after the cities with 3+ companies, so Delhi and Gurugram take the space first.

**Why it matters.** The headline concept is "the campuses are where the light comes from". The campus that sends out the most light is the one people can't name, and first-time viewers see a knot of lines near Delhi.

**Recommendation.** Place campus labels before the big cities in `declutter()`, or at least place Pilani first. Shift the Gurugram/Delhi labels instead.

#### MAP-02 · City labels on the far side of the globe pile up along the top edge

| | |
|---|---|
| **Dimension** | Visual hierarchy (D9) |
| **Severity** | Medium |
| **Confidence** | Observed (rendered); whether a real GPU renders it the same is Inferred |
| **Effort** | S |
| **Location** | `Map.svelte` DOM city markers, globe projection |

**Evidence.** In the India view, faded labels for Chicago, Raleigh, Suwanee, Plano, San Jose and San Francisco overlap near the top edge, partly behind the chip bar. Their arcs leave the frame upward (`desk.png`, `pop.png`).

**Why it matters.** This is the first thing in the frame, and it looks like a rendering glitch. It weakens the "jaw-dropping on first sight" goal the spec sets.

**Recommendation.** Hide DOM markers whose points are behind the globe horizon, or more than about 80° from the map centre, while in globe projection. Add an "and 41 in the US" chip that switches to the World view instead.

### 4.4 Accessibility — 2 findings

#### A11Y-01 · Muted text fails AA on the panel surface

| | |
|---|---|
| **Dimension** | Accessibility (D12) |
| **Severity** | Medium |
| **Confidence** | Observed (computed from CSS tokens) |
| **Effort** | S |
| **Location** | `global.css:4` `--ink-3: #6E828B` on `--surface: #13212A` |

**Evidence.** The ratio is 4.09:1 on `--surface`, below 4.5 for normal text. It passes on `--paper` at 4.63:1. `--ink-3` is used at 13px for row meta, checklist counts, "Sort", section headings like "Founders" and "Sources", and the footer.

**Why it matters.** This 13px grey carries founder and batch details, the exact information students scan for. On a dim phone screen it is the first thing to become unreadable.

**Recommendation.** Set `--ink-3: #7A8E97`. The script suggests #768A93 at 4.56:1, and #7A8E97 leaves margin. Hue and role stay the same.

#### A11Y-02 · Touch targets in the chip bar and header are under 44px on mobile

| | |
|---|---|
| **Dimension** | Accessibility (D12); Responsive (D13) |
| **Severity** | Low |
| **Confidence** | Observed (code) |
| **Effort** | S |
| **Location** | `.chip` 34px, `.textbtn` about 26px ("About", "Clear"), `.x` 36px |

**Why it matters.** "About" and "Clear" sit near other controls, and a missed tap on "Clear" wipes the filter set the user just built.

**Recommendation.** Below 960px, give `.textbtn` a 44px min-height via padding, and give chips a 40px height with an invisible 44px hit area.

### 4.5 Trust — 1 finding

#### TRUST-01 · The detail panel hides the sources that back each claim

| | |
|---|---|
| **Dimension** | Trust (D15) |
| **Severity** | Medium |
| **Confidence** | Observed (rendered + code) |
| **Effort** | S |
| **Location** | `CompanyDetail.svelte` (no sources); `c/[id].astro` shows them |

**Evidence.** The Swiggy panel shows founders and links but no sources (`detail.png`). The full page lists three source URLs (`page.png`).

**Why it matters.** "This person is a BITS alum" is a claim about a real, named person. Most visitors never open the full page, so they see the claim without what backs it up. Each row's main asset is its source.

**Recommendation.** Add a quiet **"Sources (3)"** line under the founders in the panel, linking to each source by its domain ("bits-pilani.ac.in", "swiggy.com").

### 4.6 Content & microcopy — 2 findings

#### COPY-01 · The empty state blames filters when the user only searched

**Severity** Low · **Confidence** Observed (code) · **Effort** S · `App.svelte:205-209`
"No companies match these filters." also appears for a search with no filters. Rewrite: if only `f.q` is set, show **"No companies, founders or cities match "{q}"."** with a **"Clear search"** button.

#### COPY-02 · "Hiring" means only "has a careers link"

**Severity** Low · **Confidence** Observed (code: `hiring: !!c.careers`) · **Effort** S
A careers page can list zero openings, and the "61 of them are hiring" claim in the hero is built on this. Either relabel it **"Careers page"** with "61 have open careers pages", or keep "Hiring" and state its basis in About. Taste call, but it is a claim about real companies.

### 4.7 Design system consistency — 1 finding

#### DS-01 · Spacing runs off the 4px grid, and chrome weights run heavy

**Severity** Low · **Confidence** Observed (code) · **Effort** S
Off-grid values: `.rbody` gap 3, `.chipbar` gap 6 and padding 10, `.top` padding-bottom 10, `.hero`/`.dbody`/`.dtitle` gap 14, `.aboutpop` 14/16, `.facts` 2/18, `.cta` padding 22, `.fsbody h3` margin 18, `.hirepill` 1/8. Chrome text uses weights 600-700 (chips 600, counts, sort, pill, CTA 700), so small controls are as heavy as content. Move to 4/8/12/16/20/24 and use 500 for chrome, 600 for emphasis. Leave the display headline and wordmark alone (see §6).

**Responsive** — the mobile List/Map pill overlaps the map attribution at 390px (`mob.png`). Low; lift the attribution or shift the pill 8px up.
**Feedback & states, forms, dark patterns** — no findings. Loading has a status message, the search uses 16px on mobile (no iOS zoom), filters are reflected in the URL, and nothing pushes users into anything.

## 5. Prioritized backlog

| # | ID | What to do | Severity | Effort | Why it's here |
|---|---|---|---|---|---|
| 1 | DATA-01 | One batch tag, "Pilani '08" / "Class of '10", everywhere | High | S | Fixes misreading on every row; it is the product's most specific fact |
| 2 | NAV-01 | Make the off-map notice a button leading to an Unmapped list filter | High | S | 48% of companies are reachable from the map today only by luck |
| 3 | MAP-01 | Label campuses before cities in `declutter()` | Medium | S | The first view should tell the campus story |
| 4 | MAP-02 | Hide far-side globe labels | Medium | S | Removes the glitch at the top of the first frame |
| 5 | A11Y-01 | `--ink-3` to `#7A8E97` | Medium | S | One token, every meta line |
| 6 | TRUST-01 | Sources line in the detail panel | Medium | S | Backs claims about real people where people actually read them |
| 7 | NAV-02 | "Suggest a fix" and "Add a company" links | Medium | S | Turns visitors into editors |
| 8 | DATA-02 | Stage in neutral ink; marigold only for Hiring | Low | S | Hiring becomes the loudest thing again |
| 9 | DS-01 | 4px grid and 500/600 chrome weights | Low | S | Polish |
| 10 | COPY-01/02, A11Y-02 | Copy and tap-target fixes | Low | S | Polish |

Everything here is S effort, so the order is by user impact alone.

## 6. What's working, and what I left alone

**What's working.** The concept is specific to this product: the campus-to-city arcs and the "hiring" glow are both data, not decoration. Filters are instant, live in the URL, and show their counts. The company page has proper JSON-LD and sources. Logo tiles go to a dark chip for light-on-transparent logos, and inactive companies fade. All of this is careful work.

**What I left alone, and why.** The dark-only theme, Archivo at condensed widths with the 860-weight "Built by BITSians." headline, the pill-shaped chips and CTAs, and the large hero on the map. These are written decisions in `DESIGN.md`, they hang together, and I couldn't name a cost to users. The "B" tile logo is plain, but it is the spec's monogram-tile system applied to the brand. That is consistent, not lazy.

## 7. Open questions

- **How many of the 146 unmapped companies have a known country?** If most do, country-level pins fix NAV-01 at the data layer.
- **Does the far-side label pile-up (MAP-02) happen on real GPUs?** This was seen only with software WebGL. Check in Safari and Chrome on a laptop.
- **Hypothesis (unverified):** do most visitors arrive on a company page from search rather than on the map? If so, the company page deserves the polish budget (more context, nearby BITSian companies) more than the hero does.

## Appendix — evidence log

SEEN (rendered): `desk.png` home 1440; `pop.png` sector popover; `detail.png` Swiggy panel; `page.png` `/c/swiggy`; `mob.png` home 390; `moblist.png` list 390; `mobdetail.png` sheet 390.
NOT SEEN: hover and focus states, the mobile filter sheet, zoomed-in sunflowers beyond Bengaluru, the 404 page, the production deployment.
