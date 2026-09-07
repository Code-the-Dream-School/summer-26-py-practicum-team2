FROM python:3.11-slim

WORKDIR /app

COPY services/dashboard/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/dashboard/server.py ./server.py

ENV DASHBOARD_HOST=0.0.0.0
ENV DASHBOARD_PORT=8000
EXPOSE 8000

CMD ["python", "server.py"]
