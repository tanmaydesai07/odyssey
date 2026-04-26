/**
 * twilioMenu.js — Creates and caches a Twilio Content Template for the
 * interactive WhatsApp menu (list-picker).
 *
 * After each agent response, we send this as a follow-up message so the
 * user sees a "📋 Menu" button they can tap to start a new chat, switch
 * cases, or get help.
 */

const axios = require('axios');

const CONTENT_API = 'https://content.twilio.com/v1/Content';

let _menuContentSid = null;

/**
 * Get or create the interactive menu content template.
 * Returns the Content SID which can be used with Twilio Messages API.
 */
async function getMenuContentSid() {
  if (_menuContentSid) return _menuContentSid;

  const sid = process.env.TWILIO_ACCOUNT_SID;
  const token = process.env.TWILIO_AUTH_TOKEN;

  if (!sid || !token) {
    console.error('[TwilioMenu] Missing Twilio credentials');
    return null;
  }

  try {
    // Check if we already created one (search by friendly_name)
    const listRes = await axios.get(CONTENT_API, {
      auth: { username: sid, password: token },
    });

    const existing = listRes.data.contents?.find(
      (c) => c.friendly_name === 'nyayamitr_main_menu'
    );

    if (existing) {
      _menuContentSid = existing.sid;
      console.log(`[TwilioMenu] Using existing template: ${_menuContentSid}`);
      return _menuContentSid;
    }

    // Create a new list-picker content template
    const createRes = await axios.post(
      CONTENT_API,
      {
        friendly_name: 'nyayamitr_main_menu',
        language: 'en',
        variables: {},
        types: {
          'twilio/list-picker': {
            body: '🏛️ *NyayaMitr* — What would you like to do next?',
            button: '📋 Menu',
            items: [
              {
                id: 'new_chat',
                item: '🆕 New Conversation',
                description: 'Start a fresh legal case',
              },
              {
                id: 'my_cases',
                item: '📋 My Cases',
                description: 'View and switch between your cases',
              },
              {
                id: 'get_help',
                item: '❓ Help',
                description: 'See available commands',
              },
            ],
          },
        },
      },
      {
        auth: { username: sid, password: token },
        headers: { 'Content-Type': 'application/json' },
      }
    );

    _menuContentSid = createRes.data.sid;
    console.log(`[TwilioMenu] Created template: ${_menuContentSid}`);
    return _menuContentSid;
  } catch (err) {
    console.error('[TwilioMenu] Failed to create template:', err.response?.data || err.message);
    return null;
  }
}

/**
 * Initialize the menu template on startup.
 * Call this once when the server starts.
 */
async function initMenu() {
  const sid = await getMenuContentSid();
  if (sid) {
    console.log(`[TwilioMenu] ✅ Menu template ready: ${sid}`);
  } else {
    console.log('[TwilioMenu] ⚠️ Menu template not available, falling back to text menu');
  }
}

module.exports = { getMenuContentSid, initMenu };
