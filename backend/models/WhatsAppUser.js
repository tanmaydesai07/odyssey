const mongoose = require('mongoose');

/**
 * WhatsAppUser — maps a WhatsApp phone number to a MongoDB User and
 * tracks which Case/session is currently active for that phone.
 *
 * When a message arrives from a phone number we haven't seen before,
 * we auto-create a User (with a placeholder email) and a WhatsAppUser record.
 */
const whatsAppUserSchema = new mongoose.Schema(
  {
    phoneNumber: {
      type: String,
      required: true,
      unique: true,
      index: true,
    },
    // Reference to the main User model (auto-created for WhatsApp users)
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: true,
    },
    // The currently active case _id for this phone
    activeCaseId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Case',
      default: null,
    },
    // Display name (from WhatsApp profile if available)
    displayName: {
      type: String,
      default: '',
    },
    // Preferred language detected or set by user
    language: {
      type: String,
      default: 'en',
    },
    // Total messages sent through WhatsApp
    totalMessages: {
      type: Number,
      default: 0,
    },
  },
  { timestamps: true }
);

module.exports = mongoose.model('WhatsAppUser', whatsAppUserSchema);
