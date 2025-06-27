# ResNet Kubernetes Autoscaling Application 🧠🚀

This project implements a scalable image classification service using a ResNet18 model deployed on Kubernetes. It leverages FastAPI for serving inference, Prometheus for monitoring, and a custom Python-based autoscaler to adjust the number of model replicas based on incoming traffic.

---

## 📦 Project Structure

```
.
├── autoscaller/         # Custom autoscaler (Python)
├── dispatcher/          # FastAPI dispatcher service
├── load_tester/         # Script to generate load
├── model/               # ResNet18 inference service
├── prometheus/          # Prometheus config, deployment, service
├── images/              # Sample images used for testing
├── requirements.txt     # Python dependencies
```

---

## 🚀 How to Run the Project (on Minikube via WSL Ubuntu)

### ⚙️ Requirements

- WSL2 (Ubuntu)
- Python 3.10+
- Docker
- Minikube (with Docker driver)
- `kubectl` CLI
- Prometheus Client (`pip install prometheus_client`)

---

### 1️⃣ Start Minikube

```
minikube start
```

---

### 2️⃣ Configure Docker to use Minikube's daemon

```
eval $(minikube docker-env)
```

---

### 3️⃣ Build Docker Images

```
cd model
docker build -t resnet-inference:latest .

cd ../dispatcher
docker build -t dispatcher:latest .
```

---

### 4️⃣ Apply Kubernetes Manifests

```
kubectl apply -f model/
kubectl apply -f dispatcher/
```

---

### 5️⃣ Deploy Prometheus

```
kubectl apply -f prometheus/
kubectl port-forward svc/prometheus-service 9090:9090
```

Visit Prometheus at: http://localhost:9090

---

### 6️⃣ Start the Autoscaler

```
cd autoscaller
python3 autoscaller.py
```

It queries Prometheus for metrics and scales ResNet pods accordingly.

---

### 7️⃣ Run Load Generator to Trigger Autoscaling

```
cd load_tester
python3 load_tester.py
```

This sends many image classification requests to the dispatcher.

---

## 📊 Prometheus Metrics

Metrics exposed by the model pod at `/metrics`:
- `inference_requests_total` – custom counter
- standard Python/HTTP/CPU metrics (if enabled)

Prometheus scrape config:

```yaml
scrape_configs:
  - job_name: 'resnet-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: resnet
```

---

## 🧠 Autoscaling Logic

The autoscaler monitors:
- CPU usage per pod (`container_cpu_usage_seconds_total`)
- Number of inference requests (`inference_requests_total`)

It adjusts the number of replicas for the `resnet-inference` deployment dynamically.

---

## ✅ How to Reset After Reboot

```
minikube start
eval $(minikube docker-env)
kubectl apply -f model/
kubectl apply -f dispatcher/
kubectl apply -f prometheus/
kubectl port-forward svc/prometheus-service 9090:9090
python3 autoscaller/autoscaller.py
python3 load_tester/load_tester.py
```


## 🧪 Tested On

- Ubuntu 24.04 (via WSL2)
- Minikube v1.36.0
- Docker 28+
- Python 3.12
