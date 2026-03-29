"use client";

import { BotIcon, MessageSquareIcon, Trash2Icon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useDeleteAgent } from "@/core/agents";
import type { Agent } from "@/core/agents";
import { useI18n } from "@/core/i18n/hooks";

interface AgentCardProps {
  agent: Agent;
}

export function AgentCard({ agent }: AgentCardProps) {
  const { t } = useI18n();
  const router = useRouter();
  const deleteAgent = useDeleteAgent();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const visibleToolGroups = agent.tool_groups?.slice(0, 3) ?? [];
  const hiddenToolGroupCount = Math.max(
    (agent.tool_groups?.length ?? 0) - visibleToolGroups.length,
    0,
  );

  function handleChat() {
    router.push(`/workspace/agents/${agent.name}/chats/new`);
  }

  async function handleDelete() {
    try {
      await deleteAgent.mutateAsync(agent.name);
      toast.success(t.agents.deleteSuccess);
      setDeleteOpen(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <>
      <Card className="group relative flex h-full min-h-[360px] flex-col overflow-hidden rounded-[28px] border border-slate-200/80 bg-white/95 py-0 shadow-[0_18px_45px_-28px_rgba(15,23,42,0.28)] transition-all duration-300 hover:-translate-y-1 hover:border-emerald-300/60 hover:shadow-[0_26px_70px_-30px_rgba(16,185,129,0.3)]">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-28 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.16),transparent_58%),linear-gradient(180deg,rgba(236,253,245,0.92),rgba(255,255,255,0))]" />
        <CardHeader className="relative gap-4 px-6 pt-6 pb-0">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border border-emerald-200/70 bg-emerald-50/90 text-emerald-600 shadow-inner shadow-emerald-100">
              <BotIcon className="h-6 w-6" />
            </div>
            <div className="min-w-0 flex-1">
              <CardTitle className="line-clamp-2 text-[1.75rem] leading-tight font-semibold tracking-tight text-slate-950 [overflow-wrap:anywhere]">
                {agent.name}
              </CardTitle>
              {agent.model && (
                <Badge
                  variant="secondary"
                  className="mt-3 max-w-full rounded-full border border-emerald-200/80 bg-emerald-50 px-3 py-1 text-[11px] font-medium text-emerald-700 shadow-none"
                >
                  <span className="truncate">{agent.model}</span>
                </Badge>
              )}
            </div>
            <Button
              size="icon"
              variant="ghost"
              className="text-destructive hover:text-destructive -mr-2 h-9 w-9 shrink-0 rounded-full border border-transparent bg-white/80 opacity-75 shadow-sm transition-all hover:border-red-200 hover:bg-red-50 hover:opacity-100"
              onClick={() => setDeleteOpen(true)}
              title={t.agents.delete}
            >
              <Trash2Icon className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>

        <CardContent className="relative flex flex-1 flex-col px-6 pt-5 pb-6">
          <div className="flex-1 rounded-2xl border border-slate-200/80 bg-white/85 p-4 shadow-[0_10px_24px_-24px_rgba(15,23,42,0.45)] backdrop-blur-sm">
            {agent.description ? (
              <CardDescription className="line-clamp-4 text-[15px] leading-7 text-slate-700">
                {agent.description}
              </CardDescription>
            ) : (
              <CardDescription className="text-[15px] leading-7 text-slate-400">
                {agent.name}
              </CardDescription>
            )}
          </div>

          {visibleToolGroups.length > 0 && (
            <div className="mt-5 flex flex-wrap gap-2">
              {visibleToolGroups.map((group) => (
                <Badge
                  key={group}
                  variant="outline"
                  className="rounded-full border-slate-200 bg-slate-50/90 px-3 py-1 text-xs font-medium text-slate-700"
                >
                  {group}
                </Badge>
              ))}
              {hiddenToolGroupCount > 0 && (
                <Badge
                  variant="outline"
                  className="rounded-full border-slate-200 bg-slate-50/90 px-3 py-1 text-xs font-medium text-slate-500"
                >
                  +{hiddenToolGroupCount}
                </Badge>
              )}
            </div>
          )}
        </CardContent>

        <CardFooter className="relative mt-auto border-t border-slate-100 px-6 pt-5 pb-6">
          <Button
            size="lg"
            className="h-12 w-full rounded-full bg-emerald-500 text-base font-semibold text-white shadow-[0_18px_32px_-20px_rgba(16,185,129,0.85)] transition-all hover:scale-[1.01] hover:bg-emerald-600"
            onClick={handleChat}
          >
            <MessageSquareIcon className="mr-2 h-4 w-4" />
            {t.agents.chat}
          </Button>
        </CardFooter>
      </Card>

      {/* Delete Confirm */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t.agents.delete}</DialogTitle>
            <DialogDescription>{t.agents.deleteConfirm}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteOpen(false)}
              disabled={deleteAgent.isPending}
            >
              {t.common.cancel}
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteAgent.isPending}
            >
              {deleteAgent.isPending ? t.common.loading : t.common.delete}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
