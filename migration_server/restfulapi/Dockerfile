FROM python:3.13.0
RUN apt-get update -y
RUN apt-get install -y python3-pip python3-dev build-essential
WORKDIR /app
COPY . .
RUN pip3 install -r ./requirements.txt
ENTRYPOINT ["python3"]
CMD ["/app/restfulapi.py"]