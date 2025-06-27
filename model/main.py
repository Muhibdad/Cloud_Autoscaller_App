from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from torchvision.models import resnet18, ResNet18_Weights
import torch
import base64
from PIL import Image
import io
import numpy as np
import time

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter

app = FastAPI()

# Prometheus metric
inference_counter = Counter("inference_requests_total", "Total inference requests")

# Preprocessing
preprocessor = ResNet18_Weights.IMAGENET1K_V1.transforms()
torch.set_num_threads(1)
torch.set_num_interop_threads(1)

resnet_model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
resnet_model.eval()

def infer(d):
    t = time.perf_counter()
    decoded = base64.b64decode(d["data"])
    img = Image.open(io.BytesIO(decoded))
    img = np.array(preprocessor(img))
    img = torch.from_numpy(np.array([img]))
    preds = resnet_model(img)
    labels = [
        ResNet18_Weights.IMAGENET1K_V1.meta["categories"][i]
        for i in preds[0].topk(5).indices
    ]
    print("⏱️ Inference took:", round(time.perf_counter() - t, 3), "s")
    return labels

@app.post("/infer")
async def infer_handler(request: Request):
    inference_counter.inc()
    payload = await request.json()
    result = infer(payload)
    return JSONResponse(content={"predictions": result})

@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
