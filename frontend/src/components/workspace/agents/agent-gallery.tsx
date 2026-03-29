"use client";

import { BotIcon, PlusIcon, SearchIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAgents } from "@/core/agents";
import { useI18n } from "@/core/i18n/hooks";

import { AgentCard } from "./agent-card";

export function AgentGallery() {
  const { t } = useI18n();
  const { agents, isLoading } = useAgents();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const filteredAgents = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
      return agents;
    }
    return agents.filter((agent) => {
      const haystack = [
        agent.name,
        agent.description ?? "",
        agent.model ?? "",
        ...(agent.tool_groups ?? []),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(normalizedQuery);
    });
  }, [agents, query]);

  const handleNewAgent = () => {
    router.push("/workspace/agents/new");
  };

  return (
    <div className="flex size-full flex-col">
      {/* Page header */}
      <div className="border-b border-slate-200/80 bg-white/85 px-6 py-5 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-[1600px] items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight text-slate-950">
                {t.agents.title}
              </h1>
              {!isLoading && filteredAgents.length > 0 && (
                <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600">
                  {filteredAgents.length}
                </span>
              )}
            </div>
            <p className="mt-1 text-sm leading-6 text-slate-500">
              {t.agents.description}
            </p>
          </div>
          <div className="flex w-full max-w-xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
            <div className="relative w-full sm:max-w-xs">
              <SearchIcon className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={t.agents.searchPlaceholder}
                className="h-11 rounded-full border-slate-200 bg-white pl-9 shadow-none"
              />
            </div>
            <Button
              size="lg"
              className="rounded-full bg-emerald-500 px-5 text-white shadow-[0_18px_36px_-22px_rgba(16,185,129,0.85)] hover:bg-emerald-600"
              onClick={handleNewAgent}
            >
              <PlusIcon className="mr-1.5 h-4 w-4" />
              {t.agents.newAgent}
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="mx-auto flex h-40 w-full max-w-[1600px] items-center justify-center text-sm text-slate-500">
            {t.common.loading}
          </div>
        ) : agents.length === 0 ? (
          <div className="mx-auto flex h-64 w-full max-w-[1600px] flex-col items-center justify-center gap-3 rounded-[28px] border border-dashed border-slate-200 bg-white/70 text-center shadow-[0_18px_45px_-32px_rgba(15,23,42,0.18)]">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
              <BotIcon className="h-7 w-7" />
            </div>
            <div>
              <p className="font-medium text-slate-900">{t.agents.emptyTitle}</p>
              <p className="mt-1 text-sm text-slate-500">
                {t.agents.emptyDescription}
              </p>
            </div>
            <Button
              variant="outline"
              className="mt-2 rounded-full border-slate-200 bg-white"
              onClick={handleNewAgent}
            >
              <PlusIcon className="mr-1.5 h-4 w-4" />
              {t.agents.newAgent}
            </Button>
          </div>
        ) : filteredAgents.length === 0 ? (
          <div className="mx-auto flex h-64 w-full max-w-[1600px] flex-col items-center justify-center gap-3 rounded-[28px] border border-dashed border-slate-200 bg-white/70 text-center shadow-[0_18px_45px_-32px_rgba(15,23,42,0.18)]">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-slate-100 text-slate-500">
              <SearchIcon className="h-7 w-7" />
            </div>
            <div>
              <p className="font-medium text-slate-900">
                {t.agents.searchEmptyTitle}
              </p>
              <p className="mt-1 text-sm text-slate-500">
                {t.agents.searchEmptyDescription}
              </p>
            </div>
          </div>
        ) : (
          <div className="mx-auto grid w-full max-w-[1600px] auto-rows-fr grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
            {filteredAgents.map((agent) => (
              <AgentCard key={agent.name} agent={agent} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
