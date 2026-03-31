export {};

declare global {
  interface Window {
    auraDesktop?: {
      selectProjectDirectory: () => Promise<{ path: string; name: string } | null>;
    };
  }
}
