import Link from "next/link";
import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";

export default function HomePage() {
  return (
    <main>
      <Nav />

      {/* HERO */}
      <section
        className="mx-auto max-w-[1280px] px-6 pt-20 pb-32 md:px-12 md:pt-32 md:pb-40"
        aria-labelledby="hero"
      >
        <div className="grid items-end gap-16 md:grid-cols-12 md:gap-12">
          <div className="md:col-span-8">
            <p className="eyebrow mb-6">Open-source · Apache 2.0 · Built on Gemma 4</p>
            <h1
              id="hero"
              className="font-display"
              style={{
                fontSize: "clamp(2.75rem, 7vw, 6.25rem)",
                color: "var(--color-ink)",
                marginBottom: "0.4em",
              }}
            >
              Every thirty-nine{" "}
              <span className="font-display-italic" style={{ color: "var(--color-amber-deep)" }}>
                seconds.
              </span>
            </h1>
            <p
              className="mt-6 max-w-2xl text-lg leading-relaxed md:text-xl"
              style={{ color: "var(--color-ink-soft)" }}
            >
              A child dies of pneumonia every thirty-nine seconds &mdash; almost
              always preventable, almost always far from a clinic. Malaika
              (&ldquo;Angel&rdquo; in Swahili) puts the WHO&rsquo;s child-survival
              protocol into any caregiver&rsquo;s hand &mdash; in her language,
              through her phone, fully offline.
            </p>

            <div className="mt-12 flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-5">
              <a
                href={process.env.NEXT_PUBLIC_APK_URL || "/malaika.apk"}
                download="malaika.apk"
                className="inline-flex items-center justify-center gap-3 px-6 py-4 text-base font-medium transition-colors"
                style={{
                  background: "var(--color-ink)",
                  color: "var(--color-paper)",
                  borderRadius: "var(--radius-button)",
                }}
              >
                Download for Android
                <span aria-hidden="true" style={{ fontSize: "0.95em", opacity: 0.7 }}>
                  · Apache 2.0 · ~360 MB
                </span>
              </a>
              <Link
                href="/portal"
                className="inline-flex items-center justify-center gap-2 px-6 py-4 text-base"
                style={{
                  color: "var(--color-ink)",
                  border: "1px solid var(--color-line-strong)",
                  borderRadius: "var(--radius-button)",
                }}
              >
                Open clinical portal
                <span aria-hidden="true">→</span>
              </Link>
            </div>
          </div>

          {/* Right rail: editorial pull-quote, not a stock illustration */}
          <aside
            className="md:col-span-4 md:pl-8"
            style={{ borderLeft: "1px solid var(--color-line)" }}
          >
            <p
              className="font-display-italic"
              style={{
                fontSize: "clamp(1.25rem, 1.6vw, 1.5rem)",
                lineHeight: 1.35,
                color: "var(--color-ink-soft)",
              }}
            >
              &ldquo;In every place we work &mdash; from displacement camps in
              Nigeria to refugee encampments in Greece &mdash; pneumonia is the
              common killer of children under five years old.&rdquo;
            </p>
            <p className="mt-5 text-sm" style={{ color: "var(--color-muted)" }}>
              <span style={{ color: "var(--color-ink-soft)" }}>Miriam Alia</span>
              <br />
              Vaccination Advisor &middot; Médecins Sans Frontières
            </p>
          </aside>
        </div>
      </section>

      {/* THE NUMBERS */}
      <section
        id="evidence"
        aria-labelledby="evidence-heading"
        className="mx-auto max-w-[1280px] px-6 py-24 md:px-12 md:py-32"
        style={{ borderTop: "1px solid var(--color-line)" }}
      >
        <div className="mb-20 grid gap-12 md:grid-cols-12">
          <div className="md:col-span-4">
            <p className="eyebrow mb-4">The Evidence</p>
            <h2
              id="evidence-heading"
              className="font-display"
              style={{
                fontSize: "clamp(2rem, 4vw, 3.25rem)",
                color: "var(--color-ink)",
              }}
            >
              The data is the story.
            </h2>
          </div>
          <div className="md:col-span-7 md:col-start-6">
            <p className="text-lg leading-relaxed" style={{ color: "var(--color-ink-soft)" }}>
              Every number on this page is sourced. UNICEF, the WHO, the
              Cochrane Review, peer-reviewed journals. We are not here to make
              you feel something. We are here to show you what is true.
            </p>
            <p className="mt-5 text-base leading-relaxed" style={{ color: "var(--color-muted)" }}>
              The emotion is what the data does to you.
            </p>
          </div>
        </div>

        <dl className="grid gap-12 md:grid-cols-12 md:gap-x-8">
          {/* Stat 1 */}
          <div
            className="md:col-span-4"
            style={{ borderTop: "1px solid var(--color-line-strong)", paddingTop: "1.5rem" }}
          >
            <dt className="eyebrow">Children under 5 lost in 2024</dt>
            <dd
              className="font-display tabular mt-4"
              style={{
                fontSize: "clamp(3.25rem, 6vw, 5.5rem)",
                color: "var(--color-ink)",
                lineHeight: 0.95,
              }}
            >
              4.9M
            </dd>
            <p className="mt-5 text-sm leading-relaxed" style={{ color: "var(--color-muted)" }}>
              Most from preventable causes. Fifty-eight percent in Sub-Saharan
              Africa. Twenty-five percent in South Asia.
            </p>
            <p className="mt-3 text-xs" style={{ color: "var(--color-faint)" }}>
              UN Inter-agency Group for Child Mortality Estimation, 2024.
            </p>
          </div>

          {/* Stat 2 */}
          <div
            className="md:col-span-4"
            style={{ borderTop: "1px solid var(--color-line-strong)", paddingTop: "1.5rem" }}
          >
            <dt className="eyebrow">Pneumonia + diarrhea deaths each year</dt>
            <dd
              className="font-display tabular mt-4"
              style={{
                fontSize: "clamp(3.25rem, 6vw, 5.5rem)",
                color: "var(--color-ink)",
                lineHeight: 0.95,
              }}
            >
              1.17M
            </dd>
            <p className="mt-5 text-sm leading-relaxed" style={{ color: "var(--color-muted)" }}>
              Two diseases. One in four under-five deaths. Almost all
              preventable with a vaccine, a five-cent antibiotic, and the WHO
              IMCI protocol.
            </p>
            <p className="mt-3 text-xs" style={{ color: "var(--color-faint)" }}>
              UNICEF Pneumonia Statistics, 2024.
            </p>
          </div>

          {/* Stat 3 */}
          <div
            className="md:col-span-4"
            style={{ borderTop: "1px solid var(--color-line-strong)", paddingTop: "1.5rem" }}
          >
            <dt className="eyebrow">Mortality reduction with full IMCI coverage</dt>
            <dd
              className="font-display tabular mt-4"
              style={{
                fontSize: "clamp(3.25rem, 6vw, 5.5rem)",
                color: "var(--color-amber-deep)",
                lineHeight: 0.95,
              }}
            >
              15<span style={{ color: "var(--color-ink)" }}>%</span>
            </dd>
            <p className="mt-5 text-sm leading-relaxed" style={{ color: "var(--color-muted)" }}>
              Roughly 175,000 children, every year, who would still be alive.
              The protocol works. It just hasn&rsquo;t reached everyone.
            </p>
            <p className="mt-3 text-xs" style={{ color: "var(--color-faint)" }}>
              Cochrane Review (Gera et al., 2016) — 65,570 participants. RR 0.85.
            </p>
          </div>
        </dl>
      </section>

      {/* THE STORY — UMLAZI */}
      <section
        id="story"
        aria-labelledby="story-heading"
        className="mx-auto max-w-[1280px] px-6 py-24 md:px-12 md:py-32"
        style={{ borderTop: "1px solid var(--color-line)" }}
      >
        <div className="grid gap-12 md:grid-cols-12">
          <div className="md:col-span-4">
            <p className="eyebrow mb-4">The Story</p>
            <h2
              id="story-heading"
              className="font-display"
              style={{
                fontSize: "clamp(2rem, 4vw, 3.25rem)",
                color: "var(--color-ink)",
              }}
            >
              Umlazi.
            </h2>
            <p className="mt-6 text-sm leading-relaxed" style={{ color: "var(--color-muted)" }}>
              A peer-reviewed case from a township outside Durban,
              South Africa. Published in the <em>Journal of Health, Population
              and Nutrition</em>.
            </p>
          </div>

          <div className="md:col-span-7 md:col-start-6">
            <p
              className="font-display"
              style={{
                fontSize: "clamp(1.5rem, 2.4vw, 2rem)",
                lineHeight: 1.35,
                color: "var(--color-ink)",
              }}
            >
              A young mother is discharged from a hospital with her newborn.
              On the bus home, the baby starts breathing too fast. She knows
              something is wrong.
            </p>
            <p
              className="mt-6 font-display"
              style={{
                fontSize: "clamp(1.5rem, 2.4vw, 2rem)",
                lineHeight: 1.35,
                color: "var(--color-ink)",
              }}
            >
              She wants to go back. She does not have the bus fare to do it.
            </p>
            <p
              className="mt-8 font-display-italic"
              style={{
                fontSize: "clamp(1.5rem, 2.4vw, 2rem)",
                lineHeight: 1.35,
                color: "var(--color-amber-deep)",
              }}
            >
              By the time she steps off at her stop, the baby has died.
            </p>

            <div
              className="mt-10 grid gap-6 md:grid-cols-2"
              style={{ borderTop: "1px solid var(--color-line)", paddingTop: "1.5rem" }}
            >
              <p className="text-sm leading-relaxed" style={{ color: "var(--color-ink-soft)" }}>
                It was not the medicine that failed her. It was the{" "}
                <em>distance</em> between her and the medicine &mdash; and the{" "}
                <em>cost</em> of crossing it.
              </p>
              <p className="text-sm leading-relaxed" style={{ color: "var(--color-ink-soft)" }}>
                In rural Uganda, the median mother waits two full days before
                seeking professional care for a child with pneumonia. Two
                days is the entire window between life and death.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* TWO-TIER ARCHITECTURE */}
      <section
        id="tiers"
        aria-labelledby="tiers-heading"
        className="mx-auto max-w-[1280px] px-6 py-24 md:px-12 md:py-32"
        style={{ borderTop: "1px solid var(--color-line)" }}
      >
        <div className="mb-20 grid gap-12 md:grid-cols-12">
          <div className="md:col-span-5">
            <p className="eyebrow mb-4">How it works</p>
            <h2
              id="tiers-heading"
              className="font-display"
              style={{
                fontSize: "clamp(2rem, 4vw, 3.25rem)",
                color: "var(--color-ink)",
              }}
            >
              Two tiers of care.{" "}
              <span className="font-display-italic" style={{ color: "var(--color-amber-deep)" }}>
                One model family.
              </span>
            </h2>
          </div>
          <div className="md:col-span-6 md:col-start-7">
            <p className="text-lg leading-relaxed" style={{ color: "var(--color-ink-soft)" }}>
              The phone always works. The clinic server augments. Either tier
              is independently useful. Both run Google&rsquo;s open-weights
              Gemma 4 &mdash; the only model in the world that fits text,
              vision, and multilingual reasoning at this size, on this
              hardware.
            </p>
          </div>
        </div>

        <div className="grid gap-px md:grid-cols-2" style={{ background: "var(--color-line)" }}>
          {/* Tier 0 */}
          <article
            className="p-10 md:p-14"
            style={{ background: "var(--color-cream)" }}
          >
            <p className="eyebrow mb-4">Tier 0 · The Phone</p>
            <h3
              className="font-display"
              style={{ fontSize: "1.875rem", color: "var(--color-ink)" }}
            >
              The remotest village. No internet. No clinic.
            </h3>

            <dl className="mt-10 space-y-6 text-sm">
              <div className="flex items-baseline justify-between gap-6">
                <dt style={{ color: "var(--color-muted)" }}>Model</dt>
                <dd className="text-right" style={{ color: "var(--color-ink)" }}>
                  Gemma 4 E2B · 2.58 GB on disk
                </dd>
              </div>
              <div
                className="flex items-baseline justify-between gap-6 pt-6"
                style={{ borderTop: "1px solid var(--color-line)" }}
              >
                <dt style={{ color: "var(--color-muted)" }}>Hardware</dt>
                <dd className="text-right" style={{ color: "var(--color-ink)" }}>
                  $60 Android, Mali-G68 GPU
                </dd>
              </div>
              <div
                className="flex items-baseline justify-between gap-6 pt-6"
                style={{ borderTop: "1px solid var(--color-line)" }}
              >
                <dt style={{ color: "var(--color-muted)" }}>Performance</dt>
                <dd className="text-right tabular" style={{ color: "var(--color-ink)" }}>
                  ~50 tokens / sec
                </dd>
              </div>
              <div
                className="flex items-baseline justify-between gap-6 pt-6"
                style={{ borderTop: "1px solid var(--color-line)" }}
              >
                <dt style={{ color: "var(--color-muted)" }}>Connectivity</dt>
                <dd className="text-right" style={{ color: "var(--color-ink)" }}>
                  None required &mdash; ever
                </dd>
              </div>
            </dl>

            <p className="mt-12 text-sm leading-relaxed" style={{ color: "var(--color-ink-soft)" }}>
              Twelve clinical skills. Voice in any language. Photo analysis
              for alertness, sunken eyes, visible ribs, edema. Deterministic
              WHO IMCI classification. Treatment instructions read aloud.
              The whole assessment in under a minute.
            </p>
          </article>

          {/* Tier 1 */}
          <article
            className="p-10 md:p-14"
            style={{ background: "var(--color-paper)" }}
          >
            <p className="eyebrow mb-4">Tier 1 · The Village Clinic</p>
            <h3
              className="font-display"
              style={{ fontSize: "1.875rem", color: "var(--color-ink)" }}
            >
              Ten kilometres away. One nurse. One Wi-Fi router.
            </h3>

            <dl className="mt-10 space-y-6 text-sm">
              <div className="flex items-baseline justify-between gap-6">
                <dt style={{ color: "var(--color-muted)" }}>Model</dt>
                <dd className="text-right" style={{ color: "var(--color-ink)" }}>
                  Gemma 4 E4B + ICBHI 2017 LoRA
                </dd>
              </div>
              <div
                className="flex items-baseline justify-between gap-6 pt-6"
                style={{ borderTop: "1px solid var(--color-line)" }}
              >
                <dt style={{ color: "var(--color-muted)" }}>Hardware</dt>
                <dd className="text-right" style={{ color: "var(--color-ink)" }}>
                  Refurbished mini-PC + clinic LAN
                </dd>
              </div>
              <div
                className="flex items-baseline justify-between gap-6 pt-6"
                style={{ borderTop: "1px solid var(--color-line)" }}
              >
                <dt style={{ color: "var(--color-muted)" }}>Adds</dt>
                <dd className="text-right" style={{ color: "var(--color-ink)" }}>
                  Breath sounds, deeper reasoning
                </dd>
              </div>
              <div
                className="flex items-baseline justify-between gap-6 pt-6"
                style={{ borderTop: "1px solid var(--color-line)" }}
              >
                <dt style={{ color: "var(--color-muted)" }}>Privacy</dt>
                <dd className="text-right" style={{ color: "var(--color-ink)" }}>
                  Clinic-local server, no cloud
                </dd>
              </div>
            </dl>

            <p className="mt-12 text-sm leading-relaxed" style={{ color: "var(--color-ink-soft)" }}>
              When the phone reaches Wi-Fi, it offloads what it cannot do
              alone &mdash; spectrogram analysis of breath sounds for wheeze
              and crackle detection. Eighty-five percent crackle detection
              on held-out patients. The data never leaves the clinic.
            </p>

            <Link
              href="/portal"
              className="mt-10 inline-flex items-center gap-2 text-sm font-medium link-underline"
              style={{ color: "var(--color-amber-deep)" }}
            >
              Try the breath analyzer →
            </Link>
          </article>
        </div>
      </section>

      {/* WHY ONLY GEMMA */}
      <section
        aria-labelledby="why-gemma-heading"
        className="mx-auto max-w-[1280px] px-6 py-24 md:px-12 md:py-32"
        style={{ borderTop: "1px solid var(--color-line)" }}
      >
        <div className="grid gap-12 md:grid-cols-12">
          <div className="md:col-span-5">
            <p className="eyebrow mb-4">Why Gemma 4</p>
            <h2
              id="why-gemma-heading"
              className="font-display"
              style={{
                fontSize: "clamp(2rem, 4vw, 3.25rem)",
                color: "var(--color-ink)",
              }}
            >
              The only model that fits.
            </h2>
            <p className="mt-6 text-base leading-relaxed" style={{ color: "var(--color-ink-soft)" }}>
              We benchmarked the alternatives. Llama 3.2 1B has no vision.
              Phi-3 mini doesn&rsquo;t fit. Qwen 2.5 has no vision. Only
              Gemma 4 E2B delivers all four constraints &mdash; size, vision,
              multilingual, on-device speed &mdash; on a sixty-dollar Android.
            </p>
            <p className="mt-4 text-base leading-relaxed" style={{ color: "var(--color-ink-soft)" }}>
              Per-layer embeddings give it the knowledge of a 4B model with
              the memory footprint of a 2B. That single architectural
              decision is what makes Malaika possible.
            </p>
          </div>

          <div className="md:col-span-6 md:col-start-7">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--color-line-strong)" }}>
                  <th className="py-3 text-left font-medium" style={{ color: "var(--color-muted)" }}>
                    Model
                  </th>
                  <th className="py-3 text-right font-medium" style={{ color: "var(--color-muted)" }}>
                    Size
                  </th>
                  <th className="py-3 text-right font-medium" style={{ color: "var(--color-muted)" }}>
                    Vision
                  </th>
                  <th className="py-3 text-right font-medium" style={{ color: "var(--color-muted)" }}>
                    Multilingual
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ background: "var(--color-amber-soft)" }}>
                  <td className="py-4 pl-3 font-medium" style={{ color: "var(--color-ink)" }}>
                    Gemma 4 E2B
                  </td>
                  <td className="py-4 pr-3 text-right tabular" style={{ color: "var(--color-ink)" }}>
                    2.58 GB
                  </td>
                  <td className="py-4 pr-3 text-right" style={{ color: "var(--color-amber-deep)" }}>
                    Yes
                  </td>
                  <td className="py-4 pr-3 text-right" style={{ color: "var(--color-amber-deep)" }}>
                    140+ langs
                  </td>
                </tr>
                <tr style={{ borderTop: "1px solid var(--color-line)" }}>
                  <td className="py-4" style={{ color: "var(--color-ink-soft)" }}>
                    Llama 3.2 1B
                  </td>
                  <td className="py-4 text-right tabular" style={{ color: "var(--color-ink-soft)" }}>
                    2.5 GB
                  </td>
                  <td className="py-4 text-right" style={{ color: "var(--color-muted)" }}>
                    No
                  </td>
                  <td className="py-4 text-right" style={{ color: "var(--color-muted)" }}>
                    English-leaning
                  </td>
                </tr>
                <tr style={{ borderTop: "1px solid var(--color-line)" }}>
                  <td className="py-4" style={{ color: "var(--color-ink-soft)" }}>
                    Phi-3 mini 3.8B
                  </td>
                  <td className="py-4 text-right tabular" style={{ color: "var(--color-ink-soft)" }}>
                    4.0 GB
                  </td>
                  <td className="py-4 text-right" style={{ color: "var(--color-muted)" }}>
                    No
                  </td>
                  <td className="py-4 text-right" style={{ color: "var(--color-muted)" }}>
                    English-leaning
                  </td>
                </tr>
                <tr style={{ borderTop: "1px solid var(--color-line)" }}>
                  <td className="py-4" style={{ color: "var(--color-ink-soft)" }}>
                    Qwen 2.5 1.5B
                  </td>
                  <td className="py-4 text-right tabular" style={{ color: "var(--color-ink-soft)" }}>
                    3.0 GB
                  </td>
                  <td className="py-4 text-right" style={{ color: "var(--color-muted)" }}>
                    No
                  </td>
                  <td className="py-4 text-right" style={{ color: "var(--color-muted)" }}>
                    Strong CJK
                  </td>
                </tr>
              </tbody>
            </table>
            <p className="mt-4 text-xs" style={{ color: "var(--color-faint)" }}>
              Benchmarked April 2026 on Samsung A53. Reproducible &mdash; see{" "}
              <code style={{ color: "var(--color-muted)" }}>scripts/benchmark_models.py</code>{" "}
              in the repository.
            </p>
          </div>
        </div>
      </section>

      {/* CALL TO ACTION */}
      <section
        aria-labelledby="cta-heading"
        className="mx-auto max-w-[1280px] px-6 py-24 md:px-12 md:py-32"
        style={{ borderTop: "1px solid var(--color-line)" }}
      >
        <div className="grid gap-12 md:grid-cols-12 md:items-end">
          <div className="md:col-span-7">
            <p className="eyebrow mb-4">The next thirty-nine seconds</p>
            <h2
              id="cta-heading"
              className="font-display"
              style={{
                fontSize: "clamp(2.25rem, 5vw, 4rem)",
                color: "var(--color-ink)",
              }}
            >
              Fork it tonight.{" "}
              <span className="font-display-italic" style={{ color: "var(--color-amber-deep)" }}>
                Translate it tomorrow.
              </span>{" "}
              Deploy it next week.
            </h2>
            <p className="mt-8 max-w-2xl text-lg leading-relaxed" style={{ color: "var(--color-ink-soft)" }}>
              Apache 2.0. Free, forever. No premium tier. No telemetry. No
              cloud dependency. The AI that decides whether a child lives
              must not belong to a company. It has to belong to everyone.
            </p>
          </div>
          <div className="md:col-span-5 md:pl-12">
            <div className="flex flex-col gap-3">
              <a
                href={process.env.NEXT_PUBLIC_APK_URL || "/malaika.apk"}
                download="malaika.apk"
                className="flex items-center justify-between gap-3 px-6 py-4 text-base font-medium transition-colors"
                style={{
                  background: "var(--color-ink)",
                  color: "var(--color-paper)",
                  borderRadius: "var(--radius-button)",
                }}
              >
                <span>Download for Android</span>
                <span aria-hidden="true">↓</span>
              </a>
              <Link
                href="/portal"
                className="flex items-center justify-between gap-3 px-6 py-4 text-base font-medium"
                style={{
                  color: "var(--color-ink)",
                  border: "1px solid var(--color-line-strong)",
                  borderRadius: "var(--radius-button)",
                }}
              >
                <span>Open clinical portal</span>
                <span aria-hidden="true">→</span>
              </Link>
              <Link
                href="https://github.com/malaika-ai/malaika"
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-between gap-3 px-6 py-4 text-base font-medium"
                style={{
                  color: "var(--color-ink-soft)",
                  border: "1px solid var(--color-line)",
                  borderRadius: "var(--radius-button)",
                }}
              >
                <span>View source on GitHub</span>
                <span aria-hidden="true">→</span>
              </Link>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </main>
  );
}
