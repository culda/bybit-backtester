FROM python:3.9.2-buster

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p logs trades hist_data

ENTRYPOINT ["python3" , "main.py", "2021-02-02", "2021-03-10"]