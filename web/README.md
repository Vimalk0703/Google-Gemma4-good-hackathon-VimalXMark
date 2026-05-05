# Malaika · Web

> The public-facing landing page and the clinical portal.
>
> **Two surfaces, one repository:**
> - `/` — the marketing-grade story of Malaika, with download CTAs for the Android APK.
> - `/portal` — a passcode-gated tool where clinicians upload a breathing recording and get back a Gemma-4-fine-tuned classification served by the village-clinic notebook.

---

## Run locally

```bash
cd web
cp .env.example .env.local
# edit .env.local — set BREATH_API_URL to your live notebook 12 ngrok URL
# set PORTAL_PASSCODE to whatever you want clinicians to type

npm install
npm run dev
```

Then open http://localhost:3000.

The first paint of `/` should be near-instant — the page is a server component with no client JS apart from the analyzer. The analyzer at `/portal` requires a passcode and a live `BREATH_API_URL`.

---

## Environment variables

| Var | Where read | What it is |
|-----|------------|------------|
| `BREATH_API_URL` | Server only (`/api/breath`) | The base URL of `notebooks/12_village_clinic_finetuned.ipynb`'s ngrok tunnel. Update each session — ngrok URLs are ephemeral. |
| `PORTAL_PASSCODE` | Server only (`/portal/actions.ts`) | The passcode clinicians type to enter the portal. Single shared secret for hackathon scope. Rotate before any real deployment. |
| `NEXT_PUBLIC_APK_URL` | Client | The download link for the Android APK release on GitHub. Defaults to the latest-release URL if unset. |

Never put `BREATH_API_URL` or `PORTAL_PASSCODE` behind a `NEXT_PUBLIC_` prefix — they would leak to every browser.

---

## Deploy to Vercel

```bash
# from repo root
cd web
vercel --prod
```

Then in the Vercel project settings, add the three environment variables above. The portal will work as soon as `BREATH_API_URL` and `PORTAL_PASSCODE` are set on the deployment.

For a private demo to judges, give them the passcode and the deployed URL. They can run breath analysis live without ever touching Kaggle or Colab themselves.

---

## Design system

The aesthetic is deliberate. **It is built to not look AI-generated.** Read this before you change anything visual.

### Typography

- **Display** (h1, h2, large numbers): [Fraunces](https://fonts.google.com/specimen/Fraunces) — variable serif, optical sizing 144, soft 30, wonk 0.
- **Body** (everything else): [Inter](https://fonts.google.com/specimen/Inter).
- **Italics use Fraunces' true italic**, not the regular face slanted, with `SOFT 100, WONK 1` to lean into the editorial character.
- **Small caps** for section labels (`.eyebrow`) — letter-spacing 0.18em, 75% opacity.

Both are loaded via `next/font/google` with `display: swap`, so the cumulative-layout-shift is zero.

### Colour

All tokens defined in `app/globals.css` `@theme` block. Use `var(--color-*)` — never hex literals in components.

| Token | Use |
|-------|-----|
| `--color-cream` | Page background. Warm, not white. |
| `--color-paper` | Cards. Slightly brighter than cream. |
| `--color-ink` | Primary foreground. |
| `--color-ink-soft` | Secondary foreground (paragraphs, table rows). |
| `--color-muted` | Captions, labels. |
| `--color-faint` | Citations, model attribution. |
| `--color-line` | Hairline rules between sections. |
| `--color-line-strong` | Section-emphasis rules (between stat rows). |
| `--color-amber` / `--color-amber-deep` / `--color-amber-soft` | The single accent. Use sparingly — italic emphasis, primary CTAs, severity. |
| `--color-severe` / `--color-warning` / `--color-safe` | WHO IMCI severity. Used only in the portal results card. |

**No gradients.** No glassmorphism. No bento. No icon grids. The page reads like a magazine.

### Layout

- Max width `1280px`, never wider.
- Side gutters: `1.5rem` mobile, `3rem` desktop.
- 12-column grid on desktop with deliberately asymmetric content placement (e.g. eyebrows in the left 4 columns, body in the right 7-8).
- Section dividers are 1px hairlines, never bigger.
- Vertical rhythm uses `py-24` to `py-32` for marketing sections, tighter for the portal.

### Motion

- The CSS file declares a `.reveal` keyframe for fade-up on scroll, but it's currently unused — the page is calm enough to not need it. **Don't add it lazily.** If you do, scope it to one or two hero elements at most.
- Hover transitions: 200ms ease, color or background only. No transforms, no scaling.

### What we deliberately did not include

- No newsletter sign-up.
- No "Trusted by" logo strip.
- No three-column feature card grid with icons.
- No customer carousel or testimonial slider.
- No bouncy entrance animations.
- No emoji anywhere in the UI.
- No stock illustrations or AI-generated hero images. The hero is pure typography. The right rail is a real attributed pull-quote, not decoration.

If you find yourself reaching for any of the above, stop and re-read this file.

---

## Structure

```
web/
├── app/
│   ├── layout.tsx          # Fonts, metadata, OG.
│   ├── globals.css         # Tailwind v4 + design tokens.
│   ├── page.tsx            # Landing page — single file, all sections.
│   ├── portal/
│   │   ├── page.tsx        # Server component — auth check, branches view.
│   │   ├── sign-in-form.tsx# Client form with server-action submit.
│   │   ├── analyzer.tsx    # Client component — file upload + result.
│   │   └── actions.ts      # Server actions: signIn, signOut, isSignedIn.
│   └── api/
│       └── breath/
│           └── route.ts    # POST handler — proxies to BREATH_API_URL.
├── components/
│   ├── wordmark.tsx
│   ├── nav.tsx
│   └── footer.tsx
├── public/                 # Static assets.
├── .env.example
├── package.json
├── tsconfig.json
├── next.config.ts
└── postcss.config.mjs
```

There is no `lib/` and no `hooks/` because we do not need them yet. Resist the urge to add architecture for code that doesn't exist.

---

## Data flow — how `/portal` actually works

```
  Browser (nurse)              Vercel / localhost:3000          Kaggle / Colab T4
  ─────────────────            ───────────────────────          ───────────────────
   /portal
   ↓ (records WAV in browser)
   POST /api/breath  ────►   Next.js route handler
                              · checks session cookie
                              · reads BREATH_API_URL env
                              · forwards FormData
                              ─── POST {URL}/breath ──────►  notebooks/12_village_clinic_finetuned.ipynb
                                                                  · loads Vimal0703/malaika-breath-sounds-E4B-merged
                                                                  · FastAPI: /breath + /health
                                                                  · ngrok tunnel → public URL
                                                                  · second Gemma pass = clinical note
                              ◄── JSON {abnormal, conf, note} ───
                              ◄── parsed JSON
   result card ◄────
```

**Why proxy server-side?** `BREATH_API_URL` never leaks to the browser. The 25 MB upload limit is enforced server-side in `app/api/breath/route.ts`. Notebook 12 itself has no auth — the session cookie at the proxy is the only gate.

---

## Connecting the portal to a live model

1. Run `notebooks/12_village_clinic_finetuned.ipynb` on Kaggle T4. It prints a public URL in cell 7 (something like `https://abc123.ngrok-free.app`).
2. Copy that URL into `BREATH_API_URL` in `web/.env.local` (or your Vercel env settings). **Do not include a trailing slash.**
3. Restart `npm run dev` (or redeploy on Vercel).
4. Open `/portal`, sign in, drop a `.wav` file from `notebooks/06_unsloth_binary_phase1.ipynb`'s held-out test set, and click *Analyze*. Result returns in 3-5 seconds on a T4.

If the notebook stops, the portal will surface a clear "could not reach the clinic server" message. The phone tier (Tier 0) keeps working independently — that's the whole point.

---

## Scripts

| Command | Use |
|---------|-----|
| `npm run dev` | Local dev server with hot reload. |
| `npm run build` | Production build. |
| `npm start` | Run the production build locally. |
| `npm run lint` | Next.js lint. |
| `npm run typecheck` | TypeScript check, no emit. |

---

## Future work

These are intentionally **not** in scope for the hackathon submission, but flagged for reviewers:

- Microphone recording in the browser (currently file-upload only — record-from-mic doubles the implementation surface).
- A separate Tier-1 admin view (model card, deployment health, throughput stats).
- i18n. The page is English. We have the translation infrastructure on the phone; the marketing page can come later.
- A real CMS for the doctor quotes. They're hard-coded for now; if we add five more, move them out.
- A direct GitHub OAuth sign-in instead of a shared passcode — once we have a real deployment partner.

---

*The page is built to read like a real organisation made it. If the next person to touch it remembers nothing else, remember that.*
