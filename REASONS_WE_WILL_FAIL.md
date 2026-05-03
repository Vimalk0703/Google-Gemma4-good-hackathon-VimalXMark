# Reasons Malaika Will Fail

> Anti-marketing. The honest list.
>
> This document exists because medical software lies to itself constantly, and the only honest way to ship is to write down — out loud — every reason this thing might be wrong, every limit it has, and every line we will not cross. We owe this to the children Malaika is for. We owe it to the judges. We owe it to ourselves.

---

## Things Malaika Will Never Do

These are not "current limitations." These are **deliberate, permanent boundaries.** If a future version of Malaika does any of these, it has stopped being Malaika.

### 1. Malaika will never diagnose.

Malaika does not output diagnoses. It outputs **WHO IMCI classifications** — the same output a WHO-trained nurse would produce after walking the protocol, no more and no less.

- The classification engine (`imci_protocol.py` / `imci_protocol.dart`) is **deterministic Dart and Python code**. The thresholds are hard-coded from the WHO IMCI chart booklet, with page citations.
- The LLM does **perception** (extracting findings from speech, photos). It never decides severity.
- If a future contributor proposes "let the LLM classify directly," the PR is rejected. Full stop.

### 2. Malaika will never recommend a dose without a deterministic source.

Treatment dosages come from `treatment_protocol.dart`, which reads the WHO Essential Medicines tables. The LLM is permitted to *read* the dose to the caregiver in her language, but the *number* always comes from code.

- No LLM-generated mg, ml, or frequency. Ever.
- If WHO updates a dose, we update one constant. The model is never the source of truth.

### 3. Malaika will never replace a clinician.

Malaika is **decision support for a non-clinician at home, or a community health worker in the field.** Every classification card carries the same explicit disclaimer: *"Take this child to a clinic or hospital as soon as you can. Malaika is not a doctor."*

- For RED severity → Malaika tells the caregiver to refer immediately, even if it has high confidence the home plan would also work. The asymmetry of risk dictates: when in doubt, escalate.
- For GREEN severity → Malaika never says "your child is fine." It says "based on what you described, you can treat at home for now — but watch for these danger signs and return if you see any of them." The reader is always the decision-maker.

### 4. Malaika will never silently fail.

If the model can't parse a JSON response, if a finding is uncertain, if two findings contradict — Malaika **says so out loud**.

- Self-correcting inference: max 2 retries on parse failure. Then `Uncertain` flag with raw output logged.
- Reconciliation engine flags conflicts between Q&A and vision. The conflict is shown to the caregiver, not hidden.
- Confidence is exposed in every skill result. Low confidence does not get rounded up to a clean answer.

### 5. Malaika will never send a child's data to the cloud without consent.

The on-device path (Flutter + Gemma 4 E2B) is **fully offline.** Photos, voice, and text never leave the device unless the caregiver explicitly opts into a connected mode.

- The two-tier mode (clinic server with Gemma 4 E4B + breath-sound LoRA) requires explicit consent and runs on **the clinic's own hardware** — not anyone else's cloud.
- No telemetry. No analytics. No third-party SDKs. The repo is auditable, top to bottom.

### 6. Malaika will never claim a capability the phone cannot deliver.

- **No live camera preview** on the phone — Mali GPU can't hold the model and a camera surface at the same time. We use gallery photos and we say so.
- **No breath-sound classification** on the phone — the audio path needs a spectrogram pipeline that doesn't fit in the GPU budget. The phone defers it to the clinic server.
- **No video processing** on the phone — single photo, with reconciliation against verbal Q&A. We do not pretend we can count breaths from video.
- **No real-time monitoring** — Malaika is single-encounter assessment, not continuous monitoring.

If we cannot demonstrate a feature live on a Samsung A53, it is not in the demo.

---

## Where Malaika Can Fail

Honest list. We've thought hard about each of these and built specific defences. Knowing the failure modes is how we keep the thing safe.

### Failure 1 — The vision model misreads the photo

Possible. Lighting is bad. The angle is wrong. The child is wearing a heavy blanket. Gemma 4's vision is good, not perfect.

**Defence:** *Reconciliation.* Every vision finding is cross-checked against the verbal Q&A. If the mother says "child is alert" and the vision says "child appears lethargic" — we don't pick a winner. We flag the conflict and ask the mother to confirm. Better to ask twice than to be wrong once.

**What still slips through:** rare photos where vision and verbal both agree but both are wrong (e.g., a sleeping child mistaken for an unconscious one). For RED severity, this is acceptable — escalation is the right action either way. For GREEN, we always include "watch for these danger signs and return."

### Failure 2 — The mother answers a question wrong

Common. The caregiver is panicking, exhausted, or unfamiliar with clinical vocabulary ("fast breathing" is subjective).

**Defence:** *Structured multi-value extraction.* The Q&A doesn't ask "yes / no" — it asks an open question, lets the caregiver narrate freely, and Gemma extracts up to four findings per turn. If she says "he has been coughing for three days and refuses water," the system pulls *cough, duration, fluid refusal* in one pass, and asks the next clinically-prioritized question rather than re-asking what was already volunteered.

**What still slips through:** language barriers we haven't trained on. Currently strong: English, Swahili, Hausa, Hindi, Bengali, Portuguese. Currently weak: smaller regional languages with very little training data in Gemma. We say this in the README.

### Failure 3 — The classification is wrong

Possible if the model misreports findings to the deterministic classifier. The classifier itself is auditable Dart/Python — it can't be wrong about thresholds, only about the inputs it received.

**Defence:** *21/21 golden scenario coverage.* We ship a regression suite of 21 WHO IMCI test scenarios with known-correct outcomes. Every commit runs them. If a change breaks a scenario, the change does not merge.

**What still slips through:** scenarios outside the golden set. The WHO IMCI chart book has roughly 60 distinct decision branches; we cover the 21 most common. Gaps are tracked in `docs/TESTING_STRATEGY.md`.

### Failure 4 — The fine-tuned breath-sound model is wrong

We achieved 40% overall, 85% crackle detection on held-out patients from the ICBHI 2017 dataset (notebook 06). That is a real number. It is not a clinical-grade number.

**Defence:** *Tiered confidence.* The phone never makes a decision based on breath-sound alone — it's one signal of many. The clinic server adds it as supplementary evidence to a nurse's existing assessment. The nurse is the decision-maker. Malaika is a colleague, not a replacement.

**What still slips through:** edge cases the ICBHI 2017 dataset doesn't cover well — small children under 1 year (the dataset skews older). We say this in the model card.

### Failure 5 — The phone's GPU OOMs mid-session

Real failure mode. Documented. Samsung A53's Mali-G68 has roughly 200 MB of headroom above what Gemma 4 E2B needs.

**Defence:** *Fresh sessions per inference.* We tear down the LLM session between calls to flush KV cache. We use gallery photos instead of live camera surfaces. We disable in-app camera preview entirely. We tested on the worst phone we could find (A53) and made it work there before claiming any feature.

**What still slips through:** even cheaper phones with less GPU may not run E2B at all. The README's *minimum spec* is honest: 4GB RAM, GPU with at least 2.6 GB allocatable, Android 11+.

### Failure 6 — Gemma 4 hallucinates a finding

Possible. LLMs hallucinate. That is what they do.

**Defence:** *Three-layer guards.* Input validation, content filter (prompt-injection defence + PII scrub), output validator (JSON schema + confidence gating). Plus the deterministic classification layer that ignores findings outside the WHO key list. If Gemma hallucinates "the child has a unicorn horn," the classifier just doesn't have a rule for that and the finding is dropped on the floor.

**What still slips through:** plausible-but-wrong findings within the allowed schema (e.g., "sunken eyes" when there are none). Caught by reconciliation if it disagrees with the verbal Q&A.

### Failure 7 — A caregiver follows an outdated instruction

Possible if the WHO updates IMCI and we haven't shipped a new APK.

**Defence:** *Versioned protocol.* Every classification card shows the IMCI revision date and the WHO chart-book page. The README has a public update log. Local NGOs deploying the app are contacted directly when WHO publishes major revisions.

**What still slips through:** users who never update the app. Mitigation: the app gracefully nags after 6 months with no update; after 12 months it requires the user to acknowledge a "this protocol may be outdated" warning at startup.

---

## What "Failure" Looks Like at Scale

If Malaika is deployed to a hundred thousand caregivers and every assumption above holds:

- **Some caregivers will get a wrong assessment.** Some children will be sent to a clinic who didn't need to go (false RED). Some children will be told to monitor at home who needed to go (false GREEN). Both happen with WHO-trained nurses, too. Both happen now, without Malaika.

- **The honest comparison is not "perfect software vs the status quo."** The honest comparison is *"imperfect software in every village, vs perfect software in zero villages."* The Cochrane review on IMCI showed a fifteen-percent mortality reduction with imperfect human implementation. The bar isn't perfection. The bar is **better than no protocol at all.**

- **Pneumonia kills a child every thirty-nine seconds.** If Malaika is deployed and reduces that to forty, we have changed the world. If it changes nothing, we have at least shipped open source so that someone better than us can pick up where we left off.

---

## Lines We Won't Cross

If we are ever asked to do any of the following — for funding, for a partnership, for a deployment, for any reason — we will say no:

- **Add a paid tier that gates clinical features.** Malaika is Apache 2.0. There is no premium edition. Ever.
- **Phone home with patient data for "model improvement."** Privacy is the product. We do not sell the children we are trying to save.
- **Use Malaika as a marketing surface.** No ads. No upsell. No partner offers. The screen real estate belongs to the child, the mother, and the WHO.
- **Trade clinical accuracy for engagement metrics.** Daily-active-users is not a metric we will optimise for. Lives is the metric.
- **Replace the WHO protocol with our own opinion of what works.** The protocol is the medicine. We are the wrapper.
- **Ship a feature without a working fallback.** Every LLM call has a deterministic fallback path. If we can't write the fallback, we don't ship the feature.

---

## What This Document Is For

Three reasons we wrote this:

1. **For the judges.** When you have read 600 hackathon submissions claiming to "cure" cancer, "solve" hunger, and "revolutionize" healthcare, you have earned the right to be cynical. This document is what we wrote because we are cynical too. We do not believe Malaika cures or solves or revolutionises anything. We believe it can put a protocol that already saves lives into the hands of caregivers who currently don't have it. That is what we are claiming. Nothing more.

2. **For the clinicians.** When a doctor reads this repo, the first question is "what won't this do?" — because that is the question that determines whether a doctor can recommend it. We answered it on page one.

3. **For us.** Six months from now, when the hackathon is over and the trophy is on a shelf, we will read this document again before we make any decision about what to add or change. The list of things we will not do is what keeps Malaika what it is meant to be.

---

*Last updated: 2026-04-30. Authored by the Malaika team.*
