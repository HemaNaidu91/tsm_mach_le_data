import requests
import time


BASE_URL = "http://localhost:8000"  # backend service


def wait_for_service(url, timeout=60):
    for _ in range(timeout):
        try:
            r = requests.get(url)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError(f"Service not ready: {url}")


def test_full_recommendation_flow():

    # wait for backend
    wait_for_service(f"{BASE_URL}/api/version")

    payload = [
        {"movie_id": 1, "rating": 4.0},
        {"movie_id": 2, "rating": 3.5}
    ]

    response = requests.post(
        f"{BASE_URL}/api/recommendation/predict",
        json=payload
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert "movie_id" in data[0]
    assert "predicted_rating" in data[0]
