# Runs the dashboard, and gives the notebook and the SQL loader a pinned environment.
#
# The image deliberately does NOT contain Fraud.csv: it is 471 MB, licensed separately,
# and only load_sqlite.py and the notebook need it. Mount it at run time when you want
# to rebuild the aggregates; the dashboard reads the small tracked CSVs and needs nothing.

FROM python:3.10-slim

# Keep the image quiet and reproducible.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first, so a source edit does not invalidate the install layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Streamlit's default port. Bind to every interface or the container is unreachable.
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/healthz')"

CMD ["streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true"]
