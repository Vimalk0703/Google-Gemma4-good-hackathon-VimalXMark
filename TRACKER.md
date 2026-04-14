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

### Day 4 (Apr 14) — TODO
- [ ] Download ICBHI dataset, test breath sound pipeline with real audio
- [ ] Download jaundice dataset, test with real clinical images
- [ ] Start LoRA fine-tuning on Kaggle (breath sounds)
- [ ] Test Gradio app end-to-end on GPU machine

---

## Submission Checklist (May 18)

### Mandatory — No submission without these
- [ ] **Kaggle writeup** — 1,500 words max, Track: Health & Sciences
- [ ] **YouTube video** — 3 min, public, emotional narrative + technical demo
- [ ] **Public GitHub repo** — documented, reproducible, no secrets
- [ ] **Live demo URL** — Gradio share=True, no login, mobile-friendly
- [ ] **Media gallery** — cover image, screenshots, architecture diagram

### Winning Edge — Differentiators
- [ ] Fine-tuned LoRA adapters (Unsloth prize $10K)
- [ ] Phone demo in video (AI Edge Gallery + E2B)
- [ ] 20+ validated test scenarios with accuracy metrics
- [ ] 3+ languages demonstrated (English + Swahili + Hindi minimum)
- [ ] Heart MEMS module working (or cleanly disabled)
- [ ] Kaggle notebook showing fine-tuning process

---

## Prize Alignment Scorecard

Update this weekly. Score yourself honestly 1-10.

| Criterion | Weight | Current Score | Target | Gap |
|-----------|--------|---------------|--------|-----|
| **Impact & Vision** (40%) | Highest | 8/10 | 9/10 | Need video showing human story |
| **Video Pitch** (30%) | High | 1/10 | 9/10 | **BIGGEST GAP** — not started |
| **Technical Depth** (30%) | High | 8/10 | 9/10 | Need fine-tuning + real clinical data accuracy |

### Impact & Vision — How to reach 9/10
- [x] Problem: 4.9M children/year (WHO data, March 2026)
- [x] Solution: WHO IMCI protocol on phone via Gemma 4
- [x] Offline-first architecture
- [x] Multilingual (Swahili confirmed working)
- [ ] Real user story in video (mother + child scenario)
- [ ] Partnership/deployment plan mentioned in writeup

### Video Pitch — How to reach 9/10
- [x] Script written (MALAIKA_PROPOSAL.md)
- [ ] Opening hook: mother at 2am, sick child, no clinic
- [ ] Live demo footage: Gradio assessment running
- [ ] Phone demo footage: AI Edge Gallery on Android
- [ ] Emotional B-roll: children, clinics, health workers
- [ ] Narration recorded
- [ ] Music + editing
- [ ] Upload to YouTube (public, unlisted ok)

### Technical Depth — How to reach 9/10
- [x] Multimodal: vision + audio + speech + video
- [x] IMCI state machine with WHO citations
- [x] 213 tests, 97% protocol coverage
- [x] Production patterns: guards, observability, versioned prompts
- [ ] Fine-tuned LoRA adapters deployed
- [ ] Accuracy metrics on 20+ scenarios (run with real model)
- [ ] On-device proof (E2B on phone)
- [ ] Performance benchmarks (latency, VRAM, tok/s)

---

## Critical Path

```
Week 1 (Apr 12-18): Foundation + Real GPU Testing
  ✅ Code complete (213 tests)
  → GPU end-to-end testing
  → Prompt refinement
  → Download datasets

Week 2 (Apr 19-25): Core IMCI with Real Data
  → Test all 21 golden scenarios with real model
  → Accuracy metrics for writeup
  → Fix prompts based on real outputs

Week 3 (Apr 26-May 2): Fine-tuning + Multilingual
  → LoRA training on Kaggle (breath sounds, jaundice)
  → Test Swahili, Hindi, Hausa
  → Stress test 20+ scenarios

Week 4 (May 3-9): Deploy + Phone
  → Live demo URL (Gradio share=True)
  → Phone demo (AI Edge Gallery + E2B)
  → MEMS GO/NO-GO (May 6)

Week 5 (May 10-18): Video + Submit
  → Film video (3 min)
  → Kaggle writeup (1,500 words)
  → Final review
  → SUBMIT May 18
```

---

## Risk Register

| Risk | Impact | Status | Mitigation |
|------|--------|--------|------------|
| No GPU machine for demo | CRITICAL | Open | Use Kaggle/Colab for testing, rent GPU for demo day |
| Gemma 4 accuracy too low | HIGH | Unknown | Prompt refinement + fine-tuning |
| Video not compelling | HIGH | Not started | Follow script in MALAIKA_PROPOSAL.md |
| Audio quality poor (Whisper) | MEDIUM | Tested | Whisper-small good for Swahili, fallback to text |
| Fine-tuning fails | MEDIUM | Notebook ready | Use strong prompting as fallback |
| Scope creep | HIGH | Managed | NO new features after Week 4 |
| Time runs out | MEDIUM | On track | Video + writeup start Week 5, not later |

---

## Context Anchors (Read these to stay aligned)

1. **We are building a MEDICAL INSTRUMENT, not a chatbot.** Every decision must serve child survival.
2. **Gemma 4 perceives, code decides.** The model got the breathing threshold wrong (40 vs 50). Protocol code is the safety boundary.
3. **The video is 30% of the score.** Technical depth means nothing if the pitch doesn't land.
4. **Offline is non-negotiable.** Every feature works without internet.
5. **Fine-tuning targets the Unsloth $10K prize.** The notebook IS the submission evidence.

---

*Last updated: April 13, 2026*
*Next update: Start of Day 3 (April 14)*
