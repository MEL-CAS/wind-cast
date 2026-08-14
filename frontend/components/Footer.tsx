import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";

export default function Footer() {
  const t = useTranslations("footer");
  const tn = useTranslations("nav");

  return (
    <footer className="max-w-[1120px] mx-auto mt-16 px-6 md:px-10 py-9 border-t border-border flex justify-between items-center gap-5 flex-wrap">
      <div className="min-w-0 flex items-center gap-2.5 text-text-secondary text-sm">
        <span className="shrink-0 w-5 h-5 rounded-md bg-gradient-to-br from-accent to-accent-hi" />
        <span className="min-w-0">{t("tagline")}</span>
      </div>
      <div className="min-w-0 flex gap-6 text-sm flex-wrap">
        <Link href="/prediction" className="text-text-secondary hover:text-text-primary transition-colors">
          {tn("prediction")}
        </Link>
        <Link href="/methodologie" className="text-text-secondary hover:text-text-primary transition-colors">
          {tn("methodology")}
        </Link>
        <Link href="/contact" className="text-text-secondary hover:text-text-primary transition-colors">
          {tn("contact")}
        </Link>
      </div>
    </footer>
  );
}
