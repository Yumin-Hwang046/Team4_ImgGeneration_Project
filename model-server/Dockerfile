FROM pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi uvicorn \
    "diffusers==0.27.2" "transformers==4.40.2" accelerate \
    Pillow python-dotenv openai

COPY backend/image_generator/ ./image_generator/
COPY backend/text_generator/ ./text_generator/
COPY model-server/main.py ./main.py

ENV PYTHONPATH=/app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
