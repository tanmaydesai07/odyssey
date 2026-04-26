require('dotenv').config();
const express = require('express');
const cors = require('cors');
const mongoose = require('mongoose');

const authRoutes = require('./routes/auth');
const casesRoutes = require('./routes/cases');
const whatsappRoutes = require('./routes/whatsapp');

const app = express();

// Middleware
app.use(cors({ origin: ['http://localhost:5173', 'http://localhost:5174'], credentials: true }));
app.use(express.json());
app.use(express.urlencoded({ extended: false })); // Twilio sends form-urlencoded

// Routes
app.use('/api/auth', authRoutes);
app.use('/api/cases', casesRoutes);
app.use('/api/whatsapp', whatsappRoutes);

// Health check
app.get('/api/health', (req, res) => res.json({ status: 'ok' }));

// Connect to MongoDB then start server
const PORT = process.env.PORT || 5000;

mongoose
  .connect(process.env.MONGO_URI)
  .then(() => {
    console.log('MongoDB connected');
    app.listen(PORT, () => {
      console.log(`Server running on port ${PORT}`);

      // Initialize WhatsApp interactive menu template (non-blocking)
      const { initMenu } = require('./services/twilioMenu');
      initMenu().catch((err) => console.error('[TwilioMenu] Init error:', err.message));
    });
  })
  .catch((err) => {
    console.error('MongoDB connection error:', err.message);
    process.exit(1);
  });
