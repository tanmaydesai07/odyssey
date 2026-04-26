const mongoose = require('mongoose');

const caseSchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: true,
      index: true,
    },
    sessionId: {
      type: String,
      required: true,
      unique: true,
      index: true,
    },
    title: {
      type: String,
      default: 'New case',
    },
    caseType: {
      type: String,
      enum: ['fir', 'consumer_complaint', 'rti', 'labour_complaint', 'legal_notice', 'other'],
      default: 'other',
    },
    status: {
      type: String,
      enum: ['active', 'archived', 'deleted'],
      default: 'active',
    },
    messageCount: {
      type: Number,
      default: 0,
    },
    documents: [
      {
        filename: String,
        format: String, // 'docx', 'pdf', 'txt'
        url: String,    // Cloudinary URL or local path
        storage: String, // 'cloudinary' or 'local'
        generatedAt: Date,
      },
    ],
    lastMessageAt: {
      type: Date,
      default: Date.now,
    },
  },
  { timestamps: true }
);

// Index for efficient queries
caseSchema.index({ userId: 1, status: 1, lastMessageAt: -1 });

module.exports = mongoose.model('Case', caseSchema);
