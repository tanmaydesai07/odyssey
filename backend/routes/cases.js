const express = require('express');
const axios = require('axios');
const FormData = require('form-data');
const multer = require('multer');
const Case = require('../models/Case');
const { protect } = require('../middleware/auth');

const router = express.Router();
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 10 * 1024 * 1024 } }); // 10MB

const AGENT_URL = process.env.AGENT_URL || 'http://localhost:8000';

// ─── GET /api/cases ───────────────────────────────────────────────────────────
// List all cases for the logged-in user
router.get('/', protect, async (req, res) => {
  try {
    const cases = await Case.find({ userId: req.user.id, status: 'active' })
      .sort({ lastMessageAt: -1 })
      .select('-__v');

    res.json({ cases });
  } catch (err) {
    console.error('List cases error:', err.message);
    res.status(500).json({ message: 'Server error' });
  }
});

// ─── POST /api/cases/new ──────────────────────────────────────────────────────
// Create a new case (creates session in Python agent)
router.post('/new', protect, async (req, res) => {
  try {
    // Call Python agent to create session
    const agentRes = await axios.post(`${AGENT_URL}/session/new`, {
      user_id: req.user.id,
    });

    const { session_id } = agentRes.data;

    // Save to MongoDB
    const newCase = await Case.create({
      userId: req.user.id,
      sessionId: session_id,
      title: 'New case',
    });

    res.status(201).json({
      case: newCase,
      session_id,
    });
  } catch (err) {
    console.error('Create case error:', err.message);
    res.status(500).json({ message: 'Failed to create case' });
  }
});

// ─── GET /api/cases/:id ───────────────────────────────────────────────────────
// Get a specific case by MongoDB _id
router.get('/:id', protect, async (req, res) => {
  try {
    const caseDoc = await Case.findOne({
      _id: req.params.id,
      userId: req.user.id,
    });

    if (!caseDoc) {
      return res.status(404).json({ message: 'Case not found' });
    }

    // Fetch full session data from Python agent
    const agentRes = await axios.get(`${AGENT_URL}/session/${caseDoc.sessionId}`);

    res.json({
      case: caseDoc,
      session: agentRes.data,
    });
  } catch (err) {
    console.error('Get case error:', err.message);
    res.status(500).json({ message: 'Server error' });
  }
});

// ─── POST /api/cases/:id/chat ─────────────────────────────────────────────────
// Send a message to the agent for this case
router.post('/:id/chat', protect, async (req, res) => {
  const { message } = req.body;

  if (!message || !message.trim()) {
    return res.status(400).json({ message: 'Message is required' });
  }

  try {
    const caseDoc = await Case.findOne({
      _id: req.params.id,
      userId: req.user.id,
    });

    if (!caseDoc) {
      return res.status(404).json({ message: 'Case not found' });
    }

    // Forward to Python agent
    const agentRes = await axios.post(
      `${AGENT_URL}/chat`,
      {
        session_id: caseDoc.sessionId,
        user_id: req.user.id,
        message: message.trim(),
      },
      {
        responseType: 'stream',
        timeout: 120000, // 2 minutes
      }
    );

    // Update case metadata
    caseDoc.messageCount += 1;
    caseDoc.lastMessageAt = new Date();

    // Auto-generate title from first message if still "New case"
    if (caseDoc.title === 'New case' && caseDoc.messageCount === 1) {
      caseDoc.title = message.trim().slice(0, 60);
    }

    await caseDoc.save();

    // Stream the agent's response back to frontend
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    agentRes.data.pipe(res);
  } catch (err) {
    console.error('Chat error:', err.message);
    if (!res.headersSent) {
      res.status(500).json({ message: 'Chat failed' });
    }
  }
});

// ─── DELETE /api/cases/:id ────────────────────────────────────────────────────
// Delete a case (soft delete)
router.delete('/:id', protect, async (req, res) => {
  try {
    const caseDoc = await Case.findOne({
      _id: req.params.id,
      userId: req.user.id,
    });

    if (!caseDoc) {
      return res.status(404).json({ message: 'Case not found' });
    }

    caseDoc.status = 'deleted';
    await caseDoc.save();

    res.json({ message: 'Case deleted' });
  } catch (err) {
    console.error('Delete case error:', err.message);
    res.status(500).json({ message: 'Server error' });
  }
});

// ─── POST /api/cases/:id/documents ────────────────────────────────────────────
// Generate a document for this case
router.post('/:id/documents', protect, async (req, res) => {
  const { draft_id, format } = req.body;

  try {
    const caseDoc = await Case.findOne({
      _id: req.params.id,
      userId: req.user.id,
    });

    if (!caseDoc) {
      return res.status(404).json({ message: 'Case not found' });
    }

    // Call Python agent to export document
    const agentRes = await axios.post(`${AGENT_URL}/export`, {
      session_id: caseDoc.sessionId,
      draft_id,
      format: format || 'docx',
    });

    const { download_url, filename, storage } = agentRes.data;

    // Save document metadata to case
    caseDoc.documents.push({
      filename,
      format: format || 'docx',
      url: download_url,
      storage: storage || 'local',
      generatedAt: new Date(),
    });
    await caseDoc.save();

    res.json({
      message: 'Document generated',
      filename,
      download_url,  // Direct Cloudinary URL or local path
      storage,
    });
  } catch (err) {
    console.error('Generate document error:', err.message);
    res.status(500).json({ message: 'Failed to generate document' });
  }
});

// ─── GET /api/cases/:id/documents/:filename ───────────────────────────────────
// Download a generated document
router.get('/:id/documents/:filename', protect, async (req, res) => {
  try {
    const caseDoc = await Case.findOne({
      _id: req.params.id,
      userId: req.user.id,
    });

    if (!caseDoc) {
      return res.status(404).json({ message: 'Case not found' });
    }

    const doc = caseDoc.documents.find((d) => d.filename === req.params.filename);
    if (!doc) {
      return res.status(404).json({ message: 'Document not found' });
    }

    // Proxy download from Python agent
    const agentRes = await axios.get(
      `${AGENT_URL}/document/${caseDoc.sessionId}/${req.params.filename}`,
      { responseType: 'stream' }
    );

    res.setHeader('Content-Type', agentRes.headers['content-type']);
    res.setHeader('Content-Disposition', `attachment; filename="${req.params.filename}"`);

    agentRes.data.pipe(res);
  } catch (err) {
    console.error('Download document error:', err.message);
    res.status(500).json({ message: 'Download failed' });
  }
});

// ─── POST /api/cases/:id/evidence ─────────────────────────────────────────────
// Upload an evidence file (proxies to Python agent)
router.post('/:id/evidence', protect, upload.single('file'), async (req, res) => {
  try {
    const caseDoc = await Case.findOne({ _id: req.params.id, userId: req.user.id });
    if (!caseDoc) return res.status(404).json({ message: 'Case not found' });
    if (!req.file) return res.status(400).json({ message: 'No file provided' });

    // Build multipart form for Python agent
    const form = new FormData();
    form.append('file', req.file.buffer, {
      filename: req.file.originalname,
      contentType: req.file.mimetype,
    });

    const agentRes = await axios.post(
      `${AGENT_URL}/upload/${caseDoc.sessionId}`,
      form,
      { headers: form.getHeaders(), timeout: 30000 }
    );

    res.json({
      message: 'Evidence uploaded',
      ...agentRes.data,
    });
  } catch (err) {
    console.error('Upload evidence error:', err.message);
    res.status(500).json({ message: 'Upload failed' });
  }
});

// ─── GET /api/cases/:id/evidence ──────────────────────────────────────────────
// List uploaded evidence files for this case
router.get('/:id/evidence', protect, async (req, res) => {
  try {
    const caseDoc = await Case.findOne({ _id: req.params.id, userId: req.user.id });
    if (!caseDoc) return res.status(404).json({ message: 'Case not found' });

    const agentRes = await axios.get(`${AGENT_URL}/session/${caseDoc.sessionId}`);
    const uploads = agentRes.data.uploads || [];

    res.json({ uploads });
  } catch (err) {
    console.error('List evidence error:', err.message);
    res.status(500).json({ message: 'Failed to list evidence' });
  }
});

// ─── GET /api/cases/:id/evidence/:filename ────────────────────────────────────
// Download an evidence file (proxies from Python agent)
router.get('/:id/evidence/:filename', protect, async (req, res) => {
  try {
    const caseDoc = await Case.findOne({ _id: req.params.id, userId: req.user.id });
    if (!caseDoc) return res.status(404).json({ message: 'Case not found' });

    const agentRes = await axios.get(
      `${AGENT_URL}/upload/${caseDoc.sessionId}/${req.params.filename}`,
      { responseType: 'stream' }
    );

    res.setHeader('Content-Type', agentRes.headers['content-type'] || 'application/octet-stream');
    res.setHeader('Content-Disposition', `attachment; filename="${req.params.filename}"`);
    agentRes.data.pipe(res);
  } catch (err) {
    console.error('Download evidence error:', err.message);
    res.status(500).json({ message: 'Download failed' });
  }
});

// ─── POST /api/cases/:id/extract-text ─────────────────────────────────────────
// Upload a file and extract text from it (PDF text extraction + image OCR).
// Returns extracted text that the frontend can prepend to the user's message.
const { extractText } = require('../services/textExtractor');

router.post('/:id/extract-text', protect, upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ message: 'No file provided' });
    }

    const { originalname, mimetype, buffer, size } = req.file;
    console.log(`[Extract] Processing: ${originalname} (${mimetype}, ${(size / 1024).toFixed(0)} KB)`);

    // Call python agent for robust OCR (PyMuPDF + Tesseract)
    const form = new FormData();
    form.append('file', buffer, { filename: originalname, contentType: mimetype });
    
    const extractRes = await axios.post(`${AGENT_URL}/extract-text`, form, {
        headers: form.getHeaders(),
        timeout: 60000 // OCR can be slow
    });
    
    const result = extractRes.data;

    console.log(`[Extract] Done: ${result.textLength} chars via ${result.method}`);

    // Also upload to evidence hub in background (non-blocking)
    const caseDoc = await Case.findById(req.params.id);
    if (caseDoc && caseDoc.sessionId) {
      const agentForm = new FormData();
      agentForm.append('file', buffer, { filename: originalname, contentType: mimetype });
      axios.post(`${AGENT_URL}/upload/${caseDoc.sessionId}`, agentForm, {
        headers: agentForm.getHeaders(),
        timeout: 15000,
      }).catch(() => {}); // silent
    }

    res.json(result);
  } catch (err) {
    const errorMsg = err.response?.data?.detail || err.message;
    console.error('[Extract] Error:', errorMsg);
    res.status(500).json({ message: errorMsg || 'Text extraction failed' });
  }
});

module.exports = router;
