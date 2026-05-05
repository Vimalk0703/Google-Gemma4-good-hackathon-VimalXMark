import Link from "next/link";
import { Wordmark } from "@/components/wordmark";
import { isSignedIn, signOut } from "./actions";
import { SignInForm } from "./sign-in-form";
import { Analyzer } from "./analyzer";

export const metadata = {
  title: "Clinical portal",
  description:
    "Run breath-sound analysis through the village clinic server. Connected mode for Malaika.",
  robots: { index: false, follow: false },
};

export default async function PortalPage() {
  const signedIn = await isSignedIn();

  return (
    <main style={{ minHeight: "100vh", background: "var(--color-cream)" }}>
      {/* Minimal portal nav — different from marketing nav */}
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
          <div className="flex items-center gap-6">
            <Link
              href="/"
              className="link-underline text-sm"
              style={{ color: "var(--color-ink-soft)" }}
            >
              Back to site
            </Link>
            {signedIn ? (
              <form action={signOut}>
                <button
                  type="submit"
                  className="text-sm"
                  style={{ color: "var(--color-muted)", background: "none", border: "none", padding: 0, cursor: "pointer" }}
                >
                  Sign out
                </button>
              </form>
            ) : null}
          </div>
        </div>
      </header>

      {!signedIn ? <SignInView /> : <AnalyzerView />}
    </main>
  );
}

function SignInView() {
  return (
    <section className="mx-auto grid max-w-[1280px] gap-12 px-6 py-24 md:grid-cols-12 md:px-12 md:py-32">
      <div className="md:col-span-6">
        <p className="eyebrow mb-6">Connected mode</p>
        <h1
          className="font-display"
          style={{
            fontSize: "clamp(2.25rem, 4.5vw, 3.5rem)",
            color: "var(--color-ink)",
            lineHeight: 1.05,
          }}
        >
          The village clinic{" "}
          <span className="font-display-italic" style={{ color: "var(--color-amber-deep)" }}>
            tier.
          </span>
        </h1>
        <div className="mt-10 space-y-5 text-base leading-relaxed" style={{ color: "var(--color-ink-soft)" }}>
          <p>
            This portal is for the clinic-server tier of Malaika &mdash; the
            second of two tiers in the architecture. It runs Gemma 4 E4B with
            a LoRA adapter we fine-tuned on the ICBHI 2017 respiratory sound
            dataset.
          </p>
          <p>
            Upload a short breathing recording and the model will tell you
            whether the sounds appear normal or abnormal. Use this alongside
            &mdash; never instead of &mdash; the deterministic WHO IMCI
            classification on the phone.
          </p>
          <p style={{ color: "var(--color-muted)" }}>
            We deliberately do not let any AI decide whether a child lives or
            dies. The medicine belongs to the WHO. The AI&rsquo;s job is to
            help you see what is hard to hear.
          </p>
        </div>
      </div>

      <div className="md:col-span-5 md:col-start-8">
        <div
          className="p-8 md:p-10"
          style={{
            background: "var(--color-paper)",
            boxShadow: "var(--shadow-card)",
            borderRadius: "var(--radius-card)",
          }}
        >
          <p className="eyebrow mb-2">Sign in</p>
          <h2
            className="font-display"
            style={{ fontSize: "1.875rem", color: "var(--color-ink)", marginBottom: "1.5rem" }}
          >
            Enter passcode.
          </h2>
          <SignInForm />

          <div
            className="mt-8 p-4"
            style={{
              background: "var(--color-amber-soft)",
              borderRadius: "var(--radius-button)",
              borderLeft: "2px solid var(--color-amber-deep)",
            }}
          >
            <p className="eyebrow mb-1" style={{ color: "var(--color-amber-deep)" }}>
              Hackathon viewer
            </p>
            <p className="text-sm leading-relaxed" style={{ color: "var(--color-ink-soft)" }}>
              Demo passcode: <code className="tabular" style={{ fontWeight: 500 }}>malaika</code>
            </p>
            <p className="mt-1 text-xs" style={{ color: "var(--color-muted)" }}>
              In production, the clinic operator would issue per-user credentials.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

function AnalyzerView() {
  return (
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
          Drop or pick an audio recording of a child&rsquo;s breathing. The
          server converts it to a mel-spectrogram, the fine-tuned model
          classifies it, and you see the result here. End-to-end on the
          clinic&rsquo;s own infrastructure.
        </p>
      </div>

      <Analyzer />
    </section>
  );
}
