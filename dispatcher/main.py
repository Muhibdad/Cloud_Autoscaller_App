from fastapi import FastAPI, Request
from queue import Queue
import requests
import threading
import time
import uuid

# === Config ===
QUEUE_MAX_SIZE = 100
MODEL_URL = "http://resnet-service/infer"  # model service inside Kubernetes

app = FastAPI()

# In-memory queue and result store
task_queue = Queue(maxsize=QUEUE_MAX_SIZE)
result_store = {}  # Maps request ID to model prediction


@app.post("/enqueue")
async def enqueue(request: Request):
    """
    Accepts incoming requests, assigns a UUID, and adds them to the queue.
    """
    data = await request.json()
    if task_queue.full():
        return {"status": "dropped", "reason": "Queue is full"}

    request_id = str(uuid.uuid4())
    task = {"id": request_id, "data": data["data"]}
    task_queue.put(task)
    return {"status": "queued", "id": request_id}


@app.get("/result/{request_id}")
async def get_result(request_id: str):
    """
    Allows client to query for result using the request ID.
    """
    if request_id in result_store:
        return {"status": "done", "predictions": result_store[request_id]}
    else:
        return {"status": "pending"}


def send_img_payload_to_resnet_model():
    """
    Continuously fetches tasks from queue and forwards to resnet-ml-model.
    """
    while True:
        if not task_queue.empty():
            task = task_queue.get()
            try:
                request_id = task["id"]
                payload = {"data": task["data"]}

                response = requests.post(MODEL_URL, json=payload, timeout=5)

                if response.status_code == 200:
                    prediction = response.json()["predictions"]
                    print(f" Dispatched [{request_id}]: {prediction}")
                    result_store[request_id] = prediction
                else:
                    print(f" Model error ({request_id}):", response.status_code, response.text)

            except Exception as e:
                print(f" Failed to dispatch [{task.get('id')}]: {e}")
        else:
            time.sleep(0.1)


# Start background thread
threading.Thread(target=send_img_payload_to_resnet_model, daemon=True).start()
