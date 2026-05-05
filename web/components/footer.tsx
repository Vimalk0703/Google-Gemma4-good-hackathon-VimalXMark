import Link from "next/link";

export function Footer() {
  return (
    <footer
      className="no-print mt-32"
      style={{ borderTop: "1px solid var(--color-line)" }}
    >
      <div className="mx-auto max-w-[1280px] px-6 py-16 md:px-12 md:py-24">
        <div className="grid gap-12 md:grid-cols-12">
          <div className="md:col-span-5">
            <p className="font-display text-3xl tracking-tight" style={{ color: "var(--color-ink)" }}>
              Malaika
            </p>
            <p className="mt-3 max-w-md text-sm leading-relaxed" style={{ color: "var(--color-muted)" }}>
              Open-source WHO IMCI assistant. Apache 2.0. Built for the
              Gemma 4 Good Hackathon, 2026. Designed by people who don&rsquo;t
              think a child should die from a disease we know how to treat.
            </p>
          </div>

          <div className="md:col-span-3">
            <p className="eyebrow mb-4">Project</p>
            <ul className="space-y-2 text-sm">
              <li>
                <Link
                  href="https://github.com/malaika-ai/malaika"
                  target="_blank"
                  rel="noreferrer"
                  className="link-underline"
                  style={{ color: "var(--color-ink-soft)" }}
                >
                  GitHub repository
                </Link>
              </li>
              <li>
                <Link
                  href="https://huggingface.co/Vimal0703/malaika-breath-sounds-E4B-merged"
                  target="_blank"
                  rel="noreferrer"
                  className="link-underline"
                  style={{ color: "var(--color-ink-soft)" }}
                >
                  Fine-tuned model
                </Link>
              </li>
              <li>
                <Link href="/portal" className="link-underline" style={{ color: "var(--color-ink-soft)" }}>
                  Clinical portal
                </Link>
              </li>
              <li>
                <Link
                  href="https://www.kaggle.com/competitions/gemma-4-good-hackathon"
                  target="_blank"
                  rel="noreferrer"
                  className="link-underline"
                  style={{ color: "var(--color-ink-soft)" }}
                >
                  Kaggle submission
                </Link>
              </li>
            </ul>
          </div>

          <div className="md:col-span-4">
            <p className="eyebrow mb-4">Sources</p>
            <ul className="space-y-2 text-sm">
              <li>
                <Link
                  href="https://www.who.int/news-room/fact-sheets/detail/child-mortality-under-5-years"
                  target="_blank"
                  rel="noreferrer"
                  className="link-underline"
                  style={{ color: "var(--color-ink-soft)" }}
                >
                  WHO &mdash; Child Mortality Under 5
                </Link>
              </li>
              <li>
                <Link
                  href="https://data.unicef.org/topic/child-health/pneumonia/"
                  target="_blank"
                  rel="noreferrer"
                  className="link-underline"
                  style={{ color: "var(--color-ink-soft)" }}
                >
                  UNICEF &mdash; Pneumonia Statistics
                </Link>
              </li>
              <li>
                <Link
                  href="https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858.CD010123.pub2/full"
                  target="_blank"
                  rel="noreferrer"
                  className="link-underline"
                  style={{ color: "var(--color-ink-soft)" }}
                >
                  Cochrane Review &mdash; IMCI 2016
                </Link>
              </li>
              <li>
                <Link
                  href="https://pmc.ncbi.nlm.nih.gov/articles/PMC3190369/"
                  target="_blank"
                  rel="noreferrer"
                  className="link-underline"
                  style={{ color: "var(--color-ink-soft)" }}
                >
                  J Health Popul Nutr &mdash; Umlazi case
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div
          className="mt-16 flex flex-col gap-4 pt-8 text-xs md:flex-row md:items-center md:justify-between"
          style={{ borderTop: "1px solid var(--color-line)", color: "var(--color-muted)" }}
        >
          <p>
            &copy; 2026 Malaika team. Released under Apache 2.0. Powered by{" "}
            <Link
              href="https://ai.google.dev/gemma"
              target="_blank"
              rel="noreferrer"
              className="link-underline"
              style={{ color: "var(--color-ink-soft)" }}
            >
              Google Gemma 4
            </Link>
            .
          </p>
          <p>
            Malaika is decision support, not a medical diagnosis. Always seek
            care from a qualified clinician.
          </p>
        </div>
      </div>
    </footer>
  );
}
