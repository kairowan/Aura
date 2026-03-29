"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from "@/components/ui/item";
import { Switch } from "@/components/ui/switch";
import { getBackendBaseURL } from "@/core/config";
import { useI18n } from "@/core/i18n/hooks";

import { SettingsSection } from "./settings-section";

type ChannelName = "feishu" | "slack" | "telegram";

type ManagedChannelConfig = {
  enabled: boolean;
  assistant_id: string | null;
  app_id: string | null;
  app_secret: string | null;
  bot_token: string | null;
  app_token: string | null;
  allowed_users: string[];
};

type ChannelConfigResponse = {
  default_assistant_id: string | null;
  feishu: ManagedChannelConfig;
  slack: ManagedChannelConfig;
  telegram: ManagedChannelConfig;
};

type ChannelStatusResponse = {
  service_running: boolean;
  channels: Record<string, { enabled: boolean; running: boolean }>;
};

const EMPTY_CONFIG: ChannelConfigResponse = {
  default_assistant_id: "",
  feishu: {
    enabled: false,
    assistant_id: "",
    app_id: "",
    app_secret: "",
    bot_token: "",
    app_token: "",
    allowed_users: [],
  },
  slack: {
    enabled: false,
    assistant_id: "",
    app_id: "",
    app_secret: "",
    bot_token: "",
    app_token: "",
    allowed_users: [],
  },
  telegram: {
    enabled: false,
    assistant_id: "",
    app_id: "",
    app_secret: "",
    bot_token: "",
    app_token: "",
    allowed_users: [],
  },
};

export function ChannelSettingsPage() {
  const { t } = useI18n();
  const [config, setConfig] = useState<ChannelConfigResponse>(EMPTY_CONFIG);
  const [status, setStatus] = useState<ChannelStatusResponse>({
    service_running: false,
    channels: {},
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [restarting, setRestarting] = useState<string | null>(null);

  const descriptors = useMemo(
    () => [
      {
        name: "feishu" as const,
        title: t.settings.channels.providers.feishu.title,
        description: t.settings.channels.providers.feishu.description,
        fields: [
          {
            key: "app_id" as const,
            label: t.settings.channels.providers.feishu.appIdLabel,
            placeholder: t.settings.channels.providers.feishu.appIdPlaceholder,
            type: "text",
          },
          {
            key: "app_secret" as const,
            label: t.settings.channels.providers.feishu.appSecretLabel,
            placeholder: t.settings.channels.providers.feishu.appSecretPlaceholder,
            type: "password",
          },
        ],
      },
      {
        name: "slack" as const,
        title: t.settings.channels.providers.slack.title,
        description: t.settings.channels.providers.slack.description,
        fields: [
          {
            key: "bot_token" as const,
            label: t.settings.channels.providers.slack.botTokenLabel,
            placeholder: t.settings.channels.providers.slack.botTokenPlaceholder,
            type: "password",
          },
          {
            key: "app_token" as const,
            label: t.settings.channels.providers.slack.appTokenLabel,
            placeholder: t.settings.channels.providers.slack.appTokenPlaceholder,
            type: "password",
          },
        ],
      },
      {
        name: "telegram" as const,
        title: t.settings.channels.providers.telegram.title,
        description: t.settings.channels.providers.telegram.description,
        fields: [
          {
            key: "bot_token" as const,
            label: t.settings.channels.providers.telegram.botTokenLabel,
            placeholder: t.settings.channels.providers.telegram.botTokenPlaceholder,
            type: "password",
          },
        ],
      },
    ],
    [t],
  );

  const fetchData = async () => {
    setLoading(true);
    try {
      const [configResponse, statusResponse] = await Promise.all([
        fetch(`${getBackendBaseURL()}/api/channels/config`),
        fetch(`${getBackendBaseURL()}/api/channels/`),
      ]);

      if (!configResponse.ok) {
        throw new Error(t.settings.channels.loadError);
      }

      const configData = (await configResponse.json()) as ChannelConfigResponse;
      setConfig({
        default_assistant_id: configData.default_assistant_id || "",
        feishu: {
          ...EMPTY_CONFIG.feishu,
          ...configData.feishu,
          allowed_users: configData.feishu?.allowed_users ?? [],
        },
        slack: {
          ...EMPTY_CONFIG.slack,
          ...configData.slack,
          allowed_users: configData.slack?.allowed_users ?? [],
        },
        telegram: {
          ...EMPTY_CONFIG.telegram,
          ...configData.telegram,
          allowed_users: configData.telegram?.allowed_users ?? [],
        },
      });

      if (statusResponse.ok) {
        const statusData = (await statusResponse.json()) as ChannelStatusResponse;
        setStatus(statusData);
      }
    } catch (error) {
      console.error("Failed to load channel config:", error);
      toast.error(t.settings.channels.loadError);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchData();
  }, []);

  const updateChannel = (
    channelName: ChannelName,
    updater: (current: ManagedChannelConfig) => ManagedChannelConfig,
  ) => {
    setConfig((current) => ({
      ...current,
      [channelName]: updater(current[channelName]),
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${getBackendBaseURL()}/api/channels/config`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(config),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? t.settings.channels.saveError);
      }
      toast.success(data.message ?? t.settings.channels.saveSuccess);
      if (data.status) {
        setStatus(data.status as ChannelStatusResponse);
      } else {
        await fetchData();
      }
    } catch (error) {
      console.error("Failed to save channel config:", error);
      toast.error(
        error instanceof Error ? error.message : t.settings.channels.saveError,
      );
    } finally {
      setSaving(false);
    }
  };

  const handleRestart = async (channelName: ChannelName) => {
    setRestarting(channelName);
    try {
      const response = await fetch(
        `${getBackendBaseURL()}/api/channels/${channelName}/restart`,
        {
          method: "POST",
        },
      );
      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.detail ?? data.message ?? t.settings.channels.restartError);
      }
      toast.success(t.settings.channels.restartSuccess.replace("{name}", channelName));
      await fetchData();
    } catch (error) {
      console.error("Failed to restart channel:", error);
      toast.error(
        error instanceof Error ? error.message : t.settings.channels.restartError,
      );
    } finally {
      setRestarting(null);
    }
  };

  return (
    <div className="space-y-8 pb-2">
      <SettingsSection
        title={t.settings.channels.title}
        description={t.settings.channels.description}
      >
        {loading ? (
          <div className="text-muted-foreground text-sm">{t.common.loading}</div>
        ) : (
          <div className="grid gap-6">
            <div className="rounded-2xl border bg-muted/20 p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div className="space-y-1">
                  <div className="text-sm font-medium">
                    {t.settings.channels.serviceStatusLabel}
                  </div>
                  <div className="text-muted-foreground text-sm">
                    {t.settings.channels.serviceStatusDescription}
                  </div>
                </div>
                <Badge
                  variant={status.service_running ? "default" : "secondary"}
                  className="rounded-full px-3 py-1 text-xs"
                >
                  {status.service_running
                    ? t.settings.channels.serviceRunning
                    : t.settings.channels.serviceStopped}
                </Badge>
              </div>
              <div className="mt-4 grid gap-2">
                <label className="text-sm font-medium">
                  {t.settings.channels.defaultAssistantLabel}
                </label>
                <Input
                  value={config.default_assistant_id ?? ""}
                  onChange={(event) =>
                    setConfig((current) => ({
                      ...current,
                      default_assistant_id: event.target.value,
                    }))
                  }
                  placeholder={t.settings.channels.defaultAssistantPlaceholder}
                />
              </div>
            </div>

            {descriptors.map((descriptor) => {
              const channelConfig = config[descriptor.name];
              const channelStatus = status.channels[descriptor.name];
              return (
                <Item
                  key={descriptor.name}
                  variant="outline"
                  className="items-start rounded-2xl p-5"
                >
                  <ItemContent className="gap-5">
                    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <ItemTitle>{descriptor.title}</ItemTitle>
                          <Badge
                            variant={channelStatus?.running ? "default" : "outline"}
                            className="rounded-full px-2.5 py-0.5"
                          >
                            {channelStatus?.running
                              ? t.settings.channels.running
                              : channelConfig.enabled
                                ? t.settings.channels.notRunning
                                : t.settings.channels.disabled}
                          </Badge>
                        </div>
                        <ItemDescription>{descriptor.description}</ItemDescription>
                      </div>
                      <ItemActions className="justify-end">
                        <Switch
                          checked={channelConfig.enabled}
                          onCheckedChange={(checked) =>
                            updateChannel(descriptor.name, (current) => ({
                              ...current,
                              enabled: checked,
                            }))
                          }
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={restarting === descriptor.name}
                          onClick={() => handleRestart(descriptor.name)}
                        >
                          {t.settings.channels.restartButton}
                        </Button>
                      </ItemActions>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                      {descriptor.fields.map((field) => (
                        <div key={field.key} className="grid gap-2">
                          <label className="text-sm font-medium">
                            {field.label}
                          </label>
                          <Input
                            type={field.type}
                            value={(channelConfig[field.key] as string | null) ?? ""}
                            placeholder={field.placeholder}
                            onChange={(event) =>
                              updateChannel(descriptor.name, (current) => ({
                                ...current,
                                [field.key]: event.target.value,
                              }))
                            }
                          />
                        </div>
                      ))}

                      <div className="grid gap-2">
                        <label className="text-sm font-medium">
                          {t.settings.channels.assistantLabel}
                        </label>
                        <Input
                          value={channelConfig.assistant_id ?? ""}
                          placeholder={t.settings.channels.assistantPlaceholder}
                          onChange={(event) =>
                            updateChannel(descriptor.name, (current) => ({
                              ...current,
                              assistant_id: event.target.value,
                            }))
                          }
                        />
                      </div>

                      {descriptor.name !== "feishu" && (
                        <div className="grid gap-2 md:col-span-2">
                          <label className="text-sm font-medium">
                            {t.settings.channels.allowedUsersLabel}
                          </label>
                          <Input
                            value={channelConfig.allowed_users.join(", ")}
                            placeholder={t.settings.channels.allowedUsersPlaceholder}
                            onChange={(event) =>
                              updateChannel(descriptor.name, (current) => ({
                                ...current,
                                allowed_users: event.target.value
                                  .split(",")
                                  .map((item) => item.trim())
                                  .filter(Boolean),
                              }))
                            }
                          />
                        </div>
                      )}
                    </div>
                  </ItemContent>
                </Item>
              );
            })}

            <div className="sticky bottom-0 z-10 -mx-5 mt-2 flex justify-end gap-3 border-t bg-background/95 px-5 pt-4 pb-[calc(env(safe-area-inset-bottom,0px)+0.5rem)] backdrop-blur md:-mx-6 md:px-6">
              <Button
                disabled={saving}
                onClick={handleSave}
                className="min-w-32"
              >
                {t.common.save}
              </Button>
            </div>
          </div>
        )}
      </SettingsSection>
    </div>
  );
}
