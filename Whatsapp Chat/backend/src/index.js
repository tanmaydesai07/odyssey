require("dotenv").config();
const express = require("express");
const webhookRouter = require("./routes/webhook");

const app = express();

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: false }));

// Log every incoming request
app.use((req, res, next) => {
  console.log(`➡️  ${req.method} ${req.path}`);
  next();
});

// Routes
app.use("/webhook", webhookRouter);

// Health check — open http://localhost:3001/health in browser to confirm server is up
app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    timestamp: new Date().toISOString(),
    ollama: process.env.OLLAMA_BASE_URL || "http://localhost:11434",
    model: process.env.OLLAMA_MODEL || "llama3",
    twilioNumber: process.env.TWILIO_WHATSAPP_NUMBER || "NOT SET",
  });
});

// Test endpoint — simulates a WhatsApp message without needing Twilio
// POST http://localhost:3001/test  with body { "message": "hello" }
app.post("/test", async (req, res) => {
  const fakeFrom = `whatsapp:${process.env.DESTINATION_PHONE_NUMBER}`;
  const fakeBody = req.body.message || "Hello!";

  console.log(`\n🧪 TEST: Simulating message from ${fakeFrom}: "${fakeBody}"`);

  // Inject into webhook handler
  req.body.From = fakeFrom;
  req.body.Body = fakeBody;

  // Forward to webhook router manually
  const { addMessage, getConversation } = require("./services/store");
  const { generateReply } = require("./services/ollama");

  try {
    addMessage(fakeFrom, "user", fakeBody);
    const history = getConversation(fakeFrom);
    const reply = await generateReply(history);
    addMessage(fakeFrom, "assistant", reply);
    console.log(`🤖 AI reply: ${reply}`);
    res.json({ success: true, reply });
  } catch (err) {
    console.error("❌ Test error:", err.message);
    res.status(500).json({ error: err.message });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log("\n=============================");
  console.log(`✅ Backend running on http://localhost:${PORT}`);
  console.log(`🔗 Webhook endpoint: POST http://localhost:${PORT}/webhook/twilio`);
  console.log(`🏥 Health check:     GET  http://localhost:${PORT}/health`);
  console.log(`🧪 Test endpoint:    POST http://localhost:${PORT}/test`);
  console.log("=============================\n");
});
