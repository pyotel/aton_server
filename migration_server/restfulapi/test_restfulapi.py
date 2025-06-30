#!/usr/bin/python3
#-*- encoding: utf-8 -*-
import paho.mqtt.client as mqtt

mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(username="keti", password="keti1234")
mqtt_client.connect("106.247.250.251", 31883)

if __name__ == '__main__':
    cmd = 1
    comm = "miot"
    if comm == "ais" or comm == "miot" :
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
    print(ret_str)