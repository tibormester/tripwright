const state = {
  conversation: null,
  busy: false,
  error: null,
  pendingUserTurn: null,
  loadingTimer: null,
  loadingFrameIndex: 0,
  lastSceneBackgroundUrl: null,
  sceneTransitionTimer: null,
  travelTransitioning: false,
};

const SPEAKER_AVATARS = {
  User: "/ui/user-avatar.svg",
  Narrator: "/ui/narrator-avatar.svg",
};

const LOADING_FRAMES = ["...", "..", ".", ".."];
const SCENE_COMPLETE_PREFIX = "Scene complete. Choose where to go next";

const elements = {
  sceneStage: document.getElementById("scene-stage"),
  chatLog: document.getElementById("chat-log"),
  composer: document.getElementById("composer"),
  userInput: document.getElementById("user-input"),
  sendButton: document.getElementById("send-button"),
  restartButton: document.getElementById("restart-button"),
  statusText: document.getElementById("status-text"),
  statusDot: document.getElementById("status-dot"),
  sceneLabel: document.getElementById("scene-label"),
  sceneLocation: document.getElementById("scene-location"),
  npcName: document.getElementById("npc-name"),
  npcRole: document.getElementById("npc-role"),
  travelPanel: document.getElementById("travel-panel"),
  travelOptions: document.getElementById("travel-options"),
  messageTemplate: document.getElementById("message-template"),
  sceneFadeOverlay: document.getElementById("scene-fade-overlay"),
};

async function apiRequest(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message = payload && typeof payload === "object" && payload.error
      ? payload.error
      : `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return payload;
}

async function initializeConversation() {
  stopLoadingIndicator();
  state.pendingUserTurn = null;
  state.travelTransitioning = false;
  hideSceneFadeOverlay();
  setBusy(true, "Starting conversation…");

  try {
    state.conversation = await apiRequest("POST", "/conversation/initialize", {});
    state.error = null;
    setBusy(false, "Connected");
    render();
  } catch (error) {
    handleError(error);
  }
}

async function sendTurn(userInput, options = {}) {
  const cleanedInput = userInput.trim();
  if (!state.conversation || !cleanedInput) {
    return;
  }

  const { silent = false, useSceneFade = false } = options;

  state.pendingUserTurn = silent ? null : cleanedInput;
  state.travelTransitioning = useSceneFade;

  if (!silent) {
    startLoadingIndicator();
  }

  if (useSceneFade) {
    showSceneFadeOverlay();
  }

  setBusy(true, "Waiting for response…");
  render();

  try {
    const previousHistoryLength = Array.isArray(state.conversation?.conversation_history)
      ? state.conversation.conversation_history.length
      : 0;

    state.conversation = await apiRequest("POST", "/conversation/turn", {
      state: state.conversation,
      user_input: cleanedInput,
    });
    state.error = null;
    markIncomingTurns(previousHistoryLength);
    state.pendingUserTurn = null;
    stopLoadingIndicator();
    setBusy(false, "Connected");
    render();

    if (useSceneFade) {
      window.setTimeout(() => {
        hideSceneFadeOverlay();
        state.travelTransitioning = false;
        updateComposerState();
      }, 140);
    } else {
      state.travelTransitioning = false;
    }
  } catch (error) {
    state.pendingUserTurn = null;
    stopLoadingIndicator();
    state.travelTransitioning = false;
    hideSceneFadeOverlay();
    handleError(error);
    render();
  }
}

function setBusy(busy, statusText) {
  state.busy = busy;
  elements.restartButton.disabled = busy;
  elements.statusText.textContent = statusText;
  elements.statusDot.classList.remove("ready", "error");

  if (!busy && !state.error) {
    elements.statusDot.classList.add("ready");
  }

  updateComposerState();
}

function handleError(error) {
  state.busy = false;
  state.error = error instanceof Error ? error.message : String(error);
  elements.restartButton.disabled = false;
  elements.statusText.textContent = state.error;
  elements.statusDot.classList.remove("ready");
  elements.statusDot.classList.add("error");
  updateComposerState();
}

function render() {
  renderScene();
  renderConversation();
  renderTravelOptions();
  updateComposerState();
}

function renderScene() {
  const rendering = state.conversation?.rendering || {};
  const scene = rendering.scene || {};
  const npc = rendering.npc || {};
  const background = scene.background || {};
  const backgroundUrl = background.url || null;

  elements.sceneLabel.textContent = scene.label || "Unknown Scene";
  elements.sceneLocation.textContent = scene.location || "";
  elements.npcName.textContent = npc.name || "Unknown NPC";
  elements.npcRole.textContent = npc.role || "";

  if (state.lastSceneBackgroundUrl !== null && state.lastSceneBackgroundUrl !== backgroundUrl) {
    triggerSceneTransition();
  }
  state.lastSceneBackgroundUrl = backgroundUrl;

  elements.sceneStage.style.backgroundImage = backgroundUrl
    ? `linear-gradient(rgba(66, 48, 29, 0.42), rgba(37, 25, 13, 0.62)), url('${backgroundUrl}')`
    : "linear-gradient(rgba(66, 48, 29, 0.42), rgba(37, 25, 13, 0.62)), linear-gradient(180deg, #7d6449 0%, #4f3b29 100%)";
}

function renderConversation() {
  const history = getDisplayHistory();
  const npcName = state.conversation?.npc_profile?.name;
  const npcHeadshotUrl = state.conversation?.rendering?.npc?.headshot?.url || null;

  elements.chatLog.innerHTML = "";

  if (!history.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "No conversation yet.";
    elements.chatLog.appendChild(empty);
    return;
  }

  for (const turn of history) {
    const fragment = elements.messageTemplate.content.cloneNode(true);
    const message = fragment.querySelector(".message");
    const meta = fragment.querySelector(".message-meta");
    const body = fragment.querySelector(".message-body");
    const avatar = fragment.querySelector(".message-avatar");
    const avatarImage = fragment.querySelector(".message-avatar-image");
    const avatarFallback = fragment.querySelector(".message-avatar-fallback");
    const speaker = turn?.speaker || "Unknown";
    const kind = classifySpeaker(speaker, npcName);
    const avatarUrl = getSpeakerAvatarUrl({ speaker, kind, npcHeadshotUrl });

    message.classList.add(kind);
    meta.textContent = speaker;
    body.textContent = turn?.dialogue || "";

    if (turn?.pending) {
      message.classList.add("pending");
    }

    if (turn?.incoming) {
      message.classList.add("incoming");
    }

    if (avatarUrl) {
      message.classList.add("has-avatar");
      avatar.hidden = false;
      avatarImage.src = avatarUrl;
      avatarImage.hidden = false;
      avatarFallback.hidden = true;
    } else if (kind === "npc") {
      message.classList.add("has-avatar");
      avatar.hidden = false;
      avatarFallback.textContent = (speaker || "?").charAt(0).toUpperCase();
      avatarFallback.hidden = false;
      avatarImage.hidden = true;
    }

    elements.chatLog.appendChild(fragment);
  }

  smoothScrollChatToBottom();
}

function renderTravelOptions() {
  const rendering = state.conversation?.rendering || {};
  const options = Array.isArray(rendering.travel_options) ? rendering.travel_options : [];
  const isVisible = Boolean(rendering.travel_selection && options.length);

  elements.travelPanel.hidden = !isVisible;
  elements.travelOptions.innerHTML = "";

  if (!isVisible) {
    return;
  }

  for (const [index, option] of options.entries()) {
    const card = document.createElement("article");
    card.className = "travel-option travel-option-enter";
    card.style.animationDelay = `${index * 90}ms`;

    const thumb = document.createElement("div");
    thumb.className = "travel-thumb";
    if (option?.background?.url) {
      thumb.style.backgroundImage = `linear-gradient(rgba(75, 52, 28, 0.14), rgba(39, 26, 14, 0.24)), url('${option.background.url}')`;
    }

    const copy = document.createElement("div");
    copy.className = "travel-option-copy";

    const title = document.createElement("h3");
    title.textContent = option.label || "Unknown destination";

    const description = document.createElement("p");
    description.textContent = option.description || "";

    const button = document.createElement("button");
    button.type = "button";
    button.className = "travel-command";
    button.textContent = "Travel here";
    button.disabled = state.busy;
    button.addEventListener("click", () => sendTurn(option.command || "", { silent: true, useSceneFade: true }));

    copy.append(title, description);
    card.append(thumb, copy, button);
    elements.travelOptions.appendChild(card);
  }
}

function updateComposerState() {
  const travelSelection = Boolean(state.conversation?.rendering?.travel_selection);
  const hidden = travelSelection || state.travelTransitioning;
  const disabled = state.busy || travelSelection || state.travelTransitioning;

  elements.composer.hidden = hidden;
  elements.userInput.disabled = disabled;
  elements.sendButton.disabled = disabled;
  elements.userInput.placeholder = travelSelection
    ? "Choose a destination below to continue."
    : "Talk to the character...";
}

function getDisplayHistory() {
  const rawHistory = Array.isArray(state.conversation?.conversation_history)
    ? state.conversation.conversation_history
    : [];
  const history = rawHistory.filter((turn) => !shouldHideTurn(turn));
  const npcName = state.conversation?.npc_profile?.name || "NPC";

  if (state.pendingUserTurn) {
    history.push({ speaker: "User", dialogue: state.pendingUserTurn, pending: true });
    history.push({ speaker: npcName, dialogue: LOADING_FRAMES[state.loadingFrameIndex], pending: true });
  }

  return history;
}

function shouldHideTurn(turn) {
  return turn?.speaker === "System"
    && typeof turn?.dialogue === "string"
    && turn.dialogue.startsWith(SCENE_COMPLETE_PREFIX);
}

function markIncomingTurns(previousHistoryLength) {
  const history = Array.isArray(state.conversation?.conversation_history)
    ? state.conversation.conversation_history
    : [];

  for (let index = 0; index < history.length; index += 1) {
    const turn = history[index];
    if (!turn || typeof turn !== "object") {
      continue;
    }

    if (index >= previousHistoryLength && !shouldHideTurn(turn) && turn.speaker !== "User") {
      turn.incoming = true;
      window.setTimeout(() => {
        if (turn && turn.incoming) {
          delete turn.incoming;
          renderConversation();
        }
      }, 900);
    } else {
      delete turn.incoming;
    }
  }
}

function classifySpeaker(speaker, npcName) {
  if (speaker === "User") return "user";
  if (speaker === "Narrator") return "narrator";
  if (speaker === "System") return "system";
  if (speaker === npcName) return "npc";
  return "npc";
}

function getSpeakerAvatarUrl({ speaker, kind, npcHeadshotUrl }) {
  if (kind === "npc") {
    return npcHeadshotUrl || null;
  }

  return SPEAKER_AVATARS[speaker] || null;
}

function smoothScrollChatToBottom() {
  elements.chatLog.scrollTo({
    top: elements.chatLog.scrollHeight,
    behavior: "smooth",
  });
}

function triggerSceneTransition() {
  elements.sceneStage.classList.remove("scene-transition");
  void elements.sceneStage.offsetWidth;
  elements.sceneStage.classList.add("scene-transition");

  if (state.sceneTransitionTimer !== null) {
    window.clearTimeout(state.sceneTransitionTimer);
  }

  state.sceneTransitionTimer = window.setTimeout(() => {
    elements.sceneStage.classList.remove("scene-transition");
    state.sceneTransitionTimer = null;
  }, 520);
}

function showSceneFadeOverlay() {
  elements.sceneFadeOverlay.classList.add("active");
}

function hideSceneFadeOverlay() {
  elements.sceneFadeOverlay.classList.remove("active");
}

function startLoadingIndicator() {
  stopLoadingIndicator();
  state.loadingFrameIndex = 0;
  state.loadingTimer = window.setInterval(() => {
    state.loadingFrameIndex = (state.loadingFrameIndex + 1) % LOADING_FRAMES.length;
    renderConversation();
  }, 350);
}

function stopLoadingIndicator() {
  if (state.loadingTimer !== null) {
    window.clearInterval(state.loadingTimer);
    state.loadingTimer = null;
  }
  state.loadingFrameIndex = 0;
}

elements.composer.addEventListener("submit", async (event) => {
  event.preventDefault();
  const value = elements.userInput.value.trim();
  if (!value || state.busy) {
    return;
  }

  elements.userInput.value = "";
  await sendTurn(value);
  if (!elements.composer.hidden) {
    elements.userInput.focus();
  }
});

elements.userInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.composer.requestSubmit();
  }
});

elements.restartButton.addEventListener("click", () => {
  if (!state.busy) {
    initializeConversation();
  }
});

initializeConversation();
