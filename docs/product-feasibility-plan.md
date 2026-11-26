# Short Video Studio: Feasibility, Business Plan, Architecture, Implementation Plan

Revision 2 (November 2026). Revision 1 assumed template-only videos. This revision adds story-driven scenes and text-to-video clips, and reprices the business around their real cost. Prices come from public sources checked in November 2026 and must be re-verified before any commitment.

## Summary

- **What exists:** a working MVP (`app/`) that turns a topic into a 9:16 video. It writes a story brief (problem, idea, action, result, call to action), draws a cartoon presenter whose pose and prop match each line, adds a voiceover, and adds a slow camera move. Cost per video is about $0.01 to $0.05.
- **What is missing:** generated video clips (text-to-video), a VLM that checks each clip against the narration, and proper voice and art quality.
- **Business verdict:** viable as a low-cost story-video tool for faceless business and education channels, especially Vietnamese-language ones. It is not viable as a generative-video reseller. Generated clips cost $1 to $8 per 20-second video, which breaks low-price subscriptions unless they are priced by credit.
- **Recommended path:** make the illustrated story video the default product. Offer generated clips as a metered add-on, priced above cost. Validate with your own channel first, then with a small pilot.

---

## Part 1. Feasibility

### 1.1 What is technically proven

| Capability | Status | Notes |
|---|---|---|
| Story brief (rule-based fallback and LLM path) | Built, tested | Brief schema includes story arc, pose and prop per scene |
| Illustrated presenter with poses and props | Built | 6 poses, 10 props; drawn with Pillow |
| Vietnamese text rendering | Tested | Diacritics display correctly with DejaVu Sans |
| Voiceover (gTTS) | Built, tested | Free, unofficial Google service; needs internet |
| Camera move (zoompan) per scene | Built | Slow zoom; no transitions yet |
| Technical QA (ffprobe) | Built, tested | Checks shape, length, audio, size |
| Text-to-video clips | Not built | Adapter needed; no GPU or video API key in the current environment |
| VLM check of clips against narration | Not built | Design in Part 3 |

### 1.2 Generated video cost (the key input)

Hosted text-to-video prices from the November 2026 comparison sources. They vary by resolution, audio, and source, so verify them on each vendor's page:

| Option | Reported price | 20-second video (approx.) |
|---|---|---|
| Veo 3.1 Lite, 720p | about $0.03 to $0.05 per second | $0.60 to $1.00 |
| Kling 3.0, 1080p, no audio | about $0.11 per second | about $2.20 |
| Kling O3 Standard (via Runway) | about $0.13 per second | about $2.60 |
| Veo 3.1 with audio (via Runway) | about $0.40 per second | about $8.00 |
| Open model (Wan) self-hosted | GPU about $1.89 per hour on an H100 | unknown; depends on generation time per second of video |

Sources: [Runway and vendor listings aggregated by ModelsLab](https://modelslab.com/blog/api/veo-3-1-vs-kling-3-sora-2-ai-video-api-cost-2026), [aggregated 2026 pricing overview](https://invideo.io/blog/ai-video-model-pricing), [Atlas Cloud cost-per-second comparison](https://www.atlascloud.ai/blog/case-studies/Top-5-ai-video-apis-compared-speed-latency-and-cost-per-second-2026).

**Conclusion:** A 20-second generated video costs about $1 to $8 in model fees, depending on model and audio. That is 100 to 500 times the illustrated route. Self-hosting an open model could lower the cost at high volume, but I have not measured generation time, so that case is unproven.

### 1.3 Unit economics per 20-second video

| Route | Model cost | Platform cost | Total (approx.) |
|---|---|---|---|
| Illustrated story (default) | LLM brief $0.00 to $0.02 | Render about $0.0001; voice free (gTTS) or a few cents on a paid TTS | $0.01 to $0.05 |
| Illustrated + VLM check (10 frames) | as above + about $0.02 | as above | $0.03 to $0.07 |
| Generated clips (4 to 5 scenes), 720p, no audio | $0.60 to $2.60 | as above | $0.65 to $2.70 |
| Generated clips with audio | $6 to $8 | as above | about $6 to $8.10 |

### 1.4 Platform and legal constraints (unchanged, still critical)

- **TikTok Content Posting API:** unaudited clients can only post privately, with a 5-user cap per 24 hours. Passing the audit lifts the restriction for new posts only. ([TikTok guidelines](https://developers.tiktok.com/docs/en/content-sharing-guidelines))
- **YouTube Data API:** an upload costs 1,600 quota units against a default of 10,000 per day, about six uploads. More requires a quota extension. ([YouTube quota](https://developers.google.com/youtube/v3/determine_quota_cost))
- **AI disclosure:** TikTok and YouTube require labelling of realistic AI-generated content. The app already adds a disclosure line to post text.
- **Advertising claims:** the app flags words such as "best" and "guaranteed". Vietnam's advertising law applies to product ads, so a human must still approve claims.
- **Voice:** do not clone real people's voices without written consent.
- **Music:** use licensed or royalty-free audio. The app does not add music yet.

### 1.5 Market and competition

Many AI product-video and UGC ad tools already exist, including Creatify, Arcads, HeyGen, and Higgsfield, with entry prices around $15 to $40 per month ([Higgsfield comparison](https://higgsfield.ai/blog/best-ai-ad-generators-2026)). These tools target e-commerce ads with AI actors.

Our angle is different in three ways:
1. **Story-first educational and business content**, not ad creatives.
2. **A consistent cartoon presenter** that costs almost nothing per video.
3. **Vietnamese voice and on-screen text** from the start.

We are not yet better than these tools at visual quality, and the illustrated style is basic. That is the main product risk.

### 1.6 Monetization reality (creator side)

Earnings from platforms are low, especially for Vietnamese audiences. Earlier research put Vietnam YouTube Shorts RPM around $0.03 to $0.10 per 1,000 views, and TikTok creator rates are similar or lower ([vidIQ](https://vidiq.com/blog/post/youtube-shorts-monetization/), [Dynamoi Vietnam data](https://dynamoi.com/data/youtube-adsense-rpm/vn)). A faceless channel usually earns more from brand deals, affiliate links, and its own product or course than from platform payouts. Customers buying this tool will need to make money from that route, so our pricing should not depend on platform income.

### 1.7 Feasibility verdict

- **Technically:** the illustrated story route works and is cheap. Generated clips work through a provider adapter, but cost is the constraint.
- **Commercially:** viable only if (a) the default is the cheap illustrated route and (b) generated clips are sold as metered credits priced above cost. Flat low-price plans with unlimited generated clips lose money.
- **Platform-wise:** publishing stays export-plus-approval until audits are granted.

**Go/no-go pilot (3 to 4 weeks):**
1. Make 20 to 30 story videos for your own channel and 10 pilot creators using the illustrated route.
2. Generate 10 test videos with one hosted text-to-video model, and measure cost, time, and whether the clips match the narration (checked by hand first).
3. Measure: time saved per video, posting rate, views versus the creators' usual content, and willingness to pay for credits.
4. **Go** if at least 5 pilot creators post weekly and at least 3 pay. **Pivot** toward faceless-channel services if they don't.

---

## Part 2. Business Plan

### 2.1 Problem

Creators who make faceless business and education channels need many short videos with a story, a presenter, and narration in their own language. Animation and editing are slow and costly, and generic AI video tools often don't keep a presenter consistent or match the narration.

### 2.2 Solution

A studio that turns a topic into a story video: a consistent cartoon presenter, scenes that match the narration, a voiceover, and platform-ready output with caption and hashtags. Creators choose the default illustrated style, or add generated clips when they need motion.

### 2.3 Target customers

| Segment | Need | Priority |
|---|---|---|
| Vietnamese faceless business and education channel owners | Story videos at low cost, Vietnamese voice | 1 (main) |
| Small training or course creators | Short lessons with a presenter | 2 |
| Marketing agencies with many small clients | Batch production, approvals | 3 (later) |

### 2.4 Pricing (hypothesis to test)

The illustrated route is cheap, so it can be included generously. Generated clips are metered at about 2 to 3 times their model cost.

| Plan | Monthly price | Included | Credit price |
|---|---|---|---|
| Starter | $12 to $19 | 30 illustrated story videos, Vietnamese and English voice | Generated seconds: about $0.25 to $0.40 per second |
| Pro | $39 to $59 | 150 illustrated videos, scheduling and approval, VLM check | Generated seconds: about $0.20 to $0.30 per second (volume discount) |
| Studio (agencies) | $149 to $299 | 500+ videos, multiple brands, team roles | Negotiated |

Check: a 20-second video with a silent model at about $0.10 per second costs us $2. Charged at $0.25 per second, the user pays $5, leaving about $3 of margin. With an audio model at about $0.40 per second, the same video costs us $8, which is more than the $5 charge at $0.25 per second, so the margin is negative. The default offer must therefore exclude audio-generating models, or charge more for them.

### 2.5 Revenue model

- Monthly subscriptions by plan.
- Metered credits for generated seconds, billed at cost plus a margin.
- Later: template packs, a character library, and onboarding for agencies.

### 2.6 Illustrative scenario (not a forecast)

If 200 customers pay an average of $25 per month, that is $5,000 monthly recurring revenue. Hosting, the LLM, and TTS cost well under $1 per customer per month on the illustrated route, and generated clips add cost only when customers use them. The main costs are people (2 engineers and a part-time product and support person) and sales.

### 2.7 Go-to-market

1. Make your own channel the first case study, with real views and watch-time numbers.
2. Pilot with 10 Vietnamese creators (free, in exchange for feedback and results).
3. Join creator communities and business or education groups.
4. Offer a credit bundle for users who want generated motion.

### 2.8 Competitive advantage (honest)

- Story structure and a consistent presenter, not just ad templates.
- Low cost per video on the default route.
- Vietnamese voice and text from the start.
- Simple self-hosting option for privacy later.

We do not yet have an advantage in visual quality. Improving the art is a priority.

### 2.9 Key risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Generated clips cost too much | Negative margin | Metered credits; default to illustrated; silent models only |
| Illustrated style looks basic | Low retention | Improve art; add a character library; test with real viewers |
| Better-funded AI video tools | Price pressure | Focus on story and Vietnamese; keep prices low |
| Low creator income from platforms | Weak willingness to pay | Price on production time saved, not platform earnings |
| Platform API limits | No auto-posting at scale | Export and approval first |
| AI disclosure and claims rules | Account or legal risk | Automatic disclosure; claims check; human approval |
| VLM cannot judge clips reliably | Wrong clips pass QA | Start with human review; benchmark the VLM on labeled clips |

### 2.10 Success metrics (first 6 months)

- Your own channel: 30 videos published, measured views and watch time per video against your previous content.
- Pilot: 5 of 10 creators post weekly; 3 pay for credits or a plan.
- Time per video under 15 minutes including review.
- Gross margin above 70% on the illustrated route, and above 30% on generated credits.

---

## Part 3. Architecture

### 3.1 Principles

- **Default to the cheap route:** the illustrated story video is the baseline; generated clips are optional.
- **Typed contracts between steps:** the brief schema is the only interface between the brief step and the render step.
- **Provider adapters:** LLM, VLM, TTS, and video generator each sit behind one interface.
- **Human approval before publishing.**
- **Official APIs only** for platforms.

### 3.2 Pipeline (current and planned)

```
Topic / product
      |
      v
[Brief step]  story arc, scenes, pose and prop per scene      (LLM or rule-based)  BUILT
      |
      v
[Visual step]
   route A: illustrated scene (Pillow)                          BUILT
   route B: generated clip (text-to-video, image-to-video       PLANNED
            with the presenter image as the starting frame)
      |
      v
[Check step]  VLM samples frames, compares them with narration  PLANNED
      |  fail -> regenerate that scene (max 2 retries)
      v
[Assemble]  clips in order, camera move, voiceover, QA (ffprobe) BUILT (route A)
      |
      v
[Approve and export]  caption, hashtags, AI disclosure          BUILT (export only)
      |
      v
[Publish]  platform adapters after audits                       PLANNED
```

### 3.3 Components

| Component | Responsibility | Current state |
|---|---|---|
| `app/brief.py` | Story brief, LLM prompt, claims check | Built; LLM path not yet run with a live key |
| `app/illustrate.py` | Presenter poses and props | Built; 6 poses, 10 props |
| `app/render.py` | Scene images, camera move, voice, MP4 | Built |
| `app/qa.py` | Technical checks | Built |
| `app/main.py` | API and approval flow | Built |
| `static/index.html` | Single-page UI | Built; no story-specific controls yet |
| Video adapter (`app/videogen.py`) | Text-to-video or image-to-video provider | Planned |
| VLM check (`app/vlm_check.py`) | Frame-versus-narration check | Planned |
| Credit ledger | Metering generated seconds | Planned |

### 3.4 Data contract: brief (v2)

Each scene now carries a visual spec:

```json
{
  "story": "problem_idea_action_result",
  "hook": "Want to start a business?",
  "beats": [
    {
      "on_screen": "Want to start a business?",
      "voiceover": "Want to start your own business? Here are three simple steps.",
      "visual": { "pose": "worried", "prop": "question" }
    }
  ],
  "cta": "Follow for more business tips!",
  "character": true,
  "ai_disclosure": true
}
```

Allowed poses: idle, thinking, pointing, happy, worried, celebrate. Allowed props: none, lightbulb, chart_up, checklist, coins, phone, question, cart, clock, customer, trophy. Unknown values fall back to idle and none.

### 3.5 Text-to-video route (planned design)

- **Input per scene:** the narration line, the visual prompt from the brief, and the presenter reference image.
- **Model:** a hosted image-to-video model, with the presenter image as the starting frame to keep the character consistent. Silent output by default.
- **Length:** 4 to 6 seconds per clip, joined in scene order, with the voiceover placed over the top.
- **Fallback:** if a clip fails the check or the call fails, keep the illustrated scene for that beat.

### 3.6 VLM check (planned design)

- Sample 3 to 5 frames per clip.
- Ask the VLM: does the frame show the pose and prop named in the brief, is text readable, and is anything broken?
- Output a pass or fail with a reason. Failed clips are regenerated, up to two times, then replaced by the illustrated scene.
- Benchmark first: label 100 clips by hand and measure agreement before relying on it.

### 3.7 Deployment

- **Default:** one small cloud server running the app, object storage for videos, and cloud LLM and TTS calls.
- **Privacy tier (later):** the same containers on a customer machine, with a local VLM on a GPU.
- **Cost controls:** generated clips require a credit balance, and each generation is logged with its model cost.

---

## Part 4. Implementation Plan

Team assumption: 2 engineers part-time, and you as product owner and first customer.

### Phase 0: Done (current)

- MVP app: brief, illustrated story scenes, voice, camera move, QA, post text, web UI.
- Tests: 9 passing.
- Cost per illustrated video measured at about 6 seconds of render time on a small machine.

### Phase 1: Own-channel production (weeks 1 to 3)

- Produce 20 story videos for your channel; record watch time and retention.
- Improve the presenter art: more poses, better hands, and a second character option.
- Replace gTTS with a paid voice provider for quality, or keep it for testing only.
- Add the optional music bed from licensed sources.
- **Exit:** a measured comparison of your channel's results before and after.

### Phase 2: Generated clips (weeks 3 to 6)

- Build `app/videogen.py` with one hosted image-to-video provider and silent output.
- Add a cost log per clip and a per-project spending cap.
- Hand-check 50 clips for narration match before automating the check.
- **Exit:** clips cost within the planned range, and at least 70% pass hand review.

### Phase 3: VLM check and retries (weeks 6 to 9)

- Build `app/vlm_check.py` with frame sampling and the pass/fail prompt.
- Benchmark against the hand-labeled clips; target agreement of 85% or better.
- Automatic retry and fallback to the illustrated scene.
- **Exit:** the VLM check catches the failures you found by hand.

### Phase 4: Pilot and billing (weeks 9 to 14)

- Onboard 10 creators; add accounts, plans, and a credit ledger.
- Payment provider suitable for Vietnam.
- Publishing: export and scheduling only, with direct posting after audits.
- **Exit:** 3 paying creators, and a go or pivot decision on the business.

### Phase 5: Scale (later, only after Phase 4 passes)

- Local VLM and self-hosted open video model, if volume justifies a GPU.
- Character library and template packs.
- Agency tier.

### 4.1 Milestones

| Milestone | Target | Decision |
|---|---|---|
| Own-channel results | Week 3 | Continue the illustrated product or stop |
| Generated clip cost and quality | Week 6 | Keep or drop the generated route |
| VLM check accuracy | Week 9 | Automate checks or keep human review |
| Paying creators | Week 14 | Fund scaling or pivot |

---

## Part 5. Decisions needed

1. **Default route:** illustrated story video as the default, with generated clips as a paid add-on. Recommended.
2. **Generated clips:** silent model only, unless you accept the audio cost of about $8 per 20-second video.
3. **Voice:** keep gTTS for testing, or pay for a better provider now?
4. **Target first:** your own channel, then Vietnamese creators. Or agencies first?
5. **Budget for Phase 2:** the hosted video model cost per test run, if you want the generated route tested.

## Next step

Finish the story-scene commit (blocked by permission at the moment), then produce 5 videos for your own channel on the illustrated route. Measure them against your previous content. That result decides whether generated clips are worth building.

---

## Revision history

- **Revision 1:** feasibility, business plan, architecture, and implementation plan. Template-based videos only.
- **Revision 2:** story scenes with presenter poses and props, camera move, text-to-video cost analysis, metered credit pricing, VLM check design, and a revised phased plan.
