#!/usr/bin/python3
# -*- encoding: utf-8 -*-

# http://ketiict.com:31020/ 로 접근

from flask import Flask, request, render_template, send_from_directory, jsonify, send_file
import pandas as pd
import paho.mqtt.client as mqtt
import os
import time
from datetime import datetime
from collections import defaultdict, OrderedDict
from threading import Thread
from PIL import Image
import re
from werkzeug.utils import secure_filename
from io import BytesIO
from influxdb import InfluxDBClient
import pytz
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import numpy as np
import zipfile
import io


app = Flask(__name__)

mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(username="keti", password="keti1234")
mqtt_client.connect("106.247.250.251", 31883)

# 이미지 디렉토리 경로 설정
IMAGE_DIRECTORY = './img/'

UPLOAD_FOLDER = './img/'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

MAX_FILES = 100000

def manage_directory():
    while True:
        files = [os.path.join(IMAGE_DIRECTORY, f) for f in os.listdir(IMAGE_DIRECTORY) if os.path.isfile(os.path.join(IMAGE_DIRECTORY, f))]
        if len(files) > MAX_FILES:
            # 파일 생성 시간을 기준으로 정렬 (오래된 파일이 앞에 오도록)
            files.sort(key=lambda x: os.path.getctime(x))
            # 오래된 파일 삭제
            files_to_delete = files[:len(files) - MAX_FILES]
            for file in files_to_delete:
                os.remove(file)
        time.sleep(600)  # 10분마다 확인

# 쓰레드 시작
thread = Thread(target=manage_directory)
thread.daemon = True
thread.start()

def extract_numbers(filename):
    numbers = re.findall(r'\d+', filename)
    return "_".join(numbers) if numbers else ""

def is_mostly_black(image, threshold=0.9):
    # 이미지를 numpy 배열로 변환하여 검은색 비율 계산
    grayscale_image = image.convert("L")
    pixels = np.array(grayscale_image)
    black_pixels = np.sum(pixels < 50)  # 50 미만을 검은색으로 간주
    total_pixels = pixels.size
    black_ratio = black_pixels / total_pixels
    return black_ratio > threshold


def camera_log_influxdb_write(dic_data : dict) :
    influxdb_handle = InfluxDBClient(INFLUX_HOST, INFLUX_PORT, 'root', 'keti1234', "sensors_data")
    measurement = "log_camera"
    loc = dic_data.pop("region", "")
    dict_tags = {
        "loc" : loc
    }    
    json_body = [
        {
            "measurement": measurement,
            "tags": dict_tags,
            "fields": dic_data
        }
    ]
    influxdb_handle.write_points(json_body)

@app.route('/upload', methods=['POST', 'GET'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    loc = request.args.get('loc', default='unknown')       

    if file:
        try:
            current_time = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:-3]
            original_filename = secure_filename(file.filename)
            numbers = extract_numbers(original_filename)
            if numbers:
                new_filename = f"{current_time}_{numbers}.jpg"
            else:
                new_filename = f"{current_time}.jpg"
                
            if loc != "unknown":
                target_dir = os.path.join(app.config['UPLOAD_FOLDER'], loc)
                os.makedirs(target_dir, exist_ok=True)
                file_path = os.path.join(target_dir, new_filename)
            else:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            
            # 파일을 열고 0도 회전
            image = Image.open(file)
            rotated_image = image.rotate(0)
            
            # 검은색 비율 체크
            if is_mostly_black(rotated_image):
                return jsonify({'message': 'Image is mostly black, not saved'}), 400
            
            rotated_image.save(file_path)

            dic_log_data = {}
            dic_log_data["region"] = loc
            dic_log_data["filename"] = new_filename
            dic_log_data["filepath"] = file_path
            dic_log_data["url"] = "http://ketiict.com:31020/download?filename=" + new_filename + "&loc=" + loc
            camera_log_influxdb_write(dic_log_data)
            return jsonify({'message': 'File uploaded and rotated successfully', 'file_path': file_path}), 200
        
        except Exception as e:
            return jsonify({'message': 'File processing error', 'error': str(e)}), 500

@app.route('/download', methods=['GET'])
def download_file():
    filename = request.args.get('filename')
    loc = request.args.get('loc', default='unknown')

    if not filename:
        return jsonify({'message': 'filename parameter is required'}), 400

    # 파일 경로 구성
    if loc != 'unknown':
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], loc, filename)
    else:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # 파일 존재 여부 확인 후 다운로드
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({'message': 'File not found'}), 404



@app.route('/img')
def show_images():
    from collections import defaultdict
    channels = request.args.get('channel', '1,2,3,4').split(',')
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

    image_files = [f for f in os.listdir(IMAGE_DIRECTORY) if os.path.isfile(os.path.join(IMAGE_DIRECTORY, f))]

    time_groups = defaultdict(dict)  # {(timestamp_floor): {channel: image}}

    for image in image_files:
        file_path = os.path.join(IMAGE_DIRECTORY, image)
        creation_time = os.path.getctime(file_path)
        dt = datetime.fromtimestamp(creation_time)
        image_date = dt.strftime('%Y-%m-%d')
        if image_date != selected_date:
            continue

        # 시간 기준을 2분 단위로 자르기 (floor)
        timestamp_group = dt.replace(second=0, microsecond=0, minute=(dt.minute // 2) * 2)

        # 채널 파싱
        channel_number = image.rsplit('_', 1)[-1].split('.')[0]
        if channel_number in channels:
            time_groups[timestamp_group][channel_number] = image

    # 시간 기준으로 정렬
    sorted_groups = OrderedDict(sorted(time_groups.items(), reverse=True))

    return render_template('images.html', grouped_images=sorted_groups, selected_date=selected_date)


@app.route('/img/all')
def show_all_images_by_date():
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

    image_files = [f for f in os.listdir(IMAGE_DIRECTORY) if os.path.isfile(os.path.join(IMAGE_DIRECTORY, f))]

    # (파일명, 생성시간) 목록을 담을 리스트
    filtered_images = []
    for image in image_files:
        file_path = os.path.join(IMAGE_DIRECTORY, image)
        creation_time = os.path.getctime(file_path)
        dt = datetime.fromtimestamp(creation_time)
        image_date = dt.strftime('%Y-%m-%d')

        if image_date == selected_date:
            filtered_images.append((image, creation_time))

    # 시간 기준으로 정렬
    sorted_images = sorted(filtered_images, key=lambda x: x[1])

    return render_template('images_all.html', images=sorted_images, selected_date=selected_date)

@app.route('/download-images')
def download_images():
    img_folder = os.path.join(IMAGE_DIRECTORY)
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(img_folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, img_folder)
                zipf.write(file_path, arcname)

    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name='images.zip'
    )

@app.route('/img/<filename>')
def send_image(filename):
    return send_from_directory(IMAGE_DIRECTORY, filename)

@app.route('/light_cmd')
def sim_start():
    if request.method == "GET":
        cmd = request.args.get('cmd','0')
        comm = request.args.get('comm','ais')
        if comm in ["ais", "miot"]:
            topic = "center2comm/"+ comm +"/light/cmd"
        elif comm == "lte":
            topic = "comm2aton/light/cmd"
        dict_msg = dict()
        dict_msg["measurement"] = "light_cmd"
        dict_msg["val"] = str(cmd)
        dict_msg["net"] = str(comm)
        
        mqtt_client.publish(topic, str(dict_msg))
        
        ret_str = "topic : " + topic + "  <br/>"
        ret_str += str(dict_msg)
        return ret_str
    return "null"


INFLUX_HOST = "106.247.250.251"
INFLUX_PORT = 31886

client = InfluxDBClient(INFLUX_HOST, INFLUX_PORT, 'root', 'keti1234', "sensors_data")

@app.route('/csv')
def csv():
    return render_template('csv_down.html')

@app.route('/download-data', methods=['GET'])
def download_data():
    # 요청에서 측정값(measurement)와 날짜 범위를 가져옴
    measurement = request.args.get('measurement')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # 입력 값 유효성 검사
    if not measurement or not start_date or not end_date:
        return "Error: Please provide measurement, start_date, and end_date parameters.", 400
    
    try:
        # KST 타임존 설정
        kst = pytz.timezone('Asia/Seoul')
        
        # 입력된 날짜를 KST로 해석하고 UTC로 변환
        start_datetime_kst = kst.localize(datetime.strptime(start_date, "%Y-%m-%d"))
        end_datetime_kst = kst.localize(datetime.strptime(end_date, "%Y-%m-%d"))
        
        # UTC로 변환
        start_datetime_utc = start_datetime_kst.astimezone(pytz.utc)
        end_datetime_utc = end_datetime_kst.astimezone(pytz.utc)
        
    except ValueError:
        return "Error: Dates must be in YYYY-MM-DD format.", 400
    
    # InfluxQL 쿼리 생성 (UTC 시간 사용)
    query = f'''
    SELECT * FROM "{measurement}"
    WHERE time >= '{start_datetime_utc.isoformat()}' AND time <= '{end_datetime_utc.isoformat()}'
    '''
    print(query)
    
    # InfluxDB 클라이언트 설정 (연결 설정 필요)
    client = InfluxDBClient(INFLUX_HOST, INFLUX_PORT, 'root', 'keti1234', "sensors_data")
    
    # 쿼리 실행
    result = client.query(query)
    
    # 결과를 DataFrame으로 변환
    points = list(result.get_points())
    if not points:
        return "No data found for the specified date range and measurement.", 404
    
    df = pd.DataFrame(points)
    
    # UTC 시간을 KST로 변환
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'])  # 시간 문자열을 datetime으로 변환
        df['time'] = df['time'].dt.tz_convert('Asia/Seoul')  # UTC -> KST 변환
    
    # DataFrame을 CSV로 변환
    csv_buffer = BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    
    # CSV 파일 반환
    return send_file(csv_buffer, as_attachment=True, download_name=f'{measurement}_data.csv', mimetype='text/csv')



@app.route('/measurements', methods=['GET'])
def list_measurements():
    # InfluxQL 쿼리를 통해 measurements 조회
    query = 'SHOW MEASUREMENTS'
    result = client.query(query)
    
    # measurements 리스트 생성
    measurements = [measurement['name'] for measurement in result.get_points()]
    
    # JSON 형식으로 반환
    return jsonify(measurements)

@app.route('/alert')
def alert():
    return render_template('set_alert.html')

# SMTP 설정
SMTP_SERVER = 'your_smtp_server'
SMTP_PORT = 587
SMTP_USERNAME = 'your_email@example.com'
SMTP_PASSWORD = 'your_email_password'

def send_email_alert(to_email, subject, message):
    msg = MIMEMultipart()
    msg['From'] = SMTP_USERNAME
    msg['To'] = to_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(message, 'plain'))
    
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)

@app.route('/set-alert', methods=['POST'])
def set_alert():
    measurement = request.form.get('measurement')
    field = request.form.get('field')
    condition = request.form.get('condition')
    threshold = float(request.form.get('threshold'))
    email = request.form.get('email')
    
    if not measurement or not field or not condition or not threshold or not email:
        return "Error: All fields are required.", 400

    # InfluxQL 쿼리 생성
    query = f'''
    SELECT "{field}" FROM "{measurement}"
    ORDER BY time DESC LIMIT 1
    '''
    
    result = client.query(query)
    points = list(result.get_points())
    
    if not points:
        return "No data found for the specified measurement and field.", 404
    
    latest_value = points[0][field]

    # 알림 조건 확인
    if (condition == 'above' and latest_value > threshold) or (condition == 'below' and latest_value < threshold):
        subject = f"Alert: {measurement} {field} is {condition} {threshold}"
        message = f"The latest value of {field} in {measurement} is {latest_value}, which is {condition} your threshold of {threshold}."
        send_email_alert(email, subject, message)
        return "Alert triggered and email sent.", 200
    else:
        return "Condition not met, no alert sent.", 200

@app.route('/fields', methods=['GET'])
def list_fields():
    measurement = request.args.get('measurement')
    
    if not measurement:
        return jsonify([])

    query = f'SHOW FIELD KEYS FROM "{measurement}"'
    result = client.query(query)
    
    fields = [field['fieldKey'] for field in result.get_points()]
    
    return jsonify(fields)


@app.route('/dtm')
def dtm():
    query = """
    SELECT * FROM "dtm"
    WHERE time > now() - 10m
    """
    result = client.query(query)
    loc_measurements = {}

    if result:
        points = list(result.get_points())
        for point in points:
            loc = point["loc"]
            measurement = point["measurement"]
            if loc not in loc_measurements:
                loc_measurements[loc] = {}
            if measurement == "overall_status":
                loc_measurements[loc]["overall_status"] = point["status"]
            else:
                loc_measurements[loc][measurement] = point["has_data"]

    return render_template('dtm.html', loc_measurements=loc_measurements)

@app.route('/', methods=['GET'])
def list_templates():
    """
    템플릿을 사용하는 모든 라우트와 해당 템플릿 파일 이름을 반환합니다.
    """
    template_routes = [
        {'route': '/img', 'template': 'images.html'},
        {'route': '/csv', 'template': 'csv_down.html'},
        {'route': '/alert', 'template': 'set_alert.html'},
        {'route': '/dtm', 'template': 'dtm.html'}
    ]
    return render_template('index.html', routes=template_routes)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
