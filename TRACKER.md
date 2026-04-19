# Malaika — Competition Tracker

> Check this at the START of every session. Update at the END of every session.
> **Prize target: $70K** (Main $50K + Health $10K + Unsloth $10K)
> **Deadline: May 18, 2026** (36 days from Apr 12)

---

## Daily Status

### Day 1-2 (Apr 12-13) — COMPLETED
- [x] Project structure + engineering foundation (CLAUDE.md, 7 docs)
- [x] 4 skill modules with guidelines (prompts, guards, observability, evaluation)
- [x] Core types (27 classifications) + config
- [x] IMCI protocol — all 6 WHO domains, 97% coverage
- [x] Inference engine — self-correction, caching, cost tracking
- [x] Vision (7 functions) + Audio (Whisper pipeline, 3 functions)
- [x] IMCI state machine — full flow
- [x] Gradio UI (app.py) + Piper TTS (tts.py)
- [x] 213 passing tests
- [x] Kaggle feasibility test — confirmed: text ✓, image ✓, JSON 100%, Swahili ✓, audio ✗ (Whisper fallback)
- [x] Fine-tuning notebook ready (not trained yet)

### Day 2-3 (Apr 13) — COMPLETED
- [x] Kaggle E2E integration test — FULL PIPELINE VALIDATED
- [x] Golden scenarios: 21/21 (100%)
- [x] JSON reliability: 5/5 (100%)
- [x] Fixed Gemma 4 "thinking mode" — suppress chain-of-thought in prompts
- [x] Fixed empty nutrition responses — enforce field filling
- [x] Audio pipeline: confirmed Whisper fallback needed, implemented
- [x] Gradio UI (app.py) + Piper TTS (tts.py) built
- [x] 213 local tests passing
- [x] Swahili treatment generation confirmed working

### Day 4 (Apr 14) — COMPLETED
- [x] Spectrogram pipeline: audio → mel-spectrogram PNG → Gemma 4 vision
- [x] Fixed treatment prompt (Swahili was returning JSON instead of text)
- [x] Spectrogram-based breath sound prompt + classification function
- [x] Updated fine-tuning notebook: spectrogram vision approach (not text-only)
- [x] Day 4 Kaggle notebook ready (real ICBHI data testing + all re-verification)
- [x] 227 tests passing (up from 213)
- [x] Push to GitHub and run Day 4 notebook on Colab T4
- [x] All 8 tests PASS, 21/21 golden, 5/5 JSON, Swahili plain text
- [x] Spectrogram baseline: 25% (20/20 JSON parse)
- [x] LoRA fine-tuning v1: r=8, 100 steps → 20% (too weak)
- [x] LoRA fine-tuning v2: r=32, 300 steps → 50% (100% crackle detection)
- [x] Adapter saved: 90.3 MB
- [ ] Download jaundice dataset, test with real clinical images

### Day 5 (Apr 15) — COMPLETED
- [x] Real-time voice pipeline — Tasha-style single WebSocket architecture
- [x] voice_app.py (FastAPI), voice_session.py (WebSocket handler)
- [x] Smallest AI Pulse STT + Waves TTS integration
- [x] Browser VAD (Voice Activity Detection) + audio streaming
- [x] static/index.html — orb UI, camera capture, text input

### Day 5-6 (Apr 16) — COMPLETED
- [x] **Agentic architecture overhaul** — skills-based clinical agent
- [x] NEW: malaika/skills.py — 12 clinical skills, SkillRegistry, BeliefState, SkillResult
- [x] CHANGED: chat_engine.py — process() returns structured events, findings-based step advancement + message-count fallback, per-step WHO classification, danger sign escalation
- [x] CHANGED: voice_session.py — sentence-level TTS streaming, filler audio during thinking, event forwarding to browser
- [x] CHANGED: static/index.html — IMCI progress bar, skill execution cards, classification cards (RED/YELLOW/GREEN), image request cards, finding chips, danger alert banner, assessment complete card, audio playback queue
- [x] NEW: notebooks/10_voice_agent_colab.ipynb — Colab T4 deployment via ngrok
- [x] 104 tests passing (78 protocol + 26 engine), zero regressions
- [x] Full flow tested: 12mo child → lethargic → RED Urgent Referral, fever + malaria → YELLOW Malaria
- [x] Graceful degradation without SMALLEST_API_KEY (text + image still work)
- [ ] Test voice agent end-to-end on Colab with real model

---

## Submission Checklist (May 18)

### Mandatory — No submission without these
- [ ] **Android app** — complete IMCI assessment running on-device with Gemma 4 E2B
- [ ] **Kaggle writeup** — 1,500 words max, Track: Health & Sciences
- [ ] **YouTube video** — 3 min, public. Android phone demo is the hero.
- [ ] **Public GitHub repo** — documented, reproducible, no secrets
- [ ] **Media gallery** — cover image, phone app screenshots, architecture diagram

### Winning Edge — Differentiators
- [ ] Multi-language demo on phone: English + Swahili + Hindi
- [ ] Photo analysis working on-device (dehydration, nutrition signs)
- [ ] Referral card generation after assessment
- [ ] Kaggle notebook: Unsloth fine-tuning + before/after accuracy metrics ($10K prize)
- [ ] 20+ validated test scenarios with accuracy metrics in writeup

---

## Prize Alignment Scorecard

Update this weekly. Score yourself honestly 1-10.

| Criterion | Weight | Current Score | Target | Gap |
|-----------|--------|---------------|--------|-----|
| **Innovation** (30%) | High | 7/10 | 9/10 | Need phone demo polished, show "why only Gemma 4" clearly |
| **Impact** (30%) | High | 8/10 | 9/10 | Need video with human story, referral card |
| **Technical Execution** (25%) | High | 7/10 | 9/10 | Android app needs to be bulletproof, fine-tuning notebook |
| **Accessibility** (15%) | High | 9/10 | 10/10 | Already offline + phone + multilingual — just need to show it |

### Innovation — How to reach 9/10
- [x] Only submission with real medical protocol (WHO IMCI) on a phone
- [x] Deterministic classification — LLM perceives, code decides
- [ ] Android app running complete assessment end-to-end
- [ ] Multi-language: same assessment in EN + SW + HI
- [ ] Answer "why only Gemma 4" clearly: no other model fits on a phone with vision

### Impact — How to reach 9/10
- [x] Problem: 4.9M children/year (WHO data, March 2026)
- [x] Solution: WHO IMCI protocol on phone via Gemma 4
- [x] Offline-first — works where children die
- [ ] Referral card — extends value beyond the phone screen
- [ ] Real user persona in video (Maria the CHW in Kilifi County)
- [ ] Emotional video showing the phone saving a child

### Technical Execution — How to reach 9/10
- [x] Flutter app with structured IMCI Q&A + photo analysis + classification
- [x] IMCI protocol engine: deterministic WHO classification
- [x] 104+ tests, 97% protocol coverage, 21/21 golden scenarios
- [x] Reasoning cards showing extracted findings
- [ ] Android build running smoothly on real device
- [ ] Kaggle notebook: Unsloth fine-tuning with before/after metrics
- [ ] Performance benchmarks on-device (latency, tok/s)

### Accessibility — How to reach 10/10
- [x] Runs on $150 phone (2.58GB, 676MB RAM)
- [x] Fully offline — no internet needed
- [x] 140+ languages built into model
- [ ] Demonstrate Swahili assessment in video

---

## Critical Path (MOBILE FIRST)

```
Week 1 (Apr 12-18): Foundation ✅
  ✅ Python codebase (227 tests, 21/21 golden)
  ✅ Flutter app with IMCI Q&A + vision + classification
  ✅ Gemma 4 E2B running on phone via flutter_gemma

Week 2 (Apr 19-25): Android App Polish
  → Get Android build running end-to-end on real device
  → Polish Flutter UI (looks like a product, not a prototype)
  → Test multi-language (Swahili, Hindi)
  → Add referral card generation

Week 3 (Apr 26-May 2): Fine-Tuning + Accuracy
  → Unsloth fine-tuning notebook (Kaggle)
  → Before/after accuracy metrics
  → Test 20+ scenarios on phone
  → Fix prompts based on real E2B outputs

Week 4 (May 3-9): Polish + Content
  → Final UI polish
  → Record phone demo footage
  → Draft Kaggle writeup

Week 5 (May 10-18): Video + Submit
  → Film video (3 min, phone demo is hero)
  → Kaggle writeup final
  → Final review
  → SUBMIT May 18
```

---

## Risk Register

| Risk | Impact | Status | Mitigation |
|------|--------|--------|------------|
| Android build doesn't work | **CRITICAL** | Testing needed | Flutter app exists, need to test on real Android device |
| E2B accuracy too low for clinical use | HIGH | Unknown | Prompt refinement, structured Q&A compensates |
| Video not compelling | HIGH | Not started | Phone demo IS the video — film the app working |
| Fine-tuning notebook fails | MEDIUM | Notebook exists | Use base model metrics, show architecture instead |
| Scope creep | HIGH | Managed | NO new features after Week 3. Polish only. |
| Time runs out | MEDIUM | On track | Video + writeup start Week 4, not later |

---

## Context Anchors (Read these to stay aligned)

1. **THE PHONE IS THE PRODUCT.** The Android app is the primary demo. Everything else is supplementary.
2. **"Why only Gemma 4?"** Because no other model runs on a phone with text + vision in <3GB. That's the ENTIRE argument.
3. **Gemma 4 perceives, code decides.** WHO thresholds are deterministic code, never LLM output. This is the medical safety story.
4. **Offline is non-negotiable.** Every feature works without internet on the phone.
5. **Don't claim what we can't show on-device.** No breath counting from video, no spectrogram analysis on phone. Be honest.
6. **Fine-tuning is the UPGRADE PATH.** Base model works on phone. Fine-tuned model is for clinics with compute. Shows Unsloth capability for $10K prize.

---

*Last updated: April 18, 2026 (Mobile-first pivot)*
*Next update: End of Week 2*
