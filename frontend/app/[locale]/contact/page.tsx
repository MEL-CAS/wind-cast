"use client";

import { useTranslations } from "next-intl";
import Reveal from "@/components/Reveal";

const CONTACT_EMAIL = "melissa02cassan@gmail.com";

export default function ContactPage() {
  const t = useTranslations("contact");

  return (
    <div className="max-w-[640px] mx-auto px-6 md:px-10 py-16 text-center">
      <Reveal>
        <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-2">{t("title")}</h1>
        <p className="text-text-secondary mb-10">{t("subtitle")}</p>
      </Reveal>

      <Reveal delay={0.05} className="flex justify-center">
        <a
          href={`mailto:${CONTACT_EMAIL}`}
          className="bg-gradient-to-br from-accent to-accent-hi text-[#1a0d05] font-bold px-6 py-3.5 rounded-[10px] min-h-11 shadow-[0_6px_24px_rgba(255,106,57,0.3)]"
        >
          {t("email")}
        </a>
      </Reveal>

      <Reveal delay={0.1}>
        <p className="text-sm text-text-muted mt-10">{t("freelance")}</p>
      </Reveal>
    </div>
  );
}
