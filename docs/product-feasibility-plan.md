# Automated Short-Video Product: Feasibility, Business Plan, Architecture, Implementation Plan

Status: draft for decision. Prices and platform rules were checked in late November 2026 from public sources and must be re-verified before any commitment.

---

## Part 1. Feasibility

### 1.1 Technical feasibility: YES

| Component | Maturity | Risk |
|---|---|---|
| Template video rendering (ffmpeg, MoviePy, Remotion) | Mature | Low |
| Voiceover (TTS), including Vietnamese | Mature via cloud; local options weaker for Vietnamese | Low to medium |
| Brief generation (LLM) | Mature | Low |
| Product understanding from images (VLM) | Good for common products; weak on fine detail, small text, and brand logos | Medium |
| QA of rendered frames (VLM) | Good for "is product visible / text readable / layout broken" checks | Medium |
| Generative AI video clips (Veo, Kling, Runway, etc.) | Improving, but expensive and inconsistent for specific products | High (keep out of MVP) |
| Publishing via official APIs | Possible, but heavily restricted (see 1.3) | High |

**Conclusion:** Template-based rendering with a cloud LLM and VLM is clearly feasible. Generative video and fully unattended posting are not needed for the MVP.

### 1.2 Market and competition: FEASIBLE BUT CROWDED

Existing AI ad/UGC video tools include Creatify, Arcads, HeyGen, and Higgsfield. Published prices vary between sources; reported starting points are roughly $15 to $40 per month, with per-clip costs of about $2 to $10 for AI-actor or generative clips. (Sources: [Higgsfield comparison](https://higgsfield.ai/blog/best-ai-ad-generators-2026), [Creatify pricing](https://creatify.ai/blog/arcads-pricing-(2026)-plans-credits-and-what-you-ll-actually-pay).)

Implication: a generic "AI product video" tool will compete on price and features against well-funded products. We need a narrower wedge.

**Candidate wedges (ranked by my recommendation):**

1. **Vietnamese and Southeast Asian marketplace sellers** (TikTok Shop, Shopee, Lazada, Facebook). Vietnamese voiceover and captions, local price and promo formats, and output tuned for these platforms. Competitors built for English-speaking markets are weaker here.
2. **Small agencies and freelancers** managing many SKUs for several clients. They need batch production and approval workflows.
3. **Privacy-sensitive sellers** who want local or private processing of product images.

### 1.3 Platform constraints (critical)

- **TikTok Content Posting API:** Until the client passes TikTok's audit, posts are restricted to private visibility, and unaudited clients can serve only up to 5 users in a 24-hour window, with those accounts private at posting time. Passing the audit does not make earlier private posts public. Audit requires a wide-audience intended use case, a user preview, editable title and hashtags, no added promotional watermarks, and explicit user consent before upload. (Source: [TikTok Content Sharing Guidelines](https://developers.tiktok.com/docs/en/content-sharing-guidelines), [bundle.social on TikTok approval](https://bundle.social/blog/tiktok-api-approval).)
- **YouTube Data API:** `videos.insert` costs 1,600 quota units. The default project allocation is 10,000 units per day, which is about six uploads per day. Higher volume requires a quota extension request from Google. (Source: [YouTube quota cost](https://developers.google.com/youtube/v3/determine_quota_cost).)
- **Meta (Instagram Reels / Facebook):** Requires a Business or Creator account and Graph API approval.

**Consequence:** Fully automated posting to TikTok at scale is not available at launch. The MVP should produce **export-ready files plus a scheduling and approval workflow**, and add direct posting only after the relevant audits pass.

### 1.4 Legal and compliance (Vietnam, to be confirmed with a lawyer)

- **AI-generated content labelling:** TikTok and YouTube require disclosure of realistic AI-generated or altered content. Build the labelling into the publish step.
- **Advertising law:** Product claims (for example "best", "cures", "guaranteed results") create legal risk. The brief agent must flag them, and a human must approve.
- **Personal data:** Product images can contain people. Voice cloning of real people needs written consent. Vietnam's personal data protection rules apply to any customer data we store.
- **Music and stock assets:** Use licensed or royalty-free sources only.
- **Business registration:** A Vietnamese company or partner is needed to invoice local customers and handle payments.

### 1.5 Unit economics (estimates, to validate in the pilot)

| Cost item per video (30 s, template-based) | Estimate |
|---|---|
| LLM brief generation | < $0.01 |
| VLM product analysis (a few images) | < $0.02 |
| VLM QA (8 sampled frames) | < $0.02 |
| TTS voiceover | < $0.05 |
| Render compute | < $0.01 |
| Storage and bandwidth | < $0.01 |
| **Total (template route)** | **about $0.10 to $0.20** |
| Optional generative B-roll clip (per clip) | $2 to $10 (avoid in MVP) |

With a template route, gross margin is very high. Revenue depends on pricing and conversion, not compute. Human review time is the largest real cost, so review tooling matters.

### 1.6 Feasibility verdict

- **Technically:** Yes, with the template-first design.
- **Commercially:** Possible only with a focused wedge (Vietnamese and SEA marketplace sellers, or agencies). A generic tool faces strong competition.
- **Platform-wise:** Publishing must start as export plus approval. Direct posting depends on TikTok audit and YouTube quota decisions outside our control.

**Go/no-go test before building the full product (2 to 3 weeks, low cost):**

1. Recruit 10 to 20 Vietnamese sellers (TikTok Shop or Shopee) and offer free video production for 4 weeks.
2. Produce videos manually with a prototype pipeline (ffmpeg templates, TTS, a cloud LLM script).
3. Measure:
   - Time saved per video vs. the sellers' current process.
   - Whether sellers post the videos (activation).
   - Views, click-through, and sales compared to their usual content.
   - Willingness to pay (ask for a paid pilot at the end).
4. **Go** if at least 5 of 10 to 20 sellers post regularly and at least 3 agree to pay.
   **No-go or pivot** if sellers don't post, don't see results, or won't pay.

---

## Part 2. Business Plan

### 2.1 Problem

Small sellers and agencies need many short product videos to stay visible on TikTok Shop, Shopee, and Reels. Filming and editing each video takes hours, or they pay freelancers. Most sellers cannot produce enough content.

### 2.2 Solution

A system that turns product images and a short brief into ready-to-post vertical videos, with Vietnamese voiceover, captions, and a quality check, and that schedules them for approval and posting.

### 2.3 Target customers

| Segment | Need | Priority |
|---|---|---|
| Solo TikTok Shop / Shopee sellers (SME) | Many videos per week at low cost | 1 (main) |
| Small video or ad agencies | Batch output for multiple clients, approval workflow | 2 |
| Brands with in-house marketing teams | Localization, brand control, compliance | 3 (later) |

### 2.4 Pricing (initial hypothesis to test)

| Plan | Price (per month) | Included |
|---|---|---|
| Starter | Around $15 to $20 | 30 videos, 1 brand, export only |
| Pro | Around $50 to $80 | 150 videos, scheduling, VLM QA, Vietnamese and English voice |
| Agency | Around $150 to $300 | 500+ videos, multiple brands, team approval roles |

Pricing must be tested in the pilot. Competitors' entry prices are roughly $15 to $40 per month, so we can match the low end and compete on language and platform fit.

### 2.5 Revenue model

- Monthly subscription by plan.
- Overage packs for extra videos.
- Later: onboarding service for agencies, and a marketplace template library.

### 2.6 Illustrative scenario (not a forecast)

Assume 200 paying Pro-equivalent customers at about $60 per month: about $12,000 monthly recurring revenue. Operating costs (cloud, APIs, storage) are small per customer, so the main costs are people (2 to 3 engineers, 1 product and operations person) and sales. Whether this is achievable depends entirely on the pilot results.

### 2.7 Go-to-market

1. **Pilot** with 10 to 20 sellers (free, in exchange for feedback and results).
2. **Community channels:** Vietnamese e-commerce seller groups, TikTok Shop creator and seller communities, and local marketing meetups.
3. **Case studies** from pilot sellers with real view and sales numbers.
4. **Partnerships** with MCNs, marketing agencies, and e-commerce service providers.

### 2.8 Competitive advantage

- Vietnamese voice and captions, and content styled for Vietnamese marketplaces.
- Lower price point suited to SME budgets.
- Option for local or private processing (VLM run on-premise).
- Integrated approval, scheduling, and compliance checks.

### 2.9 Key risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Platform API restrictions (TikTok audit, YouTube quota) | Can't auto-post at scale | Export and scheduling first; apply for audits and quota early |
| Strong competitors | Price pressure | Focus on Vietnamese market and SME workflows |
| Low-quality output | Churn | VLM QA gate, human review, template library |
| Legal claims in ads | Liability for customers and us | Claims checker, mandatory human approval |
| AI disclosure rules change | Forced redesign | Labelling as a configurable step |
| Platform algorithm changes | Views drop | Don't promise results; sell production capacity |
| Cloud VLM cost or outage | Margin or service risk | Local VLM option; provider abstraction |

### 2.10 Success metrics (first 6 months)

- Pilot: at least 5 of 10 to 20 sellers post weekly.
- Time per video under 10 minutes including review (vs. hours manually).
- Paying customers: 3 from the pilot, then 30 within 3 months of launch.
- Monthly churn under 8%.
- Gross margin above 80% on the template route.

---

## Part 3. Architecture

### 3.1 Principles

- **Template-first rendering;** generative clips are optional add-ons.
- **Agents are narrow and typed:** each agent reads and writes versioned JSON schemas.
- **Provider abstraction:** cloud or local for LLM, VLM, and TTS behind one interface.
- **Human approval gate** before any publish.
- **Official APIs only** for platforms.

### 3.2 System diagram

```
                 +-------------------+
 Seller/Agency ->|   Web app / API   |<---- Approval UI, dashboard
                 | (FastAPI + React) |
                 +---------+---------+
                           |
                   +-------v--------+
                   |  Postgres      |  products, briefs, jobs, posts, metrics
                   +-------+--------+
                           |
                   +-------v--------+
                   |  Job queue     |  (Redis + Celery / RQ)
                   +--+----+----+---+
                      |    |    |
        +-------------+    |    +-------------------+
        |                  |                        |
+-------v--------+  +------v---------+      +-------v--------+
| Brief Agent    |  | Production     |      | Publish Agent  |
| - VLM: product |  | Agent          |      | - TikTok adapter|
|   analysis     |  | - TTS          |      | - YouTube adapter|
| - LLM: script, |  | - Subtitles    |      | - Meta adapter |
|   shot list,   |  | - Render       |      | - Scheduler    |
|   claims check |  |   (ffmpeg /    |      | - AI label     |
+-------+--------+  |   Remotion)    |      +-------+--------+
        |           | - VLM QA       |              |
        |           +------+---------+              |
        |                  |                        |
+-------v------------------v------------------------v--------+
|  Model gateway: cloud (Claude / GPT / Gemini) or local     |
|  (vLLM serving Qwen-VL / InternVL; local TTS)              |
+------------------------------------------------------------+
        |
+-------v--------+   +---------------+   +-----------------+
| Object storage |   | Secrets vault |   | Metrics & logs  |
| (S3 / MinIO)   |   | (OAuth tokens)|   | (Prometheus,    |
| images, videos |   |               |   |  Grafana/Sentry)|
+----------------+   +---------------+   +-----------------+
```

### 3.3 Components

| Component | Responsibility | Tech (suggested) |
|---|---|---|
| Web app / API | Product upload, brief review, approvals, schedule, dashboard | FastAPI, React or Next.js |
| Database | Products, briefs (versioned), jobs, renders, posts, metrics | PostgreSQL |
| Job queue | Run long steps asynchronously, retry failures | Redis + Celery (or Temporal for later complexity) |
| Brief Agent | Analyze product images (VLM), write brief (LLM), check claims | Python, Pydantic schemas |
| Production Agent | TTS, subtitles, music, template render, frame sampling for QA | ffmpeg, MoviePy or Remotion, Docker workers |
| QA module | VLM checks on sampled frames: product visible, text in safe area, no artifacts | Same VLM gateway |
| Publish Agent | Platform adapters, scheduling, AI label, post IDs and status | Platform SDKs / HTTP APIs |
| Model gateway | Single interface for cloud and local models, cost tracking | LiteLLM or custom adapter |
| Local model server (optional) | Private VLM for QA or analysis | vLLM, 1 GPU with 24 GB VRAM or more for a 7B-class model |
| Storage | Source images, generated videos, exports | S3-compatible (MinIO for self-host) |
| Observability | Job status, cost per video, error alerts | OpenTelemetry, Sentry, Grafana |

### 3.4 Data contract: `brief.json` (v1, sketch)

```json
{
  "brief_id": "uuid",
  "version": 1,
  "product": { "name": "", "category": "", "features": [], "price": null, "source_images": [] },
  "target": { "market": "VN", "language": "vi", "audience": "" },
  "platform": { "name": "tiktok_shop", "aspect": "9:16", "max_seconds": 30 },
  "hook": "",
  "beats": [ { "t": "0-3s", "visual": "", "voiceover": "", "on_screen_text": "" } ],
  "cta": "",
  "music_mood": "",
  "claims_check": { "risky_claims": [], "status": "needs_review" },
  "ai_disclosure_required": true,
  "approval": { "status": "pending", "by": null }
}
```

### 3.5 Workflow states

`draft brief` -> `brief approved` -> `assets ready` -> `rendered` -> `QA passed` (or `QA failed` -> re-render, max 2 retries) -> `final approved` -> `exported` or `scheduled` -> `published` -> `metrics collected`.

Every state change is stored in Postgres so jobs can be resumed after failures.

### 3.6 Deployment options

- **SaaS (default):** cloud-hosted app, cloud models, S3 storage, managed Postgres and Redis.
- **Private / on-premise (agency or privacy tier):** same containers on a customer server with a local VLM on a GPU.
- **Hybrid (recommended for launch):** cloud LLM for briefs, local or cloud VLM for QA depending on volume and customer requirement.

### 3.7 Security

- OAuth tokens for platforms stored in a secrets vault, never in code or logs.
- Per-tenant data isolation in the database and storage paths.
- Uploaded images scanned for file type and size; people in images flagged for consent.
- Audit log for every approval and publish action.

---

## Part 4. Implementation Plan

Assumes a team of 2 to 3 engineers, 1 product and operations person, and part-time legal review. Timelines are estimates.

### Phase 0: Feasibility (weeks 1 to 3)

- Build a manual prototype pipeline: cloud LLM script, template render (ffmpeg), Vietnamese TTS, captions.
- Recruit 10 to 20 pilot sellers; run the 4-week free pilot described in Part 1.6.
- Start the TikTok Content Posting API audit application and the YouTube quota extension request now, since they take time and don't block the pilot.
- Lawyer review of AI labelling, advertising claims, and personal data handling.
- **Exit criteria:** go/no-go decision against the Part 1.6 thresholds.

### Phase 1: MVP (weeks 4 to 11)

- Product upload and brief creation (Brief Agent with cloud VLM and LLM).
- Template library (5 to 10 templates for common categories).
- Production Agent: TTS, captions, music, render workers.
- QA module (cloud VLM, frame sampling).
- Approval UI: review brief, preview video, approve, edit.
- Export: MP4 with captions, title, and hashtag text for copy-paste.
- Basic dashboard: videos created, status, cost per video.
- **Exit criteria:** 10 pilot sellers produce at least 50 videos with under 10 minutes of human review per video.

### Phase 2: Publishing and scheduling (weeks 12 to 17)

- Scheduling calendar and queue.
- YouTube Shorts adapter (after quota extension is granted).
- Meta Reels adapter (for Business or Creator accounts).
- TikTok adapter: private posting first; switch to public only after audit passes.
- AI disclosure label added automatically where required.
- Post status and metrics collection (views, clicks) from platform APIs.
- **Exit criteria:** paid pilot (3+ customers) running scheduled posts for 4 weeks without manual uploads.

### Phase 3: Quality and scale (weeks 18 to 26)

- Local VLM option (vLLM on a GPU); benchmark quality and cost vs cloud.
- Metrics feedback loop: Brief Agent uses past performance to suggest hooks and formats.
- Multi-brand and team roles for agencies.
- Billing and subscription management (payment provider suitable for Vietnam).
- Template marketplace and A/B variants of the same product.
- Generative B-roll as an optional paid add-on, if demand justifies the cost.

### Phase 4: Growth

- Marketplace integrations (Shopee and Lazada product feeds).
- Additional languages (Thai, Indonesian) using the same pipeline.
- Enterprise or private deployment tier.

### 4.1 Milestones summary

| Milestone | Target week | Decision |
|---|---|---|
| Pilot results | Week 3 to 4 | Go / pivot / stop |
| MVP with pilot sellers | Week 11 | Continue to publishing |
| Paid pilot | Week 17 | Fund scaling |
| Local VLM benchmark | Week 22 | Offer private tier or not |

### 4.2 Team and tooling

- Backend: Python (FastAPI, Celery, Pydantic)
- Frontend: React or Next.js
- Infrastructure: Docker, a managed Postgres and Redis, S3-compatible storage, one GPU server if local models are used
- Quality: automated tests on brief schemas and render output; a golden set of 20 products to check QA stability

### 4.3 Budget (rough, to refine)

- Development team: largest cost (salaries or contractors for 6 months)
- Cloud API usage: low at pilot scale (estimated under a few hundred dollars per month for 20 sellers using the template route)
- GPU server for local VLM (optional): one-time or monthly lease, roughly the cost of one mid-range GPU instance
- Legal review and company setup in Vietnam
- Marketing and pilot incentives

---

## Part 5. Decisions needed before building

1. **Target segment:** Vietnamese TikTok Shop and Shopee sellers first, or agencies first?
2. **Launch model:** export-and-schedule (safer, recommended) or direct posting from day one (depends on TikTok audit timing)?
3. **VLM strategy:** cloud at launch with a local option later, or local from the start (requires GPU budget)?
4. **Team and budget:** how many engineers and for how many months?
5. **Legal entity:** Vietnamese company or partner for billing?

## Next step

Run the Phase 0 pilot. The pilot will show whether sellers actually post and pay, which is the main open question. Platform audit requests should be submitted now, in parallel.
