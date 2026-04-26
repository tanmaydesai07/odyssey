const express = require("express");
const router = express.Router();
const { addMessage, getConversation } = require("../services/store");
const { generateReply } = require("../services/ollama");
const { sendWhatsAppMessage } = require("../services/twilio");

/**
 * POST /webhook/twilio
 */
router.post("/twilio", async (req, res) => {
  console.log("\n========== INCOMING WEBHOOK ==========");
  console.log("Headers:", JSON.stringify(req.headers, null, 2));
  console.log("Body:", JSON.stringify(req.body, null, 2));
  console.log("======================================\n");

  const from = req.body.From;
  const body = req.body.Body;

  if (!from || !body) {
    console.error("❌ Missing From or Body in request");
    return res.status(400).send("Missing From or Body");
  }

  console.log(`📥 Message from: ${from}`);
  console.log(`📝 Message text: ${body}`);

  try {
    // 1. Save user message
    console.log("💾 Saving user message to store...");
    addMessage(from, "user", body);

    // 2. Get conversation history
    const history = getConversation(from);
    console.log(`📚 Conversation history length: ${history.length} messages`);

    // 3. Call Ollama
    console.log(`🤖 Calling Ollama (model: ${process.env.OLLAMA_MODEL || "llama3"})...`);
    const replyText = await generateReply(history);
    console.log(`✅ Ollama replied: ${replyText}`);

    // 4. Save AI reply
    addMessage(from, "assistant", replyText);

    // 5. Send via Twilio
    console.log(`📤 Sending reply via Twilio to ${from}...`);
    const msg = await sendWhatsAppMessage(from, replyText);
    console.log(`✅ Twilio sent! SID: ${msg.sid}`);

    res.set("Content-Type", "text/xml");
    res.send(`<?xml version="1.0" encoding="UTF-8"?><Response></Response>`);

  } catch (error) {
    console.error("\n========== ERROR ==========");
    console.error("Message:", error.message);
    console.error("Stack:", error.stack);
    console.error("===========================\n");
    res.status(500).send("Internal Server Error");
  }
});

module.exports = router;
