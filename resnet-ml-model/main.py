from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from torchvision.models import resnet18, ResNet18_Weights
import torch
import base64
from PIL import Image
import io
import numpy as np
import time

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram

app = FastAPI()

# Prometheus metrics
inference_counter = Counter("inference_requests_total", "Total inference requests")

# Updated buckets for better percentile tracking (especially p99)
inference_duration = Histogram(
    "http_request_duration_seconds",
    "Histogram of inference durations in seconds",
    buckets=(0.005, 0.01, 0.02, 0.03, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 2, 5)
)

# Preprocessing
preprocessor = ResNet18_Weights.IMAGENET1K_V1.transforms()
torch.set_num_threads(1)
torch.set_num_interop_threads(1)

# Load the model
resnet_model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
resnet_model.eval()

# Inference logic
def infer(d):
    decoded = base64.b64decode(d["data"])
    img = Image.open(io.BytesIO(decoded))
    img = np.array(preprocessor(img))
    img = torch.from_numpy(np.array([img]))

    preds = resnet_model(img)
    labels = [
        ResNet18_Weights.IMAGENET1K_V1.meta["categories"][i]
        for i in preds[0].topk(5).indices
    ]
    return labels

# Inference endpoint
@app.post("/infer")
async def infer_handler(request: Request):
    inference_counter.inc()
    payload = await request.json()
    with inference_duration.time():  # Tracks request duration for histogram
        result = infer(payload)
    return JSONResponse(content={"predictions": result})

# Prometheus metrics endpoint
@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
