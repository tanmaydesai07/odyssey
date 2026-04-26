/**
 * In-memory conversation store.
 * Keeps per-user message history so the AI has context across messages.
 * In production, swap this out for a database (MongoDB, PostgreSQL, etc.)
 */

// { [phoneNumber]: [ { role: "user"|"assistant", content: string } ] }
const conversations = {};

function getConversation(phoneNumber) {
  if (!conversations[phoneNumber]) {
    conversations[phoneNumber] = [];
  }
  return conversations[phoneNumber];
}

function addMessage(phoneNumber, role, content) {
  const conversation = getConversation(phoneNumber);
  conversation.push({ role, content });
}

module.exports = { getConversation, addMessage };
