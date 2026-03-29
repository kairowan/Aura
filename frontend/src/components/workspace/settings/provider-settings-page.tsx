"use client";

import { useQueryClient } from "@tanstack/react-query";
import { CloudIcon, SaveIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getBackendBaseURL } from "@/core/config";
import { useI18n } from "@/core/i18n/hooks";

import { SettingsSection } from "./settings-section";

interface ProviderConfig {
  base_url: string;
  api_key: string;
  model_id: string;
  display_name: string;
}

export function ProviderSettingsPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [config, setConfig] = useState<ProviderConfig>({
    base_url: "",
    api_key: "",
    model_id: "",
    display_name: "",
  });

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await fetch(`${getBackendBaseURL()}/api/provider/config`);
        if (response.ok) {
          const data = await response.json();
          setConfig({
            base_url: data.base_url || "",
            api_key: data.api_key || "",
            model_id: data.model_id || "",
            display_name: data.display_name || "",
          });
        }
      } catch (error) {
        console.error("Failed to fetch provider config:", error);
      }
    };
    void fetchConfig();
  }, []);

  const handleSave = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${getBackendBaseURL()}/api/provider/config`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(config),
      });

      if (response.ok) {
        await queryClient.invalidateQueries({ queryKey: ["models"] });
        toast.success(t.settings.provider.saveSuccess);
      } else {
        toast.error(t.settings.provider.saveError);
      }
    } catch (error) {
      console.error("Failed to save provider config:", error);
      toast.error(t.settings.provider.saveError);
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async () => {
    setValidating(true);
    try {
      const response = await fetch(`${getBackendBaseURL()}/api/provider/validate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(config),
      });
      const data = await response.json();

      if (response.ok) {
        toast.success(data.message ?? t.settings.provider.validateSuccess);
      } else {
        toast.error(data.detail ?? t.settings.provider.validateError);
      }
    } catch (error) {
      console.error("Failed to validate provider config:", error);
      toast.error(t.settings.provider.validateError);
    } finally {
      setValidating(false);
    }
  };

  return (
    <div className="space-y-8 pb-2">
      <SettingsSection
        title={t.settings.provider.title}
        description={t.settings.provider.description}
      >
        <div className="grid gap-6">
          <div className="grid gap-2">
            <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
              {t.settings.provider.displayNameLabel}
            </label>
            <Input
              placeholder={t.settings.provider.displayNamePlaceholder}
              value={config.display_name}
              onChange={(e) =>
                setConfig({ ...config, display_name: e.target.value })
              }
              className="bg-white/50 backdrop-blur-sm"
            />
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
              {t.settings.provider.baseUrlLabel}
            </label>
            <Input
              placeholder={t.settings.provider.baseUrlPlaceholder}
              value={config.base_url}
              onChange={(e) => setConfig({ ...config, base_url: e.target.value })}
              className="bg-white/50 backdrop-blur-sm"
            />
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
              {t.settings.provider.apiKeyLabel}
            </label>
            <Input
              type="password"
              placeholder={t.settings.provider.apiKeyPlaceholder}
              value={config.api_key}
              onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
              className="bg-white/50 backdrop-blur-sm"
            />
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
              {t.settings.provider.modelIdLabel}
            </label>
            <Input
              placeholder={t.settings.provider.modelIdPlaceholder}
              value={config.model_id}
              onChange={(e) => setConfig({ ...config, model_id: e.target.value })}
              className="bg-white/50 backdrop-blur-sm"
            />
          </div>

          <div className="sticky bottom-0 z-10 -mx-5 mt-2 flex justify-end gap-3 border-t bg-background/95 px-5 pt-4 pb-[calc(env(safe-area-inset-bottom,0px)+0.5rem)] backdrop-blur md:-mx-6 md:px-6">
            <Button
              type="button"
              variant="outline"
              disabled={validating}
              onClick={handleValidate}
              className="min-w-32"
            >
              <CloudIcon className="mr-2 size-4" />
              {t.settings.provider.validateButton}
            </Button>
            <Button
              disabled={loading}
              onClick={handleSave}
              className="min-w-32 bg-emerald-500 text-white shadow-[0_0_20px_rgba(16,185,129,0.4)] transition-all hover:scale-105 hover:bg-emerald-600"
            >
              <SaveIcon className="mr-2 size-4" />
              {t.common.save}
            </Button>
          </div>
        </div>
      </SettingsSection>
    </div>
  );
}
