# MALAIKA — TWO-PRESENTER READING SCRIPT

*Vimal (V) carries the story and the impact. Mark (M) carries the engineering and the demo.*
*~8:30 total. Pause where it says (pause). Breathe where there's a blank line.*

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

Every number you'll hear in this video is sourced. UNICEF. WHO. The Cochrane Review. Peer-reviewed journals. The citations will be on screen.

We are not here to make you cry. We are here to show you what the data shows.

**The data is the story.** The emotion is what the data does to you.

---

## 2. THE NUMBERS  *(0:50 – 1:35)*  · **VIMAL**

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

## 3. THE STORY  *(1:35 – 2:50)*  · **VIMAL**

I want to tell you about a real moment, documented in a peer-reviewed study from South Africa.

A young mother in Umlazi has just been discharged from a hospital with her newborn baby.

She gets on the bus.

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

In rural Uganda, the median mother waits **two full days** before seeking professional care for a child with pneumonia.

For pneumonia, two days is the entire window between life and death.

It isn't because she doesn't love her child. It's because the nearest clinic is twenty kilometres away. There's no taxi. There's no money for a taxi. The road is gone after the rains.

She does what mothers everywhere have always done. She holds her child. She prays. She hopes the morning brings a fever that breaks on its own.

For about half of those mothers — the morning does not.

---

## 4. WHY THIS HAPPENS  *(2:50 – 3:35)*  · **VIMAL**

Here is the part nobody talks about.

The World Health Organization has a protocol for exactly this situation. It's called **IMCI** — Integrated Management of Childhood Illness.

When IMCI is fully implemented, it cuts under-five mortality by **fifteen percent**. That's a Cochrane systematic review. Sixty-five thousand participants.

But to learn IMCI properly, a nurse has to go through eleven days of residential training. It is expensive.

And meanwhile, Africa as a continent has **one point five health workers per thousand people**. The WHO minimum is **four point four five**. By 2030, the shortage hits **six point one million** workers.

(pause)

The protocol that could save a million children a year is sitting in a manual, in a drawer, in a clinic, in a town that most caregivers will never reach.

That is not a medical problem.

**That is a distribution problem.**

---

## 5. THE PARADOX  *(3:35 – 4:00)*  · **VIMAL**

But something has changed.

**The phone got to the village before the doctor did.**

Four hundred and eighty-nine million unique mobile subscribers in Sub-Saharan Africa today. A working Android smartphone for sixty US dollars. Less than the cost of a single hospital visit.

The phone is already in the mother's hand. Already in the village. Already charged.

So we asked one question.

(pause)

What if the phone could **be** the doctor?

(half-beat — V steps back, M steps forward)

---

## 6. THE ENGINEERING  *(4:00 – 5:00)*  · **MARK**

I'm Mark. I'm the engineer on this team.

Vimal asked the question. I want to tell you what it took to answer it.

Putting a doctor inside a sixty-dollar phone is harder than it sounds. We tried.

The bigger language models — they wouldn't fit. We tried separate models for text and vision — they wouldn't load together. We tried English-only models — that didn't help the mothers Malaika is for.

Then Google released **Gemma 4 E2B**.

Two billion active parameters. Two and a half gigabytes on disk. Text, vision, and multilingual reasoning — all in one single model.

It is the first model in the world that fits all of that on a sixty-dollar Android.

The "E" stands for *effective*. Gemma 4 was engineered with per-layer embeddings — so it has the knowledge of a four-billion-parameter model, but only spends two billion parameters of compute per response.

That is how you run AI this smart, on a phone this small.

(pause)

There is no other model in the world that does this. Not Llama, not Phi, not Qwen — we benchmarked all of them. The benchmark table is in the README.

This entire app exists because Google chose to release Gemma **open-weights** — not behind an API, not behind a paywall. The weights themselves. On the device. In the mother's pocket.

---

## 7. THE ARCHITECTURE  *(5:00 – 5:30)*  · **MARK**

Inside Malaika is something we call the **belief state** — an internal map of what we know about the child, what is uncertain, and what still needs to be asked.

The WHO IMCI assessment is broken into **twelve clinical skills** — danger signs, breathing, dehydration, fever, nutrition, and so on.

Gemma decides which skill to invoke next, based on what the belief state already knows.

If Gemma is unsure, it asks again. If two findings contradict, it flags the conflict. If a danger sign appears, it stops everything and tells the mother to refer immediately.

That orchestration is what people call **agentic AI**. Gemma 4 has twelve hundred percent better tool use than Gemma 3.

Without that single capability, none of this would work on a phone.

---

## 8. THE DEMO  *(5:30 – 6:30)*  · **MARK**

*[Phone in hand. Pull down notification shade. Airplane mode is on. Hold for two seconds.]*

This is a sixty-dollar Android phone. Airplane mode is on. There is no SIM card. There is no Wi-Fi.

From this point on, nothing leaves this device.

*[Tap the Malaika icon. App opens. A warm voice greets in Swahili.]*

This is **Malaika**. The word means *Angel*, in Swahili.

*[Demo: app asks "How old is your child?" Mother answers in Hausa. English caption appears live.]*

It asks the same questions a WHO-trained nurse would ask — in any language she speaks.

*[Demo: gallery photo. Vision analysis runs on screen.]*

Then it asks for one photo. And Gemma looks at the child the way a nurse would look. Is she alert? Are the eyes sunken? Are the ribs visible? Is there swelling?

*[Demo: classification card appears in red. "SEVERE PNEUMONIA — REFER URGENTLY".]*

And then — and this part matters — Malaika does **not** diagnose.

Every classification you see is hard-coded WHO IMCI thresholds. Deterministic medicine. Not a model's guess.

We do not let an AI decide whether a child lives or dies. The AI's job is the human part — listening, looking, translating. The medicine belongs to the WHO.

*[Demo: treatment screen — amoxicillin, refer urgently, do not wait.]*

The output is a clear instruction in her language. What to give. What to do. When to go.

This whole flow works on the phone. Offline. Forever.

---

## 9. THE TWO-TIER VISION  *(6:30 – 7:00)*  · **MARK**

But the phone is only the first tier.

In a small district hospital — a clinic ten kilometres from the remotest village, with one nurse and one Wi-Fi router — we run a **second tier**: a clinic server with the bigger **Gemma 4 E4B model**, plus a LoRA adapter we fine-tuned ourselves on the ICBHI 2017 respiratory dataset.

That fine-tuned adapter does what the phone honestly can't — it analyses breath-sound spectrograms for wheeze and crackle detection. We hit eighty-five percent crackle detection on held-out patients. The full numbers are in the repo's notebook 06.

When the phone has Wi-Fi, it offloads the audio analysis to that clinic server. When it doesn't, it falls back to the on-device model. Same Gemma family. Same open-weights story. Same on-device privacy — the clinic server is the clinic's own hardware.

The phone in the village. The fine-tuned model in the clinic. The same architecture, scaled across two tiers of care.

(half-beat — M steps back, V steps forward)

---

## 10. THE STORY, AGAIN  *(7:00 – 7:30)*  · **VIMAL**

I want to take you back to the bus.

(pause)

The mother in Umlazi. Same midnight. Same fever.

This time — this time — there is a sixty-dollar phone in her bag.

She opens Malaika. She speaks in her own language. She holds the phone over her child for one photo.

In thirty seconds, before the bus has reached the next stop, she has the same answer a WHO nurse would give her:

**Severe respiratory distress. Return to the hospital now. This is an emergency.**

She gets off at the next stop. She turns around. She goes back.

(pause)

That is the entire difference. Not a hospital. Not a doctor. Not a billion-dollar piece of medical equipment.

A phone she already owned, and a protocol that finally reached her.

---

## 11. WHAT THIS MEANS  *(7:30 – 7:45)*  · **VIMAL**

If Malaika gets us anywhere close to that fifteen-percent IMCI number, we are talking about **one hundred and seventy-five thousand** children, every year, who would still be alive.

Four hundred and eighty children. Every single day. Still in their mothers' arms.

And that is just two diseases. That is just the deaths we counted.

---

## 12. THE CLOSE  *(7:45 – 8:30)*  · **VIMAL** *(M stands beside, silent)*

Malaika is open source. Free. Forever. Apache 2.0.

We built it on Gemma — Google's open-weights model — because the AI that decides whether a child lives must not belong to a company.

It has to belong to everyone.

(pause)

I'm a storyteller. Mark is an engineer. Neither of us is a doctor.

We built Malaika in thirty-six days, because once you read these numbers — you cannot unread them.

**That is what hackathons are for.** To take ideas that should exist, and force them into the world.

This started on a whiteboard. Today it runs on a sixty-dollar phone. Tomorrow it can run in any village on earth.

You can fork it tonight. Translate it tomorrow. Deploy it next week.

(pause — V looks straight into the lens. M holds still beside him.)

Pneumonia kills a child every thirty-nine seconds.

(pause)

**The next thirty-nine seconds belong to us.**

*[Hold for two seconds of silence. Both stay still. Then logo card.]*

---

## END CARD

> **Malaika** — *Angel, in Swahili.*
>
> Open-source WHO IMCI assistant.
> Powered by **Gemma 4 E2B** on the phone (offline, $60 Android).
> Powered by **Gemma 4 E4B + fine-tuned LoRA** on the village clinic server (basic internet).
>
> Apache 2.0 · github.com/malaika-ai

---

## SPEAKER TIME BREAKDOWN

| Speaker | Sections | Approx. time | Share |
|---------|----------|-------------:|------:|
| **Vimal** | 1, 2, 3, 4, 5, 10, 11, 12 | ~5:30 | 65% |
| **Mark** | 6, 7, 8, 9 | ~3:00 | 35% |

Vimal carries the human arc — open, problem, story, redemption, close.
Mark carries the engineering arc — model choice, architecture, demo, two-tier vision.

The split mirrors the film's central tension — *the human story is the medicine; the engineering is what delivers it.*

---

## DELIVERY NOTES

- **Pace** ~135 wpm. Pauses are weapons — let silence land.
- **Mark's tone:** restrained, factual, slightly proud. Engineer voice — accurate but warm. Not a sales pitch.
- **Vimal's tone:** restrained, urgent, reflective. The numbers should sound like he's reading them off a wall he's stared at for a month.
- **No background music** until the final logo card. The breathing audio in §1 and the silences are doing all the emotional work.

*End of script. ~1,560 words. ~8:30 at conversational pace, two-presenter format.*
