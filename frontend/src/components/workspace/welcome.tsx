"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useMemo } from "react";

import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

import { AuroraText } from "../ui/aurora-text";

let waved = false;

export function Welcome({
  className,
  mode,
}: {
  className?: string;
  mode?: "ultra" | "pro" | "thinking" | "flash";
}) {
  const { t } = useI18n();
  const searchParams = useSearchParams();
  const isUltra = useMemo(() => mode === "ultra", [mode]);
  const colors = useMemo(() => {
    if (isUltra) {
      return ["#f59e0b", "#fbbf24", "#fef3c7"];
    }
    return ["#10b981", "#3b82f6", "#a855f7"];
  }, [isUltra]);
  useEffect(() => {
    waved = true;
  }, []);
  return (
    <div
      className={cn(
        "mx-auto flex w-full max-w-2xl flex-col items-center justify-center gap-2 rounded-[48px] border border-white/60 bg-white/40 pt-8 pb-8 px-12 text-center shadow-[0_0_40px_rgba(16,185,129,0.1)] backdrop-blur-2xl",
        className,
      )}
    >
      <div className="animate-fade-in-up text-4xl font-bold tracking-tight text-slate-950">
        {searchParams.get("mode") === "skill" ? (
          `✨ ${t.welcome.createYourOwnSkill} ✨`
        ) : (
          <div className="flex flex-col items-center gap-4">
            <div className={cn("inline-block text-6xl drop-shadow-[0_0_40px_rgba(16,185,129,0.6)]", !waved ? "animate-wave" : "animate-pulse")}>
              {isUltra ? "🚀" : "💠"}
            </div>
            <AuroraText colors={colors} className="text-5xl">{t.welcome.greeting}</AuroraText>
          </div>
        )}
      </div>
      {searchParams.get("mode") === "skill" ? (
        <div className="animate-fade-in text-slate-500/80 delay-200 text-base">
          {t.welcome.createYourOwnSkillDescription.includes("\n") ? (
            <pre className="font-sans whitespace-pre-wrap break-words">
              {t.welcome.createYourOwnSkillDescription}
            </pre>
          ) : (
            <p>{t.welcome.createYourOwnSkillDescription}</p>
          )}
        </div>
      ) : (
        <div className="animate-fade-in text-slate-500/80 delay-300 text-base">
          {t.welcome.description.includes("\n") ? (
            <pre className="whitespace-pre-wrap break-words">{t.welcome.description}</pre>
          ) : (
            <p>{t.welcome.description}</p>
          )}
        </div>
      )}
    </div>
  );
}
