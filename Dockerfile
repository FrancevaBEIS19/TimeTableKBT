FROM python:3.9

WORKDIR /timetablekbt

COPY requirements.txt /timetablekbt/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /timetablekbt/requirements.txt

COPY . /timetablekbt

CMD ["python", "main.py"]
