import Link from "next/link";

/**
 * Editorial wordmark — pure typography, no icon file.
 * Looks intentional, not AI-generated stock-logo.
 */
export function Wordmark({
  size = "md",
  href = "/",
}: {
  size?: "sm" | "md" | "lg";
  href?: string;
}) {
  const sizes = {
    sm: "text-base",
    md: "text-lg",
    lg: "text-2xl",
  } as const;

  const content = (
    <span className={`font-display ${sizes[size]} tracking-tight`}>
      <span style={{ color: "var(--color-ink)" }}>Malaika</span>
      <span
        className="font-display-italic"
        style={{ color: "var(--color-amber-deep)", marginLeft: "0.15em" }}
      >
        ·
      </span>
    </span>
  );

  if (!href) return content;
  return (
    <Link href={href} className="inline-block" aria-label="Malaika home">
      {content}
    </Link>
  );
}
