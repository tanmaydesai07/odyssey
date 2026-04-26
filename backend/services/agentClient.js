/**
 * agentClient.js — Calls the Python agent (FastAPI :8000) from the
 * Node.js backend.  Unlike the browser-facing SSE proxy in cases.js,
 * this collects the full streamed response into a single string so we
 * can send it as one WhatsApp message.
 */

const axios = require('axios');

const AGENT_URL = process.env.AGENT_URL || 'http://localhost:8000';

/**
 * Send a message to the agent and wait for the full answer.
 *
 * @param {string} sessionId  — Python agent session id
 * @param {string} userId     — MongoDB user _id string
 * @param {string} message    — User's message text
 * @param {string} language   — Language code (default 'en')
 * @returns {Promise<{answer: string, documents: Array}>}
 */
async function chatWithAgent(sessionId, userId, message, language = 'en') {
  try {
    const response = await axios.post(
      `${AGENT_URL}/chat`,
      {
        session_id: sessionId,
        user_id: userId,
        message,
        language,
      },
      {
        responseType: 'stream',
        timeout: 180000, // 3 minutes — agent can be slow
      }
    );

    return new Promise((resolve, reject) => {
      let answer = '';
      let documents = [];
      let buffer = '';
      let allObservations = [];

      response.data.on('data', (chunk) => {
        buffer += chunk.toString();

        // SSE format: "data: {...}\n\n"
        const lines = buffer.split('\n');
        buffer = lines.pop(); // keep incomplete line in buffer

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;

          try {
            const evt = JSON.parse(jsonStr);

            if (evt.type === 'answer') {
              answer = evt.content || '';
            }

            // Collect all observations for document detection
            if (evt.type === 'observation' && evt.content) {
              allObservations.push(evt.content);
              const docs = extractAllDocuments(evt.content, sessionId);
              for (const doc of docs) {
                if (!documents.find(d => d.url === doc.url)) {
                  documents.push(doc);
                }
              }
            }
          } catch {
            // Ignore malformed SSE lines
          }
        }
      });

      response.data.on('end', () => {
        // Process any remaining buffer
        if (buffer.startsWith('data: ')) {
          try {
            const evt = JSON.parse(buffer.slice(6).trim());
            if (evt.type === 'answer') answer = evt.content || '';
          } catch {}
        }

        // Also scan the final answer for document URLs
        const docsInAnswer = extractAllDocuments(answer, sessionId);
        for (const doc of docsInAnswer) {
          if (!documents.find(d => d.url === doc.url)) {
            documents.push(doc);
          }
        }

        console.log(`[agentClient] Answer length: ${answer.length}, Documents found: ${documents.length}`);
        if (documents.length > 0) {
          console.log('[agentClient] Documents:', documents.map(d => d.filename).join(', '));
        }

        resolve({ answer, documents });
      });

      response.data.on('error', (err) => {
        reject(new Error(`Agent stream error: ${err.message}`));
      });
    });
  } catch (err) {
    console.error('[agentClient] chatWithAgent error:', err.message);
    throw err;
  }
}

/**
 * Create a new session on the Python agent.
 *
 * @param {string} userId     — MongoDB user _id
 * @param {string} caseTitle  — Title for the case
 * @returns {Promise<{session_id: string}>}
 */
async function createAgentSession(userId, caseTitle = 'WhatsApp Case') {
  const res = await axios.post(`${AGENT_URL}/session/new`, {
    user_id: userId,
    case_title: caseTitle,
  });
  return res.data;
}

/**
 * Get a document download URL from the agent.
 *
 * @param {string} sessionId
 * @param {string} filename
 * @returns {string} Full URL to download the document
 */
function getDocumentUrl(sessionId, filename) {
  return `${AGENT_URL}/document/${sessionId}/${filename}`;
}

/**
 * Extract ALL document references from text.
 * The agent's document_exporter tool returns JSON like:
 *   {"draft_id":"abc","format":"pdf","file_path":"...","download_url":"https://res.cloudinary.com/...","storage":"cloudinary","message":"..."}
 *
 * We need to catch:
 * 1. JSON with download_url (Cloudinary URLs)
 * 2. JSON with file_path (local files → serve via agent)
 * 3. Bare Cloudinary URLs in text
 * 4. Local /document/session/file paths
 *
 * @param {string} text — observation or answer text
 * @param {string} sessionId — current session for building local URLs
 * @returns {Array<{url: string, filename: string}>}
 */
function extractAllDocuments(text, sessionId) {
  if (!text) return [];
  const results = [];

  // ── Strategy 1: Parse JSON objects embedded in the text ──
  // The observation often contains raw JSON from the tool output
  const jsonBlocks = text.match(/\{[^{}]*"(?:download_url|file_path|draft_id)"[^{}]*\}/g) || [];
  for (const block of jsonBlocks) {
    try {
      const obj = JSON.parse(block);
      const draft_id = obj.draft_id || null;
      const format = obj.format || null;

      if (obj.download_url && obj.download_url.startsWith('http')) {
        const filename = obj.filename || extractFilenameFromUrl(obj.download_url) || `document.${format || 'pdf'}`;
        results.push({ url: obj.download_url, filename, draft_id, format });
      } else if (obj.file_path && sessionId) {
        const filename = obj.file_path.split(/[\\/]/).pop();
        results.push({
          url: `${AGENT_URL}/document/${sessionId}/${filename}`,
          filename,
          draft_id,
          format,
        });
      }
    } catch {
      // Not valid JSON, try next
    }
  }

  // Also try parsing the entire text as JSON
  try {
    const fullObj = JSON.parse(text.trim());
    const draft_id = fullObj.draft_id || null;
    const format = fullObj.format || null;
    if (fullObj.download_url && fullObj.download_url.startsWith('http')) {
      const filename = fullObj.filename || extractFilenameFromUrl(fullObj.download_url) || `document.${format || 'pdf'}`;
      if (!results.find(r => r.url === fullObj.download_url)) {
        results.push({ url: fullObj.download_url, filename, draft_id, format });
      }
    }
  } catch {
    // Not a JSON string
  }

  // ── Strategy 2: Match Cloudinary URLs directly ──
  // https://res.cloudinary.com/xxx/raw/upload/v123/nyayamitr/session/filename.pdf
  const cloudinaryUrls = text.match(/https?:\/\/res\.cloudinary\.com\/[^\s"'\]]+/g) || [];
  for (const url of cloudinaryUrls) {
    const filename = extractFilenameFromUrl(url);
    if (filename && !results.find(r => r.url === url)) {
      results.push({ url, filename });
    }
  }

  // ── Strategy 3: Match any http URL ending in document extensions ──
  const docUrls = text.match(/https?:\/\/[^\s"'\]]+\.(?:pdf|docx|txt)(?:\?[^\s"'\]]*)?\b/gi) || [];
  for (const url of docUrls) {
    const filename = extractFilenameFromUrl(url);
    if (filename && !results.find(r => r.url === url)) {
      results.push({ url, filename });
    }
  }

  // ── Strategy 4: Match local /document/ paths ──
  const localPaths = text.match(/\/document\/([a-f0-9]+)\/([^\s"']+)/g) || [];
  for (const path of localPaths) {
    const parts = path.match(/\/document\/([a-f0-9]+)\/(.+)/);
    if (parts) {
      const url = `${AGENT_URL}${path}`;
      if (!results.find(r => r.url === url)) {
        results.push({ url, filename: parts[2] });
      }
    }
  }

  // ── Strategy 5: Match "Download: URL" pattern the agent often uses ──
  const downloadMatches = text.match(/[Dd]ownload:\s*(https?:\/\/[^\s"'\]]+)/g) || [];
  for (const match of downloadMatches) {
    const url = match.replace(/[Dd]ownload:\s*/, '').trim();
    const filename = extractFilenameFromUrl(url) || 'document.pdf';
    if (!results.find(r => r.url === url)) {
      results.push({ url, filename });
    }
  }

  return results;
}

/**
 * Extract filename from a URL path.
 */
function extractFilenameFromUrl(url) {
  try {
    const pathname = new URL(url).pathname;
    const parts = pathname.split('/');
    const last = parts[parts.length - 1];
    // Decode and return if it looks like a filename
    const decoded = decodeURIComponent(last);
    if (decoded && decoded.includes('.')) return decoded;
    return null;
  } catch {
    // Fallback: just grab last segment
    const parts = url.split('/');
    return parts[parts.length - 1]?.split('?')[0] || null;
  }
}

/**
 * Call the Python agent's /export endpoint to generate a document
 * and upload it to Cloudinary, returning a public download_url.
 *
 * @param {string} sessionId
 * @param {string} draftId
 * @param {string} format  — 'pdf' | 'docx' | 'txt'
 * @returns {Promise<{download_url: string, filename: string} | null>}
 */
async function exportDocument(sessionId, draftId, format = 'pdf') {
  try {
    console.log(`[agentClient] Calling /export: session=${sessionId}, draft=${draftId}, format=${format}`);
    const res = await axios.post(`${AGENT_URL}/export`, {
      session_id: sessionId,
      draft_id: draftId,
      format,
    }, { timeout: 60000 });

    const { download_url, filename, storage } = res.data;
    console.log(`[agentClient] Export result: url=${download_url}, storage=${storage}`);
    return { download_url, filename, storage };
  } catch (err) {
    console.error(`[agentClient] Export failed: ${err.message}`);
    return null;
  }
}

/**
 * Ensure a document has a public URL that Twilio can access.
 * If the doc already has a Cloudinary URL, return it.
 * Otherwise, call /export to upload to Cloudinary.
 *
 * @param {object} doc       — { url, filename, draft_id?, format? }
 * @param {string} sessionId — agent session ID
 * @returns {Promise<string|null>} — public HTTPS URL or null
 */
async function ensurePublicUrl(doc, sessionId) {
  // Already a public Cloudinary URL
  if (doc.url && doc.url.startsWith('https://') && !doc.url.includes('localhost') && !doc.url.includes('ngrok')) {
    return doc.url;
  }

  // Try to re-export via /export to get a Cloudinary URL
  if (doc.draft_id) {
    const format = doc.format || (doc.filename?.split('.').pop()) || 'pdf';
    const result = await exportDocument(sessionId, doc.draft_id, format);
    if (result && result.download_url && result.download_url.startsWith('https://')) {
      return result.download_url;
    }
  }

  // Check session data for existing Cloudinary docs
  try {
    const sessionRes = await axios.get(`${AGENT_URL}/session/${sessionId}`);
    const sessionDocs = sessionRes.data.documents || [];
    for (const sdoc of sessionDocs) {
      if (sdoc.download_url && sdoc.download_url.startsWith('https://') && 
          (sdoc.filename === doc.filename || (doc.draft_id && sdoc.draft_id === doc.draft_id))) {
        return sdoc.download_url;
      }
    }
  } catch {
    // Session fetch failed, continue
  }

  return null;
}

/**
 * Transcribe an audio file (voice message) to text via the Python agent.
 *
 * @param {string} audioUrl    — URL to the audio file (Twilio media URL)
 * @param {string} language    — Language code (e.g., 'en', 'hi', 'mr')
 * @returns {Promise<{text: string, language: string}>}
 */
async function transcribeAudio(audioUrl, language = 'en') {
  try {
    console.log(`[agentClient] Transcribing audio: ${audioUrl.slice(0, 60)}...`);
    const res = await axios.post(`${AGENT_URL}/transcribe`, {
      audio_url: audioUrl,
      language,
      auth_user: process.env.TWILIO_ACCOUNT_SID,
      auth_pass: process.env.TWILIO_AUTH_TOKEN,
    }, { timeout: 60000 });

    console.log(`[agentClient] Transcription result: "${res.data.text?.slice(0, 80)}..."`);
    return res.data;
  } catch (err) {
    console.error('[agentClient] Transcription failed:', err.response?.data || err.message);
    throw new Error(`Transcription failed: ${err.message}`);
  }
}

module.exports = {
  chatWithAgent,
  createAgentSession,
  getDocumentUrl,
  extractAllDocuments,
  exportDocument,
  ensurePublicUrl,
  transcribeAudio,
};
