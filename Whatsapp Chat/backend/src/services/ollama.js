const http = require("http");

const OLLAMA_BASE_URL = process.env.OLLAMA_BASE_URL || "http://localhost:11434";
const OLLAMA_MODEL = process.env.OLLAMA_MODEL || "llama3";

const SYSTEM_PROMPT = `You are a helpful and friendly AI assistant on WhatsApp.
Keep your responses concise and conversational, suitable for a messaging app.
Be helpful, accurate, and engaging. Avoid long markdown formatting — plain text only.`;

function generateReply(history) {
  return new Promise((resolve, reject) => {
    const messages = [
      { role: "system", content: SYSTEM_PROMPT },
      ...history,
    ];

    const body = JSON.stringify({
      model: OLLAMA_MODEL,
      messages,
      stream: false,
    });

    const url = new URL("/api/chat", OLLAMA_BASE_URL);

    console.log(`🔗 Ollama URL: ${url.toString()}`);
    console.log(`📦 Ollama model: ${OLLAMA_MODEL}`);
    console.log(`💬 Sending ${messages.length} messages to Ollama`);

    const options = {
      hostname: url.hostname,
      port: url.port || 11434,
      path: url.pathname,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(body),
      },
    };

    const req = http.request(options, (res) => {
      console.log(`📡 Ollama HTTP status: ${res.statusCode}`);
      let data = "";

      res.on("data", (chunk) => {
        data += chunk;
      });

      res.on("end", () => {
        console.log(`📡 Ollama raw response: ${data}`);
        try {
          const parsed = JSON.parse(data);
          const reply = parsed?.message?.content?.trim();
          if (!reply) {
            return reject(new Error(`Empty reply from Ollama. Full response: ${data}`));
          }
          resolve(reply);
        } catch (err) {
          reject(new Error(`Failed to parse Ollama response: ${err.message}. Raw: ${data}`));
        }
      });
    });

    req.on("error", (err) => {
      console.error(`❌ Ollama connection error: ${err.message}`);
      reject(new Error(`Ollama request failed: ${err.message}`));
    });

    req.setTimeout(60000, () => {
      console.error("❌ Ollama request timed out after 60s");
      req.destroy();
      reject(new Error("Ollama request timed out"));
    });

    req.write(body);
    req.end();
  });
}

module.exports = { generateReply };
