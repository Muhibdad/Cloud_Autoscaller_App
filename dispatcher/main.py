# from fastapi import FastAPI, Request
# from queue import Queue
# import requests
# import threading
# import time

# # Create FastAPI app
# app = FastAPI()

# # Configuration
# QUEUE_MAX_SIZE = 100
# MODEL_URL = "http://resnet-service/infer"  # Kubernetes service for your model

# # Create a fixed-size in-memory queue
# task_queue = Queue(maxsize=QUEUE_MAX_SIZE)

# @app.post("/enqueue")
# async def enqueue(request: Request):
#     """
#     Accepts incoming image classification requests and adds them to the queue.
#     If the queue is full, the request is dropped.
#     """
#     data = await request.json()
#     if task_queue.full():
#         return {"status": "dropped", "reason": "Queue is full"}
#     task_queue.put(data)
#     return {"status": "queued"}

# def dispatch_worker():
#     """
#     Background worker that pulls items from the queue and forwards them to the model service.
#     This simulates load balancing, and decouples load from the model.
#     """
#     while True:
#         if not task_queue.empty():
#             request_data = task_queue.get()
#             try:
#                 response = requests.post(MODEL_URL, json=request_data, timeout=5)
#                 if response.status_code == 200:
#                     print("✅ Dispatched: ", response.json()["predictions"])
#                 else:
#                     print("❌ Error:", response.status_code)
#             except Exception as e:
#                 print("❌ Failed to dispatch:", e)
#         else:
#             time.sleep(0.1)  # avoid busy-looping when queue is empty

# # Start the background dispatcher thread when app launches
# threading.Thread(target=dispatch_worker, daemon=True).start()


from fastapi import FastAPI, Request
from queue import Queue
import requests
import threading
import time
import uuid

# === Config ===
QUEUE_MAX_SIZE = 100
MODEL_URL = "http://resnet-service/infer"  # model service inside Kubernetes
# ==============

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


def dispatch_worker():
    """
    Continuously fetches tasks from queue and forwards to model.
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
                    print(f"✅ Dispatched [{request_id}]: {prediction}")
                    result_store[request_id] = prediction
                else:
                    print(f"❌ Model error ({request_id}):", response.status_code, response.text)

            except Exception as e:
                print(f"❌ Failed to dispatch [{task.get('id')}]: {e}")
        else:
            time.sleep(0.1)


# Start background thread
threading.Thread(target=dispatch_worker, daemon=True).start()
