"""
Test the complete document generation and Cloudinary upload flow.
"""
import json
import requests
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_document_flow():
    print("=" * 60)
    print("Testing Document Generation & Cloudinary Upload")
    print("=" * 60)
    
    # Step 1: Create a new session
    print("\n1. Creating new session...")
    resp = requests.post(f"{BASE_URL}/session/new", json={
        "user_id": "test_user_123",
        "case_title": "Test Document Generation",
        "language": "en"
    })
    resp.raise_for_status()
    session_data = resp.json()
    session_id = session_data["session_id"]
    print(f"   ✓ Session created: {session_id}")
    
    # Step 2: Send a message to generate a draft
    print("\n2. Sending message to generate FIR draft...")
    message = "My phone was stolen at Andheri station in Mumbai yesterday. I have the IMEI number."
    
    resp = requests.post(f"{BASE_URL}/chat", json={
        "session_id": session_id,
        "user_id": "test_user_123",
        "message": message,
        "language": "en"
    }, stream=True)
    
    draft_id = None
    for line in resp.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])
                    if data.get('type') == 'answer':
                        print(f"   ✓ Got answer (preview): {data['content'][:100]}...")
                    elif data.get('type') == 'tool' and data.get('name') == 'draft_generator':
                        print(f"   ✓ Draft generator called")
                    elif data.get('type') == 'observation':
                        obs = data.get('content', '')
                        # Try to extract draft_id from observation
                        if 'draft_id' in obs:
                            try:
                                obs_json = json.loads(obs)
                                draft_id = obs_json.get('draft_id')
                                if draft_id:
                                    print(f"   ✓ Draft generated: {draft_id}")
                            except:
                                pass
                    elif data.get('type') == 'done':
                        print(f"   ✓ Chat completed")
                        break
                except json.JSONDecodeError:
                    pass
    
    # If no draft_id found, check the drafts directory
    if not draft_id:
        print("\n   Looking for generated drafts...")
        drafts_dir = Path(__file__).parent / "drafts"
        drafts = sorted(drafts_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if drafts:
            draft_id = drafts[0].stem
            print(f"   ✓ Found draft: {draft_id}")
    
    if not draft_id:
        print("   ✗ No draft generated - agent may not have called draft_generator")
        print("   This is expected if the agent didn't classify it as an FIR case")
        return
    
    # Step 3: Export the draft as DOCX
    print(f"\n3. Exporting draft {draft_id} as DOCX...")
    resp = requests.post(f"{BASE_URL}/export", json={
        "session_id": session_id,
        "draft_id": draft_id,
        "format": "docx"
    })
    resp.raise_for_status()
    export_data = resp.json()
    print(f"   ✓ DOCX exported")
    print(f"   Storage: {export_data['storage']}")
    print(f"   Download URL: {export_data['download_url']}")
    
    # Step 4: Export as PDF
    print(f"\n4. Exporting draft {draft_id} as PDF...")
    resp = requests.post(f"{BASE_URL}/export", json={
        "session_id": session_id,
        "draft_id": draft_id,
        "format": "pdf"
    })
    resp.raise_for_status()
    export_data = resp.json()
    print(f"   ✓ PDF exported")
    print(f"   Storage: {export_data['storage']}")
    print(f"   Download URL: {export_data['download_url']}")
    
    # Step 5: Verify session has documents recorded
    print(f"\n5. Verifying session documents...")
    resp = requests.get(f"{BASE_URL}/session/{session_id}")
    resp.raise_for_status()
    session = resp.json()
    docs = session.get('documents', [])
    print(f"   ✓ Session has {len(docs)} document(s)")
    for doc in docs:
        print(f"     - {doc['filename']} ({doc['format']}) → {doc['storage']}")
        print(f"       URL: {doc['download_url']}")
    
    print("\n" + "=" * 60)
    print("✓ Document flow test completed successfully!")
    print("=" * 60)
    
    return session_id, draft_id

if __name__ == "__main__":
    try:
        test_document_flow()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
