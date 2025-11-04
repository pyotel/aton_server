#!/usr/bin/python3
#-*- encoding: utf-8 -*-

import paho.mqtt.client as mqtt
import json
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError
import datetime
import argparse
import re
import os

parser = argparse.ArgumentParser(description='')
parser.add_argument('--local', required=False, help='JETSON에서 테스트로 바로 실행 시킬 때 1 입력', default="0")
args = parser.parse_args()
MIOT_TEST_MODE = int(args.local)

TOPIC = "comm2center/#"

MQTT_HOST = os.getenv('MQTT_HOST', "mosquitto")
MQTT_PORT = int(os.getenv('MQTT_PORT', "1883"))
miot_args_json_path = "./miot_args.json"
   
INFLUX_HOST = os.getenv('INFLUX_HOST', "106.247.250.251")
INFLUX_PORT = int(os.getenv('INFLUX_PORT', "31886"))

print(f"[INFO] MQTT Configuration: {MQTT_HOST}:{MQTT_PORT}")
print(f"[INFO] InfluxDB Configuration: {INFLUX_HOST}:{INFLUX_PORT}")

def get_field_types(measurement, influxdb_handle):
    field_types = {}
    query = f'SHOW FIELD KEYS FROM "{measurement}"'
    result = influxdb_handle.query(query)
    for item in result.get_points():
        field_name = item['fieldKey']
        field_type = item['fieldType']
        field_types[field_name] = field_type
    return field_types

def cast_to_field_type(field_name, value, field_types):
    # field_types 딕셔너리에 해당 필드가 있으면, db의 타입에 맞게 변환
    if field_name in field_types:
        field_type = field_types[field_name]
        try:
            if field_type == 'float':
                return float(value)
            elif field_type == 'integer':
                return int(float(value))  # int로 변환 전에 float로 한 번 변환(문자열 '1.0' 등 처리)
            elif field_type == 'boolean':
                # influxdb boolean은 True/False 또는 1/0으로 저장됨
                if str(value).lower() in ['true', '1']:
                    return True
                elif str(value).lower() in ['false', '0']:
                    return False
                else:
                    return bool(value)
            else:
                return value  # string 등 기타 타입은 그대로 반환
        except Exception as e:
            # 변환 실패 시 원래 값 반환
            return value
    else:
        return value

def log_influxdb_write(dic_data : dict) :
    influxdb_handle = InfluxDBClient(INFLUX_HOST, INFLUX_PORT, 'root', 'keti1234', "sensors_data")
    measurement = "log_network"
    loc = dic_data.pop("region", "")
    dict_tags = {
        "host": dic_data.pop("host", ""),
        "net" : dic_data.pop("net", ""),
        "loc" : loc,
        "location" : loc,
    }    
    json_body = [
        {
            "measurement": measurement,
            "tags": dict_tags,
            "fields": dic_data
        }
    ]
    influxdb_handle.write_points(json_body)

def influxdb_write(dbname, dic_data : dict):
    measurement = dic_data.pop("measurement", "none").replace("/","_")
    if measurement == "none" :
        print("ERROR!! Measurement is none")
        print(dic_data)
        return
    
    
    influxdb_handle = InfluxDBClient(INFLUX_HOST, INFLUX_PORT, 'root', 'keti1234', dbname)
    
    field_types = get_field_types(measurement, influxdb_handle)
    loc = dic_data.pop("region", "")
    dict_tags = {
        "host": dic_data.pop("host", ""),
        "net" : dic_data.pop("net", ""),
        "loc" : loc,
        "location" : loc,
    }
    token = dic_data.pop("token", "")
    if token : dict_tags["token"] = token
    
    if "container_name" in dic_data : dict_tags["contname"] = dic_data.get("container_name", "none")
    
    # BMSSerialNo를 태그로 처리
    if "BMSSerialNo" in dic_data:
        dict_tags["BMSSerialNo"] = dic_data.pop("BMSSerialNo")
    
    # cam_parsed measurement에 대한 기본 필드 추가
    if measurement == "cam_vp":
        default_fields = {
            "significant_wave_height": 0.0,
            "average_wave_height": 0.0,
            "maximum_wave_height": 0.0,
            "collision": int(0)
        }
        for field, default_value in default_fields.items():
            if field not in dic_data:
                dic_data[field] = default_value
    
    for field_name in dic_data.keys():
        field_value = cast_to_field_type(field_name, dic_data[field_name], field_types)
        dic_data[field_name] = field_value

    json_body = [
        {
            "measurement": measurement,
            "tags": dict_tags,
            "fields": dic_data
        }
    ]
    try:
        influxdb_handle.write_points(json_body)
    except Exception as e:
        print(f"ERROR: InfluxDB에 데이터 쓰기 실패 - {e}")


        
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe(TOPIC)


previous_time = datetime.datetime.now()
miot_args_dict = {}
miot_val_list = []
miot_msg = ""
miot_ss_start = False
def on_message(client, userdata, msg):
    global previous_time
    global miot_msg
    global miot_val_list
    global miot_ss_start
    
    def network_stat_write(host, msg_str, region, net_str):
        global previous_time
        current_time = datetime.datetime.now()
        previous_time = current_time
        dict_net_data = {
            "measurement": "network",
            "rx_size" : len(msg_str),
            "host" : host,
            "net" : net_str,
            "region" : region
        }
        if net_str == "miot" :
            print(dict_net_data)
        influxdb_write(dbname="sensors_data", dic_data=dict_net_data)
            
    net = ""
    if "miot" in msg.topic : net = "miot"
    elif "lte" in msg.topic : net = "lte"
    elif "ais" in msg.topic  :
        net = "ais"
        print("========AIS msg. is arrived.=========")
        dic_ais_log_data = {}
        dic_ais_log_data["net"] = "ais"
        dic_ais_log_data["msg"] = msg.payload.decode('utf-8')
        network_stat_write(data.get("host", "none"), msg_str, data.get("region", "none"), dic_ais_log_data)
        log_influxdb_write(dic_ais_log_data)
        
    if net == "miot" :
        print(msg.topic+" "+str(msg.payload))
        recv_msg =  msg.payload.decode('utf-8')
        network_stat_write("keti", recv_msg, "yeosu", "miot")
        
        ss_index = recv_msg.find("S")
        ee_index = recv_msg.find("E")
        
        if ss_index != -1:
            miot_msg = recv_msg[ss_index + 2:]
            miot_ss_start = True
        elif ss_index == -1 and ee_index == -1:
            miot_msg += recv_msg
        elif ee_index != -1 :
            if miot_ss_start == True :
                miot_ss_start = False
                miot_msg += recv_msg[:ee_index]
                print(miot_msg)
                miot_msg_val_list = miot_msg.split(",")
                ss_index = -1
                ee_index = -1
                
                for meas_key in miot_args_dict.keys() :
                    fields_key_list = miot_args_dict[meas_key]
                    field_dict = {}
                    field_dict["sensor_name"] = meas_key
                    field_dict["measurement"] = "sensor_" + meas_key
                    field_dict["net"] = "miot"
                    for field_key in fields_key_list :
                        if len(miot_msg_val_list) > 0 :
                            field_dict[field_key] = miot_msg_val_list.pop(0)
                            try:
                                field_dict[field_key] = float(field_dict[field_key])
                            except ValueError:
                                pass
                        else : 
                            print("[ERR] miot_msg_val_list is empty")
                            field_dict[field_key] = 0
                            if field_key == "host" : field_dict[field_key] = "none"
                    miot_val_list.append(field_dict)
                
                print(miot_val_list)
                for dic_data in miot_val_list :
                    try :
                        influxdb_write(dbname="sensors_data", dic_data=dic_data)
                    except Exception as e:
                        print("An error occurred: ", e)
                miot_val_list.clear()
            else :
                print("miot msg without \'S\' is thrown away ")
                miot_msg = ""

    else :
        msg_str = msg.payload.decode()
        msg_str = msg_str.replace("'", '"')

        try:
            data = json.loads(msg_str)
            for net_str in ["ais", "lte"] :
                if net_str in msg.topic :
                    data["net"] = net_str
                    break
            if data["net"] == "ais" :
                print("ais")
                print(data)
            
            network_stat_write(data.get("host", "none"), msg_str, data.get("region", "none"), data["net"])
            influxdb_write(dbname="sensors_data", dic_data=data)
            
        except ValueError as e:
            print("Error parsing JSON: ", e)
            print("Error Message received: " + msg.payload.decode())


if __name__ == "__main__" :

    with open(miot_args_json_path, 'r') as file:
        data = json.load(file)
        for item in data:
            miot_args_dict[item['name']] = item['fields']
    print(miot_args_dict)
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.username_pw_set(username="keti", password="keti1234")
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_forever()
