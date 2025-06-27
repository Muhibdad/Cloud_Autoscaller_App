import os
import base64
import random
import requests
import time
import threading

# === CONFIG ===
IMAGE_FOLDER = "./images"
ENQUEUE_URL = "http://192.168.49.2:31239/enqueue"
RESULT_URL = "http://192.168.49.2:31239/result"
POLL_INTERVAL = 1  # seconds between polling result
MAX_WAIT_TIME = 20  # seconds to wait for result
CONCURRENCY = 5  # Number of parallel threads
REQUESTS_PER_THREAD = 20  # Requests per thread
DELAY_BETWEEN_REQUESTS = 0.2  # seconds between requests per thread
# ==============

def encode_random_image():
    files = [f for f in os.listdir(IMAGE_FOLDER) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    if not files:
        raise FileNotFoundError("No image files found in folder.")
    file_path = os.path.join(IMAGE_FOLDER, random.choice(files))
    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return {"data": b64}, os.path.basename(file_path)

def send_request():
    for _ in range(REQUESTS_PER_THREAD):
        try:
            payload, filename = encode_random_image()
            print(f"📤 Sending image: {filename}")
            response = requests.post(ENQUEUE_URL, json=payload)
            if response.status_code != 200:
                print("❌ Enqueue failed:", response.text)
                continue

            response_data = response.json()
            request_id = response_data.get("id")
            if not request_id:
                print("❌ No request ID returned.")
                continue

            start = time.time()
            while time.time() - start < MAX_WAIT_TIME:
                result_resp = requests.get(f"{RESULT_URL}/{request_id}")
                if result_resp.status_code == 200:
                    result_data = result_resp.json()
                    if "predictions" in result_data:
                        print("✅ Prediction:", result_data["predictions"])
                        break
                time.sleep(POLL_INTERVAL)
            else:
                print("⏰ Timed out waiting for prediction.")

        except Exception as e:
            print("❌ Exception during request:", e)

        time.sleep(DELAY_BETWEEN_REQUESTS)

def main():
    print(f"🚀 Starting load with {CONCURRENCY} threads...")
    threads = []
    for _ in range(CONCURRENCY):
        t = threading.Thread(target=send_request)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    print("✅ Load test complete.")

if __name__ == "__main__":
    main()
