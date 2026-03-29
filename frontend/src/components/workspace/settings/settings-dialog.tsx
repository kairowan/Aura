"use client";

import {
  BellIcon,
  InfoIcon,
  BrainIcon,
  PaletteIcon,
  SparklesIcon,
  WrenchIcon,
  CloudIcon,
  BotIcon,
  MessagesSquare,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AboutSettingsPage } from "@/components/workspace/settings/about-settings-page";
import { AutomationSettingsPage } from "@/components/workspace/settings/automation-settings-page";
import { AppearanceSettingsPage } from "@/components/workspace/settings/appearance-settings-page";
import { ChannelSettingsPage } from "@/components/workspace/settings/channel-settings-page";
import { MemorySettingsPage } from "@/components/workspace/settings/memory-settings-page";
import { NotificationSettingsPage } from "@/components/workspace/settings/notification-settings-page";
import { SkillSettingsPage } from "@/components/workspace/settings/skill-settings-page";
import { ToolSettingsPage } from "@/components/workspace/settings/tool-settings-page";
import { ProviderSettingsPage } from "@/components/workspace/settings/provider-settings-page";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

export type SettingsSection =
  | "appearance"
  | "memory"
  | "tools"
  | "skills"
  | "notification"
  | "aiProvider"
  | "channels"
  | "automation"
  | "about";

type SettingsDialogProps = React.ComponentProps<typeof Dialog> & {
  defaultSection?: SettingsSection;
};

export function SettingsDialog(props: SettingsDialogProps) {
  const { defaultSection = "appearance", ...dialogProps } = props;
  const { t } = useI18n();
  const [activeSection, setActiveSection] =
    useState<SettingsSection>(defaultSection);

  useEffect(() => {
    // When opening the dialog, ensure the active section follows the caller's intent.
    // This allows triggers like "About" to open the dialog directly on that page.
    if (dialogProps.open) {
      setActiveSection(defaultSection);
    }
  }, [defaultSection, dialogProps.open]);

  const sections = useMemo(
    () => [
      {
        id: "appearance",
        label: t.settings.sections.appearance,
        icon: PaletteIcon,
      },
      {
        id: "notification",
        label: t.settings.sections.notification,
        icon: BellIcon,
      },
      {
        id: "memory",
        label: t.settings.sections.memory,
        icon: BrainIcon,
      },
      { id: "tools", label: t.settings.sections.tools, icon: WrenchIcon },
      { id: "aiProvider", label: t.settings.sections.aiProvider, icon: CloudIcon },
      { id: "channels", label: t.settings.sections.channels, icon: MessagesSquare },
      { id: "automation", label: t.settings.sections.automation, icon: BotIcon },
      { id: "skills", label: t.settings.sections.skills, icon: SparklesIcon },
      { id: "about", label: t.settings.sections.about, icon: InfoIcon },
    ],
    [
      t.settings.sections.appearance,
      t.settings.sections.memory,
      t.settings.sections.tools,
      t.settings.sections.skills,
      t.settings.sections.notification,
      t.settings.sections.aiProvider,
      t.settings.sections.channels,
      t.settings.sections.automation,
      t.settings.sections.about,
    ],
  );
  return (
    <Dialog
      {...dialogProps}
      onOpenChange={(open) => props.onOpenChange?.(open)}
    >
      <DialogContent
        className="top-[48%] flex h-[min(78vh,860px)] max-h-[calc(100vh-3rem)] flex-col overflow-hidden p-4 sm:top-[50%] sm:max-w-5xl sm:p-5 md:max-w-6xl md:p-6"
        aria-describedby={undefined}
      >
        <DialogHeader className="gap-1">
          <DialogTitle>{t.settings.title}</DialogTitle>
          <p className="text-muted-foreground text-sm">
            {t.settings.description}
          </p>
        </DialogHeader>
        <div className="grid min-h-0 flex-1 gap-3 md:grid-cols-[240px_minmax(0,1fr)]">
          <nav className="bg-sidebar min-h-0 overflow-y-auto rounded-xl border p-2 max-md:max-h-48">
            <ul className="space-y-1 pr-1">
              {sections.map(({ id, label, icon: Icon }) => {
                const active = activeSection === id;
                return (
                  <li key={id}>
                    <button
                      type="button"
                      onClick={() => setActiveSection(id as SettingsSection)}
                      className={cn(
                        "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                        active
                          ? "bg-primary text-primary-foreground shadow-sm"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground",
                      )}
                    >
                      <Icon className="size-4" />
                      <span>{label}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>
          <ScrollArea className="h-full min-h-0 rounded-xl border bg-background/70">
            <div className="space-y-8 p-5 pb-10 md:p-6 md:pb-12">
              {activeSection === "appearance" && <AppearanceSettingsPage />}
              {activeSection === "memory" && <MemorySettingsPage />}
              {activeSection === "tools" && <ToolSettingsPage />}
              {activeSection === "skills" && (
                <SkillSettingsPage
                  onClose={() => props.onOpenChange?.(false)}
                />
              )}
              {activeSection === "notification" && <NotificationSettingsPage />}
              {activeSection === "aiProvider" && <ProviderSettingsPage />}
              {activeSection === "channels" && <ChannelSettingsPage />}
              {activeSection === "automation" && <AutomationSettingsPage />}
              {activeSection === "about" && <AboutSettingsPage />}
            </div>
          </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  );
}
