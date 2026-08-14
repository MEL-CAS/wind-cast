"use client";

import { motion } from "framer-motion";

export default function ColdStartLoader({ title, text }: { title: string; text: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-5 py-16 px-6 text-center">
      <div className="relative w-16 h-16">
        <motion.span
          className="absolute inset-0 rounded-full border-2 border-accent-soft"
          animate={{ scale: [1, 1.4, 1], opacity: [0.6, 0, 0.6] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        />
        <span className="absolute inset-3 rounded-full bg-gradient-to-br from-accent to-accent-hi shadow-[0_6px_24px_rgba(255,106,57,0.35)]" />
      </div>
      <div>
        <p className="font-semibold text-text-primary">{title}</p>
        <p className="text-sm text-text-secondary mt-1.5 max-w-sm">{text}</p>
      </div>
    </div>
  );
}
