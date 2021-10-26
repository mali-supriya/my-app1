# -*- coding: utf-8 -*-
"""
Created on Wed Oct 20 12:01:00 2021

@author: malis
"""

import json
from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route('/api',methods=['POST'])
def index():
    record = json.loads(request.data)
    schedule_id=record["schedule_id"]
    TOKEN=record["X-AUTH-TOKEN"]
    headers = {"X-AUTH-TOKEN": TOKEN}
    callback_url_input = record["callback_url_input"]
    #response = requests.get(callback_url_input,headers=headers)
    #print(response.json())
    #callback_url_output = record["callback_url_output"]
    #headers['Content-Type']='application/json'
    #json_path = r"outputjson.json"
    #f = open(json_path,)
    #data = json.load(f)
    #data = json.dumps(data)
    #response = requests.post(callback_url_output, data=data, headers=headers)
    #print(response.text)
    return type(callback_url_input)

if __name__ == '__main__':
    app.run()
