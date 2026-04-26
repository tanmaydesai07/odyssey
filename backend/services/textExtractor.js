/**
 * textExtractor.js — Extract text from PDFs (native text + OCR) and images (OCR).
 *
 * Used by the chat endpoint to let users upload documents inline for
 * contract analysis, document review, etc.
 */

const { PDFParse } = require('pdf-parse');
const Tesseract = require('tesseract.js');
const path = require('path');
const fs = require('fs');

/**
 * Extract text from a PDF buffer.
 * Uses pdf-parse v2 class-based API.
 *
 * @param {Buffer} buffer — PDF file contents
 * @returns {Promise<{text: string, pages: number, method: string}>}
 */
async function extractFromPDF(buffer) {
  try {
    const parser = new PDFParse({ data: new Uint8Array(buffer) });
    await parser.load();
    
    let text = '';
    let pages = 0;
    try {
      const info = await parser.getInfo();
      pages = info?.numPages || info?.numpages || 0;
    } catch { /* info not critical */ }

    try {
      text = await parser.getText();
      if (typeof text !== 'string') text = String(text || '');
      text = text.trim();
    } catch (e) {
      console.error('[TextExtractor] getText failed:', e.message);
    }

    // Cleanup
    try { parser.destroy(); } catch {}

    if (text.length > 50) {
      return {
        text,
        pages: pages || 1,
        method: 'pdf-parse',
      };
    }

    return {
      text: text || '[PDF contained very little extractable text. It may be a scanned document — try uploading individual page images for OCR.]',
      pages: pages || 1,
      method: 'pdf-parse (low-text)',
    };
  } catch (err) {
    console.error('[TextExtractor] PDF parse error:', err.message);
    throw new Error(`PDF extraction failed: ${err.message}`);
  }
}

/**
 * Extract text from an image using Tesseract OCR.
 *
 * @param {Buffer} buffer — Image file contents
 * @param {string} lang   — Tesseract language code (default: 'eng')
 * @returns {Promise<{text: string, confidence: number, method: string}>}
 */
async function extractFromImage(buffer, lang = 'eng') {
  try {
    console.log(`[TextExtractor] Running OCR (lang=${lang})...`);
    const { data } = await Tesseract.recognize(buffer, lang, {
      logger: (m) => {
        if (m.status === 'recognizing text') {
          process.stdout.write(`\r[TextExtractor] OCR progress: ${Math.round(m.progress * 100)}%`);
        }
      },
    });
    console.log(''); // newline after progress

    const text = data.text?.trim() || '';
    console.log(`[TextExtractor] OCR complete: ${text.length} chars, confidence: ${Math.round(data.confidence)}%`);

    return {
      text: text || '[No text detected in the image.]',
      confidence: data.confidence,
      method: 'tesseract-ocr',
    };
  } catch (err) {
    console.error('[TextExtractor] OCR error:', err.message);
    throw new Error(`OCR extraction failed: ${err.message}`);
  }
}

/**
 * Detect file type and extract text accordingly.
 *
 * @param {Buffer} buffer       — File contents
 * @param {string} originalName — Original filename (for extension detection)
 * @param {string} mimeType     — MIME type from multer
 * @returns {Promise<{text: string, fileType: string, method: string, pages?: number, confidence?: number}>}
 */
async function extractText(buffer, originalName, mimeType) {
  const ext = path.extname(originalName || '').toLowerCase();

  // PDF
  if (mimeType === 'application/pdf' || ext === '.pdf') {
    const result = await extractFromPDF(buffer);
    return { ...result, fileType: 'pdf' };
  }

  // Images
  if (mimeType?.startsWith('image/') || ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'].includes(ext)) {
    // Map common language preferences to Tesseract codes
    const result = await extractFromImage(buffer, 'eng+hin');
    return { ...result, fileType: 'image' };
  }

  // Plain text files
  if (mimeType === 'text/plain' || ext === '.txt') {
    return {
      text: buffer.toString('utf-8'),
      fileType: 'text',
      method: 'direct',
    };
  }

  throw new Error(`Unsupported file type: ${mimeType || ext}`);
}

module.exports = { extractText, extractFromPDF, extractFromImage };
