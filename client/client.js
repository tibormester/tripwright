#!/usr/bin/env node
"use strict";

const http = require("http");
const readline = require("readline");

const BASE_URL = process.env.API_URL || "http://localhost:5000";

function request(method, path, body) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, BASE_URL);
    const payload = body ? JSON.stringify(body) : null;
    const options = {
      hostname: url.hostname,
      port: url.port || (url.protocol === "https:" ? 443 : 80),
      path: url.pathname,
      method,
      headers: { "Content-Type": "application/json" },
    };
    if (payload) {
      options.headers["Content-Length"] = Buffer.byteLength(payload);
    }
    const req = http.request(options, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        try {
          resolve(JSON.parse(data));
        } catch {
          resolve(data);
        }
      });
    });
    req.on("error", reject);
    if (payload) req.write(payload);
    req.end();
  });
}

async function printHistory() {
  const msgs = await request("GET", "/messages");
  if (!Array.isArray(msgs) || msgs.length === 0) {
    console.log("(no messages yet)");
    return;
  }
  for (const m of msgs) {
    console.log(`[${m.role}] ${m.text}`);
  }
}

async function main() {
  console.log("TripWright CLI — type a message and press Enter.");
  console.log("Commands: /history  /clear  /quit\n");

  await printHistory();

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
      await printHistory();
      rl.prompt();
      return;
    }
    if (input === "/clear") {
      await request("DELETE", "/messages");
      console.log("History cleared.");
      rl.prompt();
      return;
    }
    const result = await request("POST", "/messages", { role: "user", text: input });
    if (result.error) {
      console.error("Error:", result.error);
    } else {
      console.log(`[${result.role}] ${result.text}`);
    }
    rl.prompt();
  });

  rl.on("close", () => {
    console.log("Goodbye.");
    process.exit(0);
  });
}

main().catch((err) => {
  console.error("Failed to connect to backend:", err.message);
  process.exit(1);
});
