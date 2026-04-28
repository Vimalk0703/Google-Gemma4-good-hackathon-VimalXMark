# Malaika Agentic Enhancement Plan

> Branch: `enhancements`
> Goal: turn rigid scripted Q&A into intelligent orchestration that
> showcases Gemma 4's agentic capabilities — without touching the
> working camera/vision/classification stack or the model's memory budget.

---

## Hard Rules (do NOT violate)

1. **Camera flow is sacred.** `MalaikaCameraPlugin.kt`, `CaptureScreen`,
   Path A model unload/reload — all stay exactly as they are. Verified
   working on Samsung A53.
2. **Memory budget unchanged.** Model loads with `maxTokens=200` at splash.
   Every new prompt MUST fit input + output inside that 200-token window.
   Never call `getActiveModel(maxTokens=…>200)` outside the splash path.
3. **WHO IMCI classification stays deterministic.** `imci_protocol.dart`
   thresholds are the medical authority. The LLM PERCEIVES findings; the
   code DECIDES severity. Never let the model override a classification.
4. **Treatment plan stays deterministic.** `treatment_protocol.dart` reads
   WHO dosing tables. Don't rewrite this with an LLM.
5. **Every LLM call has a fallback path.** If JSON parse fails, malformed
   output, or model overflow — fall back to today's working behavior. We
   improve the happy path; we don't fragilize the safe path.
6. **Offline-only.** No network calls. Everything is on-device Gemma 4 E2B.

---

## Diagnosis (one paragraph)

The current pipeline calls Gemma once per turn with a narrow prompt
("reply with one word: yes/no/unclear"), throws away the user's original
text (`cleanInput = 'yes'` in `home_screen.dart:765`), then runs a regex
auto-fill on the cleaned word. So "fever for 2 days, very sleepy" becomes
`yes`, the auto-fill scans `yes` for digits, finds none, and the bot
asks "how many days has the fever lasted?" anyway. Three findings
volunteered, one captured, two lost. The conversation feels rigid because
question order is hardcoded in `imciQuestions[]` and rephrasing is just
the LLM wrapping a fixed string. Vision findings (6 of them) feed
question selection but never feed question wording or final-report prose.

---

## The Four Enhancements

### #1 — Structured JSON Multi-Value Extraction

**Problem:** one finding per turn; original text discarded.

**Design:**
- New helper `_extractStructuredFindings(userText, currentStep, knownFindings)` returning `Map<String, dynamic>`.
- Single Gemma call with this prompt shape:
  ```
  Step: <fever>
  Possible findings (key: type):
    has_fever: bool
    fever_days: int
    stiff_neck: bool
    malaria_risk: bool
  Caregiver said: "<text>"
  Reply ONLY a JSON object with keys you are sure about.
  Example: {"has_fever": true, "fever_days": 2}
  ```
- Parse with `jsonDecode` wrapped in try/catch. On failure → fall back to today's `_buildExtractPrompt` + `_interpretExtraction`.
- Whitelist allowed keys per step so the LLM can't invent fields.
- Token budget: prompt ~70 in, response ~40 out → fits 200.

**Touches:**
- `lib/screens/home_screen.dart` — new helper, replace single-value branch in `_sendText`.
- `lib/core/imci_questionnaire.dart` — new method `recordStructuredAnswers(Map findings, String userText)` that updates findings + advances index past auto-filled questions. Keep `recordAnswer(String)` intact as fallback.

**Done when:** "fever for 2 days, very sleepy" → `has_fever=true, fever_days=2, lethargic=true` recorded in one turn, bot does NOT re-ask any of those.

---

### #2 — Agentic Next-Question Selection

**Problem:** questions march in `imciQuestions[]` order regardless of clinical priority.

**Design:**
- New helper `_pickNextQuestion(remainingQuestions, knownFindings, visionSummary)` returns a question_id.
- Gemma prompt:
  ```
  Confirmed: lethargic=true, fever=true, fever_days=2
  Remaining questions:
    - stiff_neck: Does your child have a stiff neck?
    - malaria_risk: Are you in a malaria area?
    - has_diarrhea: Diarrhea?
    - …
  Pick the most clinically important next question.
  Reply with ONLY the question_id.
  ```
- Validate response is in the remaining-id list. If not → fall back to in-order next.
- Only invoked AFTER each step's findings have been ingested. Never reorders ACROSS steps (preserves WHO IMCI flow: danger → breathing → diarrhea → fever → nutrition).
- Token budget: prompt ~100 in, response ~5 out.

**Touches:**
- `lib/screens/home_screen.dart` — call `_pickNextQuestion` between recording an answer and asking the next.
- `lib/core/imci_questionnaire.dart` — expose `remainingQuestionsInStep(step)` getter.

**Safety:** classification still keyed off WHO thresholds, regardless of question order.

**Done when:** if `lethargic+fever` are both true, bot prioritizes `stiff_neck` (meningitis check) over `malaria_risk` without us hardcoding it.

---

### #3 — Context-Aware Question Wording

**Problem:** "Ask the caregiver: <Q>" produces robotic rephrasing with no awareness of what's been said.

**Design:**
- Replace the existing `_ask('Ask the caregiver: ${nextQ.question}')` with `_buildContextualAsk(nextQ, knownFindings, visionSummary)`.
- Prompt shape:
  ```
  You are a caring child health worker. So far:
   - Child is 12 months old
   - You saw in the photo: lethargic, sunken eyes
   - Caregiver told you: fever 2 days
  Ask the next question warmly and reference what you know.
  Question to ask: "<Q.question>"
  Reply with ONE warm sentence ending in a question mark.
  ```
- Enforce: response must contain `?`. If not → use raw `Q.question`.
- Strip leading filler the model loves to add ("Sure!", "Of course!"). Already done elsewhere — reuse pattern.
- Token budget: prompt ~120 in, response ~25 out.

**Touches:**
- `lib/screens/home_screen.dart` — new helper, swap call sites in `_continueToTargetedQA` and follow-up question paths.
- No state changes.

**Done when:** after seeing sunken eyes, instead of "Does your child have diarrhea?" the bot says "I noticed your little one's eyes look sunken — has there been any diarrhea?"

---

### #4 — Rich Final Report

**Problem:** `buildReportContext` truncates findings to a flat list; report doesn't explain WHY a classification is red/yellow.

**Design:**
- New `buildRichReportContext()` in `imci_questionnaire.dart` returns a structured object:
  ```
  {
    age: 12, weight: 6,
    vision: ["lethargic", "sunken_eyes"],
    verbal: ["has_fever (2 days)", "has_diarrhea"],
    classifications: [
      { step: "fever", severity: "yellow", reason: "fever 2 days, no danger signs" },
      { step: "diarrhea", severity: "red", reason: "diarrhea + lethargic + sunken eyes = severe dehydration (WHO Plan C)" },
    ],
    treatment: ["ORS Plan C", "co-trimoxazole 240mg twice daily x5"],
  }
  ```
- Two-call report generation (each call ≤200 tokens):
  1. **Call A — Caregiver narrative:** "Tell the caregiver in 2-3 caring sentences what you found and why it matters." Input: vision + verbal + top severity + reason.
  2. **Call B — Action plan:** "List the 3 most important things the caregiver must do, numbered, simple words." Input: treatment + severity.
- Final report card concatenates Call A + classification chips + Call B + medicine cards.
- Falls back to today's flat `buildReportContext` if either call fails.

**Touches:**
- `lib/core/imci_questionnaire.dart` — add `buildRichReportContext()` (keep old `buildReportContext` for fallback).
- `lib/screens/home_screen.dart` — `_generateFinalReport` calls A then B sequentially, builds composite UI card.

**Done when:** report mentions specific findings ("I saw your child's eyes look sunken AND you said there's been diarrhea — together this is severe dehydration") rather than generic boilerplate.

---

## Implementation Order & Checkpoints

| Phase | Enhancement | Why this order | Verifiable on phone |
|-------|-------------|----------------|---------------------|
| P1 | #1 Structured Extraction | Fixes the visible bug; unblocks all later phases (they rely on rich findings being in state) | Type "fever 3 days, very tired" → see 3 findings extracted in one turn |
| P2 | #2 Agentic Question Selection | Reuses #1's findings to make question order intelligent | Trigger lethargic+fever → next Q is stiff_neck (not malaria) |
| P3 | #3 Contextual Wording | Reuses #1+#2 state to produce natural questions | After photo of sunken-eye child → next Q references what was seen |
| P4 | #4 Rich Final Report | Reuses everything | Final report mentions specific findings + WHY |

After **each phase**: build APK, install on A53, run a full assessment end-to-end. Don't move to the next phase until the current one works on real hardware.

---

## Risk & Safety Matrix

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| JSON parse fails | Med | try/catch → fall back to today's single-value extract |
| LLM hallucinates a finding key | Med | Whitelist allowed keys per step; drop unknown keys |
| Model overflows 200-token window | Low if prompts stay tight | Pre-count tokens (rough = words × 1.3); split into smaller calls |
| LLM picks a clinically wrong "next question" | Low | WHO classification thresholds still authoritative; question order doesn't change classification result |
| Contextual wording loses the question | Low | Validate response contains `?`; else use raw `Q.question` |
| Rich report regresses to vague prose | Low | Keep flat fallback; A/B in code for emergency revert |

---

## Definition of Done

A test session: open app → take photo of test image → answer "fever for 3 days, very tired" → walk through targeted questions → see final report.

Pass criteria:
- [ ] No question is asked whose answer was already in user text.
- [ ] Question order reflects clinical priority, not list order.
- [ ] At least one question text references a known finding.
- [ ] Final report mentions ≥2 specific findings by name.
- [ ] No regressions: camera still opens, vision still extracts, classification still matches WHO thresholds.
- [ ] LMKD still doesn't kill us during the flow (memory budget held).
- [ ] All 4 phases shipped behind a single feature flag `kAgenticOrchestration` so we can A/B revert if a demo machine misbehaves.

---

## Files We Will Touch

- `lib/screens/home_screen.dart` — orchestration changes (additive, never replacing the fallback paths)
- `lib/core/imci_questionnaire.dart` — `recordStructuredAnswers`, `buildRichReportContext`, `remainingQuestionsInStep`
- `lib/core/agentic_assessor.dart` — possibly extend with extraction-prompt builders (TBD during implementation)
- New: `lib/core/agentic_orchestrator.dart` — pure functions for prompt building, JSON parsing, fallback logic. Easier to test, easier to revert.

## Files We Will NOT Touch

- `MalaikaCameraPlugin.kt`, `MainActivity.kt`, `AndroidManifest.xml`
- `lib/screens/capture_screen.dart`, `lib/services/malaika_camera.dart`
- `lib/core/imci_protocol.dart` (medical thresholds)
- `lib/core/treatment_protocol.dart` (WHO dosing)
- `lib/screens/splash_screen.dart` (model load configuration)
- `pubspec.yaml` (no new dependencies)
