const state = {
  conversation: null,
  busy: false,
  error: null,
};

const elements = {
  chatLog: document.getElementById("chat-log"),
  composer: document.getElementById("composer"),
  userInput: document.getElementById("user-input"),
  sendButton: document.getElementById("send-button"),
  restartButton: document.getElementById("restart-button"),
  statusText: document.getElementById("status-text"),
  statusDot: document.getElementById("status-dot"),
  sceneImage: document.getElementById("scene-image"),
  sceneLabel: document.getElementById("scene-label"),
  sceneLocation: document.getElementById("scene-location"),
  npcName: document.getElementById("npc-name"),
  npcRole: document.getElementById("npc-role"),
  npcPortrait: document.getElementById("npc-portrait"),
  npcFallback: document.getElementById("npc-fallback"),
  travelPanel: document.getElementById("travel-panel"),
  travelOptions: document.getElementById("travel-options"),
  messageTemplate: document.getElementById("message-template"),
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
  setBusy(true, "Starting conversation…");
  try {
    state.conversation = await apiRequest("POST", "/conversation/initialize", {});
    state.error = null;
    render();
    setBusy(false, "Connected");
  } catch (error) {
    handleError(error);
  }
}

async function sendTurn(userInput) {
  if (!state.conversation || !userInput.trim()) {
    return;
  }

  setBusy(true, "Waiting for NPC response…");
  try {
    state.conversation = await apiRequest("POST", "/conversation/turn", {
      state: state.conversation,
      user_input: userInput,
    });
    state.error = null;
    render();
    setBusy(false, "Connected");
  } catch (error) {
    handleError(error);
  }
}

function setBusy(busy, statusText) {
  state.busy = busy;
  elements.sendButton.disabled = busy;
  elements.restartButton.disabled = busy;
  elements.userInput.disabled = busy;
  elements.statusText.textContent = statusText;
  elements.statusDot.classList.remove("ready", "error");
  if (!busy && !state.error) {
    elements.statusDot.classList.add("ready");
  }
}

function handleError(error) {
  state.busy = false;
  state.error = error instanceof Error ? error.message : String(error);
  elements.sendButton.disabled = false;
  elements.restartButton.disabled = false;
  elements.userInput.disabled = false;
  elements.statusText.textContent = state.error;
  elements.statusDot.classList.remove("ready");
  elements.statusDot.classList.add("error");
}

function render() {
  renderScene();
  renderConversation();
  renderTravelOptions();
}

function renderScene() {
  const rendering = state.conversation?.rendering || {};
  const scene = rendering.scene || {};
  const npc = rendering.npc || {};
  const background = scene.background || {};
  const headshot = npc.headshot || {};

  elements.sceneLabel.textContent = scene.label || "Unknown Scene";
  elements.sceneLocation.textContent = scene.location || "";
  elements.sceneImage.style.backgroundImage = background.url
    ? `linear-gradient(180deg, rgba(15, 23, 42, 0.12), rgba(2, 6, 23, 0.92)), url('${background.url}')`
    : "linear-gradient(160deg, rgba(56, 189, 248, 0.18), rgba(15, 23, 42, 0.75)), linear-gradient(180deg, rgba(15, 23, 42, 0.4), rgba(2, 6, 23, 0.95))";

  elements.npcName.textContent = npc.name || "Unknown NPC";
  elements.npcRole.textContent = npc.role || "";

  if (headshot.url) {
    elements.npcPortrait.src = headshot.url;
    elements.npcPortrait.hidden = false;
    elements.npcFallback.hidden = true;
  } else {
    elements.npcPortrait.hidden = true;
    elements.npcFallback.hidden = false;
  }
}

function renderConversation() {
  const history = Array.isArray(state.conversation?.conversation_history)
    ? state.conversation.conversation_history
    : [];

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
    const speaker = turn?.speaker || "Unknown";

    message.classList.add(classifySpeaker(speaker, state.conversation?.npc_profile?.name));
    meta.textContent = speaker;
    body.textContent = turn?.dialogue || "";

    elements.chatLog.appendChild(fragment);
  }

  elements.chatLog.scrollTop = elements.chatLog.scrollHeight;
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

  for (const option of options) {
    const card = document.createElement("article");
    card.className = "travel-option";

    const top = document.createElement("div");
    top.className = "travel-option-top";

    const thumb = document.createElement("div");
    thumb.className = "travel-thumb";
    if (option?.background?.url) {
      thumb.style.backgroundImage = `linear-gradient(180deg, rgba(15, 23, 42, 0.18), rgba(2, 6, 23, 0.82)), url('${option.background.url}')`;
    }

    const copy = document.createElement("div");
    copy.className = "travel-option-copy";

    const title = document.createElement("h3");
    title.textContent = option.label || "Unknown destination";

    const description = document.createElement("p");
    description.textContent = option.description || "";

    const npcInfo = document.createElement("p");
    npcInfo.textContent = option?.npc?.name ? `Meet ${option.npc.name}` : "";

    copy.append(title, description, npcInfo);
    top.append(thumb, copy);

    const button = document.createElement("button");
    button.type = "button";
    button.className = "travel-command";
    button.textContent = option.command || "Choose";
    button.disabled = state.busy;
    button.addEventListener("click", () => sendTurn(option.command || ""));

    card.append(top, button);
    elements.travelOptions.appendChild(card);
  }
}

function classifySpeaker(speaker, npcName) {
  if (speaker === "User") return "user";
  if (speaker === "Narrator") return "narrator";
  if (speaker === "System") return "system";
  if (speaker === npcName) return "npc";
  return "npc";
}

elements.composer.addEventListener("submit", async (event) => {
  event.preventDefault();
  const value = elements.userInput.value.trim();
  if (!value || state.busy) {
    return;
  }

  elements.userInput.value = "";
  await sendTurn(value);
  elements.userInput.focus();
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
