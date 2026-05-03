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

async function initializeConversation() {
  return request("POST", "/conversation/initialize", {});
}

async function sendUserTurn(state, userInput) {
  return request("POST", "/conversation/turn", {
    state,
    user_input: userInput,
  });
}

async function main() {
  console.log("TripWright NPC CLI");
  console.log("Commands: /restart  /history  /quit\n");

  let conversationState = await initializeConversation();
  printNewTurns(conversationState, 0);

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: "> ",
  });

  rl.prompt();

  rl.on("line", async (line) => {
    const input = line.trim();

    if (!input) {
      rl.prompt();
      return;
    }

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
      conversationState = await initializeConversation();
      printNewTurns(conversationState, 0);
      rl.prompt();
      return;
    }

    const previousLength = Array.isArray(conversationState?.conversation_history)
      ? conversationState.conversation_history.length
      : 0;

    conversationState = await sendUserTurn(conversationState, input);
    printNewTurns(conversationState, previousLength, { includeUser: false });
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
