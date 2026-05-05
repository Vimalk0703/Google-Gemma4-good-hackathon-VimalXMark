# MALAIKA — TWO-PRESENTER READING SCRIPT

*Vimal (V) carries the story and the impact. Mark (M) carries the engineering and the demo.*
*~11:15 total. Pause where it says (pause). Breathe where there's a blank line.*

---

## TURN-TAKING NOTES — read these before recording

- **Vimal opens** and **Vimal closes**. The story has one voice — Mark joins for the technical middle and the demo.
- **Hand-offs are silent.** When V finishes, hold half a beat, then M starts. No "and now Mark will tell you about…" — that wastes runtime and breaks the rhythm. The audience figures it out instantly.
- **On stage: V is on the left, M is on the right** (mirror it on camera). When the active speaker is talking, they step a quarter-step forward; the other holds still and listens. The geometry tells the audience who to watch.
- **Both stay on camera the whole film.** No cuts to "just Vimal" or "just Mark." The team is the message: an engineer and a storyteller, working together to make this real.
- **The final close is shared.** V delivers the last two lines. M stands beside him in silence. The image is the team handing the project to the audience.

---

## 1. OPEN  *(0:00 – 0:30)*  · **VIMAL**

Hi. I'm Vimal.

Before I tell you anything about what we built — I want you to listen to something for ten seconds.

*[breathing audio plays — child with pneumonia, fast and shallow]*

That is the sound of a child with pneumonia.

In the time it took you to listen to that — somewhere in the world, a child stopped breathing.

(pause)

This isn't a film about a rare disease.

It's about a disease we have a vaccine for. A five-cent antibiotic for. A protocol the World Health Organization wrote thirty years ago.

And it's still killing more than seven hundred thousand children. Every year.

(pause)

Before we go any further — one thing.

Every claim in this video has a citation. If a number is on screen, the source is in our `SOURCES.md` file. UNICEF. WHO. The Cochrane Review. Peer-reviewed journals.

We even keep a separate document — *Reasons We Will Fail* — listing every limit Malaika has, on purpose. We did not come here to overclaim. We came here with receipts.

**The data is the story.** The emotion is what the data does to you.

---

## 2. THE NUMBERS  *(0:30 – 1:15)*  · **VIMAL**

In 2024, **four point nine million** children did not see their fifth birthday.

That is the population of an entire country — gone, every single year.

**Fifty-eight percent** of them — in Sub-Saharan Africa.
**Twenty-five percent** — in South Asia.

And of those four point nine million, more than **one point one million** were killed by just two diseases.

Pneumonia. And diarrhea.

(pause)

The headline I cannot get out of my head is this.

**A child dies from pneumonia every thirty-nine seconds.**

(pause)

In the next seven minutes of this video, we will lose ten children — to a disease the medicine could have saved.

The medicine exists. The science is settled.

So why are children still dying?

---

## 3. THE STORY  *(1:15 – 2:15)*  · **VIMAL**

I want to tell you about a real moment, documented in a peer-reviewed study from South Africa.

A young mother in Umlazi has just been discharged from a hospital with her newborn baby. She gets on the bus.

Halfway home, the baby starts breathing too fast.

She knows something is wrong. She *knows*.

She wants to get off the bus and go straight back to the hospital.

(pause)

She doesn't have the bus fare to do it.

(pause)

She rides the rest of the way home. She holds her child. She watches him breathing. She prays.

By the time she steps off at her stop — the baby has died.

(long pause)

That is a published case. It happened.

It was not the medicine that failed her. It was the **distance** between her and the medicine — and the **cost** of crossing it.

In rural Uganda, the median mother waits **two full days** before seeking professional care for a child with pneumonia. For pneumonia, two days is the entire window between life and death.

It isn't because she doesn't love her child. It's because the nearest clinic is twenty kilometres away. There's no taxi. There's no money for a taxi. The road is gone after the rains.

She does what mothers everywhere have always done. She holds her child. She prays.

For about half of those mothers — the morning does not bring relief.

---

## 4. WHY THIS HAPPENS  *(2:15 – 2:55)*  · **VIMAL**

Here is the part nobody talks about.

The World Health Organization has a protocol for exactly this situation. It's called **IMCI** — Integrated Management of Childhood Illness.

When IMCI is fully implemented, it cuts under-five mortality by **fifteen percent**. That's a Cochrane systematic review. Sixty-five thousand participants.

But to learn IMCI properly, a nurse goes through eleven days of residential training. Africa has **one and a half** health workers per thousand people. The WHO minimum is **four and a half**. By 2030, the shortage hits **six million** workers.

(pause)

The protocol that could save a million children a year is sitting in a manual, in a drawer, in a clinic, in a town that most caregivers will never reach.

That is not a medical problem.

**That is a distribution problem.**

---

## 5. THE PARADOX  *(2:55 – 3:20)*  · **VIMAL**

But something has changed.

**The phone got to the village before the doctor did.**

Four hundred and eighty-nine million unique mobile subscribers in Sub-Saharan Africa today. A working Android smartphone for sixty US dollars. Less than the cost of a single hospital visit.

The phone is already in the mother's hand. Already in the village. Already charged.

So we asked one question.

(pause)

What if the phone could **be** the doctor?

---

## 6. WHY PNEUMONIA  *(3:20 – 3:45)*  · **VIMAL**

Why this disease, and not the dozen others?

Three reasons.

**One.** Pneumonia is the largest single killer of children under five with a *known, written, peer-reviewed* protocol. The medicine is solved.

**Two.** IMCI is the only WHO under-five protocol that is **multimodal by design.** You **listen** to the breathing. You **look** at the child. You **ask** the mother. No other under-five killer needs all three modalities in one moment.

**Three.** Gemma 4 is the first model in the world that does all three modalities — on the phone the mother already owns.

The problem and the model fit each other exactly. That is not a coincidence we are claiming. That is a coincidence we are exploiting.

(pause)

And this is an **unsolved problem.** The medicine is solved. The protocol is solved. The science is solved.

What has never been solved is *how* to put a WHO-trained nurse next to every child in every village in the world.

For thirty years, the answer was *"train more nurses."* It has not worked. It cannot work in time.

Until last year, there was no other answer. **Now there is.**

(half-beat — V steps back, M steps forward)

---

## 7. THE MODEL CHOICE  *(3:45 – 4:35)*  · **MARK**

I'm Mark. The engineer.

Vimal's job for thirty-six days was to keep asking — *"could the phone* **be** *the doctor?"* My job was to make sure that sentence shipped as a binary. Not a metaphor.

We tested the small open models that come closest. Each one is missing at least one of the four constraints we need — *small enough to fit, vision-capable, fluent in the languages our users speak, and agentic.*

**Llama 3.2** has two flavours. The 1B and 3B fit on a phone — but they are text only. The 11B *Vision* variant adds image understanding — but at roughly eight gigabytes, it does not fit on a sixty-dollar Android.

**Phi-3.5 Vision** is the right size at four-bit quantisation, and it does have vision. But Microsoft built it primarily for English — it was not trained to speak Swahili, Hausa, or Yoruba.

**Qwen 2.5 VL** at three billion has vision too, and it's strong on Chinese, English, and a handful of European languages. African-language coverage, again, is the weak link.

**Gemma 4 E2B** is the only model that combines *all four* — small enough to fit in two and a half gigabytes, vision-capable, multilingual across a hundred and forty languages including the African ones our users actually speak, and *agentic* — engineered for the twelve-skill tool-use orchestration the assessment needs.

The "E" stands for *effective*. Gemma 4 is engineered with **per-layer embeddings** — it has the capability of a four-billion-parameter model, but only spends two billion parameters of compute per response.

That is how you run AI this smart, on a phone this small.

(pause)

This entire app exists because Google chose to release Gemma **open-weights** — not behind an API, not behind a paywall. The weights themselves. On the device. In the mother's pocket.

---

## 8. THE ARCHITECTURE — BELIEF STATE & SKILLS  *(4:35 – 5:30)*  · **MARK**

Inside Malaika is something we call the **belief state**. It is simpler than it sounds.

It is three lists, kept in memory while Malaika talks to the mother.

**What we have confirmed.** Findings the model has heard, seen, or extracted with high confidence. *"Cough — three days. Refusing fluids. Ribs not visible."*

**What is uncertain.** Findings flagged as low-confidence — or contradicted by another signal. *"Mother says alert. Photo says lethargic. Confirm."*

**What is still pending.** IMCI questions the protocol says we have not yet asked.

Every answer the mother gives, every photo she takes, updates one of those three lists. That is the belief state. *That* is what makes the agent agentic.

(pause)

Around it is the **skill registry** — twelve clinical skills, each one a typed tool Gemma 4 can invoke.

**Six skills look at the child** — alertness, skin colour, chest indrawing, dehydration signs, wasting, and edema.

**Three skills listen and count** — parse the mother's natural-language answer, count the breathing rate, classify breath sounds.

**Three skills decide and explain** — apply the WHO IMCI thresholds, generate the treatment plan, and speak it back in the mother's language.

Twelve skills. Real, named, in `malaika/skills.py`. Count the registrations yourself.

Gemma decides which skill to invoke next, based on what the belief state already knows. If two findings contradict, it flags the conflict. If a danger sign appears, it stops everything and tells the mother to refer immediately.

That orchestration is what people call **agentic AI**. Gemma 4 has a **twelve-hundred-percent** improvement in tool use over Gemma 3. Without that single capability, the twelve-skill agent would need a server. With it, the agent runs in the mother's pocket. **That is the entire difference between a chatbot and a clinic.**

---

## 9. WHY FINE-TUNE — AND WHY *NOT*  *(5:30 – 6:25)*  · **MARK**

The honest engineering question is — *why* fine-tune Gemma at all? And the question most teams skip — *what didn't we fine-tune?*

The answer changes by modality.

**For vision — we did not fine-tune.** Base Gemma 4 already sees a sunken eye. A visible rib. An alert face. It already does, out of the box, what a nurse's eyes do. A system prompt — *"look for these clinical signs, return JSON"* — is enough. Fine-tuning would have added complexity, slowed inference, and not improved accuracy. **The simplest version that works is the right version.**

**For breath sounds — we had to.** A mel-spectrogram is not in Gemma's base training distribution. The model has the eyes; it does not have the medical mapping between *vertical bursts at two-hundred hertz* and *crackles*. The base model literally cannot read spectrograms as clinical signal — it describes them as *"blue regions and vertical lines."* So we taught it.

Sixty steps of QLoRA. The **ICBHI 2017** respiratory dataset — nine hundred and twenty real recordings, held out by *patient*, not by sample. Eighty-two megabytes of LoRA weights on top of a model that already speaks the mother's language and already understands her child's photo.

**The same brain that runs the IMCI assessment is the brain that hears the wheeze.** One model. One deployment. One open-weights story.

On held-out patients, **eighty-five percent crackle detection.** That is a real number. It is also hackathon-grade — not FDA-cleared. The seed, the split, and the eval cell are in notebook six. We also publish a *base-versus-fine-tuned comparison notebook* — same data, same task, two models — so you can see *exactly* what the LoRA adds. Plan is in `docs/NOTEBOOK_13_BASE_VS_FINETUNED_PLAN.md`.

(pause)

That is our engineering principle, in one line: **fine-tune only what the model cannot already see.** Not as a cost-cutting move — as a discipline. The simplest engineering decision a team can make is the one that does *not* call for a custom model. We optimise for the *boundary* between what the base model already knows and what it has never been shown — and only cross that boundary when we have to.

---

## 10. THE PHONE DEMO  *(6:25 – 7:25)*  · **MARK**

*[Phone in hand. Pull down notification shade. Airplane mode is on. Hold for two seconds.]*

This is a sixty-dollar Android phone. Airplane mode is on. There is no SIM card. There is no Wi-Fi.

From this point on, nothing leaves this device.

*[Tap the Malaika icon. App opens. A warm voice greets in Swahili: "Habari. Mimi ni Malaika."]*

This is **Malaika**. The word means *Angel*, in Swahili.

*[Demo: app asks "How old is your child?" Mother answers in Hausa. English caption appears live.]*

It asks the same questions a WHO-trained nurse would ask — in any language she speaks. Swahili. Hausa. Hindi. Bengali. Yoruba. Amharic. Portuguese. The mother does not adapt to the phone. The phone adapts to her.

*[Demo: gallery photo. Vision analysis runs on screen.]*

Then it asks for **one** photo. From the gallery. Not live camera — the GPU on a sixty-dollar phone cannot hold the language model and a camera surface at the same time. We could fake a live preview by demoing on a Pixel 9. We chose not to. *The phone in this demo is the phone in the village.*

Gemma looks at the child the way a nurse would look. Is she alert? Are the eyes sunken? Are the ribs visible? Is there swelling?

*[Demo: classification card appears in red. "SEVERE PNEUMONIA — REFER URGENTLY".]*

And here is the part that matters most. **Malaika does not diagnose.**

Here is the line we drew, and we drew it on purpose.

**Gemma's job is perception.** It listens to the mother. It looks at the child. It translates between Hausa and Swahili and English. It extracts the findings into structured JSON.

**The medicine's job is decision.** Every red card you see on this screen is a hard-coded WHO IMCI threshold — written into Dart, with the chart-book page cited above the line. Not a probability. Not a model's guess. Not a hallucination.

If Gemma reports a finding wrong, the threshold either ignores it or the reconciliation engine flags the conflict. If the WHO updates a threshold next year, we change one line of code.

**The boundary between what AI does and what code does is the entire safety story of this product.**

We do not let an AI decide whether a child lives or dies. The AI's job is the human part — listening, looking, translating. The medicine belongs to the World Health Organization.

*[Demo: treatment screen — amoxicillin, refer urgently, do not wait.]*

The output is a clear instruction in her language. What to give. What to do. When to go.

This whole flow works on the phone. Offline. Forever.

---

## 11. THE OTHER APP — THE CLINIC PORTAL  *(7:25 – 8:20)*  · **MARK**

Two surfaces. Two users. Two designs.

The Android app you just saw is for **the mother.** Fully offline. In her pocket. In her language. Built for a sixty-dollar phone in a village with no signal.

**The clinical portal is for the nurse.** A different product, a different user, a different shape — built for a clinic with one Wi-Fi router and one laptop.

It is *not* a fallback. The phone never calls the clinic. The clinic never calls the phone. They are independent products that share one architecture.

Why two? Because the phone has one honest limit. It cannot listen to a child's chest. The Mali GPU on a sixty-dollar Android can hold the language model **or** a spectrogram pipeline — not both.

So in the village clinic — ten kilometres away, with a three-hundred-dollar mini-PC — we run **Gemma 4 E4B** plus the LoRA adapter we just talked about.

*[Mark turns to laptop. Browser is on `/portal`. Passcode field. Drop-zone for audio.]*

This is the **clinical portal.** Passcode-gated, browser-based, runs on any laptop the clinic already owns. A nurse drops a thirty-second recording —

*[Demo: drop a `.wav`. Progress: upload → spectrogram → inference. Result card appears.]*

— three seconds later, on the clinic's GPU, she gets back the classification, the confidence, and a **senior-nurse-voice clinical note** generated by a *second* Gemma pass.

No app to install. No SDK. No cloud. The audio file goes from the nurse's browser to the clinic's own server, and back.

**Same Gemma family. Same open-weights story.** Same on-device privacy — the clinic server is the clinic's own hardware.

The mother's phone in the village. The nurse's laptop in the clinic. Two apps, two users, **one architecture**, scaled across two tiers of care.

(half-beat — M steps back, V steps forward)

---

## 12. THE STORY, AGAIN  *(8:20 – 9:10)*  · **VIMAL**

I want to take you back to the bus.

(pause)

The mother in Umlazi. Same midnight. Same fever.

This time — this time — there is a sixty-dollar phone in her bag.

She opens Malaika. She speaks in her own language. She holds the phone over her child for one photo.

In thirty seconds — before the bus has reached the next stop — she has the same answer a WHO nurse would give her:

**Severe respiratory distress. This is an emergency. Return to the hospital now.**

(pause)

Now — let me be honest about what Malaika does and does not do.

Malaika does not give her bus fare. The first time, she did not go back because she did not have it. That has not changed.

What *has* changed is the **certainty.** The first time, she did not know whether the next thirty minutes were *"maybe-fine, see how she sleeps"* — or life-or-death. With Malaika, she knows. The protocol of the World Health Organization — in her hand, in her language — said so.

That certainty is what she did not have the first time. With it, she has something to fight with. To beg the driver. To wake a neighbour. To borrow. To walk the road if she has to.

It is not enough. **But it is everything she did not have before.**

She gets off at the next stop. She does whatever she can. She goes back.

(pause)

And in the morning — when she walks into the district clinic — the same nurse who would have spent two hours on her case opens a laptop, drops the audio recording the phone made on the bus, and gets back a clinical note in three seconds.

A phone in her hand. A laptop in the clinic. The same architecture, scaled across two tiers of care — built by two people, in thirty-six days, with code that anyone in this room can fork tonight.

---

## 13. WHAT THIS MEANS  *(9:10 – 9:30)*  · **VIMAL**

If Malaika gets us anywhere close to that fifteen-percent IMCI number, we are talking about **one hundred and seventy-five thousand** children, every year, who would still be alive.

Four hundred and eighty children. Every single day. Still in their mothers' arms.

That is a *projection*, not a measurement. The fifteen percent comes from human-delivered IMCI in the Cochrane review. We are claiming Malaika *could* approach that number. We have not proven it. We will say it that way until we have.

And that is just two diseases. That is just the deaths we counted.

---

## 14. THE CLOSE  *(9:30 – 10:15)*  · **VIMAL** *(M stands beside, silent)*

Malaika is open source. Free. Forever. Apache 2.0.

We built it on Gemma — Google's open-weights model — because the AI that decides whether a child lives must not belong to a company.

**It has to belong to everyone.**

(pause)

Here is what we believe, as engineers.

Technology is not just for business optimisation and growth. **It is for communities.** It is for enhancing and impacting human lives — in every possible way that the people building it can imagine.

AI is the most powerful lever any of us will hold in our careers. **Open weights are how that lever gets out of the data centre and into the hands of people.** Google's Gemma 4 is — right now, today — the clearest path the industry has chosen to put cognition into anyone's hands. Not as customers of an API. As citizens of a model.

That is what *decentralising access to technology* means. Not a slogan. **A file you can read, modify, and ship.**

(pause)

I'm Vimal. I architect enterprise AI systems at scale.

Mark is an electronics and edge-AI engineer — he knows what it takes to make a model run on hardware most engineers ignore.

Neither of us is a doctor.

This started in a coffee shop. We were planning a workshop on open source — what it means as a public good. The same week, Google released Gemma 4. The same week, we found this hackathon. **The world handed us a model, a deadline, and a problem — and we said yes.**

(pause)

We could have built this for agriculture — pest detection on-device, in the farmer's hand.
For education — a tutor in any language a child speaks.
For finance, for climate, for accessibility, for justice.
Open source has a use case in every industry the competition lists.

We chose children.

Because we do not know which child becomes the next **Sundar Pichai** — the boy from a two-room home in Tamil Nadu who today runs the company that built the model in this video.

The next **Wangari Maathai** — the village girl from Kenya who won the Nobel Peace Prize for planting tens of millions of trees in her country.

The next **Yusuf Hamied** — the Indian chemist who pushed generic medicines into the hands of millions of Africans who could not otherwise afford them.

We do not know which one of those four point nine million children, lost every year before the age of five, would have changed the world.

**Everyone deserves a place in this world.**

(pause)

Hackathons are not just for prizes. They are for forcing into existence the things that *should* exist. We won our first hackathon — and discovered a way of building we could not have planned. We came to this one by choice.

If Malaika gets us anywhere close to the fifteen-percent IMCI number — one hundred and seventy-five thousand children, every year — *that is not an ambition.* That is **a vision Gemma 4 makes achievable.** Not by us alone. By anyone, anywhere, who forks it tonight.

You can fork it tonight. Translate it tomorrow. Deploy it next week.

(pause — V looks straight into the lens. M holds still beside him.)

Pneumonia kills a child every thirty-nine seconds.

(pause)

**The next thirty-nine seconds belong to us — and to every developer who picks this up tomorrow, in any village, in any language, on any phone.**

*[Hold for two seconds of silence. Both stay still. Then logo card.]*

---

## END CARD

> **Malaika** — *Angel, in Swahili.*
>
> Open-source WHO IMCI assistant.
> Powered by **Gemma 4 E2B** on the phone (offline, $60 Android).
> Powered by **Gemma 4 E4B + fine-tuned LoRA** on the village clinic server (basic internet).
> A passcode-gated **clinical portal** so any nurse with a browser can use it.
>
> Apache 2.0 · github.com/malaika-ai

---

## SPEAKER TIME BREAKDOWN

| Speaker | Sections | Approx. time | Share |
|---------|----------|-------------:|------:|
| **Vimal** | 1, 2, 3, 4, 5, 6, 12, 13, 14 | ~6:25 | 63% |
| **Mark** | 7, 8, 9, 10, 11 | ~3:50 | 37% |

Vimal carries the human arc — open, problem, story, why-pneumonia, redemption, close.
Mark carries the engineering arc — model choice, belief-state-and-skills, fine-tuning principle, phone demo, clinic portal.

The split mirrors the film's central tension — *the human story is the medicine; the engineering is what delivers it.*

---

## DELIVERY NOTES

- **Pace** ~135 wpm. Pauses are weapons — let silence land.
- **Mark's tone:** restrained, factual, slightly proud. Engineer voice — accurate but warm. Not a sales pitch.
- **Vimal's tone:** restrained, urgent, reflective. The numbers should sound like he's reading them off a wall he's stared at for a month.
- **No background music** until the final logo card. The breathing audio in §1 and the silences are doing all the emotional work.
- **§11 needs a laptop on a side table.** Practice the camera-cut from phone (§10) to laptop (§11) — keep both visible if possible. The visual is *"two devices, one architecture."*
- **The "hackathon-grade, not FDA-cleared" line in §9 is a feature, not an apology.** Deliver it with the same quiet pride as the 85% number itself. Honesty is the moat.
- **The bus-fare honesty beat in §12 is the line that separates Malaika from every other "AI for good" pitch.** Slow down. Let the audience see that we know what our software does and what it does not. That single beat earns every other claim in the film.
- **§14 names three world-changers** (Sundar Pichai, Wangari Maathai, Yusuf Hamied). Pronounce each one carefully. They are not decoration — they are the receipt for "everyone deserves a place in this world."

*End of script. ~2,650 words. ~11:15 at conversational pace, two-presenter format.*
