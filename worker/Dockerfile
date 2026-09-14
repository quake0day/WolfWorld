FROM pytorch/pytorch:2.7.1-cuda12.8-cudnn9-devel
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 MAX_JOBS=4 TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0" WORLDMIRROR_REPO=/opt/HY-World-2.0 WOLFWORLD_DATA=/data
RUN apt-get update && apt-get install -y --no-install-recommends git ffmpeg libgl1 libglib2.0-0 build-essential ninja-build && rm -rf /var/lib/apt/lists/*
ARG WORLDMIRROR_COMMIT=df9988efb87bfc0f4947eb3889411cf957478b06
RUN git clone https://github.com/Tencent-Hunyuan/HY-World-2.0.git /opt/HY-World-2.0 && git -C /opt/HY-World-2.0 checkout "$WORLDMIRROR_COMMIT"
WORKDIR /opt/HY-World-2.0
# Use the wheel with bundled CUDA runtime rather than building CuPy from source.
RUN sed '/^cupy==/d' requirements.txt > /tmp/worldmirror-requirements.txt && pip install --no-cache-dir -r /tmp/worldmirror-requirements.txt cupy-cuda12x==13.6.0
RUN pip install --no-cache-dir --no-build-isolation gsplat==1.5.3 flash-attn==2.8.3
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY engine.py server.py /app/
EXPOSE 8788
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8788"]
