FROM python:3.12-slim
WORKDIR /app
ENV PYTHONPATH=/app/src PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY src/ /app/src/
COPY .actor/build-manifest.json /app/build-manifest.json
USER 65534:65534
CMD ["python", "-m", "beanfit.apify_actor"]
