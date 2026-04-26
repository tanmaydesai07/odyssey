const twilio = require("twilio");

const accountSid = process.env.TWILIO_ACCOUNT_SID;
const authToken = process.env.TWILIO_AUTH_TOKEN;
const fromNumber = process.env.TWILIO_WHATSAPP_NUMBER;

console.log("🔧 Twilio config check:");
console.log("  ACCOUNT_SID:", accountSid ? `${accountSid.slice(0, 8)}...` : "❌ MISSING");
console.log("  AUTH_TOKEN:", authToken ? "✅ set" : "❌ MISSING");
console.log("  WHATSAPP_NUMBER:", fromNumber || "❌ MISSING");

const client = twilio(accountSid, authToken);

async function sendWhatsAppMessage(to, body) {
  console.log(`📤 Twilio sending from: ${fromNumber}`);
  console.log(`📤 Twilio sending to:   ${to}`);
  console.log(`📤 Message body: ${body}`);

  const message = await client.messages.create({
    from: fromNumber,
    to,
    body,
  });

  return message;
}

module.exports = { sendWhatsAppMessage };
