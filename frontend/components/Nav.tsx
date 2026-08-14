"use client";

import { useState } from "react";
import { useTranslations, useLocale } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";

const LOCALES = ["fr", "en"] as const;

export default function Nav() {
  const t = useTranslations("nav");
  const locale = useLocale();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const links = [
    { href: "/", label: t("home") },
    { href: "/prediction", label: t("prediction") },
    { href: "/methodologie", label: t("methodology") },
    { href: "/contact", label: t("contact") },
  ];

  return (
    // Note: the mobile overlay below is rendered OUTSIDE <nav> on purpose — <nav>
    // uses backdrop-blur (a backdrop-filter), which per spec makes it a containing
    // block for position:fixed descendants. A fixed overlay nested inside it would
    // size itself against the ~72px navbar instead of the viewport.
    <>
    <nav className="sticky top-0 z-50 flex items-center justify-between px-6 md:px-10 py-4 backdrop-blur-md bg-gradient-to-b from-bg/90 to-bg/55 border-b border-border">
      <Link href="/" className="flex items-center gap-2.5 font-extrabold text-lg tracking-tight">
        <span className="relative w-6.5 h-6.5 rounded-lg bg-gradient-to-br from-accent to-accent-hi shadow-[0_4px_16px_rgba(255,106,57,0.35)] overflow-hidden" />
        WindCast
      </Link>

      <div className="hidden md:flex gap-8">
        {links.map((l) => {
          const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
          return (
            <Link
              key={l.href}
              href={l.href}
              className={`relative text-sm font-medium transition-colors ${
                active ? "text-text-primary" : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {l.label}
              {active && (
                <span className="absolute -bottom-1.5 left-0 h-0.5 w-full bg-accent rounded-full" />
              )}
            </Link>
          );
        })}
      </div>

      <div className="hidden md:flex items-center gap-4">
        <div className="flex border border-border-strong rounded-lg overflow-hidden text-xs font-semibold">
          {LOCALES.map((loc) => (
            <Link
              key={loc}
              href={pathname}
              locale={loc}
              className={`px-2.5 py-1.5 transition-colors ${
                locale === loc ? "bg-accent-soft text-accent" : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {loc.toUpperCase()}
            </Link>
          ))}
        </div>
        <Link
          href="/prediction"
          className="bg-gradient-to-br from-accent to-accent-hi text-[#1a0d05] font-bold text-sm px-4.5 py-2.5 rounded-lg shadow-[0_6px_22px_rgba(255,106,57,0.3)] hover:-translate-y-0.5 transition-transform"
        >
          {t("cta")}
        </Link>
      </div>

      <button
        className="md:hidden flex flex-col gap-1.5 w-11 h-11 items-center justify-center"
        aria-label="Menu"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <span className={`block h-0.5 w-6 bg-text-primary transition-transform ${open ? "translate-y-2 rotate-45" : ""}`} />
        <span className={`block h-0.5 w-6 bg-text-primary transition-opacity ${open ? "opacity-0" : ""}`} />
        <span className={`block h-0.5 w-6 bg-text-primary transition-transform ${open ? "-translate-y-2 -rotate-45" : ""}`} />
      </button>
    </nav>

      {open && (
        <div
          className="md:hidden fixed inset-x-0 top-[64px] bottom-0 z-40 flex flex-col gap-1 p-6"
          style={{ backgroundColor: "#0c0e12" }}
        >
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className="text-lg font-medium py-3.5 border-b border-border text-text-primary min-h-11"
            >
              {l.label}
            </Link>
          ))}
          <div className="flex gap-3 mt-5">
            {LOCALES.map((loc) => (
              <Link
                key={loc}
                href={pathname}
                locale={loc}
                onClick={() => setOpen(false)}
                className={`px-4 py-2.5 rounded-lg border text-sm font-semibold min-h-11 flex items-center ${
                  locale === loc ? "border-accent text-accent" : "border-border-strong text-text-secondary"
                }`}
              >
                {loc.toUpperCase()}
              </Link>
            ))}
          </div>
          <Link
            href="/prediction"
            onClick={() => setOpen(false)}
            className="mt-5 bg-gradient-to-br from-accent to-accent-hi text-[#1a0d05] font-bold text-center px-5 py-3.5 rounded-lg min-h-11"
          >
            {t("cta")}
          </Link>
        </div>
      )}
    </>
  );
}
