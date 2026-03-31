"use client";

import { FolderOpen, PencilLine, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function getProjectLabel(projectRoot: string | null): string {
  if (!projectRoot) {
    return "未绑定项目";
  }
  const segments = projectRoot.split(/[\\/]/).filter(Boolean);
  return segments.at(-1) ?? projectRoot;
}

export function ProjectBindingChip({
  projectRoot,
  canUseDesktopPicker,
  onPickProject,
  onClearProject,
  className,
}: {
  projectRoot: string | null;
  canUseDesktopPicker: boolean;
  onPickProject: () => Promise<string | null>;
  onClearProject: () => void;
  className?: string;
}) {
  const projectLabel = getProjectLabel(projectRoot);

  const handlePickProject = async () => {
    try {
      const selected = await onPickProject();
      if (selected) {
        toast.success("已绑定当前线程项目目录");
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "无法绑定当前项目目录";
      toast.error(message);
    }
  };

  const handleClearProject = () => {
    onClearProject();
    toast.success("已取消当前线程项目绑定");
  };

  return (
    <div
      className={cn(
        "bg-background/75 border-border/60 flex min-w-0 items-center gap-2 rounded-full border px-2 py-1 shadow-xs backdrop-blur",
        className,
      )}
    >
      <FolderOpen className="text-muted-foreground size-4 shrink-0" />
      <div className="min-w-0">
        <div className="max-w-44 truncate text-xs font-medium">
          {projectLabel}
        </div>
        <div className="text-muted-foreground max-w-52 truncate text-[11px]">
          {projectRoot ?? "绑定后代理可通过 /mnt/project 访问目录"}
        </div>
      </div>
      <Button
        type="button"
        size="sm"
        variant="ghost"
        className="h-7 rounded-full px-2 text-xs"
        onClick={handlePickProject}
      >
        <PencilLine className="size-3.5" />
        {projectRoot ? "更换" : canUseDesktopPicker ? "选择" : "输入"}
      </Button>
      {projectRoot && (
        <Button
          type="button"
          size="icon-sm"
          variant="ghost"
          className="rounded-full"
          onClick={handleClearProject}
          aria-label="清除项目绑定"
        >
          <X className="size-3.5" />
        </Button>
      )}
    </div>
  );
}
