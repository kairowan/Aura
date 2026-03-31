"use client";

import { useCallback, useEffect, useState } from "react";

const THREAD_PROJECT_BINDINGS_KEY = "aura.thread-project-bindings";

type ThreadProjectBindings = Record<string, string>;

function readThreadProjectBindings(): ThreadProjectBindings {
  if (typeof window === "undefined") {
    return {};
  }

  try {
    const raw = window.localStorage.getItem(THREAD_PROJECT_BINDINGS_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw);
    return typeof parsed === "object" && parsed !== null ? parsed : {};
  } catch {
    return {};
  }
}

function writeThreadProjectBindings(bindings: ThreadProjectBindings) {
  window.localStorage.setItem(
    THREAD_PROJECT_BINDINGS_KEY,
    JSON.stringify(bindings),
  );
}

function normalizeProjectRoot(value: string | null | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

export function useThreadProjectBinding(threadId: string) {
  const [projectRoot, setProjectRootState] = useState<string | null>(null);
  const canUseDesktopPicker =
    typeof window !== "undefined" &&
    Boolean(window.auraDesktop?.selectProjectDirectory);

  useEffect(() => {
    const bindings = readThreadProjectBindings();
    setProjectRootState(bindings[threadId] ?? null);
  }, [threadId]);

  const setProjectRoot = useCallback(
    (value: string | null) => {
      const normalized = normalizeProjectRoot(value);
      setProjectRootState(normalized);

      const bindings = readThreadProjectBindings();
      if (normalized) {
        bindings[threadId] = normalized;
      } else {
        delete bindings[threadId];
      }
      writeThreadProjectBindings(bindings);
    },
    [threadId],
  );

  const pickProjectRoot = useCallback(async () => {
    if (window.auraDesktop?.selectProjectDirectory) {
      const selection = await window.auraDesktop.selectProjectDirectory();
      if (selection?.path) {
        setProjectRoot(selection.path);
      }
      return selection?.path ?? null;
    }

    const manualPath = window.prompt(
      "输入要绑定到当前线程的项目绝对路径",
      projectRoot ?? "",
    );
    const normalized = normalizeProjectRoot(manualPath);
    if (manualPath === null) {
      return null;
    }
    setProjectRoot(normalized);
    return normalized;
  }, [projectRoot, setProjectRoot]);

  return {
    projectRoot,
    setProjectRoot,
    clearProjectRoot: () => setProjectRoot(null),
    pickProjectRoot,
    canUseDesktopPicker,
  };
}
