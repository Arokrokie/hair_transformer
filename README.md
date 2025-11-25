## Deploying on Render

This repository contains an AI-backed Django app. Some dependencies (PyTorch, CUDA-enabled packages) can cause conflicts when Render installs packages on CPU-only build machines. Follow the steps below to deploy reliably on Render using CPU PyTorch wheels.

Recommended Render Build Command

- In your Render service settings, set the **Build Command** to the following (copy-paste):

```bash
pip install -U pip
# Install CPU-only PyTorch + torchvision from the official PyTorch wheel index
pip install "torch==2.9.0+cpu" "torchvision==0.24.0+cpu" -f https://download.pytorch.org/whl/torch_stable.html
# Then install the rest of dependencies
pip install -r requirements.txt
```

Notes

- I removed `bitsandbytes` from `requirements.txt` to avoid GPU/CUDA-only package failures on CPU Render instances. If you need `bitsandbytes` (or other GPU-specific packages), deploy to a GPU-enabled host or use a separate `requirements.gpu.txt` used only on GPU machines.
- Some packages may still have loose torch requirements. Pre-installing CPU PyTorch before `pip install -r requirements.txt` prevents pip from pulling CUDA variants and their large NVIDIA wheel dependencies.
- If you plan to use GPU on Render, contact Render support for GPU-enabled instances or deploy to a GPU provider (AWS/GCP/Azure/Gradient/Paperspace) and keep `bitsandbytes`, `triton`, etc. in a GPU requirements file.

Quick local test

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

If you want, I can also create a `requirements.cpu.txt` (trimmed) and a `requirements.gpu.txt` (full) to make deployments explicit. Tell me which you prefer.

---

Generated guidance by the project maintainer assistant.
