import Link from "next/link";
import { Wordmark } from "@/components/wordmark";
import { Analyzer } from "./analyzer";

export const metadata = {
  title: "Clinical portal",
  description:
    "Run breath-sound analysis through the village clinic server. Connected mode for Malaika.",
  robots: { index: false, follow: false },
};

export default function PortalPage() {
  return (
    <main style={{ minHeight: "100vh", background: "var(--color-cream)" }}>
      <header
        style={{ borderBottom: "1px solid var(--color-line)", background: "var(--color-cream)" }}
      >
        <div className="mx-auto flex max-w-[1280px] items-center justify-between px-6 py-5 md:px-12">
          <div className="flex items-center gap-6">
            <Wordmark />
            <span
              className="hidden text-sm md:inline"
              style={{ color: "var(--color-muted)", letterSpacing: "0.02em" }}
            >
              · Clinical portal
            </span>
          </div>
          <Link
            href="/"
            className="link-underline text-sm"
            style={{ color: "var(--color-ink-soft)" }}
          >
            Back to site
          </Link>
        </div>
      </header>

      <section className="mx-auto max-w-[1024px] px-6 py-16 md:px-12 md:py-24">
        <div className="mb-12">
          <p className="eyebrow mb-4">Breath sound analyzer</p>
          <h1
            className="font-display"
            style={{
              fontSize: "clamp(2rem, 4vw, 3rem)",
              color: "var(--color-ink)",
              lineHeight: 1.05,
            }}
          >
            Listen, on a hardware budget the phone{" "}
            <span className="font-display-italic" style={{ color: "var(--color-amber-deep)" }}>
              does not have.
            </span>
          </h1>
          <p
            className="mt-6 max-w-2xl text-base leading-relaxed"
            style={{ color: "var(--color-ink-soft)" }}
          >
            Drop or pick an audio recording of a child&rsquo;s breathing &mdash;
            or load the bundled ICBHI sample below. The server converts it to a
            mel-spectrogram, the fine-tuned model classifies it, and you see
            the result here. End-to-end on the clinic&rsquo;s own infrastructure.
          </p>
        </div>

        <Analyzer />
      </section>
    </main>
  );
}
