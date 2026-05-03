"use client";

import { useState, useTransition } from "react";
import { signIn } from "./actions";

export function SignInForm() {
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  return (
    <form
      action={(formData) => {
        setError(null);
        startTransition(async () => {
          const result = await signIn(formData);
          if (result?.error) setError(result.error);
        });
      }}
      className="space-y-5"
      aria-describedby={error ? "signin-error" : undefined}
    >
      <div>
        <label
          htmlFor="passcode"
          className="block text-sm font-medium"
          style={{ color: "var(--color-ink-soft)" }}
        >
          Access passcode
        </label>
        <input
          id="passcode"
          name="passcode"
          type="password"
          autoComplete="current-password"
          required
          autoFocus
          className="mt-2 block w-full px-4 py-3 text-base"
          style={{
            background: "var(--color-paper)",
            color: "var(--color-ink)",
            border: "1px solid var(--color-line-strong)",
            borderRadius: "var(--radius-button)",
            outline: "none",
          }}
          placeholder="Enter the passcode you were given"
        />
      </div>

      {error ? (
        <p
          id="signin-error"
          role="alert"
          className="text-sm leading-relaxed"
          style={{ color: "var(--color-severe)" }}
        >
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={isPending}
        className="w-full px-4 py-3 text-base font-medium transition-opacity"
        style={{
          background: "var(--color-ink)",
          color: "var(--color-paper)",
          borderRadius: "var(--radius-button)",
          opacity: isPending ? 0.65 : 1,
          cursor: isPending ? "wait" : "pointer",
        }}
      >
        {isPending ? "Verifying..." : "Sign in"}
      </button>

      <p className="text-xs leading-relaxed" style={{ color: "var(--color-muted)" }}>
        The portal is for clinicians and field workers running Malaika in
        connected mode. If you do not have a passcode, contact the team via
        the GitHub repository.
      </p>
    </form>
  );
}
