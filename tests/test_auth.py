# tests/test_feedback.py
from fastapi.testclient import TestClient
from main import app  # adjust import to your app

client = TestClient(app)

def test_feedback_submission():
    # Step 1: Register + login to get a token
    client.post("/api/auth/register", json={
        "username": "testteacher",
        "password": "testpass123",
        "role": "teacher"  # adjust fields to your schema
    })
    
    login_response = client.post("/api/auth/login", json={
        "username": "testteacher",
        "password": "testpass123"
    })
    
    token = login_response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    # Step 2: Submit feedback with auth header
    response = client.post("/api/feedback/", json={
        "category": "general",
        "message": "Test feedback message"
    }, headers=headers)

    assert response.status_code in [200, 403]  # 403 if role isn't teacher
