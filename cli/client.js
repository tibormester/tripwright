#!/usr/bin/env node
"use strict";

const http = require("http");
const https = require("https");
const readline = require("readline");

const BASE_URL = process.env.API_URL || "http://localhost:5000";

function request(method, path, body) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, BASE_URL);
    const transport = url.protocol === "https:" ? https : http;
    const payload = body ? JSON.stringify(body) : null;

    const options = {
      hostname: url.hostname,
      port: url.port || (url.protocol === "https:" ? 443 : 80),
      path: `${url.pathname}${url.search}`,
      method,
      headers: { "Content-Type": "application/json" },
    };

    if (payload) {
      options.headers["Content-Length"] = Buffer.byteLength(payload);
    }

    const req = transport.request(options, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        let parsed = data;
        try {
          parsed = data ? JSON.parse(data) : null;
        } catch {
          // keep raw text
        }

        if (res.statusCode >= 400) {
          const message =
            parsed && typeof parsed === "object" && parsed.error
              ? parsed.error
              : `Request failed with status ${res.statusCode}`;
          reject(new Error(message));
          return;
        }

        resolve(parsed);
      });
    });

    req.on("error", reject);
    if (payload) req.write(payload);
    req.end();
  });
}

function formatTurn(turn) {
  if (!turn || typeof turn !== "object") return "";
  const speaker = turn.speaker || "Unknown";
  const dialogue = turn.dialogue || "";
  return `\n[${speaker}]\n${dialogue}\n`;
}

function printNewTurns(state, previousLength = 0, options = {}) {
  const { includeUser = true } = options;
  const history = Array.isArray(state?.conversation_history)
    ? state.conversation_history
    : [];

  if (history.length === 0) {
    console.log("(no conversation yet)");
    return;
  }

  const turnsToPrint = history
    .slice(previousLength)
    .filter((turn) => includeUser || turn?.speaker !== "User");

  for (const turn of turnsToPrint) {
    process.stdout.write(formatTurn(turn));
  }
}

async function initializeWorld(lodgingInput) {
  return request("POST", "/world/initialize", {
    lodging_input: lodgingInput,
  });
}

async function sendUserTurn(state, worldId, userInput) {
  return request("POST", "/conversation/turn", {
    state: buildConversationStateForRequest(state),
    world_id: worldId,
    user_input: userInput,
  });
}

function askQuestion(rl, prompt) {
  return new Promise((resolve) => rl.question(prompt, resolve));
}

function buildConversationStateForRequest(conversation) {
  if (!conversation || typeof conversation !== "object") {
    return conversation;
  }

  const { rendering: _rendering, ...rest } = conversation;
  return rest;
}

function printConversationEnvelope(envelope) {
  if (!envelope || typeof envelope !== "object") {
    console.log("(no response)");
    return;
  }

  if (envelope.fallback_mode) {
    console.log(`\n[system]\nUsing fallback scene data: ${envelope.fallback_reason || "unknown reason"}\n`);
  }

  const conversation = envelope.conversation || envelope;
  if (conversation?.scene_label) {
    console.log(`\n=== ${conversation.scene_label} ===`);
  }
  if (conversation?.rendering?.scene?.description) {
    console.log(conversation.rendering.scene.description);
  }
  printNewTurns(conversation, 0);
}

async function main() {
  console.log("TripWright CLI");
  console.log("Commands: /restart  /history  /quit  /command <n>\n");

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: "> ",
  });

  let worldEnvelope = null;
  let conversationState = null;
  let worldId = null;
  let lastLodgingInput = "";

  async function startWorld(lodgingInput) {
    lastLodgingInput = lodgingInput.trim();
    worldEnvelope = await initializeWorld(lastLodgingInput);
    conversationState = worldEnvelope.conversation;
    worldId = worldEnvelope.world_id || null;
    printConversationEnvelope(worldEnvelope);
  }

  const initialInput = await askQuestion(rl, "Enter a Booking.com URL or lodging query: ");
  await startWorld(initialInput);
  rl.prompt();

  rl.on("line", async (line) => {
    const input = line.trim();

    if (!input) {
      rl.prompt();
      return;
    }

    try {
      if (input === "/quit") {
        rl.close();
        return;
      }

      if (input === "/history") {
        printNewTurns(conversationState, 0);
        rl.prompt();
        return;
      }

      if (input === "/restart") {
        const nextInput = await askQuestion(rl, "Enter a Booking.com URL or lodging query: ");
        await startWorld(nextInput || lastLodgingInput);
        rl.prompt();
        return;
      }

      const previousLength = Array.isArray(conversationState?.conversation_history)
        ? conversationState.conversation_history.length
        : 0;

      conversationState = await sendUserTurn(conversationState, worldId, input);
      const nextHistoryLength = Array.isArray(conversationState?.conversation_history)
        ? conversationState.conversation_history.length
        : 0;
      const printOffset = nextHistoryLength < previousLength ? 0 : previousLength;

      if (conversationState?.scene_label && printOffset === 0) {
        console.log(`\n=== ${conversationState.scene_label} ===`);
      }
      printNewTurns(conversationState, printOffset, { includeUser: false });
    } catch (error) {
      console.error(`Error: ${error.message}`);
    }

    rl.prompt();
  });

  rl.on("close", () => {
    console.log("Goodbye.");
    process.exit(0);
  });
}

main().catch((err) => {
  console.error("Failed to run client:", err.message);
  process.exit(1);
});
