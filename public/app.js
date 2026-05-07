const state = {
  conversation: null,
  world: null,
  worldId: null,
  busy: false,
  error: null,
  pendingUserTurn: null,
  loadingTimer: null,
  loadingFrameIndex: 0,
  lastSceneBackgroundUrl: null,
  sceneTransitionTimer: null,
  travelTransitioning: false,
  startupVisible: true,
  lastLodgingInput: "",
  worldLoadingVisible: false,
  loadedTravelOptions: [],
  travelOptionsProgress: null,
  travelOptionsPolling: false,
};

const SPEAKER_AVATARS = {
  User: "/ui/user-avatar.svg",
  Narrator: "/ui/narrator-avatar.svg",
};

const LOADING_FRAMES = ["...", "..", ".", ".."];
const SCENE_COMPLETE_PREFIX = "Scene complete. Choose where to go next";

const elements = {
  sceneStage: document.getElementById("scene-stage"),
  chatPanel: document.getElementById("chat-panel"),
  chatLog: document.getElementById("chat-log"),
  composer: document.getElementById("composer"),
  userInput: document.getElementById("user-input"),
  sendButton: document.getElementById("send-button"),
  restartButton: document.getElementById("restart-button"),
  statusText: document.getElementById("status-text"),
  statusDot: document.getElementById("status-dot"),
  sceneLabel: document.getElementById("scene-label"),
  sceneLocation: document.getElementById("scene-location"),
  sceneDescription: document.getElementById("scene-description"),
  npcName: document.getElementById("npc-name"),
  npcRole: document.getElementById("npc-role"),
  travelPanel: document.getElementById("travel-panel"),
  travelOptions: document.getElementById("travel-options"),
  travelIntro: document.getElementById("travel-intro"),
  travelProgress: document.getElementById("travel-progress"),
  messageTemplate: document.getElementById("message-template"),
  sceneFadeOverlay: document.getElementById("scene-fade-overlay"),
  startupPanel: document.getElementById("startup-panel"),
  startupForm: document.getElementById("startup-form"),
  startupInput: document.getElementById("lodging-input"),
  startupButton: document.getElementById("startup-button"),
  worldLoadingModal: document.getElementById("world-loading-modal"),
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

async function initializeWorld(lodgingInput) {
  const cleanedInput = lodgingInput.trim();
  if (!cleanedInput) {
    handleError(new Error("Please enter a Booking.com URL or lodging query."));
    render();
    return;
  }

  stopLoadingIndicator();
  state.pendingUserTurn = null;
  state.travelTransitioning = false;
  state.lastLodgingInput = cleanedInput;
  state.worldLoadingVisible = true;
  hideSceneFadeOverlay();
  setBusy(true, "Preparing your trip…");
  render();

  try {
    const payload = await apiRequest("POST", "/world/initialize", {
      lodging_input: cleanedInput,
    });
    state.conversation = payload.conversation || null;
    state.world = payload.world || null;
    state.worldId = payload.world_id || null;
    state.startupVisible = false;
    state.worldLoadingVisible = false;
    state.error = null;
    syncTravelOptionStateFromConversation();
    setBusy(false, payload.cache_hit ? "Ready" : "Ready");
    render();
    if (!elements.composer.hidden) {
      elements.userInput.focus();
    }
  } catch (error) {
    state.worldLoadingVisible = false;
    handleError(error);
    render();
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

  setBusy(true, "Thinking…");
  render();

  try {
    const previousHistoryLength = Array.isArray(state.conversation?.conversation_history)
      ? state.conversation.conversation_history.length
      : 0;

    state.conversation = await apiRequest("POST", "/conversation/turn", {
      state: buildConversationStateForRequest(state.conversation),
      world_id: state.worldId,
      user_input: cleanedInput,
    });
    state.error = null;
    syncTravelOptionStateFromConversation();
    markIncomingTurns(previousHistoryLength);
    state.pendingUserTurn = null;
    stopLoadingIndicator();
    setBusy(false, "Ready");
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
  elements.startupButton.disabled = busy;
  elements.startupInput.disabled = busy;
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
  elements.startupButton.disabled = false;
  elements.startupInput.disabled = false;
  elements.statusText.textContent = state.error;
  elements.statusDot.classList.remove("ready");
  elements.statusDot.classList.add("error");
  updateComposerState();
}

function render() {
  renderScene();
  renderStartup();
  renderWorldLoadingModal();
  renderConversation();
  renderTravelOptions();
  updateComposerState();
}

function renderStartup() {
  elements.startupPanel.hidden = !state.startupVisible;
  elements.chatPanel.hidden = state.startupVisible;
  if (state.startupVisible && elements.startupInput.value !== state.lastLodgingInput) {
    elements.startupInput.value = state.lastLodgingInput;
  }
}

function renderWorldLoadingModal() {
  elements.worldLoadingModal.hidden = !state.worldLoadingVisible;
}

function renderScene() {
  const rendering = state.conversation?.rendering || {};
  const scene = rendering.scene || {};
  const npc = rendering.npc || {};
  const background = scene.background || {};
  const backgroundUrl = resolveAssetUrl(background);

  elements.sceneLabel.textContent = scene.label || (state.startupVisible ? "TripWright" : "Current Scene");
  elements.sceneLocation.textContent = scene.location || (state.startupVisible
    ? "Give TripWright a lodging and it will build a tailored arrival scene."
    : "");
  elements.sceneDescription.textContent = scene.description || (state.startupVisible
    ? "You will get a custom opening scene, a local host character, and three nearby places to visit."
    : "");
  elements.npcName.textContent = npc.name || "—";
  elements.npcRole.textContent = npc.role || "—";

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
  const npcHeadshot = state.conversation?.rendering?.npc?.headshot || null;
  const npcHeadshotUrl = resolveAssetUrl(npcHeadshot);

  elements.chatLog.innerHTML = "";

  if (state.startupVisible) {
    return;
  }

  if (!history.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "Your conversation will appear here once the scene begins.";
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
      avatarImage.dataset.fallbackUrl = resolveFallbackAssetUrl(npcHeadshot) || "";
      avatarImage.onerror = () => {
        const fallbackUrl = avatarImage.dataset.fallbackUrl;
        if (fallbackUrl && avatarImage.src !== new URL(fallbackUrl, window.location.origin).href) {
          avatarImage.src = fallbackUrl;
          return;
        }
        avatarImage.hidden = true;
        avatarFallback.textContent = (speaker || "?").charAt(0).toUpperCase();
        avatarFallback.hidden = false;
      };
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
  const loading = Boolean(rendering.travel_options_loading);
  const progress = state.travelOptionsProgress || rendering.travel_options_progress || null;
  const options = state.loadedTravelOptions.length
    ? state.loadedTravelOptions
    : (Array.isArray(rendering.travel_options) ? rendering.travel_options : []);
  const isVisible = !state.startupVisible && Boolean(rendering.travel_selection && (loading || options.length));

  elements.travelPanel.hidden = !isVisible;
  elements.travelOptions.innerHTML = "";

  if (!isVisible) {
    return;
  }

  if (loading) {
    elements.travelIntro.textContent = "Your next destinations are loading. The latest reply is ready — hang tight for the options.";
    if (progress) {
      elements.travelProgress.hidden = false;
      elements.travelProgress.textContent = `Loading destination art ${progress.loaded || 0}/${progress.total || 0}...`;
    } else {
      elements.travelProgress.hidden = false;
      elements.travelProgress.textContent = "Loading destination art...";
    }
  } else {
    elements.travelIntro.textContent = "Choose your next stop to continue the trip.";
    elements.travelProgress.hidden = true;
    elements.travelProgress.textContent = "";
  }

  for (const [index, option] of options.entries()) {
    const card = document.createElement("article");
    card.className = "travel-option travel-option-enter";
    card.style.animationDelay = `${index * 90}ms`;

    const thumb = document.createElement("div");
    thumb.className = "travel-thumb";
    const optionBackgroundUrl = resolveAssetUrl(option?.background);
    if (optionBackgroundUrl) {
      thumb.style.backgroundImage = `linear-gradient(rgba(75, 52, 28, 0.14), rgba(39, 26, 14, 0.24)), url('${optionBackgroundUrl}')`;
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
    button.disabled = state.busy || loading;
    button.addEventListener("click", () => sendTurn(option.command || "", { silent: true, useSceneFade: true }));

    copy.append(title, description);
    card.append(thumb, copy, button);
    elements.travelOptions.appendChild(card);
  }
}

function syncTravelOptionStateFromConversation() {
  const rendering = state.conversation?.rendering || {};
  const isSelection = Boolean(rendering.travel_selection);
  const loading = Boolean(rendering.travel_options_loading);

  if (!isSelection) {
    state.loadedTravelOptions = [];
    state.travelOptionsProgress = null;
    state.travelOptionsPolling = false;
    return;
  }

  const immediateOptions = Array.isArray(rendering.travel_options) ? rendering.travel_options : [];
  if (immediateOptions.length) {
    state.loadedTravelOptions = immediateOptions;
  }
  state.travelOptionsProgress = rendering.travel_options_progress || null;

  if (loading && !state.travelOptionsPolling && state.worldId) {
    state.travelOptionsPolling = true;
    void loadTravelOptionsSequentially();
  }
}

async function loadTravelOptionsSequentially() {
  try {
    while (state.conversation?.rendering?.travel_selection) {
      const loadedIds = state.loadedTravelOptions.map((option) => option.location_id);
      const payload = await apiRequest("POST", "/world/travel-options/next", {
        world_id: state.worldId,
        loaded_option_ids: loadedIds,
      });

      if (payload?.option) {
        state.loadedTravelOptions = [...state.loadedTravelOptions, payload.option];
      }
      state.travelOptionsProgress = payload?.progress || state.travelOptionsProgress;

      if (state.travelOptionsProgress?.complete) {
        if (state.conversation?.rendering) {
          state.conversation.rendering.travel_options_loading = false;
          state.conversation.rendering.travel_options_progress = state.travelOptionsProgress;
          state.conversation.rendering.travel_options = state.loadedTravelOptions;
        }
        break;
      }

      renderTravelOptions();
    }
  } catch (error) {
    handleError(error);
  } finally {
    state.travelOptionsPolling = false;
    render();
  }
}

function updateComposerState() {
  const travelSelection = Boolean(state.conversation?.rendering?.travel_selection);
  const hidden = state.startupVisible || travelSelection || state.travelTransitioning;
  const disabled = state.busy || state.startupVisible || travelSelection || state.travelTransitioning;

  elements.composer.hidden = hidden;
  elements.userInput.disabled = disabled;
  elements.sendButton.disabled = disabled;
  elements.userInput.placeholder = travelSelection
    ? "Choose a destination below to continue."
    : "Write your reply...";
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

function buildConversationStateForRequest(conversation) {
  if (!conversation || typeof conversation !== "object") {
    return conversation;
  }

  const {
    rendering: _rendering,
    ...rest
  } = conversation;

  const sanitizedHistory = Array.isArray(rest.conversation_history)
    ? rest.conversation_history.map((turn) => {
        if (!turn || typeof turn !== "object") {
          return turn;
        }
        const { incoming: _incoming, pending: _pending, ...cleanTurn } = turn;
        return cleanTurn;
      })
    : [];

  return {
    ...rest,
    conversation_history: sanitizedHistory,
  };
}

function resolveAssetUrl(asset) {
  if (!asset || typeof asset !== "object") {
    return null;
  }
  if (asset.using_fallback && asset.fallback_url) {
    return asset.fallback_url;
  }
  if (asset.exists && asset.url) {
    return asset.url;
  }
  if (!asset.exists && asset.fallback_url) {
    return asset.fallback_url;
  }
  return asset.url || null;
}

function resolveFallbackAssetUrl(asset) {
  if (!asset || typeof asset !== "object") {
    return null;
  }
  return asset.fallback_url || null;
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

elements.startupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await initializeWorld(elements.startupInput.value);
});

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
  if (state.busy) {
    return;
  }
  stopLoadingIndicator();
  hideSceneFadeOverlay();
  state.conversation = null;
  state.world = null;
  state.worldId = null;
  state.pendingUserTurn = null;
  state.travelTransitioning = false;
  state.startupVisible = true;
  state.loadedTravelOptions = [];
  state.travelOptionsProgress = null;
  state.travelOptionsPolling = false;
  state.error = null;
  state.worldLoadingVisible = false;
  setBusy(false, "Ready");
  render();
  elements.startupInput.focus();
});

render();
