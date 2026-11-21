from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_and_get_support_requests(client: TestClient) -> None:
    # Create a conversation
    conv_res = client.post("/api/conversations", json={"title": "Thread per richieste"})
    conv_id = conv_res.json()["id"]

    # Register 2 requests
    req1_res = client.post(
        f"/api/conversations/{conv_id}/requests",
        json={
            "title": "Reset Password",
            "description": "L'utente non accede a Windows",
            "initial_category": "account",
        },
    )
    assert req1_res.status_code == 201
    req1_id = req1_res.json()["id"]

    req2_res = client.post(
        f"/api/conversations/{conv_id}/requests",
        json={
            "title": "Guasto Stampante",
            "description": "La stampante non risponde in rete",
            "initial_category": "hardware",
        },
    )
    assert req2_res.status_code == 201
    req2_id = req2_res.json()["id"]

    # List all requests
    list_res = client.get("/api/requests")
    assert list_res.status_code == 200
    list_data = list_res.json()

    assert list_data["total"] >= 2
    ids = [item["id"] for item in list_data["items"]]
    assert req1_id in ids
    assert req2_id in ids

    # Filter by status
    open_res = client.get("/api/requests?status=open")
    assert open_res.status_code == 200
    for item in open_res.json()["items"]:
        assert item["status"] == "open"

    # Get single request
    single_res = client.get(f"/api/requests/{req1_id}")
    assert single_res.status_code == 200
    assert single_res.json()["title"] == "Reset Password"
    assert single_res.json()["conversation_id"] == conv_id

    # 404 for nonexistent request
    not_found = client.get("/api/requests/nonexistent_req_404")
    assert not_found.status_code == 404
