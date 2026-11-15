FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY pk_rewriter ./pk_rewriter
COPY web ./web
RUN pip install --no-cache-dir -e . && useradd --create-home --uid 10001 app
USER app
ENV OLLAMA_URL=http://ollama:11434
EXPOSE 8000
CMD ["uvicorn", "pk_rewriter.api:app", "--host", "0.0.0.0", "--port", "8000"]
