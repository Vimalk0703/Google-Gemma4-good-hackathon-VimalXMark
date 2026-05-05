"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

const COOKIE_NAME = "malaika_portal_session";
const COOKIE_MAX_AGE = 60 * 60 * 8; // 8 hours

export async function signIn(formData: FormData) {
  const submitted = String(formData.get("passcode") ?? "").trim();
  const expected = process.env.PORTAL_PASSCODE ?? "";

  if (!expected) {
    return { error: "Portal is not configured. Set PORTAL_PASSCODE in the deployment environment." };
  }

  if (submitted !== expected) {
    return { error: "That passcode does not match. If you need access, contact the team." };
  }

  const jar = await cookies();
  jar.set(COOKIE_NAME, "1", {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: COOKIE_MAX_AGE,
  });

  redirect("/portal");
}

export async function signOut() {
  const jar = await cookies();
  jar.delete(COOKIE_NAME);
  redirect("/portal");
}

export async function isSignedIn(): Promise<boolean> {
  const jar = await cookies();
  return jar.get(COOKIE_NAME)?.value === "1";
}
