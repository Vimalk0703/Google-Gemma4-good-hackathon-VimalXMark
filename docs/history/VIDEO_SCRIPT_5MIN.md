# MALAIKA — 5-MINUTE PITCH CUT

*Vimal (V) carries the story. Mark (M) carries the engineering and the demos.*
*~5:00 total — including ~1:35 of pre-recorded demo clips inside §4 and §5.*
*Companion to the full-length director's cut at `VIDEO_SCRIPT_v2.md`.*

---

## TURN-TAKING NOTES

Same staging as the long-form: V on the left, M on the right. Both stay on camera throughout. Hand-offs are silent — no *"and now Mark will…"*. Demo clips play full-screen with their own audio — **both presenters off-camera and silent during clips.**

The five-minute cut moves at ~150 wpm, not the 135 of the long form. Pauses are still weapons — but pick fewer of them, and let each one land harder.

---

## 1. OPEN  *(0:00 – 0:30)*  · **VIMAL**

I'm Vimal.

*[breathing audio plays — child with pneumonia, fast and shallow — five seconds]*

That is the sound of a child with pneumonia.

In the time you just listened — somewhere in the world, a child stopped breathing.

(pause)

A child dies from pneumonia every **thirty-nine seconds.** From a disease we have a vaccine for, a five-cent antibiotic for, and a WHO protocol for.

Every claim in this video has a citation. We came here with receipts.

---

## 2. THE PROBLEM  *(0:30 – 1:10)*  · **VIMAL**

The medicine isn't the problem. The **distribution** is.

The WHO has a protocol — IMCI — that cuts under-five mortality by **fifteen percent.** That's a Cochrane review, sixty-five thousand patients. But to use IMCI, a nurse needs eleven days of training. Africa is **six million** health workers short.

The protocol is sitting in a manual, in a drawer, in a clinic, in a town the mother will never reach.

(pause)

But something has changed. **The phone got to the village before the doctor did.** Four hundred and eighty-nine million mobile subscribers in Sub-Saharan Africa. A working Android for sixty US dollars.

So we asked one question.

What if the phone could **be** the doctor?

(half-beat — V steps back, M steps forward)

---

## 3. WHY GEMMA 4  *(1:10 – 1:35)*  · **MARK**

I'm Mark. The engineer.

We need four things on a sixty-dollar phone — *small enough to fit, vision, the African languages our users speak, and agentic tool use.*

Llama 3.2 has no vision. Phi-3.5 Vision can't speak Swahili. Qwen 2.5 VL can't either. Llama 3.2-Vision doesn't fit.

**Gemma 4 E2B is the only model that does all four** — two and a half gigabytes, vision, a hundred and forty languages, and a twelve-hundred-percent improvement in tool use over Gemma 3. This entire app exists because Google released the weights open.

---

## 4. THE PHONE — WHAT IT DOES  *(1:35 – 2:55)*  · **MARK**

On the phone, Gemma does four jobs, end-to-end.

**It listens** — offline speech, in any language she speaks. **It looks** — six vision skills, one photo. **It reasons** — twelve clinical skills, hard-coded WHO thresholds. **It speaks** — offline text-to-speech, in the mother's language.

All of it runs on the phone's GPU. No SIM. No Wi-Fi. No cloud. Ever.

(half-beat)

Now look at a real assessment, in the Malaika app — on a real Samsung A53, in airplane mode. One continuous take.

*[—— PRE-RECORDED PHONE WALKTHROUGH PLAYS — ~55 seconds — full audio retained — see `DEMO_WALKTHROUGH.md` ——]*

*(Camera holds the demo full-screen. Both presenters off-camera and silent.)*

(half-beat — return to two-presenter shot)

The red classification card at the end is the part where Malaika **stops being AI.** Every threshold is hard-coded WHO IMCI, in Dart, with the chart-book page cited above the line.

**The boundary between what AI does and what code does is the entire safety story of this product.**

---

## 5. THE OTHER APP — THE CLINIC PORTAL  *(2:55 – 4:00)*  · **MARK**

The phone has one honest limit. It cannot listen to a child's chest. The Mali GPU on a sixty-dollar Android can hold the language model **or** a spectrogram pipeline — not both.

So in the village clinic ten kilometres away, on a three-hundred-dollar mini-PC, we run **Gemma 4 E4B plus a LoRA we fine-tuned on ICBHI 2017** — eighty-five percent crackle detection on held-out patients.

In front of it, a browser portal a nurse can open from any laptop. Live connection-health banner. Browser-native audio recording. And the defining feature — the **AI Clinical Note**: a second Gemma pass that writes a senior-nurse-voice paragraph for the chart, grounded in WHO IMCI.

(half-beat)

Look at the live portal.

*[—— PRE-RECORDED WEB PORTAL WALKTHROUGH PLAYS — ~40 seconds — full audio retained ——]*

> **What's on screen during this clip, in order:**
> landing → passcode sign-in → green connection-health banner → record-in-browser (15s of breath audio, encodes to WAV in-browser) → multi-stage progress (`upload → spectrogram → inference`) → result card (`abnormal · 91%` + spectrogram) → AI Clinical Note paragraph → WHO IMCI context block.

*(Camera holds the portal full-screen. Both presenters off-camera and silent.)*

(half-beat — return to two-presenter shot)

**Same Gemma family. Same open-weights story.** Two apps, two users, **one architecture** — scaled across two tiers of care.

(half-beat — M steps back, V steps forward)

---

## 6. THE HONEST BEAT  *(4:00 – 4:30)*  · **VIMAL**

I have to be honest about one thing.

There is a published case from South Africa — a mother in Umlazi, riding home from the hospital, knew her baby was breathing too fast. She wanted to get off the bus. She didn't have the bus fare. By the time she reached her stop, the baby had died.

Malaika does not give her the bus fare.

What it gives her is **certainty** — the same answer a WHO nurse would give her, in her language, in thirty seconds. With certainty, she has something to fight with. To beg the driver. To wake a neighbour. To borrow. To walk the road.

**It is not enough. But it is everything she did not have before.**

---

## 7. CLOSE  *(4:30 – 5:00)*  · **VIMAL** *(M stands beside, silent)*

Malaika is open source. Apache 2.0. Forever.

We built it on Gemma because **the AI that decides whether a child lives must not belong to a company. It has to belong to everyone.**

We do not know which of the four point nine million children we lose every year would have changed the world. The next Sundar Pichai. The next Wangari Maathai. The next Yusuf Hamied.

**Everyone deserves a place in this world.**

You can fork it tonight. Translate it tomorrow. Deploy it next week.

(pause — V looks straight into the lens)

Pneumonia kills a child every thirty-nine seconds.

**The next thirty-nine seconds belong to us.**

*[Hold for two seconds of silence. Then end card.]*

---

## END CARD

> **Malaika** — *Angel, in Swahili.*
>
> Open-source WHO IMCI assistant.
> Gemma 4 E2B on the phone (offline, $60 Android).
> Gemma 4 E4B + fine-tuned LoRA on the village clinic server.
>
> Full version (13:30): *[YouTube link]*
> Apache 2.0 · *[GitHub repo URL]*

---

## TIMING CHECK

| § | Time | Speaker | What |
|---|-----:|---------|------|
| 1 | 0:30 | V | Open · 39 seconds · receipts |
| 2 | 0:40 | V | Distribution problem · phone-in-the-village |
| 3 | 0:25 | M | Why only Gemma 4 |
| 4 | 1:20 | M | Phone capabilities · 55s recorded clip · safety boundary |
| 5 | 1:05 | M | Clinic portal capabilities · 40s recorded clip · architecture wrap |
| 6 | 0:30 | V | Bus-fare honesty |
| 7 | 0:30 | V | Close · open weights · 39 seconds |
| **Total** | **5:00** | | |

| Speaker / Source | Time | Share |
|------------------|-----:|------:|
| **Vimal** (live) | 2:10 | 43% |
| **Mark** (live) | 1:15 | 25% |
| **Pre-recorded clips** | 1:35 | 32% |

---

## WHAT WE COMPRESSED — AND WHY THE ESSENCE SURVIVES

Every cut was deliberate. The full-length cut still exists at `VIDEO_SCRIPT_v2.md` for the YouTube director's cut and the Kaggle media gallery.

| Cut from full | What survives in this cut | Where |
|---|---|---|
| §3 Umlazi story (~1:00) | Compressed into §6 (30s) — same emotional beat, two sentences instead of eight | §6 |
| §4 IMCI training/shortage detail (~40s) | The two numbers that matter — *fifteen percent · six million* — survive as one line | §2 |
| §6 Why pneumonia · three reasons (~40s) | Cut entirely — the 39-seconds headline already does the work | — |
| §7 Model-by-model competitor benchmark (~50s) | Compressed to four sentences naming each competitor's failure mode | §3 |
| §8 Belief state · 12 skills detail (~55s) | Compressed to *"twelve clinical skills, hard-coded WHO thresholds"* — the demo *shows* it | §4 |
| §9 Why fine-tune AND why not (~55s) | Compressed to *"fine-tuned on ICBHI 2017 · 85% crackle detection"* — the receipt survives | §5 |
| §12 Umlazi redemption beat (~50s) | Folded into §6 — *"certainty · what she did not have before"* | §6 |
| §13 175,000 children projection (~20s) | Cut — implied by §1 (39 seconds) and §2 (15%) | — |
| §14 closing essay (~90s) | Compressed to §7 (30s) — kept the three world-changers, *"everyone deserves a place"*, and the 39-seconds payoff | §7 |

**What we did NOT cut:**
- The 39-seconds hook (§1 open + §7 close)
- The "distribution, not medicine" framing (§2)
- The phone demo (§4)
- The two-tier architecture (§5)
- The AI Clinical Note mention (§5)
- The bus-fare honesty beat (§6)
- The open-weights philosophical close (§7)
- The three world-changers list (§7)

These eight beats are the soul of the long-form. If a judge watches only the five-minute cut, they get every beat that decides the score.

---

## DELIVERY NOTES

- **Pace ~150 wpm.** Brisker than the long form. Five minutes is tight — long pauses are a luxury we don't have. Two pauses per section, max.
- **Both demo clips run with their own audio.** Cut camera fully away — both presenters sit out the clip in silence, off-frame. Reframe to two-presenter the moment the clip ends. **Do not narrate over the demo audio.**
- **§6 — the honest beat — is the moral spine.** Don't rush it. The *"It is not enough. But it is everything she did not have before"* line is the line that separates Malaika from every other "AI for good" pitch in the competition.
- **§7 close — three beats, do not collapse them:** *(1)* open weights · belongs to everyone, *(2)* the three world-changers · everyone deserves a place, *(3)* every thirty-nine seconds · belongs to us. Each beat needs its own breath.
- **No background music** until the end card. The breathing audio in §1 carries every emotional beat that follows.
- **The clip cuts in §4 and §5** are the two highest-risk transitions of the film. Practice them. The audience must understand instantly that *"this is the actual app, doing the actual thing"* — not a render, not a mockup, not a Pixel 9 fake. The recorded clips already have that proof; don't talk over them.

*End of script. ~525 spoken words + ~1:35 of demo clips. ~5:00 at brisk conversational pace.*
