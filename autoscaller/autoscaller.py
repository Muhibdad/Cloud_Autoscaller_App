import requests
import time
import math
import os

PROMETHEUS_URL = "http://192.168.49.2:30090"
DEPLOYMENT_NAME = "resnet-inference"
NAMESPACE = "default"

# Target rate (inferences/sec) per pod before scaling up
TARGET_RPS_PER_POD = 0.5
MAX_REPLICAS = 5
MIN_REPLICAS = 1
CHECK_INTERVAL = 15  # seconds

def get_request_rate():
    try:
        query = 'rate(inference_requests_total[1m])'
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query})
        data = response.json()
        result = data["data"]["result"]
        if result:
            rate = float(result[0]["value"][1])
            print(f"📈 Current request rate: {rate:.3f} req/sec")
            return rate
        else:
            print("ℹ️ No traffic yet.")
            return 0.0
    except Exception as e:
        print("❌ Failed to get request rate from Prometheus:", e)
        return None

def get_current_replicas():
    try:
        result = os.popen(f"kubectl get deployment {DEPLOYMENT_NAME} -n {NAMESPACE} -o jsonpath='{{.spec.replicas}}'").read()
        return int(result.strip())
    except Exception as e:
        print("❌ Failed to get current replicas:", e)
        return None

def scale_to(replicas):
    try:
        os.system(f"kubectl scale deployment {DEPLOYMENT_NAME} --replicas={replicas} -n {NAMESPACE}")
        print(f"✅ Scaled to {replicas} replicas.")
    except Exception as e:
        print("❌ Failed to scale:", e)

def autoscale():
    print("🚀 Starting autoscaler...")
    while True:
        rate = get_request_rate()
        if rate is None:
            time.sleep(CHECK_INTERVAL)
            continue

        current_replicas = get_current_replicas()
        if current_replicas is None:
            time.sleep(CHECK_INTERVAL)
            continue

        desired_replicas = max(MIN_REPLICAS, min(MAX_REPLICAS, math.ceil(rate / TARGET_RPS_PER_POD)))

        if desired_replicas != current_replicas:
            print(f"🔄 Scaling from {current_replicas} to {desired_replicas} replicas...")
            scale_to(desired_replicas)
        else:
            print(f"✅ Desired replicas ({desired_replicas}) already running.")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    autoscale()
