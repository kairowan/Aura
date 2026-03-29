import {
  CompassIcon,
  GraduationCapIcon,
  ImageIcon,
  MicroscopeIcon,
  PenLineIcon,
  ShapesIcon,
  SparklesIcon,
  VideoIcon,
} from "lucide-react";

import type { Translations } from "./types";

export const enUS: Translations = {
  // Locale meta
  locale: {
    localName: "English",
  },

  // Common
  common: {
    home: "Home",
    settings: "Settings",
    delete: "Delete",
    rename: "Rename",
    share: "Share",
    openInNewWindow: "Open in new window",
    close: "Close",
    more: "More",
    search: "Search",
    download: "Download",
    thinking: "Thinking",
    artifacts: "Artifacts",
    public: "Public",
    custom: "Custom",
    notAvailableInDemoMode: "Not available in demo mode",
    loading: "Loading...",
    version: "Version",
    lastUpdated: "Last updated",
    code: "Code",
    preview: "Preview",
    cancel: "Cancel",
    save: "Save",
    install: "Install",
    create: "Create",
    export: "Export",
    exportAsMarkdown: "Export as Markdown",
    exportAsJSON: "Export as JSON",
    exportSuccess: "Conversation exported",
  },

  // Welcome
  welcome: {
    greeting: "Hello, again!",
    description:
      "Welcome to 💠 Aura, an open source super agent. With built-in and custom skills, Aura helps you search on the web, analyze data, and generate artifacts like slides, web pages and do almost anything.",

    createYourOwnSkill: "Create Your Own Skill",
    createYourOwnSkillDescription:
      "Create your own skill to release the power of Aura. With customized skills,\nAura can help you search on the web, analyze data, and generate\n artifacts like slides, web pages and do almost anything.",
  },

  // Clipboard
  clipboard: {
    copyToClipboard: "Copy to clipboard",
    copiedToClipboard: "Copied to clipboard",
    failedToCopyToClipboard: "Failed to copy to clipboard",
    linkCopied: "Link copied to clipboard",
  },

  // Input Box
  inputBox: {
    placeholder: "How can I assist you today?",
    createSkillPrompt:
      "We're going to build a new skill step by step with `skill-creator`. To start, what do you want this skill to do?",
    addAttachments: "Add attachments",
    mode: "Mode",
    flashMode: "Flash",
    flashModeDescription: "Fast and efficient, but may not be accurate",
    reasoningMode: "Reasoning",
    reasoningModeDescription:
      "Reasoning before action, balance between time and accuracy",
    proMode: "Pro",
    proModeDescription:
      "Reasoning, planning and executing, get more accurate results, may take more time",
    ultraMode: "Ultra",
    ultraModeDescription:
      "Pro mode with subagents to divide work; best for complex multi-step tasks",
    reasoningEffort: "Reasoning Effort",
    reasoningEffortMinimal: "Minimal",
    reasoningEffortMinimalDescription: "Retrieval + Direct Output",
    reasoningEffortLow: "Low",
    reasoningEffortLowDescription: "Simple Logic Check + Shallow Deduction",
    reasoningEffortMedium: "Medium",
    reasoningEffortMediumDescription:
      "Multi-layer Logic Analysis + Basic Verification",
    reasoningEffortHigh: "High",
    reasoningEffortHighDescription:
      "Full-dimensional Logic Deduction + Multi-path Verification + Backward Check",
    searchModels: "Search models...",
    surpriseMe: "Surprise",
    surpriseMePrompt: "Surprise me",
    followupLoading: "Generating follow-up questions...",
    followupConfirmTitle: "Send suggestion?",
    followupConfirmDescription:
      "You already have text in the input. Choose how to send it.",
    followupConfirmAppend: "Append & send",
    followupConfirmReplace: "Replace & send",
    suggestions: [
      {
        suggestion: "Write",
        prompt: "Write a blog post about the latest trends on [topic]",
        icon: PenLineIcon,
      },
      {
        suggestion: "Research",
        prompt:
          "Conduct a deep dive research on [topic], and summarize the findings.",
        icon: MicroscopeIcon,
      },
      {
        suggestion: "Collect",
        prompt: "Collect data from [source] and create a report.",
        icon: ShapesIcon,
      },
      {
        suggestion: "Learn",
        prompt: "Learn about [topic] and create a tutorial.",
        icon: GraduationCapIcon,
      },
    ],
    suggestionsCreate: [
      {
        suggestion: "Webpage",
        prompt: "Create a webpage about [topic]",
        icon: CompassIcon,
      },
      {
        suggestion: "Image",
        prompt: "Create an image about [topic]",
        icon: ImageIcon,
      },
      {
        suggestion: "Video",
        prompt: "Create a video about [topic]",
        icon: VideoIcon,
      },
      {
        type: "separator",
      },
      {
        suggestion: "Skill",
        prompt:
          "We're going to build a new skill step by step with `skill-creator`. To start, what do you want this skill to do?",
        icon: SparklesIcon,
      },
    ],
  },

  // Sidebar
  sidebar: {
    newChat: "New chat",
    chats: "Chats",
    recentChats: "Recent chats",
    demoChats: "Demo chats",
    agents: "Agents",
  },

  // Agents
  agents: {
    title: "Agents",
    description:
      "Create and manage custom agents with specialized prompts and capabilities.",
    newAgent: "New Agent",
    searchPlaceholder: "Search by agent name, description, model, or tool",
    searchEmptyTitle: "No matching agents",
    searchEmptyDescription: "Try a shorter keyword or adjust the spelling.",
    emptyTitle: "No custom agents yet",
    emptyDescription:
      "Create your first custom agent with a specialized system prompt.",
    chat: "Chat",
    delete: "Delete",
    deleteConfirm:
      "Are you sure you want to delete this agent? This action cannot be undone.",
    deleteSuccess: "Agent deleted",
    newChat: "New chat",
    createPageTitle: "Design your Agent",
    createPageSubtitle:
      "Describe the agent you want — I'll help you create it through conversation.",
    nameStepTitle: "Name your new Agent",
    nameStepHint:
      "Letters, digits, and hyphens only — stored lowercase (e.g. code-reviewer)",
    nameStepPlaceholder: "e.g. code-reviewer",
    nameStepContinue: "Continue",
    nameStepInvalidError:
      "Invalid name — use only letters, digits, and hyphens",
    nameStepAlreadyExistsError: "An agent with this name already exists",
    nameStepCheckError: "Could not verify name availability — please try again",
    nameStepBootstrapMessage:
      "The new custom agent name is {name}. Let's bootstrap it's **SOUL**.",
    agentCreated: "Agent created!",
    startChatting: "Start chatting",
    backToGallery: "Back to Gallery",
  },

  // Breadcrumb
  breadcrumb: {
    workspace: "Workspace",
    chats: "Chats",
  },

  // Workspace
  workspace: {
    officialWebsite: "Aura's official website",
    githubTooltip: "Aura on Github",
    settingsAndMore: "Settings and more",
    visitGithub: "Aura on GitHub",
    reportIssue: "Report a issue",
    contactUs: "Contact us",
    about: "About Aura",
  },

  // Conversation
  conversation: {
    noMessages: "No messages yet",
    startConversation: "Start a conversation to see messages here",
  },

  // Chats
  chats: {
    searchChats: "Search chats",
  },

  // Page titles (document title)
  pages: {
    appName: "Aura",
    chats: "Chats",
    newChat: "New chat",
    untitled: "Untitled",
  },

  // Tool calls
  toolCalls: {
    moreSteps: (count: number) => `${count} more step${count === 1 ? "" : "s"}`,
    lessSteps: "Less steps",
    executeCommand: "Execute command",
    presentFiles: "Present files",
    needYourHelp: "Need your help",
    useTool: (toolName: string) => `Use "${toolName}" tool`,
    searchFor: (query: string) => `Search for "${query}"`,
    searchForRelatedInfo: "Search for related information",
    searchForRelatedImages: "Search for related images",
    searchForRelatedImagesFor: (query: string) =>
      `Search for related images for "${query}"`,
    searchOnWebFor: (query: string) => `Search on the web for "${query}"`,
    viewWebPage: "View web page",
    listFolder: "List folder",
    readFile: "Read file",
    writeFile: "Write file",
    clickToViewContent: "Click to view file content",
    writeTodos: "Update to-do list",
    skillInstallTooltip: "Install skill and make it available to Aura",
  },

  // Subtasks
  uploads: {
    uploading: "Uploading...",
    uploadingFiles: "Uploading files, please wait...",
  },

  subtasks: {
    subtask: "Subtask",
    executing: (count: number) =>
      `Executing ${count === 1 ? "" : count + " "}subtask${count === 1 ? "" : "s in parallel"}`,
    in_progress: "Running subtask",
    completed: "Subtask completed",
    failed: "Subtask failed",
  },

  // Token Usage
  tokenUsage: {
    title: "Token Usage",
    input: "Input",
    output: "Output",
    total: "Total",
  },
  
  // Shortcuts
  shortcuts: {
    searchActions: "Search actions...",
    noResults: "No results found.",
    actions: "Actions",
    keyboardShortcuts: "Keyboard Shortcuts",
    keyboardShortcutsDescription: "Navigate Aura faster with keyboard shortcuts.",
    openCommandPalette: "Open Command Palette",
    toggleSidebar: "Toggle Sidebar",
  },

  // Settings
  settings: {
    title: "Settings",
    description: "Adjust how Aura looks and behaves for you.",
    sections: {
      appearance: "Appearance",
      memory: "Memory",
      tools: "Tools",
      skills: "Skills",
      notification: "Notification",
      about: "About",
      aiProvider: "AI Provider",
      channels: "Channels",
      automation: "Automation",
    },
    memory: {
      title: "Memory",
      description:
        "Aura automatically learns from your conversations in the background. These memories help Aura understand you better and deliver a more personalized experience.",
      empty: "No memory data to display.",
      rawJson: "Raw JSON",
      markdown: {
        overview: "Overview",
        userContext: "User context",
        work: "Work",
        personal: "Personal",
        topOfMind: "Top of mind",
        historyBackground: "History",
        recentMonths: "Recent months",
        earlierContext: "Earlier context",
        longTermBackground: "Long-term background",
        updatedAt: "Updated at",
        facts: "Facts",
        empty: "(empty)",
        table: {
          category: "Category",
          confidence: "Confidence",
          confidenceLevel: {
            veryHigh: "Very high",
            high: "High",
            normal: "Normal",
            unknown: "Unknown",
          },
          content: "Content",
          source: "Source",
          createdAt: "CreatedAt",
          view: "View",
        },
      },
    },
    appearance: {
      themeTitle: "Theme",
      themeDescription:
        "Choose how the interface follows your device or stays fixed.",
      system: "System",
      light: "Light",
      dark: "Dark",
      systemDescription: "Match the operating system preference automatically.",
      lightDescription: "Bright palette with higher contrast for daytime.",
      darkDescription: "Dim palette that reduces glare for focus.",
      languageTitle: "Language",
      languageDescription: "Switch between languages.",
    },
    tools: {
      title: "Tools",
      description: "Manage the configuration and enabled status of MCP tools.",
      searchPlaceholder: "Search tool name or description",
      emptySearch: "No matching tools.",
    },
    skills: {
      title: "Agent Skills",
      description:
        "Manage the configuration and enabled status of the agent skills.",
      createSkill: "Create skill",
      searchPlaceholder: "Search skill name or description",
      emptySearch: "No matching skills.",
      emptyTitle: "No agent skill yet",
      emptyDescription:
        "Put your agent skill folders under the `/skills/custom` folder under the root folder of Aura.",
      emptyButton: "Create Your First Skill",
    },
    notification: {
      title: "Notification",
      description:
        "Aura only sends a completion notification when the window is not active. This is especially useful for long-running tasks so you can switch to other work and get notified when done.",
      requestPermission: "Request notification permission",
      deniedHint:
        "Notification permission was denied. You can enable it in your browser's site settings to receive completion alerts.",
      testButton: "Send test notification",
      testTitle: "Aura",
      testBody: "This is a test notification.",
      notSupported: "Your browser does not support notifications.",
      disableNotification: "Disable notification",
    },
    channels: {
      title: "Channels",
      description:
        "Connect Aura to Feishu, Slack, or Telegram. Saving here hot-reloads the channel service without restarting the desktop app.",
      loadError: "Failed to load channel settings.",
      saveSuccess: "Channel settings saved.",
      saveError: "Failed to save channel settings.",
      restartSuccess: "{name} channel restarted.",
      restartError: "Failed to restart the channel. Check the credentials and service logs.",
      serviceStatusLabel: "Channel Service Status",
      serviceStatusDescription: "Shows whether the IM channel service is online and whether each configured channel is actually running.",
      serviceRunning: "Service running",
      serviceStopped: "Service stopped",
      defaultAssistantLabel: "Default Assistant ID",
      defaultAssistantPlaceholder: "e.g. lead_agent",
      assistantLabel: "Channel Assistant ID",
      assistantPlaceholder: "Leave empty to inherit the default assistant",
      allowedUsersLabel: "Allowed User IDs",
      allowedUsersPlaceholder: "Comma-separated user IDs. Leave empty to allow all users.",
      running: "Running",
      notRunning: "Not running",
      disabled: "Disabled",
      restartButton: "Restart channel",
      providers: {
        feishu: {
          title: "Feishu / Lark",
          description: "Connect Aura to Feishu via long-lived connection for internal team collaboration.",
          appIdLabel: "App ID",
          appIdPlaceholder: "Enter the Feishu app ID",
          appSecretLabel: "App Secret",
          appSecretPlaceholder: "Enter the Feishu app secret",
        },
        slack: {
          title: "Slack",
          description: "Use Slack Socket Mode so Aura can respond inside channels and threads.",
          botTokenLabel: "Bot Token",
          botTokenPlaceholder: "e.g. xoxb-...",
          appTokenLabel: "App Token",
          appTokenPlaceholder: "e.g. xapp-...",
        },
        telegram: {
          title: "Telegram",
          description: "Use a Telegram bot with long polling for personal assistant or group scenarios.",
          botTokenLabel: "Bot Token",
          botTokenPlaceholder: "Enter the Telegram bot token",
        },
      },
    },
    automation: {
      title: "Automation",
      description:
        "Create scheduled Aura jobs that run prompts automatically and optionally push results to connected channels.",
      loadError: "Failed to load automation jobs.",
      validationError: "Both the job name and prompt are required.",
      createTitle: "Create automation",
      createDescription: "Define what Aura should do, how often it should run, and where the result should be delivered.",
      nameLabel: "Job name",
      namePlaceholder: "e.g. Daily product signal summary",
      promptLabel: "Prompt",
      promptPlaceholder: "Describe the work Aura should perform on each run.",
      assistantLabel: "Assistant ID",
      assistantPlaceholder: "Defaults to lead_agent",
      scheduleTypeLabel: "Schedule type",
      scheduleInterval: "Interval",
      scheduleDaily: "Daily",
      intervalLabel: "Interval in minutes",
      dailyTimeLabel: "Daily run time",
      deliveryChannelLabel: "Delivery channel",
      deliveryChatIdLabel: "Target chat ID",
      deliveryChatIdPlaceholder: "e.g. a Feishu chat id or Telegram chat_id",
      deliveryNone: "Store the result inside Aura only",
      enabledLabel: "Enable immediately",
      enabledDescription: "Disabled jobs stay saved but will not auto-run until re-enabled.",
      createButton: "Create job",
      createSuccess: "Automation job created.",
      createError: "Failed to create automation job.",
      updateError: "Failed to update automation job.",
      runNowButton: "Run now",
      runSuccess: "Automation job started.",
      runError: "Failed to run automation job.",
      deleteSuccess: "Automation job deleted.",
      deleteError: "Failed to delete automation job.",
      enableSuccess: "Automation job enabled.",
      disableSuccess: "Automation job disabled.",
      listTitle: "Existing jobs",
      empty: "No automation jobs yet.",
      scheduleLabel: "Schedule",
      nextRunLabel: "Next run",
      lastRunLabel: "Last run",
      deliveryLabel: "Delivery",
      lastErrorLabel: "Latest error",
      lastOutputLabel: "Latest output",
      notScheduled: "Not scheduled",
      intervalSummary: "Every {minutes} minute(s)",
      dailySummary: "Daily at {time}",
      statusIdle: "Idle",
      statusRunning: "Running",
      statusSuccess: "Success",
      statusError: "Error",
      disabled: "Disabled",
    },
    provider: {
      title: "AI Provider",
      description: "Configure a custom AI provider (e.g., OpenAI, Deepseek, Claude) for Aura's core capabilities.",
      baseUrlLabel: "API Base URL",
      baseUrlPlaceholder: "e.g., https://api.openai.com/v1",
      apiKeyLabel: "API Key",
      apiKeyPlaceholder: "Enter your API key",
      modelIdLabel: "Model ID",
      modelIdPlaceholder: "e.g., gpt-4o, deepseek-chat",
      displayNameLabel: "Display Name",
      displayNamePlaceholder: "e.g., My Custom AI",
      validateButton: "Test Connection",
      validateSuccess: "AI provider connection succeeded.",
      validateError: "AI provider connection failed. Check the base URL, API key, and model ID.",
      saveSuccess: "AI Provider configuration saved and the model list was refreshed.",
      saveError: "Failed to save configuration. Please check the backend status.",
    },
    acknowledge: {
      emptyTitle: "Acknowledgements",
      emptyDescription: "Credits and acknowledgements will show here.",
    },
  },
};
