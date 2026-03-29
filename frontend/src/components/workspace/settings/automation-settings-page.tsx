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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { getBackendBaseURL } from "@/core/config";
import { useI18n } from "@/core/i18n/hooks";

import { SettingsSection } from "./settings-section";

type AutomationJob = {
  id: string;
  name: string;
  prompt: string;
  schedule_type: "interval" | "daily";
  interval_minutes: number;
  daily_time: string;
  assistant_id: string;
  enabled: boolean;
  delivery_channel: string | null;
  delivery_chat_id: string | null;
  next_run_at: number | null;
  last_run_at: number | null;
  last_status: "idle" | "running" | "success" | "error";
  last_error: string | null;
  last_output: string | null;
};

type AutomationListResponse = {
  jobs: AutomationJob[];
};

const DEFAULT_DRAFT = {
  name: "",
  prompt: "",
  schedule_type: "interval" as "interval" | "daily",
  interval_minutes: "60",
  daily_time: "09:00",
  assistant_id: "",
  enabled: true,
  delivery_channel: "none",
  delivery_chat_id: "",
};

export function AutomationSettingsPage() {
  const { t } = useI18n();
  const [jobs, setJobs] = useState<AutomationJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [actioningId, setActioningId] = useState<string | null>(null);
  const [draft, setDraft] = useState(DEFAULT_DRAFT);

  const deliveryOptions = useMemo(
    () => [
      { value: "none", label: t.settings.automation.deliveryNone },
      { value: "feishu", label: t.settings.channels.providers.feishu.title },
      { value: "slack", label: t.settings.channels.providers.slack.title },
      { value: "telegram", label: t.settings.channels.providers.telegram.title },
    ],
    [t],
  );

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${getBackendBaseURL()}/api/automations/`);
      if (!response.ok) {
        throw new Error(t.settings.automation.loadError);
      }
      const data = (await response.json()) as AutomationListResponse;
      setJobs(data.jobs);
    } catch (error) {
      console.error("Failed to load automations:", error);
      toast.error(t.settings.automation.loadError);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchJobs();
  }, []);

  const handleCreate = async () => {
    if (!draft.name.trim() || !draft.prompt.trim()) {
      toast.error(t.settings.automation.validationError);
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetch(`${getBackendBaseURL()}/api/automations/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: draft.name.trim(),
          prompt: draft.prompt.trim(),
          schedule_type: draft.schedule_type,
          interval_minutes: Number(draft.interval_minutes) || 60,
          daily_time: draft.daily_time,
          assistant_id: draft.assistant_id.trim() || undefined,
          enabled: draft.enabled,
          delivery_channel:
            draft.delivery_channel === "none" ? undefined : draft.delivery_channel,
          delivery_chat_id: draft.delivery_chat_id.trim() || undefined,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? t.settings.automation.createError);
      }

      toast.success(t.settings.automation.createSuccess);
      setDraft(DEFAULT_DRAFT);
      await fetchJobs();
    } catch (error) {
      console.error("Failed to create automation:", error);
      toast.error(
        error instanceof Error ? error.message : t.settings.automation.createError,
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handlePatch = async (
    jobId: string,
    payload: Record<string, string | boolean | number | null>,
    successMessage?: string,
  ) => {
    setActioningId(jobId);
    try {
      const response = await fetch(`${getBackendBaseURL()}/api/automations/${jobId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? t.settings.automation.updateError);
      }
      if (successMessage) {
        toast.success(successMessage);
      }
      await fetchJobs();
    } catch (error) {
      console.error("Failed to update automation:", error);
      toast.error(
        error instanceof Error ? error.message : t.settings.automation.updateError,
      );
    } finally {
      setActioningId(null);
    }
  };

  const handleRunNow = async (jobId: string) => {
    setActioningId(jobId);
    try {
      const response = await fetch(
        `${getBackendBaseURL()}/api/automations/${jobId}/run`,
        {
          method: "POST",
        },
      );
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? t.settings.automation.runError);
      }
      toast.success(t.settings.automation.runSuccess);
      await fetchJobs();
    } catch (error) {
      console.error("Failed to run automation:", error);
      toast.error(
        error instanceof Error ? error.message : t.settings.automation.runError,
      );
    } finally {
      setActioningId(null);
    }
  };

  const handleDelete = async (jobId: string) => {
    setActioningId(jobId);
    try {
      const response = await fetch(`${getBackendBaseURL()}/api/automations/${jobId}`, {
        method: "DELETE",
      });
      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.detail ?? t.settings.automation.deleteError);
      }
      toast.success(t.settings.automation.deleteSuccess);
      await fetchJobs();
    } catch (error) {
      console.error("Failed to delete automation:", error);
      toast.error(
        error instanceof Error ? error.message : t.settings.automation.deleteError,
      );
    } finally {
      setActioningId(null);
    }
  };

  const formatTimestamp = (value: number | null) => {
    if (!value) {
      return t.settings.automation.notScheduled;
    }
    return new Date(value * 1000).toLocaleString();
  };

  const getStatusLabel = (status: AutomationJob["last_status"]) => {
    if (status === "running") {
      return t.settings.automation.statusRunning;
    }
    if (status === "success") {
      return t.settings.automation.statusSuccess;
    }
    if (status === "error") {
      return t.settings.automation.statusError;
    }
    return t.settings.automation.statusIdle;
  };

  const getScheduleLabel = (job: AutomationJob) => {
    if (job.schedule_type === "daily") {
      return t.settings.automation.dailySummary.replace("{time}", job.daily_time);
    }
    return t.settings.automation.intervalSummary.replace(
      "{minutes}",
      String(job.interval_minutes),
    );
  };

  return (
    <div className="space-y-8 pb-2">
      <SettingsSection
        title={t.settings.automation.title}
        description={t.settings.automation.description}
      >
        <div className="grid gap-6">
          <div className="rounded-2xl border bg-muted/20 p-5">
            <div className="space-y-5">
              <div className="space-y-1">
                <div className="text-base font-semibold">
                  {t.settings.automation.createTitle}
                </div>
                <div className="text-muted-foreground text-sm">
                  {t.settings.automation.createDescription}
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="grid gap-2">
                  <label className="text-sm font-medium">
                    {t.settings.automation.nameLabel}
                  </label>
                  <Input
                    value={draft.name}
                    placeholder={t.settings.automation.namePlaceholder}
                    onChange={(event) =>
                      setDraft((current) => ({
                        ...current,
                        name: event.target.value,
                      }))
                    }
                  />
                </div>
                <div className="grid gap-2">
                  <label className="text-sm font-medium">
                    {t.settings.automation.assistantLabel}
                  </label>
                  <Input
                    value={draft.assistant_id}
                    placeholder={t.settings.automation.assistantPlaceholder}
                    onChange={(event) =>
                      setDraft((current) => ({
                        ...current,
                        assistant_id: event.target.value,
                      }))
                    }
                  />
                </div>
              </div>

              <div className="grid gap-2">
                <label className="text-sm font-medium">
                  {t.settings.automation.promptLabel}
                </label>
                <Textarea
                  value={draft.prompt}
                  placeholder={t.settings.automation.promptPlaceholder}
                  className="min-h-28"
                  onChange={(event) =>
                    setDraft((current) => ({
                      ...current,
                      prompt: event.target.value,
                    }))
                  }
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="grid gap-2">
                  <label className="text-sm font-medium">
                    {t.settings.automation.scheduleTypeLabel}
                  </label>
                  <Select
                    value={draft.schedule_type}
                    onValueChange={(value: "interval" | "daily") =>
                      setDraft((current) => ({
                        ...current,
                        schedule_type: value,
                      }))
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="interval">
                        {t.settings.automation.scheduleInterval}
                      </SelectItem>
                      <SelectItem value="daily">
                        {t.settings.automation.scheduleDaily}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {draft.schedule_type === "interval" ? (
                  <div className="grid gap-2">
                    <label className="text-sm font-medium">
                      {t.settings.automation.intervalLabel}
                    </label>
                    <Input
                      type="number"
                      min={1}
                      value={draft.interval_minutes}
                      onChange={(event) =>
                        setDraft((current) => ({
                          ...current,
                          interval_minutes: event.target.value,
                        }))
                      }
                    />
                  </div>
                ) : (
                  <div className="grid gap-2">
                    <label className="text-sm font-medium">
                      {t.settings.automation.dailyTimeLabel}
                    </label>
                    <Input
                      type="time"
                      value={draft.daily_time}
                      onChange={(event) =>
                        setDraft((current) => ({
                          ...current,
                          daily_time: event.target.value,
                        }))
                      }
                    />
                  </div>
                )}
              </div>

              <div className="grid gap-4 md:grid-cols-[minmax(0,220px)_minmax(0,1fr)]">
                <div className="grid gap-2">
                  <label className="text-sm font-medium">
                    {t.settings.automation.deliveryChannelLabel}
                  </label>
                  <Select
                    value={draft.delivery_channel}
                    onValueChange={(value) =>
                      setDraft((current) => ({
                        ...current,
                        delivery_channel: value,
                      }))
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {deliveryOptions.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid gap-2">
                  <label className="text-sm font-medium">
                    {t.settings.automation.deliveryChatIdLabel}
                  </label>
                  <Input
                    value={draft.delivery_chat_id}
                    placeholder={t.settings.automation.deliveryChatIdPlaceholder}
                    onChange={(event) =>
                      setDraft((current) => ({
                        ...current,
                        delivery_chat_id: event.target.value,
                      }))
                    }
                  />
                </div>
              </div>

              <div className="flex flex-col gap-3 rounded-xl border border-dashed px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="space-y-1">
                  <div className="text-sm font-medium">
                    {t.settings.automation.enabledLabel}
                  </div>
                  <div className="text-muted-foreground text-sm">
                    {t.settings.automation.enabledDescription}
                  </div>
                </div>
                <Switch
                  checked={draft.enabled}
                  onCheckedChange={(checked) =>
                    setDraft((current) => ({
                      ...current,
                      enabled: checked,
                    }))
                  }
                />
              </div>

              <div className="flex justify-end">
                <Button disabled={submitting} onClick={handleCreate}>
                  {t.settings.automation.createButton}
                </Button>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="text-base font-semibold">
              {t.settings.automation.listTitle}
            </div>
            {loading ? (
              <div className="text-muted-foreground text-sm">{t.common.loading}</div>
            ) : jobs.length === 0 ? (
              <div className="text-muted-foreground rounded-xl border border-dashed px-4 py-8 text-sm">
                {t.settings.automation.empty}
              </div>
            ) : (
              jobs.map((job) => (
                <Item
                  key={job.id}
                  variant="outline"
                  className="items-start rounded-2xl p-5"
                >
                  <ItemContent className="gap-4">
                    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <ItemTitle>{job.name}</ItemTitle>
                          <Badge
                            variant={
                              job.last_status === "success"
                                ? "default"
                                : job.last_status === "error"
                                  ? "destructive"
                                  : "secondary"
                            }
                            className="rounded-full px-2.5 py-0.5"
                          >
                            {getStatusLabel(job.last_status)}
                          </Badge>
                          {!job.enabled && (
                            <Badge variant="outline" className="rounded-full px-2.5 py-0.5">
                              {t.settings.automation.disabled}
                            </Badge>
                          )}
                        </div>
                        <ItemDescription className="line-clamp-3">
                          {job.prompt}
                        </ItemDescription>
                      </div>
                      <ItemActions className="justify-end">
                        <Switch
                          checked={job.enabled}
                          disabled={actioningId === job.id}
                          onCheckedChange={(checked) =>
                            void handlePatch(
                              job.id,
                              { enabled: checked },
                              checked
                                ? t.settings.automation.enableSuccess
                                : t.settings.automation.disableSuccess,
                            )
                          }
                        />
                      </ItemActions>
                    </div>

                    <div className="grid gap-2 text-sm md:grid-cols-2">
                      <div>
                        <span className="font-medium">
                          {t.settings.automation.scheduleLabel}
                        </span>
                        <span className="text-muted-foreground ml-2">
                          {getScheduleLabel(job)}
                        </span>
                      </div>
                      <div>
                        <span className="font-medium">
                          {t.settings.automation.nextRunLabel}
                        </span>
                        <span className="text-muted-foreground ml-2">
                          {formatTimestamp(job.next_run_at)}
                        </span>
                      </div>
                      <div>
                        <span className="font-medium">
                          {t.settings.automation.lastRunLabel}
                        </span>
                        <span className="text-muted-foreground ml-2">
                          {formatTimestamp(job.last_run_at)}
                        </span>
                      </div>
                      <div>
                        <span className="font-medium">
                          {t.settings.automation.deliveryLabel}
                        </span>
                        <span className="text-muted-foreground ml-2">
                          {job.delivery_channel && job.delivery_chat_id
                            ? `${job.delivery_channel}: ${job.delivery_chat_id}`
                            : t.settings.automation.deliveryNone}
                        </span>
                      </div>
                    </div>

                    {(job.last_error || job.last_output) && (
                      <div className="rounded-xl bg-muted/30 px-4 py-3 text-sm">
                        <div className="font-medium">
                          {job.last_error
                            ? t.settings.automation.lastErrorLabel
                            : t.settings.automation.lastOutputLabel}
                        </div>
                        <div className="text-muted-foreground mt-1 whitespace-pre-wrap break-words">
                          {job.last_error ?? job.last_output}
                        </div>
                      </div>
                    )}

                    <div className="flex flex-wrap justify-end gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={actioningId === job.id}
                        onClick={() => void handleRunNow(job.id)}
                      >
                        {t.settings.automation.runNowButton}
                      </Button>
                      <Button
                        type="button"
                        variant="destructive"
                        size="sm"
                        disabled={actioningId === job.id}
                        onClick={() => void handleDelete(job.id)}
                      >
                        {t.common.delete}
                      </Button>
                    </div>
                  </ItemContent>
                </Item>
              ))
            )}
          </div>
        </div>
      </SettingsSection>
    </div>
  );
}
