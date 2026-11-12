# BITSian Network PRD: find BITSians at every company on the map

Status: draft, 2026-11-09 · Owners: whyujjwal, Devansh Goel · Builds on `docs/PRD.md` (the map) · Living document

Gap tags: 🔶 **Assumption** (plausible, not yet checked) · 🔵 **Open Question** (needs discovery or a decision)

## 1. Executive summary

BITSians Map today answers "which companies did BITSians start, and are they hiring?" for 306 companies and 388 founders. Students want the next step: **"who from BITS works there, and will they refer me?"** We will build an **opt-in BITSian Network**. BITSians of any campus and batch create a verified profile saying where they work and whether they're open to referrals. Each company on the map then shows its BITSians, and students can send a referral request, with limits, that the alum accepts or declines.

We will grow towards "every possible BITSian" through channels that bring consent with them:
- batch and chapter ambassadors
- founders claiming their company page
- an invite to people found in licensed data
- verification by BITS email

We will not scrape LinkedIn or publish anyone who hasn't joined. Alongside this, real job listings come from the hiring platforms' public APIs. The interface stays in the current light map design: a **People** section on each company card and a **Network** view in the rail.

Success means verified members in at least half of the hiring companies on the map within two quarters, and most referral requests answered within a week. 🔶 **Assumption:** both targets; see §6.

## 2. Problem statement

### Who has this problem?
- **Students** of all four campuses looking for internships and jobs.
- **Alumni** who are happy to refer juniors but get unstructured, repetitive requests.
- **Founders** on the map who want BITSian hires.

### What is the problem?
- A student who finds a company on the map has no way to see which BITSians work there, or whether any of them would help.
- Today they search LinkedIn by hand, guess, and send cold messages.
- Alumni get scattered DMs with no context, many from people they can't place, and no easy way to say "yes, but only for backend roles", or no.

### Why is it painful?
- **Students:** hours of searching per company. Low reply rates to cold messages 🔶 **Assumption**. Students without seniors in their network lose out.
- **Alumni:** inbox noise and guilt about ignoring juniors. Requests miss the basics they need: role, resume, batch.
- **The map:** the "61 hiring" promise stops at a careers page.

### Evidence
- **The data only knows founders.** It has 306 companies and 388 founders, but no employees. 50% of founders have no known campus and 41% have no batch year. Completeness is already the dataset's weak point (`docs/PRD.md` §2).
- **"Hiring" isn't real job data.** It means "has a careers link". Only 7 of 61 careers links point directly at a known hiring platform (3 Greenhouse, 2 Keka, 1 Ashby, 1 Darwinbox). Others may embed one 🔵 **Open Question:** we need a scan of the 61 pages.
- **The user is asking for it.** The project owner asked for this ("find people in those companies on the map", referrals). There are no student interviews yet 🔵 **Open Question:** we need 5–8 interviews during internship season.
- **The legal limits are set.** LinkedIn's terms forbid scraping, and hiQ v. LinkedIn ended against the scraper on breach of contract. India's DPDP Act 2023 requires consent and a specific purpose for personal data. Coresignal's licence limits republishing.

> Before moving on: the problem is *connection with consent*, not *data volume*. A list of 10,000 names nobody agreed to doesn't produce referrals. 500 people who said "yes, I refer" does.

## 3. Target users & personas

### Primary: Aditi, final-year student (Goa '27)
- **Situation:** hunting for an internship or first job, mostly on her phone, and has used the map's tracker.
- **Goal:** for a shortlisted company, find one BITSian there who refers for her kind of role, and ask well.
- **Pain:** cold messages go unanswered, and she doesn't know who is approachable.
- **Job to be done:** "When I've shortlisted a company, help me reach a BITSian there who is willing to refer me, so my application gets seen."

### Secondary: Karthik, alum at a Series B startup (Pilani '15)
- **Situation:** happy to refer two or three good juniors a month, but gets 20 vague DMs.
- **Goal:** get requests in one place with the role and resume, set limits, decline politely and quickly.
- **Job to be done:** "When a junior asks for a referral, let me judge it in a minute and say yes or no without guilt."

### Tertiary: Rahul, founder on the map (Hyderabad '10)
- **Goal:** claim the company page, add open roles, and invite BITSians on the team.
- **Value to us:** one founder can bring their whole BITSian team onto the network.

### Not served in this phase
Recruiters and non-BITSians: they can browse public company pages but not the network. Parents and press: no access to people data.

> Before moving on: each persona has a part to play. Aditi asks, Karthik answers, and Rahul brings people in. Acquisition (§5A) has to reach Karthik and Rahul, not just Aditi.

## 4. Strategic context

- **Why now:**
  - The map, tracker and light redesign are merged (PR #1 and #2), so the product has a place to show people.
  - Internship season (Dec–Feb) is when students need referrals most 🔶 **Assumption**.
- **Market:** about 100,000 or more living BITS alumni and about 18,000 students 🔶 **Assumption:** confirm with BITSAA. Realistic opt-in in year one is 2,000–5,000 alumni 🔶 **Assumption:** about 2–5% of reachable alumni.
- **Alternatives:**

  | Alternative | Weakness |
  |---|---|
  | LinkedIn search | Can't filter "BITS + this company + will refer", and the messages are cold |
  | BITSAA directory | Not tied to companies or jobs 🔵 **Open Question:** what does it hold, and could we partner? |
  | Batch WhatsApp groups | Unsearchable, and limited to your own batch |
  | Paid referral marketplaces | Generic, nothing BITS-specific |

- **Strategic bet:** a consented, BITS-only network tied to a map of companies is hard to copy, because it needs both the community's trust and the map's data. Scraping would give a bigger list sooner, but it can't be launched publicly and would cost that trust.

## 5. Solution overview

### A. Acquisition: towards every BITSian, with consent

| Channel | How it works | Expected yield 🔶 |
|---|---|---|
| **1. Founders claim their company** | "Is this your company? Claim it" on all 306 company pages. A founder verifies by email at the company's domain, then invites their BITSian employees with a link | Highest: one founder brings 1–20 people |
| **2. Batch and chapter ambassadors** | One volunteer per batch, campus and BITSAA chapter shares an invite link in their WhatsApp groups. A leaderboard shows members by batch | Broadest reach |
| **3. Students invite seniors** | After saving a company, a student with no BITSian there gets "Know a BITSian at X? Invite them" (one invite per senior, with no list import) | Fills specific gaps |
| **4. Licensed-data outreach** | Coresignal (already licensed) or People Data Labs used **privately** to find likely BITSians at companies on the map. Each gets **one** invitation email with an easy opt-out, and is never shown on the site unless they join. Suppression list is kept forever | Targeted, so it needs care: see §9 |
| **5. Official partnerships** | BITSAA, the placement units and alumni relations at all four campuses: a sign-up link in alumni newsletters, and possibly verified alumni email 🔵 **Open Question** | Credibility and verification |
| **6. Self-serve sign-up** | "Join the BITSian Network" in the rail and on the hero | Baseline |

**Verification (who counts as a BITSian):**
1. A BITS email address (student domains per campus, and alumni addresses if BITS issues them 🔵 **Open Question**).
2. Two verified BITSians vouch for them.
3. Manual review of proof, such as a degree certificate or LinkedIn education, by a moderator, for edge cases.

A verified badge shows which route was used. Nothing is published before verification.

### B. Profiles (what we store, and who sees it)
- **Basic details:** name, campus, batch year, degree (optional), current company (linked to the map when it matches), role and team, city.
- **Links:** LinkedIn URL and other links, optional and supplied by the user.
- **Referral settings:** an on/off switch for "Open to referrals", the roles they refer for (engineering, product, design, data, business, other), and a monthly cap (default 3).
- **Visibility, per profile:**
  - *Verified BITSians only* (default)
  - *Public on company pages*
  - *Hidden* (counted in totals only)
- **The user's own controls:** download their data, and delete their account and data at any time.

### C. On the map: a clean UI in the v4 design
- **Company detail card:** a new **People at <company>** section after Open roles.
  - "4 BITSians · 2 open to referrals" (count only for visitors who aren't signed in)
  - avatar rows with name, batch tag ("Pilani '15") and role
  - a **Request referral** button on people who are open to referrals
- **Map markers:** a small people-count badge on company chips from zoom 9, and a "Has BITSians open to referrals" filter chip.
- **Rail:** a **Network** item. Its tabs are *People* (search by company, role, batch, campus, city), *My requests* (students) and *Inbox* (referrers).
- **Profile page:** `/p/<handle>`, shown only to the audience the person chose.
- **Requests:** a short form. It asks for the role (link to the job), why this company (280 characters), and a resume link, and attaches the student's batch automatically. The referrer sees it in their Inbox and can Accept, Decline with a canned polite reason, or Ask for more. Contact details are shared only after they accept.
- **Jobs:** open roles pulled from Greenhouse, Lever and Ashby public job-board APIs, plus others where possible. They're listed in the Open roles card, and each role can be saved and tracked like a company is today.

### D. What this means technically
The site is static today. The network needs a backend: auth, a database and email.
- **Proposed:** Cloudflare Workers + D1 (SQLite) + Turnstile (bot protection) + a transactional email provider, all on the Cloudflare account that already serves the site 🔵 **Open Question:** choose the email provider.
- Public company pages stay static and fast. People data loads after sign-in, through the API.
- This is the project's first database, so `RELEASING.md` needs a migrations section and backups before launch.

> Before moving on: each acquisition channel maps to a persona. Founder claims bring Rahul, ambassadors and invites bring Karthik, and students bring the demand. Every profile is created by the person themselves, or after they accepted an invitation.

## 6. Success metrics

### Primary metric
**Accepted referral requests per month**: an answered "yes" is the outcome students care about. Baseline 0. Target 100/month by the end of internship season (Feb 2027) 🔶 **Assumption**.

### Secondary metrics
| Metric | Target (two quarters after launch) 🔶 |
|---|---|
| Verified members | 2,000, at least 60% of them alumni |
| Hiring companies on the map with at least 1 member open to referrals | 50% (31 of 61) |
| Companies claimed by a founder | 60 of 306 |
| Requests answered (accept or decline) within 7 days | 70% |
| Acceptance rate of answered requests | 30–50% (too high suggests caps are too loose or quality is unchecked) |
| Invitations from licensed data that turn into sign-ups | 8% or more |
| Job listings pulled automatically | 40 or more companies |

### Guardrails
- **Complaints and opt-outs:** fewer than 1% of invited people report spam. Every opt-out is honoured within 24 hours.
- **Takedown and erasure requests:** completed within 72 hours. Zero people published without consent.
- **Referrer load:** no member over their monthly cap. The median referrer gets 3 or fewer requests a month.
- **Map performance:** public pages stay static. Opening a company card costs no more than one API call.

## 7. User stories & requirements

### Epic hypothesis
We believe that **a consented, verified BITSian Network shown on each company of the map, with structured and capped referral requests**, will get students referred at BITSian companies more often than cold outreach. Alumni will join because requests arrive structured, capped and easy to decline. We'll know it worked when accepted referrals reach 100/month and complaints stay under 1%.

### Stories

**N1 · Join and verify**
As Karthik, I want to join with my BITS email (or get vouched for), so that students know I'm really a BITSian.
- [ ] Sign-up with a BITS email, Google or LinkedIn sign-in (identity only), plus Turnstile.
- [ ] BITS email domains verify instantly. Otherwise two vouches or moderator review, with the status shown on the profile.
- [ ] Nothing is visible to others until verified.

**N2 · Profile and privacy**
As Karthik, I want to choose who sees my profile and whether I take referrals, so that I control my inbox.
- [ ] Visibility options: Verified BITSians only (default), Public on company pages, or Hidden.
- [ ] Referral on/off, role types and monthly cap (default 3), plus a holiday toggle.
- [ ] Company typed or picked from the map's list. It links to the map company when they match, otherwise it's queued for review as a possible new company.
- [ ] Data export (JSON) and account deletion, which removes the person's data in under 72 hours, backups included 🔵 **Open Question:** how long are backups kept?

**N3 · People on the company card**
As Aditi, I want to see the BITSians at a company and who is open to referrals, so that I know whom to ask.
- [ ] Visitors who aren't signed in see counts only. Verified members see the list, as each person's visibility setting allows.
- [ ] Members who are open to referrals sort first, then by batch closeness to the viewer.
- [ ] A "Has BITSians open to referrals" filter on the map and list.

**N4 · Request a referral**
As Aditi, I want to send a clear request with my resume and target role, so that the alum can decide quickly.
- [ ] Required: target role or job link, a reason (280 characters), and a resume link. The student's batch is attached automatically.
- [ ] A student can have at most 5 open requests in total, and 1 per company.
- [ ] Shown in *My requests* as Sent, Accepted, Declined or Expired (after 14 days with no answer).
- [ ] An accepted request moves the company to Applied in the existing tracker, with a note.

**N5 · Referrer inbox**
As Karthik, I want to accept, decline or ask for more in one tap, so that requests don't pile up.
- [ ] Inbox with the request details. Accept shares contact details both ways. Decline offers canned polite reasons.
- [ ] An email digest (daily or weekly, the user's choice), not one email per request.
- [ ] Once the cap is reached, the profile shows "Not taking requests this month".

**N6 · Founders claim their company**
As Rahul, I want to claim my company page and invite my BITSian team, so that students find us and we find BITSian hires.
- [ ] Claim by email at the company domain, or by moderator review.
- [ ] The founder can correct company facts, add the careers platform slug for job imports, and get an invite link for employees.
- [ ] A "Claimed by founder" badge on the company card.

**N7 · Invitations from licensed data** *(too big: split before building)*
- N7a: Matching job. Licensed records matched to companies on the map, stored only in the private database and never shown in the UI.
- N7b: One invitation email per person with a one-click opt-out. The suppression list is checked before every send.
- N7c: Sending limits (no more than 200 a day), bounce and complaint tracking, and an automatic pause above 1% complaints.
- N7d: Legal review of the email wording and the licence terms before the first send 🔵 **Open Question**.

**N8 · Real job listings**
As Aditi, I want to see a company's open roles on its card, so that I can pick the role before asking for a referral.
- [ ] A daily job pulls Greenhouse, Lever and Ashby public job boards for companies whose platform slug is known, from founders or detected on the careers page.
- [ ] Roles listed with title, team, location and a link. Each role can be saved and tracked.
- [ ] "Hiring" means at least one open role was found in the last 14 days. Otherwise the company falls back to "has a careers page".

**N9 · Safety and moderation**
- [ ] Report profile or report request. A moderator queue for verification, reports and claims.
- [ ] Automatic limits on new accounts. Repeat offenders are blocked.
- [ ] An audit log of moderator actions.

### Constraints & edge cases
- **People who change jobs:** we ask "Still at X?" every 6 months. If they don't answer within 30 days, their profile becomes Hidden.
- **Founders who are also employees elsewhere:** they can have several companies, with one marked as current.
- **Current students:** they can have profiles but appear only on internship companies, and only if they choose.
- **Minors:** none expected. The sign-up flow requires the user to confirm they are 18 or older 🔵 **Open Question:** do any first-years need special handling?

## 8. Out of scope

- **Scraping LinkedIn** or any site whose terms forbid it. **Publishing people who haven't joined**, including from licensed data.
- **In-app chat.** Accepting a request shares contact details, and conversation happens over email or LinkedIn.
- **Paid features, recruiter accounts, resume databases.**
- **A mobile app.** The responsive web app covers phones.
- **Automatic LinkedIn imports beyond sign-in** (LinkedIn's API doesn't return work or education history without partner access).
- **Endorsements or ratings of referrers or students.** They invite gaming and hurt feelings. Revisit after launch.

## 9. Dependencies & risks

### Dependencies
- Cloudflare D1, Workers and Turnstile, plus an email provider. A domain for email, so the site may need a custom domain 🔵 **Open Question**.
- A moderator rota: at least 2 volunteers and about 3 hours a week 🔶 **Assumption**.
- BITSAA or university cooperation, for newsletters and alumni email verification. Helpful, not blocking.
- Coresignal licence terms for outreach use 🔵 **Open Question**.

### Risks & mitigations
| Risk | Mitigation |
|---|---|
| **Anti-pattern: growth by scraping.** Chasing "every BITSian" with a scraped list gives big numbers but no consent, LinkedIn bans and DPDP exposure, and a public launch that destroys trust | Out of scope (§8). Licensed data is used only for one-time invitations, never shown, and guarded by suppression lists |
| **Anti-pattern: building the network before the demand.** Profiles nobody visits | Launch on companies students already save (tracker data, aggregated), and seed through founder claims at the 61 hiring companies first |
| **Request spam burns out referrers** | Caps (5 open per student, 1 per company, the referrer's monthly cap), structured requests, a digest instead of per-request emails, declines in one tap |
| **Impersonation or fake profiles** | Verification before publishing, vouching limits, reports and moderation, an audit log |
| **Privacy breach** (first database of personal data) | Collect the minimum, encrypt contact fields, restrict access by role, export and erasure, keep backups for a limited time 🔵, write a breach runbook before launch |
| **Cold start** (empty People sections) | Show "Invite a BITSian here" instead of an empty list, and run founder claims first |
| **Stale employment data** | 6-monthly "Still at X?" check, with profiles auto-hidden if unanswered |
| **The project's first backend makes releases riskier** | Extend `RELEASING.md` with database migrations (additive only), backups and rollback, and add CI before launch (the open item from the release audit) |

## 10. Open questions

- 🔵 Does BITS issue lifelong alumni email addresses on a domain we can verify against? Would BITSAA confirm members?
- 🔵 Do the Coresignal (or People Data Labs) licence terms allow one-time invitation emails?
- 🔵 Who moderates, and how fast must reports be handled?
- 🔵 Custom domain and email-sending domain for the site?
- 🔵 Which hiring platforms do the 61 hiring companies use (scan their careers pages)?
- 🔵 Should students see referrer names before signing in? The current answer is no, counts only.
- 🔶 Alumni will join for structured, capped requests. Test with 20 alumni before building N5.

## Self-assessment

- **Strongest section:** §5A and §8–9, acquisition with consent and the limits on it. They make "every possible BITSian" achievable without the legal and trust failure of scraping, and each channel names its yield and risk.
- **Weakest section:** §6 targets. There is no baseline for opt-in or referral behaviour yet, so 2,000 members and 100 accepted referrals a month are reasoned guesses.
- **Top assumptions to validate:**
  1. Alumni will opt in and answer capped, structured requests. Test: ask 20 alumni with a clickable mockup.
  2. Founders will claim pages and invite their teams. Test: email 20 founders on the map.
  3. Students prefer asking a named BITSian over applying cold. Test: 5–8 student interviews.
- **Recommended next step:**
  - **Build N8 (real job listings) now.** It needs no personal data and makes "hiring" real.
  - **Before any backend work:** run the alumni and founder tests above, and get answers on BITS email verification and the data licence.
  - **Then** run `/plan-roadmap` to sequence N1–N6 behind CI and the database runbook.
