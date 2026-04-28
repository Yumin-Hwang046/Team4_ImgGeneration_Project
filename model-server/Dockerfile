FROM pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn Pillow python-dotenv openai "diffusers==0.32.2" "transformers==4.44.2" accelerate rembg onnxruntime numpy "xformers==0.0.26.post1"

COPY backend/image_generator/ ./image_generator/
COPY backend/text_generator/ ./text_generator/
COPY model-server/main.py ./main.py

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
