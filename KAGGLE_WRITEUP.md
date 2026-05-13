# Malaika — Kaggle Writeup (paste-ready)

> This file maps directly to the Kaggle Writeup form for **The Gemma 4 Good Hackathon**.
> Each section below corresponds to a field in the form. Copy and paste in order.
>
> **Submission deadline:** May 18, 2026, 7:59 PM EDT.
> **Word limit on Project Description:** 1,500 words (this draft: ~1,450).

---

## 1. Title  *(form field — max 80 characters)*

```
Malaika — A WHO child-survival assistant on a $60 phone, fully offline.
```

*(70 characters.)*

---

## 2. Subtitle  *(form field — max 140 characters)*

```
Open-source, multilingual, multimodal. Powered end-to-end by Gemma 4 — on every phone the village mother already owns. Apache 2.0.
```

*(133 characters.)*

---

## 3. Submission Track  *(form field — pick one)*

**Impact Track → Health & Sciences.**

*(Primary. The project is auto-eligible for the Main Track on overall merit, and for the Special Technology Track on Unsloth — we fine-tuned Gemma 4 E4B with Unsloth QLoRA — and LiteRT — the phone runs Gemma 4 E2B through LiteRT-LM.)*

---

## 4. Card and Thumbnail Image  *(form field — 560 × 280)*

Required dimensions: **560 × 280** (the form note overrides the 1280×720 mentioned elsewhere in the Kaggle rules — go with what the form says).

**Design brief for the editor / designer:**

- **Composition:** Hands of a mother holding a sleeping child, half in shadow. The child's face is calm. Mother's other hand holds a budget Android phone — Malaika's amber/gold wordmark glowing on screen. Background: dawn light through a corrugated-iron window. Warmth, not despair.
- **Top-third overlay (sans-serif, white):** *"Malaika — Angel, in Swahili."*
- **Bottom-third overlay:** *"Open-source WHO IMCI assistant. Gemma 4. Offline. On any phone."*
- **Format:** JPG, ≤ 1 MB, 560 × 280 pixels (Kaggle thumbnail aspect ratio).
- **Avoid:** clinical sterility, dramatic suffering, AI-generated faces. Use real photography or a posed shot with a model + signed release.

---

## 5. Media Gallery  *(form field — YouTube videos)*

Attach in this order:

1. **The Kaggle submission video (≤ 3 minutes).** Short cut: **[https://youtu.be/Gf415IgJr0s](https://youtu.be/Gf415IgJr0s)**
   *⚠️ Verify duration is ≤ 3:00 before attaching. If the cut is 3:30, a 30-second trim is needed.*

2. **Full storytelling film (12 minutes).** *Linked in the writeup body as "must-watch for the full picture."* **[https://youtu.be/2p932LTc_wE](https://youtu.be/2p932LTc_wE)**

3. **Full working app demo on Samsung A53.** **[https://youtu.be/yV8jBH6-_I0](https://youtu.be/yV8jBH6-_I0)**

---

## 6. Project Links  *(form field — Attachments → Project Links)*

### Description for the section *(≈200 words — paste above the link list, or use as the section's intro field if Kaggle exposes one)*

These seven links are the proof for every claim in this writeup. If you have five minutes, open the **live clinical portal** — click *Load sample audio* and you will see the full Tier-1 pipeline (mel-spectrogram → fine-tuned Gemma 4 classification → AI Clinical Note) execute in roughly seven seconds, with no login. The **GitHub repository** is the second stop: Apache 2.0 end-to-end across Flutter, Python, the clinic server, the notebooks, and the web portal, with an *"Evidence at a glance"* map at the top of the `README.md` pointing to each load-bearing file. The **Hugging Face model** is the Unsloth-track submission — Gemma 4 E4B with our QLoRA adapter merged, fine-tuned on ICBHI 2017 with a patient-level held-out split (no segment-level leakage), 85% crackle detection on patients the model never saw. The **twelve-minute film** carries the full storytelling arc; the **Samsung A53 demo** carries the unedited, airplane-mode proof. Finally, `SOURCES.md` cites the primary-source URL for every UNICEF / WHO / Cochrane / peer-reviewed number, and `REASONS_WE_WILL_FAIL.md` lists the capabilities Malaika deliberately does *not* claim. We came with receipts. These links are them. All Apache 2.0. Built by two engineers in thirty-six days, on the open model that made it shippable.

### Links to attach *(in this order)*

| # | Label | URL |
|---|---|---|
| 1 | **Live demo · open clinical portal** | https://malaika-delta.vercel.app/ |
| 2 | **Public code repository · GitHub** | https://github.com/Vimalk0703/Google-Gemma4-good-hackathon-VimalXMark |
| 3 | **Fine-tuned model · Hugging Face** | https://huggingface.co/Vimal0703/malaika-breath-sounds-E4B-merged |
| 4 | **Full storytelling film · 12 min · must-watch** | https://youtu.be/2p932LTc_wE |
| 5 | **Full app demo · Samsung A53** | https://youtu.be/yV8jBH6-_I0 |
| 6 | **Sources & citations · SOURCES.md** | https://github.com/Vimalk0703/Google-Gemma4-good-hackathon-VimalXMark/blob/main/SOURCES.md |
| 7 | **Anti-marketing · REASONS_WE_WILL_FAIL.md** | https://github.com/Vimalk0703/Google-Gemma4-good-hackathon-VimalXMark/blob/main/REASONS_WE_WILL_FAIL.md |

---

## 7. Project Description  *(form field — max 1,500 words)*

The full paste-ready body lives in its own file — **[`KAGGLE_PROJECT_DESCRIPTION.md`](KAGGLE_PROJECT_DESCRIPTION.md)** — formatted for maximum readability inside Kaggle's textbox. **1,359 words** (comfortably under the 1,500-word limit). Markdown is supported by Kaggle Writeups, so the headings, blockquotes, and emphasis all render.

To submit:

1. Open [`KAGGLE_PROJECT_DESCRIPTION.md`](KAGGLE_PROJECT_DESCRIPTION.md) on GitHub and click **Raw** (top-right of the file view) to get the unrendered markdown.
2. Copy from the first heading (`# Malaika — putting the WHO's…`) through the final signature line (`— *Vimal & Mark, May 2026. Apache 2.0.*`).
3. Paste into the Kaggle Writeup *Project Description* textbox.

Kept as a separate file so it is also the single source of truth — any edits there ship straight into the form without re-syncing this writeup.

---

## 8. Pre-submit checklist

Before clicking **Submit** on Kaggle:

- [ ] Title (≤80 chars) pasted
- [ ] Subtitle (≤140 chars) pasted
- [ ] Track set to **Health & Sciences**
- [ ] Card thumbnail (560×280) uploaded
- [ ] Short submission video (≤ 3:00) attached to media gallery — **VERIFY DURATION FIRST**
- [ ] Long film (12 min) attached to media gallery
- [ ] App demo video attached to media gallery
- [ ] Project Description (body of §7 above) pasted into textbox
- [ ] Word count verified ≤ 1,500
- [ ] Project Links all added (live demo, GitHub repo, APK, HF model, sources, REASONS_WE_WILL_FAIL)
- [ ] GitHub repo set to **public**
- [ ] Vercel deployment is live and the landing page loads with no login
- [ ] Apache 2.0 LICENSE file is in the repo root
