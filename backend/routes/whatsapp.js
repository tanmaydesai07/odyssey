/**
 * whatsapp.js — WhatsApp webhook route for NyayaMitr.
 *
 * Receives Twilio webhook calls, resolves the phone number to a user/session,
 * calls the Python agent, and sends the response back via WhatsApp.
 *
 * Special commands:
 *   /new          — Start a new case
 *   /cases        — List active cases
 *   /switch <n>   — Switch to case number n
 *   /help         — Show available commands
 */

const express = require('express');
const twilio = require('twilio');
const axios = require('axios');
const mongoose = require('mongoose');
const WhatsAppUser = require('../models/WhatsAppUser');
const User = require('../models/User');
const Case = require('../models/Case');
const { chatWithAgent, createAgentSession, getDocumentUrl, ensurePublicUrl, exportDocument, transcribeAudio } = require('../services/agentClient');
const { getMenuContentSid, initMenu } = require('../services/twilioMenu');

const router = express.Router();

const AGENT_URL = process.env.AGENT_URL || 'http://localhost:8000';

// Twilio client — lazy-loaded to ensure env vars are available
let _twilioClient = null;
function getTwilioClient() {
  if (!_twilioClient) {
    const sid = process.env.TWILIO_ACCOUNT_SID;
    const token = process.env.TWILIO_AUTH_TOKEN;
    console.log(`[WhatsApp] Initializing Twilio client (SID: ${sid ? sid.slice(0, 8) + '...' : 'MISSING'})`);
    _twilioClient = twilio(sid, token);
  }
  return _twilioClient;
}
const TWILIO_FROM = process.env.TWILIO_WHATSAPP_NUMBER || 'whatsapp:+14155238886';

/**
 * Get the public base URL (ngrok or production).
 * Twilio needs this to fetch media files.
 */
function getPublicUrl() {
  return process.env.PUBLIC_URL || 'http://localhost:5000';
}

// ── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Send a text message via WhatsApp.
 */
async function sendWhatsApp(to, body) {
  // WhatsApp has a 1600 character limit per message
  const MAX_LEN = 1500;
  const chunks = [];

  if (body.length <= MAX_LEN) {
    chunks.push(body);
  } else {
    let remaining = body;
    while (remaining.length > MAX_LEN) {
      let splitIdx = remaining.lastIndexOf('\n\n', MAX_LEN);
      if (splitIdx < 100) splitIdx = remaining.lastIndexOf('\n', MAX_LEN);
      if (splitIdx < 100) splitIdx = remaining.lastIndexOf('. ', MAX_LEN);
      if (splitIdx < 100) splitIdx = MAX_LEN;
      chunks.push(remaining.slice(0, splitIdx));
      remaining = remaining.slice(splitIdx).trimStart();
    }
    if (remaining) chunks.push(remaining);
  }

  const results = [];
  for (const chunk of chunks) {
    const msg = await getTwilioClient().messages.create({
      from: TWILIO_FROM,
      to,
      body: chunk,
    });
    results.push(msg);
  }
  return results;
}

/**
 * Send a media file (document) via WhatsApp.
 * mediaUrl MUST be a publicly accessible HTTPS URL.
 */
async function sendWhatsAppMedia(to, mediaUrl, caption = '') {
  console.log(`[WhatsApp] Sending media: ${mediaUrl}`);
  const msg = await getTwilioClient().messages.create({
    from: TWILIO_FROM,
    to,
    body: caption || 'Here is your document 📄',
    mediaUrl: [mediaUrl],
  });
  return msg;
}

/**
 * Send the interactive menu after every response.
 * Uses Twilio Content Template (list-picker) if available,
 * falls back to a text-based menu.
 */
async function sendMenu(to) {
  try {
    const contentSid = await getMenuContentSid();
    if (contentSid) {
      // Send interactive list-picker menu
      await getTwilioClient().messages.create({
        from: TWILIO_FROM,
        to,
        contentSid,
      });
      console.log(`[WhatsApp] ✅ Interactive menu sent to ${to}`);
    } else {
      // Fallback: text-based menu
      await sendWhatsApp(to, '─────────────\n📋 *Menu:* Reply with:\n• /new — New conversation\n• /cases — Switch to previous chat\n• /help — Help');
    }
  } catch (err) {
    console.error('[WhatsApp] Failed to send menu:', err.message);
    // Silent fail — menu is optional
  }
}

/**
 * Convert a document reference to a publicly accessible URL.
 * - Cloudinary URLs → use as-is (already public)
 * - Local agent URLs / file paths → proxy through our ngrok URL
 */
function makePublicDocUrl(doc, sessionId) {
  // Already a public HTTPS URL (Cloudinary, etc.)
  if (doc.url && doc.url.startsWith('https://') && !doc.url.includes('localhost')) {
    return doc.url;
  }

  // Build a proxy URL through our public ngrok endpoint
  const publicBase = getPublicUrl();
  return `${publicBase}/api/whatsapp/media/${sessionId}/${doc.filename}`;
}

/**
 * Clean markdown for WhatsApp — WhatsApp supports *bold* and _italic_
 * but not ## headings or complex markdown.
 */
function cleanForWhatsApp(text) {
  if (!text) return text;

  // Remove raw JSON blocks (agent sometimes leaks tool output)
  text = text.replace(/\{[^{}]*"(?:draft_id|file_path|download_url|format)"[^{}]*\}/g, '');

  // Remove lines that are just file paths
  text = text.replace(/^.*[A-Z]:\\\\.*$/gm, '');
  text = text.replace(/^.*\/exports\/.*$/gm, '');

  // Convert ## headings to *bold* lines
  text = text.replace(/^#{1,3}\s+(.+)$/gm, '*$1*');

  // Convert **bold** to *bold* (WhatsApp format)
  text = text.replace(/\*\*(.+?)\*\*/g, '*$1*');

  // Keep bullet points as-is (WhatsApp renders them fine)
  // Remove HTML tags if any
  text = text.replace(/<[^>]+>/g, '');

  // Clean up excessive whitespace
  text = text.replace(/\n{3,}/g, '\n\n');

  return text.trim();
}

/**
 * Get or create a WhatsAppUser + User + Case for a phone number.
 * Returns { waUser, user, activeCase }
 */
async function getOrCreateSession(phoneNumber, profileName) {
  let waUser = await WhatsAppUser.findOne({ phoneNumber });

  if (waUser) {
    const user = await User.findById(waUser.userId);
    let activeCase = null;

    if (waUser.activeCaseId) {
      activeCase = await Case.findOne({
        _id: waUser.activeCaseId,
        status: 'active',
      });
    }

    if (!activeCase) {
      activeCase = await createNewCase(waUser.userId.toString(), phoneNumber);
      waUser.activeCaseId = activeCase._id;
      await waUser.save();
    }

    return { waUser, user, activeCase };
  }

  // New WhatsApp user — auto-create User and Case
  console.log(`[WhatsApp] New user from ${phoneNumber}, creating account...`);

  const cleanPhone = phoneNumber.replace(/[^0-9]/g, '');
  const name = profileName || `WhatsApp User ${cleanPhone.slice(-4)}`;

  const user = await User.create({
    name,
    email: `wa_${cleanPhone}@whatsapp.local`,
    password: `wa_auto_${cleanPhone}_${Date.now()}`,
  });

  const activeCase = await createNewCase(user._id.toString(), phoneNumber);

  waUser = await WhatsAppUser.create({
    phoneNumber,
    userId: user._id,
    activeCaseId: activeCase._id,
    displayName: name,
  });

  console.log(`[WhatsApp] Created user ${user._id}, case ${activeCase._id} for ${phoneNumber}`);

  return { waUser, user, activeCase };
}

/**
 * Create a new Case and Python agent session.
 */
async function createNewCase(userId, phoneNumber) {
  try {
    const agentRes = await createAgentSession(userId, 'WhatsApp Case');
    const { session_id } = agentRes;

    const newCase = await Case.create({
      userId,
      sessionId: session_id,
      title: 'WhatsApp Case',
    });

    console.log(`[WhatsApp] Created case ${newCase._id} with session ${session_id}`);
    return newCase;
  } catch (err) {
    console.error('[WhatsApp] Failed to create case via agent:', err.message);
    const fallbackSessionId = new mongoose.Types.ObjectId().toString().slice(0, 12);
    const newCase = await Case.create({
      userId,
      sessionId: fallbackSessionId,
      title: 'WhatsApp Case',
    });
    return newCase;
  }
}

// ── Command Handlers ─────────────────────────────────────────────────────────

const HELP_TEXT = `🏛️ *NyayaMitr WhatsApp Commands*

/new — Start a new legal case
/cases — List your active cases
/switch <number> — Switch to a specific case
/help — Show this help message

Just type your legal question to get started! 🇮🇳`;

async function handleCommand(command, phoneNumber, waUser) {
  const cmd = command.toLowerCase().trim();

  if (cmd === '/help') {
    return { text: HELP_TEXT, handled: true };
  }

  if (cmd === '/new') {
    const newCase = await createNewCase(waUser.userId.toString(), phoneNumber);
    waUser.activeCaseId = newCase._id;
    await waUser.save();
    return {
      text: '✅ *New case started!*\n\nDescribe your legal issue and I\'ll help you navigate it step by step.',
      handled: true,
    };
  }

  if (cmd === '/cases') {
    const cases = await Case.find({
      userId: waUser.userId,
      status: 'active',
    }).sort({ lastMessageAt: -1 }).limit(10);

    if (cases.length === 0) {
      return { text: 'No active cases. Type /new to start one!', handled: true };
    }

    let text = '📋 *Your Cases:*\n\n';
    cases.forEach((c, i) => {
      const isActive = waUser.activeCaseId && c._id.equals(waUser.activeCaseId);
      const marker = isActive ? ' ← *active*' : '';
      const date = c.lastMessageAt ? c.lastMessageAt.toLocaleDateString() : 'N/A';
      text += `${i + 1}. ${c.title} (${c.messageCount} msgs, ${date})${marker}\n`;
    });
    text += '\nUse /switch <number> to switch cases.';

    return { text, handled: true };
  }

  if (cmd.startsWith('/switch')) {
    const num = parseInt(cmd.replace('/switch', '').trim(), 10);
    if (isNaN(num) || num < 1) {
      return { text: '❌ Usage: /switch <number>\nE.g., /switch 2', handled: true };
    }

    const cases = await Case.find({
      userId: waUser.userId,
      status: 'active',
    }).sort({ lastMessageAt: -1 }).limit(10);

    if (num > cases.length) {
      return { text: `❌ Only ${cases.length} cases available. Use /cases to see them.`, handled: true };
    }

    const target = cases[num - 1];
    waUser.activeCaseId = target._id;
    await waUser.save();

    return {
      text: `✅ Switched to case: *${target.title}*\n\nContinue your conversation.`,
      handled: true,
    };
  }

  return { handled: false };
}

/**
 * Handle interactive menu item selections.
 * Twilio sends ListId when user taps an item in the list-picker.
 */
async function handleMenuSelection(listId, phoneNumber, waUser) {
  switch (listId) {
    case 'new_chat': {
      const newCase = await createNewCase(waUser.userId.toString(), phoneNumber);
      waUser.activeCaseId = newCase._id;
      await waUser.save();
      return {
        text: '✅ *New case started!*\n\nDescribe your legal issue and I\'ll help you navigate it step by step.',
        handled: true,
      };
    }
    case 'my_cases': {
      const cases = await Case.find({
        userId: waUser.userId,
        status: 'active',
      }).sort({ lastMessageAt: -1 }).limit(10);

      if (cases.length === 0) {
        return { text: 'No active cases. Type /new to start one!', handled: true };
      }

      let text = '📋 *Your Cases:*\n\n';
      cases.forEach((c, i) => {
        const isActive = waUser.activeCaseId && c._id.equals(waUser.activeCaseId);
        const marker = isActive ? ' ← *active*' : '';
        const date = c.lastMessageAt ? c.lastMessageAt.toLocaleDateString() : 'N/A';
        text += `${i + 1}. ${c.title} (${c.messageCount} msgs, ${date})${marker}\n`;
      });
      text += '\nReply /switch <number> to switch cases.';
      return { text, handled: true };
    }
    case 'get_help':
      return { text: HELP_TEXT, handled: true };
    default:
      return { handled: false };
  }
}

// ── Document Proxy Route ─────────────────────────────────────────────────────
// Twilio can't reach localhost:8000. This route proxies document downloads
// from the Python agent through our ngrok-exposed Node.js server.

/**
 * GET /api/whatsapp/media/:sessionId/:filename
 * Proxies document download from the Python agent so Twilio can fetch it.
 */
router.get('/media/:sessionId/:filename', async (req, res) => {
  const { sessionId, filename } = req.params;

  console.log(`[WhatsApp] Document proxy request: ${sessionId}/${filename}`);

  try {
    // Fetch from Python agent
    const agentRes = await axios.get(
      `${AGENT_URL}/document/${sessionId}/${filename}`,
      { responseType: 'stream', timeout: 30000 }
    );

    // Set proper content type
    const contentType = agentRes.headers['content-type'] || 'application/octet-stream';
    res.setHeader('Content-Type', contentType);
    res.setHeader('Content-Disposition', `inline; filename="${filename}"`);

    // Pipe the file through to Twilio
    agentRes.data.pipe(res);
  } catch (err) {
    console.error(`[WhatsApp] Document proxy error: ${err.message}`);
    res.status(404).json({ error: 'Document not found' });
  }
});

// ── Webhook Route ────────────────────────────────────────────────────────────

/**
 * GET /api/whatsapp/webhook — Twilio verification.
 */
router.get('/webhook', (req, res) => {
  res.status(200).send('WhatsApp webhook is active');
});

/**
 * POST /api/whatsapp/webhook — Receives incoming WhatsApp messages from Twilio.
 */
router.post('/webhook', async (req, res) => {
  const from = req.body.From;
  let body = req.body.Body || '';
  const profileName = req.body.ProfileName || '';
  const listId = req.body.ListId || null;  // From interactive list-picker selections
  const numMedia = parseInt(req.body.NumMedia || '0', 10);
  const mediaUrl = req.body.MediaUrl0 || null;
  const mediaType = req.body.MediaContentType0 || '';

  console.log(`\n📱 [WhatsApp] Message from: ${from}`);
  if (body) console.log(`📝 [WhatsApp] Text: ${body}`);
  if (listId) console.log(`📋 [WhatsApp] ListId: ${listId}`);
  if (numMedia > 0) console.log(`🎤 [WhatsApp] Media: ${numMedia} file(s), type=${mediaType}`);

  // Voice messages have media but no body text
  if (!from || (!body && numMedia === 0)) {
    console.error('[WhatsApp] Missing From and no content');
    return res.status(400).send('Missing From or content');
  }

  // Respond immediately to Twilio (15s timeout)
  res.set('Content-Type', 'text/xml');
  res.send(`<?xml version="1.0" encoding="UTF-8"?><Response></Response>`);

  // Process async
  processWhatsAppMessage(from, body, profileName, listId, { numMedia, mediaUrl, mediaType }).catch((err) => {
    console.error('[WhatsApp] Background processing error:', err.message);
  });
});

/**
 * Background processor — resolves user/session, handles commands or
 * forwards to the AI agent.
 */
async function processWhatsAppMessage(phoneNumber, messageText, profileName, listId, media = {}) {
  try {
    // 1. Get or create the user/session
    const { waUser, user, activeCase } = await getOrCreateSession(phoneNumber, profileName);

    // Update message counter
    waUser.totalMessages += 1;
    await waUser.save();

    // 1.5. Handle voice messages — transcribe audio to text
    if (media.numMedia > 0 && media.mediaType && media.mediaType.startsWith('audio/')) {
      console.log(`🎤 [WhatsApp] Voice message detected, transcribing...`);
      await sendWhatsApp(phoneNumber, '🎤 _Transcribing your voice message..._');

      try {
        const result = await transcribeAudio(media.mediaUrl, waUser.language || 'en');
        if (result.text) {
          messageText = result.text;
          console.log(`🎤 [WhatsApp] Transcribed: "${messageText.slice(0, 80)}..."`);
          await sendWhatsApp(phoneNumber, `📝 _You said:_ "${messageText}"`);
        } else {
          await sendWhatsApp(phoneNumber, '⚠️ I couldn\'t understand the voice message. Please try again or type your question.');
          await sendMenu(phoneNumber);
          return;
        }
      } catch (err) {
        console.error('[WhatsApp] Transcription error:', err.message);
        await sendWhatsApp(phoneNumber, '⚠️ I couldn\'t process the voice message. Please try typing your question instead.');
        await sendMenu(phoneNumber);
        return;
      }
    }

    // Skip if no text to process (e.g., image without caption)
    if (!messageText || !messageText.trim()) {
      await sendWhatsApp(phoneNumber, '💬 Please send a text or voice message with your legal question.');
      await sendMenu(phoneNumber);
      return;
    }

    // 2. Check for menu item taps (Twilio sends ListId for list-picker selections)
    if (listId) {
      const menuResult = await handleMenuSelection(listId, phoneNumber, waUser);
      if (menuResult.handled) {
        await sendWhatsApp(phoneNumber, menuResult.text);
        await sendMenu(phoneNumber);
        return;
      }
    }

    // 3. Check for text commands
    if (messageText.startsWith('/')) {
      const cmdResult = await handleCommand(messageText, phoneNumber, waUser);
      if (cmdResult.handled) {
        await sendWhatsApp(phoneNumber, cmdResult.text);
        await sendMenu(phoneNumber);
        return;
      }
    }

    // 3. Forward to agent
    console.log(`[WhatsApp] Forwarding to agent — session: ${activeCase.sessionId}`);

    const { answer, documents } = await chatWithAgent(
      activeCase.sessionId,
      user._id.toString(),
      messageText,
      waUser.language
    );

    // 4. Update case metadata
    activeCase.messageCount += 1;
    activeCase.lastMessageAt = new Date();
    if (activeCase.title === 'WhatsApp Case' || activeCase.title === 'New case') {
      activeCase.title = messageText.trim().slice(0, 60);
    }
    await activeCase.save();

    // 5. Clean and send the text response
    const cleanedAnswer = cleanForWhatsApp(answer) ||
      'I couldn\'t process your request. Please try rephrasing your question.';

    await sendWhatsApp(phoneNumber, cleanedAnswer);

    // 6. Send any documents that were generated
    for (const doc of documents) {
      try {
        // Get a publicly accessible URL (Cloudinary) that Twilio can fetch
        console.log(`[WhatsApp] Processing document: ${doc.filename} (draft_id: ${doc.draft_id || 'N/A'})`);
        
        let publicUrl = await ensurePublicUrl(doc, activeCase.sessionId);
        
        if (!publicUrl && doc.draft_id) {
          // Try exporting as PDF (more universally supported on WhatsApp)
          console.log(`[WhatsApp] Trying PDF export for draft ${doc.draft_id}...`);
          const pdfResult = await exportDocument(activeCase.sessionId, doc.draft_id, 'pdf');
          if (pdfResult && pdfResult.download_url) {
            publicUrl = pdfResult.download_url;
            doc.filename = pdfResult.filename || doc.filename.replace(/\.docx$/, '.pdf');
          }
        }

        if (publicUrl) {
          console.log(`[WhatsApp] Sending document: ${doc.filename}`);
          console.log(`[WhatsApp]   Public URL: ${publicUrl}`);

          await sendWhatsAppMedia(
            phoneNumber,
            publicUrl,
            `📄 *${doc.filename}*\nHere's your generated document.`
          );
          console.log(`[WhatsApp] ✅ Document sent: ${doc.filename}`);
        } else {
          console.log(`[WhatsApp] ⚠️ No public URL available for ${doc.filename}`);
          await sendWhatsApp(
            phoneNumber,
            `📄 Your document *${doc.filename}* was generated. You can download it from the web app.`
          );
        }
      } catch (docErr) {
        console.error(`[WhatsApp] ❌ Failed to send document ${doc.filename}:`, docErr.message);
        await sendWhatsApp(
          phoneNumber,
          `📄 Your document *${doc.filename}* was generated but I couldn't send it as an attachment. You can download it from the web app.`
        );
      }
    }

    // 8. Send interactive menu after the response
    await sendMenu(phoneNumber);

    console.log(`[WhatsApp] ✅ Response sent to ${phoneNumber}`);

  } catch (err) {
    console.error(`[WhatsApp] Error processing message from ${phoneNumber}:`, err.message);

    try {
      await sendWhatsApp(
        phoneNumber,
        '⚠️ Sorry, I encountered an error processing your request. Please try again in a moment.\n\nIf the problem persists, try /new to start a fresh case.'
      );
    } catch (sendErr) {
      console.error('[WhatsApp] Failed to send error message:', sendErr.message);
    }
  }
}

module.exports = router;
