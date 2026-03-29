"use client";

import { useEffect, useState } from "react";
import { DrawIoEmbed } from "react-drawio";

import { env } from "@/env";
import { cn } from "@/lib/utils";

type DrawioPreviewProps = {
  className?: string;
  xml: string;
};

export function DrawioPreview({ className, xml }: DrawioPreviewProps) {
  const [isReady, setIsReady] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const [hasTimedOut, setHasTimedOut] = useState(false);

  useEffect(() => {
    const root = document.documentElement;
    const syncTheme = () => setIsDark(root.classList.contains("dark"));

    syncTheme();

    const observer = new MutationObserver(syncTheme);
    observer.observe(root, {
      attributes: true,
      attributeFilter: ["class"],
    });

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (isReady) {
      return;
    }

    const timeout = window.setTimeout(() => {
      setHasTimedOut(true);
    }, 12000);

    return () => window.clearTimeout(timeout);
  }, [isReady]);

  return (
    <div className={cn("relative size-full bg-background", className)}>
      <div className={cn("absolute inset-0", !isReady && "invisible")}>
        <DrawIoEmbed
          baseUrl={
            env.NEXT_PUBLIC_DRAWIO_BASE_URL ?? "https://embed.diagrams.net"
          }
          xml={xml}
          urlParameters={{
            ui: "min",
            chrome: true,
            nav: true,
            layers: true,
            dark: isDark,
            spin: false,
          }}
          onLoad={() => {
            setIsReady(true);
            setHasTimedOut(false);
          }}
        />
      </div>
      {!isReady && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-background/95 px-6 text-center">
          <div className="text-sm font-medium">正在加载 Draw.io 预览</div>
          <div className="text-muted-foreground max-w-sm text-xs leading-5">
            该预览使用 diagrams.net 的嵌入式查看器渲染当前 artifact。你也可以切回代码视图查看原始 XML。
          </div>
          {hasTimedOut && (
            <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs leading-5 text-amber-700 dark:text-amber-300">
              Draw.io 预览加载超时。请检查网络访问，或先切换到代码视图继续查看 XML。
            </div>
          )}
        </div>
      )}
    </div>
  );
}
