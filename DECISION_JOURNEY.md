# How We Arrived at Malaika — Decision Journey

> **Purpose**: Preserves the full strategic thinking process so any future session has complete context on WHY we chose this direction, what we explored, what we rejected, and the evidence behind every decision.
>
> **Related files**:
> - [RESEARCH.md](./RESEARCH.md) — Full competition analysis, winner patterns, global problems data, Google strategy alignment
> - [MALAIKA_PROPOSAL.md](./MALAIKA_PROPOSAL.md) — The final idea proposal with technical architecture, video script, and sprint plan
> - Geotab reference: [geotab-hackathon/CLAUDE.md](./geotab-hackathon/CLAUDE.md) — How we structured our winning Geotab project
> - Geotab reference: [geotab-hackathon/COMPETITION.md](./geotab-hackathon/COMPETITION.md) — Geotab competition rules and strategy

---

## Phase 1: Understanding the Competition

### What we learned
- **$200K prize pool** — 8x larger than Geotab ($25K). Stakes are higher.
- **Judging is 70% storytelling + impact, 30% tech** — fundamentally different from a typical ML competition. Video is "the most important part of your submission."
- **Can win multiple tracks** — Main ($50K) + Impact ($10K) + Special Tech ($10K) = $70K max.
- **Only 53 submissions from 6,196 entrants** — massive drop-off. Just finishing puts us in the top tier.
- **Gemma 4 must be central** — not a wrapper, not a side piece.

### Key insight
The Geotab hackathon was about building the best PRODUCT. This hackathon is about telling the best STORY backed by real tech. We need to optimize for the video first, then ensure the tech is genuinely impressive.

**Source**: Competition page analysis — see [RESEARCH.md](./RESEARCH.md) sections 1-4.

---

## Phase 2: Studying Previous Winners

### Gemma 3n Impact Challenge ($150K, 600+ submissions, 8 winners)

We analyzed every confirmed winner:

| Winner | Domain | Key Pattern |
|--------|--------|-------------|
| Gemma Vision | Blindness | Real user (developer's blind brother), offline, camera + voice |
| Vite Vere | Cognitive disability | Offline, images → simple instructions, won Google AI Edge prize |
| Dream Assistant | Speech impairment | Fine-tuned on ONE person's speech (Unsloth) |
| LENTERA | Education | Offline microserver WiFi hub, used Ollama |
| Sixth Sense | Security | Gemma + YOLO-NAS combined |
| 3VA | Cerebral palsy | Pictograms → language for ONE user, Apple MLX |

### Patterns that won
1. Every winner had a **REAL person** — not abstract demographics
2. **Offline-first** was non-negotiable
3. **Accessibility dominated** — 4 of 6+ winners
4. **Multimodal** — images, audio, video, not just text
5. **Personalized fine-tuning** showed technical depth
6. **Emotionally resonant videos** tied to specific people's lives

### What this told us
The judges (Google PMs) reward projects that prove Gemma can change REAL LIVES, not just demonstrate technical capability. One person's story beats a million users' statistics.

**Source**: See [RESEARCH.md](./RESEARCH.md) section 5 and [memory: project_gemma3n_winner_patterns.md].

---

## Phase 3: Understanding Google's Strategic Intent

### Why Google released Gemma 4 as open source
- Democratize AI before the "AI divide" forms
- Enable apps where Google Cloud doesn't reach (offline, rural, developing world)
- Apache 2.0 license to remove adoption friction
- Sundar Pichai: *"We have the chance to democratize access from the start"*

### Google's social good funding tells us what they care about
- $120M — Global AI Opportunity Fund
- $30M — AI for Government Innovation
- $30M — Generative AI Accelerator
- $25M — AI for Global Goals
- $6B total committed (Google.org 2025)
- **Health AI is priority #1** — MedGemma, ClinicDX in sub-Saharan Africa, MedGemma Impact Challenge

### Mark's key insight
> *"If you can combine as many Google strengths together in one Open Source model, that would be the killer app."*

Google's strengths: Vision + Voice + Translate + Function Calling + On-device + Health AI

**Source**: See [RESEARCH.md](./RESEARCH.md) section 6 and [memory: project_google_strategy_alignment.md].

---

## Phase 4: Strategic Blog Analysis

### Sudha Rani Maddala's expert guide ([Medium post](https://sudhamsr.medium.com/the-gemma-4-good-hackathon-aef927f17ef1))

#### Red flags — ideas to AVOID
- Generic AI tutor
- Generic AI doctor chatbot
- Mental health chatbot
- Vague climate assistant
- "Agentic" app without clear user pain point

> **Test**: If describable in one sentence and 500 others will build it — it's a warning sign.

#### What strong submissions look like
- Solves **one specific workflow** (not ten)
- Targets **one clear user** (not "everyone")
- Functions **end-to-end** (input → model → tools → output → action)
- Uses **Gemma 4 meaningfully** (not generic chatbot layer)

This blog was critical in killing several of our ideas and sharpening our criteria.

**Source**: See [RESEARCH.md](./RESEARCH.md) section 12.

---

## Phase 5: Ideas We Explored and Why We Rejected Them

### Idea 1: "FarmGuard" — AI Agronomist
- **What**: Phone camera identifies crop disease, recommends treatment offline
- **Why it was promising**: $220B/year crop losses, 570M smallholder farms, combines vision + audio + translation
- **Why we REJECTED it**: FarmWise and AgriGemma **already exist in the competition** doing the exact same thing. No longer unique.
- **Decision**: KILLED — competition overlap

### Idea 2: "MamaAI" — Maternal Health Guardian
- **What**: Pregnancy tracking, danger sign detection for community health workers
- **Why it was promising**: 260,000 preventable maternal deaths/year, devastating statistics
- **Why we deferred**: Strong concept but VillageDoc already in competition (health assistant space). Medical liability framing complex. Narrower than what we landed on.
- **Decision**: DEFERRED — folded maternal health into broader child survival approach

### Idea 3: "ReadAloud" — AI Literacy Tutor
- **What**: Child reads aloud, AI listens, assesses, provides feedback offline
- **Why it was promising**: 70% of children in LMICs can't read, 617M below proficiency
- **Why we REJECTED it**: Blog explicitly flags "generic AI tutor" as red flag. LENTERA already won education in Gemma 3n. Multiple education notebooks in current competition. Mark noted: "Education using Gemini is already a Google product."
- **Decision**: KILLED — oversaturated, risk of being seen as generic

### Idea 4: "SkinScan" — Dermatological AI
- **What**: Phone-based skin condition screening fine-tuned with Unsloth
- **Why it was promising**: 1.9B affected, visual AI perfect fit, Mark mentioned it
- **Why we REJECTED it**: Blog flags "AI doctor" as oversaturated. Narrow scope might not feel "big enough" for Main Track 1st. Mark's suggestion but not the final direction.
- **Decision**: KILLED — too narrow, medical liability risk

### Idea 5: "VoiceBridge" — Universal AAC Device
- **What**: Replace $15K communication devices with a free phone app for people who can't speak
- **Why it was promising**: 97M need AAC, 3% access in developing world (30x gap), combines MediaPipe + Gemma 4 + Unsloth, accessibility dominated previous winners
- **Why we moved past it**: Vimal questioned: "Is there real need beyond papers?" and "Isn't this just a regular agentic workflow?" Valid pushback — the problem is huge on paper but demand is unproven, and the tech, while well-integrated, isn't fundamentally novel.
- **Decision**: MOVED PAST — problem didn't feel "huge enough" in gut-check, tech not sufficiently differentiated

### Idea 6: "Sapien" — Every Expert in Your Pocket
- **What**: Universal AI that becomes whatever expert you need (doctor, agronomist, pharmacologist, herpetologist) based on what you show it
- **Why it was promising**: Visionary concept, uses ALL Gemma 4 capabilities, "the 99% who never used AI" narrative
- **Why we REJECTED it**: Vimal said directly: "No I don't like this idea." Too broad, too platform-y. The blog warned against trying to do everything. Loses focus and emotional specificity. Jack of all trades, master of none.
- **Decision**: KILLED — too broad, lacks emotional focus

### Idea 7: "MedScan" — Counterfeit Medicine Detection
- **What**: Phone camera scans pills/packaging to detect fake medicine
- **Why it was promising**: 250K children die from fake drugs, $150K lab → phone disruption, multi-stage vision pipeline
- **Why we didn't pick it**: Strong concept but less emotionally compelling in video than child mortality. The "scan pill" moment is functional, not tear-jerker. Competing with this against Malaika, we felt Malaika has the stronger emotional + technical + scale combination.
- **Decision**: STRONG RUNNER-UP — could revisit if Malaika proves infeasible

### Idea 8: "BreathGuard" — Phone That Listens to Children Breathe
- **What**: Real-time video breathing analysis + audio breath classification for child pneumonia
- **Why it was promising**: 700K children die from pneumonia, $50K monitor → phone disruption
- **Why it EVOLVED**: This was the seed that grew into Malaika. We realized limiting it to just pneumonia was too narrow when the WHO IMCI protocol covers ALL the major child killers (pneumonia + diarrhea + malaria + malnutrition + danger signs) with the same multimodal approach.
- **Decision**: EVOLVED INTO MALAIKA — broadened from pneumonia-only to full IMCI protocol

---

## Phase 6: The Convergence — Why Malaika

### The three threads that converged

**Thread 1: Problem scale**
We kept asking: what's the BIGGEST problem? The answer: 4.9 million children under 5 die every year (WHO, March 2026). Most from preventable causes. This is the single most devastating, most well-documented, most actionable problem in global health.

**Thread 2: The protocol gap**
The WHO IMCI protocol exists. It's proven. It's adopted by 100+ countries. It saves lives. But <25% of health facilities have enough trained workers. The knowledge exists — it just can't reach the mothers who need it. This is an INFORMATION DELIVERY problem, which is exactly what AI solves.

**Thread 3: Gemma 4's unique capabilities**
No previous model could do what Gemma 4 does on a phone:
- Real-time video analysis (breathing rate from chest movement)
- Native audio processing (breath sound classification)
- 140+ language voice interaction
- Agentic function calling (clinical protocol as tool chain)
- All on-device, offline, on a $100 phone

These three threads converge into ONE idea: **put the IMCI protocol into Gemma 4, enhanced with multimodal sensing, accessible to any mother in any language offline.**

### Why it's NOT a "generic AI doctor chatbot"
The blog warned about this. Malaika avoids it because:
1. It implements a **specific, validated WHO protocol** — not AI-generated medical advice
2. It's a **medical instrument** (like an AED), not a conversational AI
3. It actively **ASSESSES** through camera and audio — not just Q&A
4. It targets **children under 5** specifically — not general health
5. It's designed for **untrained caregivers** — not health workers
6. Each step follows **published clinical guidelines** — not hallucinations

### How Mark's requirements are met

| Mark's Requirement | How Malaika Delivers |
|-------------------|---------------------|
| "Combine as many Google strengths" | Vision + Voice + Translate + Function Calling + On-device + Health AI |
| "Push the model to its limits" | Simultaneous video + audio + voice processing, 14+ tools, agentic protocol |
| "Physical and virtual. Multimodal." | Camera (physical), audio (physical), voice (physical), AI reasoning (virtual) |
| "Voice, image, text, TTS" | All four modalities used |
| "Appeal to emotion. A real tear jerker." | Mother saving child at 2am — the video writes itself |
| "I didn't know you could do that with Gemma 4" | Real-time clinical assessment from phone sensors, offline |
| "Show what constrained open source CAN do" | $100 phone doing what $50K equipment + trained clinician does |
| "Stay in Google ecosystem" | WAXAL, MedGemma patterns, MediaPipe, AI Edge, LiteRT |
| "Solve a real problem at scale" | 4.9 million deaths/year, 100+ countries using IMCI |

### How Vimal's requirements are met

| Vimal's Requirement | How Malaika Delivers |
|--------------------|---------------------|
| "Extremely huge problem" | 4.9M children/year — doesn't get bigger |
| "Groundbreaking, like wow" | First time IMCI runs as multimodal AI on a phone |
| "Technical implementation should stand out" | 14+ tools, real-time video/audio, agentic protocol, LoRA fine-tuning |
| "Accessible for health, disability, remote villages" | Voice-based, camera-based, offline, multilingual |
| "Open source can solve this" | Must be offline, free, customizable — only open source works |
| "Disrupting something" | Months of CHW training → app. $50K equipment → phone camera. |
| "Not a generic chatbot" | Protocol-based instrument, multimodal sensing, specific to children |

---

## Phase 7: Key Strategic Decisions Still Ahead

### Decided
- [x] Competition target: Main 1st ($50K) + Health & Sciences ($10K) + Unsloth ($10K)
- [x] Core concept: WHO IMCI protocol as multimodal AI on Gemma 4
- [x] Name: Malaika (Angel in Swahili)
- [x] Model: Gemma 4 E4B (on-device via Ollama)
- [x] Fine-tuning: Unsloth on Mark's RTX 3060

### Pending (need team alignment)
- [ ] Mark's confirmation on the idea
- [ ] Tech stack for the app (React Native? Flutter? Web app? Progressive Web App?)
- [ ] Specific demo scenarios to film for video
- [ ] Who to find as a "real user" for the video story
- [ ] Video production approach (film ourselves? stock footage? animation?)
- [ ] Sprint plan finalization and task assignment
- [ ] GitHub repo setup
- [ ] Kaggle writeup draft ownership

---

## File Map — How Everything Connects

```
deepmind-hackathon/
│
├── RESEARCH.md              ← Full competition analysis, all research data, 
│                              winner patterns, Google strategy, global problems,
│                              competition landscape, expert blog insights,
│                              decision matrix across all ideas
│
├── MALAIKA_PROPOSAL.md      ← The final idea: problem, solution, architecture,
│                              tools, fine-tuning plan, video script, sprint plan,
│                              why-it-wins analysis
│
├── DECISION_JOURNEY.md      ← THIS FILE: how we got here, what we explored,
│                              what we rejected and why, the convergence logic
│
├── geotab-hackathon/        ← Reference from our winning Geotab project
│   ├── CLAUDE.md            ← How we structured dev guide (model for new CLAUDE.md)
│   ├── COMPETITION.md       ← How we tracked competition rules
│   ├── METHODOLOGY.md       ← Development methodology
│   ├── PROMPTS.md           ← Prompt engineering notes
│   └── ...
│
└── (NEXT: to be created)
    ├── CLAUDE.md            ← Development guide for Malaika (like Geotab's)
    ├── COMPETITION.md       ← Competition rules quick reference
    └── src/                 ← Project source code
```

---

## Memory Files (Claude Context Persistence)

These files are stored in Claude's memory system and loaded automatically in future sessions:

| File | What It Contains |
|------|-----------------|
| `user_profile.md` | Vimal's background, competition history, working style |
| `project_competition_overview.md` | Prize breakdown, deadlines, judging criteria, submission requirements |
| `project_gemma3n_winner_patterns.md` | What made previous winners win |
| `project_google_strategy_alignment.md` | Google's vision for Gemma, social good priorities |
| `project_competition_landscape.md` | What other teams are building (agriculture taken, education oversaturated) |

---

*Document created: April 12, 2026*
*Last updated: April 12, 2026*
