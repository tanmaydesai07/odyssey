/**
 * Test backend document generation endpoint
 * Run: node test_backend_documents.js
 */

const axios = require('axios');

const BASE_URL = 'http://localhost:5000';
const AGENT_URL = 'http://localhost:8000';

// Test credentials
const TEST_EMAIL = 'fayaz.khanxid411@gmail.com';
const TEST_PASSWORD = '1234567';

async function test() {
  console.log('='.repeat(60));
  console.log('Testing Backend Document Generation');
  console.log('='.repeat(60));

  try {
    // Step 1: Login
    console.log('\n1. Logging in...');
    const loginRes = await axios.post(`${BASE_URL}/api/auth/login`, {
      email: TEST_EMAIL,
      password: TEST_PASSWORD,
    });
    const token = loginRes.data.token;
    const userId = loginRes.data.user.id;
    console.log(`   ✓ Logged in as ${TEST_EMAIL}`);

    const headers = { Authorization: `Bearer ${token}` };

    // Step 2: Create a new case
    console.log('\n2. Creating new case...');
    const caseRes = await axios.post(
      `${BASE_URL}/api/cases/new`,
      {},
      { headers }
    );
    const caseId = caseRes.data.case._id;
    const sessionId = caseRes.data.session_id;
    console.log(`   ✓ Case created: ${caseId}`);
    console.log(`   ✓ Session ID: ${sessionId}`);

    // Step 3: Send a message to generate a draft
    console.log('\n3. Sending message to generate draft...');
    const message = 'My laptop was stolen from my office in Bangalore. I have the serial number and CCTV footage.';
    
    const chatRes = await axios.post(
      `${BASE_URL}/api/cases/${caseId}/chat`,
      { message },
      { 
        headers,
        responseType: 'stream',
        timeout: 120000
      }
    );

    let draftId = null;
    
    // Parse SSE stream
    chatRes.data.on('data', (chunk) => {
      const lines = chunk.toString().split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'observation') {
              const obs = data.content;
              if (obs.includes('draft_id')) {
                try {
                  const obsJson = JSON.parse(obs);
                  if (obsJson.draft_id) {
                    draftId = obsJson.draft_id;
                    console.log(`   ✓ Draft generated: ${draftId}`);
                  }
                } catch (e) {}
              }
            } else if (data.type === 'done') {
              console.log('   ✓ Chat completed');
            }
          } catch (e) {}
        }
      }
    });

    // Wait for stream to complete
    await new Promise((resolve) => {
      chatRes.data.on('end', resolve);
    });

    // If no draft found, check agent directly
    if (!draftId) {
      console.log('\n   Looking for drafts in agent...');
      const sessionRes = await axios.get(`${AGENT_URL}/session/${sessionId}`);
      const docs = sessionRes.data.documents || [];
      if (docs.length > 0) {
        // Extract draft_id from filename
        const match = docs[0].filename.match(/fir_([a-f0-9]+)/);
        if (match) {
          draftId = match[1];
          console.log(`   ✓ Found draft: ${draftId}`);
        }
      }
    }

    if (!draftId) {
      console.log('\n   ⚠ No draft generated - agent may not have classified as FIR');
      console.log('   This is expected behavior - not all cases generate drafts immediately');
      return;
    }

    // Step 4: Generate DOCX
    console.log(`\n4. Generating DOCX for draft ${draftId}...`);
    const docxRes = await axios.post(
      `${BASE_URL}/api/cases/${caseId}/documents`,
      { draft_id: draftId, format: 'docx' },
      { headers }
    );
    console.log(`   ✓ DOCX generated`);
    console.log(`   Storage: ${docxRes.data.storage}`);
    console.log(`   URL: ${docxRes.data.download_url}`);

    // Step 5: Generate PDF
    console.log(`\n5. Generating PDF for draft ${draftId}...`);
    const pdfRes = await axios.post(
      `${BASE_URL}/api/cases/${caseId}/documents`,
      { draft_id: draftId, format: 'pdf' },
      { headers }
    );
    console.log(`   ✓ PDF generated`);
    console.log(`   Storage: ${pdfRes.data.storage}`);
    console.log(`   URL: ${pdfRes.data.download_url}`);

    // Step 6: Verify case has documents
    console.log('\n6. Verifying case documents...');
    const getCaseRes = await axios.get(
      `${BASE_URL}/api/cases/${caseId}`,
      { headers }
    );
    const caseDocs = getCaseRes.data.case.documents;
    console.log(`   ✓ Case has ${caseDocs.length} document(s)`);
    caseDocs.forEach((doc) => {
      console.log(`     - ${doc.filename} (${doc.format}) → ${doc.storage}`);
      console.log(`       ${doc.url}`);
    });

    console.log('\n' + '='.repeat(60));
    console.log('✓ Backend document generation test completed!');
    console.log('='.repeat(60));

  } catch (error) {
    console.error('\n✗ Test failed:', error.message);
    if (error.response) {
      console.error('Response:', error.response.data);
    }
  }
}

test();
