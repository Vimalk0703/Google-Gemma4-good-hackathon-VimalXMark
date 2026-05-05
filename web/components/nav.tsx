import Link from "next/link";
import { Wordmark } from "./wordmark";

export function Nav() {
  return (
    <header
      className="sticky top-0 z-40 backdrop-blur-md no-print"
      style={{
        background: "color-mix(in oklch, var(--color-cream) 92%, transparent)",
        borderBottom: "1px solid var(--color-line)",
      }}
    >
      <div className="mx-auto flex max-w-[1280px] items-center justify-between px-6 py-4 md:px-12">
        <Wordmark />
        <nav className="hidden items-center gap-8 md:flex">
          <Link href="#story" className="link-underline text-sm" style={{ color: "var(--color-ink-soft)" }}>
            Story
          </Link>
          <Link href="#tiers" className="link-underline text-sm" style={{ color: "var(--color-ink-soft)" }}>
            How it works
          </Link>
          <Link href="#evidence" className="link-underline text-sm" style={{ color: "var(--color-ink-soft)" }}>
            Evidence
          </Link>
          <Link
            href="https://github.com/malaika-ai/malaika"
            target="_blank"
            rel="noreferrer"
            className="link-underline text-sm"
            style={{ color: "var(--color-ink-soft)" }}
          >
            GitHub
          </Link>
          <Link
            href="/portal"
            className="text-sm font-medium"
            style={{
              color: "var(--color-paper)",
              background: "var(--color-ink)",
              padding: "0.55rem 1rem",
              borderRadius: "var(--radius-button)",
              transition: "background 200ms ease",
            }}
          >
            Clinical portal
          </Link>
        </nav>
        <Link
          href="/portal"
          className="md:hidden text-sm font-medium"
          style={{ color: "var(--color-amber-deep)" }}
        >
          Portal →
        </Link>
      </div>
    </header>
  );
}
