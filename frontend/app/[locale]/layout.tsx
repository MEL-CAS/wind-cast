import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { NextIntlClientProvider, hasLocale } from "next-intl";
import { notFound } from "next/navigation";
import { routing } from "@/i18n/routing";
import WindCanvas from "@/components/WindCanvas";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import "../globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
const jetbrainsMono = JetBrains_Mono({ variable: "--font-jetbrains-mono", subsets: ["latin"], weight: ["500", "600"] });

export const metadata: Metadata = {
  title: "WindCast — prévision de vent pour l'industrie",
  description:
    "Prévision de vitesse de vent à 24h, calibrée par régime, pour vos décisions de levage, de sécurité chantier et de production éolienne.",
  icons: { icon: "/favicon.ico" },
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  return (
    <html lang={locale} className={`${inter.variable} ${jetbrainsMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col relative">
        <NextIntlClientProvider>
          <WindCanvas />
          <div className="fixed inset-0 z-0 bg-halo pointer-events-none" />
          <div className="fixed inset-0 z-0 bg-grid pointer-events-none" />
          <div className="fixed inset-0 z-0 bg-vignette pointer-events-none" />
          <div className="relative z-10 flex flex-col min-h-full">
            <Nav />
            <main className="flex-1">{children}</main>
            <Footer />
          </div>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
