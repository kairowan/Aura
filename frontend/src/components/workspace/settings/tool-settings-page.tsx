"use client";

import { SearchIcon } from "lucide-react";
import { useMemo, useState } from "react";

import { Input } from "@/components/ui/input";
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from "@/components/ui/item";
import { Switch } from "@/components/ui/switch";
import { useI18n } from "@/core/i18n/hooks";
import { useMCPConfig, useEnableMCPServer } from "@/core/mcp/hooks";
import type { MCPServerConfig } from "@/core/mcp/types";
import { env } from "@/env";

import { SettingsSection } from "./settings-section";

export function ToolSettingsPage() {
  const { t } = useI18n();
  const { config, isLoading, error } = useMCPConfig();
  return (
    <SettingsSection
      title={t.settings.tools.title}
      description={t.settings.tools.description}
    >
      {isLoading ? (
        <div className="text-muted-foreground text-sm">{t.common.loading}</div>
      ) : error ? (
        <div>Error: {error.message}</div>
      ) : (
        config && <MCPServerList servers={config.mcp_servers} />
      )}
    </SettingsSection>
  );
}

function MCPServerList({
  servers,
}: {
  servers: Record<string, MCPServerConfig>;
}) {
  const { t } = useI18n();
  const { mutate: enableMCPServer } = useEnableMCPServer();
  const [query, setQuery] = useState("");
  const filteredServers = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return Object.entries(servers).filter(([name, config]) => {
      if (!normalizedQuery) {
        return true;
      }
      const haystack = [name, config.description ?? ""].join(" ").toLowerCase();
      return haystack.includes(normalizedQuery);
    });
  }, [query, servers]);

  return (
    <div className="flex w-full flex-col gap-4">
      <div className="relative w-full sm:w-80">
        <SearchIcon className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" />
        <Input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t.settings.tools.searchPlaceholder}
          className="pl-9"
        />
      </div>
      {filteredServers.length === 0 ? (
        <div className="text-muted-foreground rounded-lg border border-dashed px-4 py-6 text-sm">
          {t.settings.tools.emptySearch}
        </div>
      ) : (
        filteredServers.map(([name, config]) => (
          <Item className="w-full" variant="outline" key={name}>
            <ItemContent>
              <ItemTitle>
                <div className="flex items-center gap-2">
                  <div>{name}</div>
                </div>
              </ItemTitle>
              <ItemDescription className="line-clamp-4">
                {config.description}
              </ItemDescription>
            </ItemContent>
            <ItemActions>
              <Switch
                checked={config.enabled}
                disabled={env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true"}
                onCheckedChange={(checked) =>
                  enableMCPServer({ serverName: name, enabled: checked })
                }
              />
            </ItemActions>
          </Item>
        ))
      )}
    </div>
  );
}
