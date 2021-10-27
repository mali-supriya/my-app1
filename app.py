import json
import pyscipopt
import requests
from flask import Flask, request, jsonify
from mip_optimization import Optimization
app = Flask(__name__)

@app.route('/api',methods=['POST'])
def index():
    try:
        record = json.loads(request.data)
        schedule_id=record["schedule_id"]
        TOKEN=record["X-AUTH-TOKEN"]
        headers = {"X-AUTH-TOKEN": TOKEN}
        callback_url_input = record["callback_url_input"]
        callback_url_input = callback_url_input+"?id="+str(schedule_id)
        response = requests.get(callback_url_input,headers=headers)
        data=response.json()
        sch_hist = len(data['scheduleData']["schedule_history"])
        Optimization(data,sch_hist)
        #callback_url_output = record["callback_url_output"]
        #headers['Content-Type']='application/json'
        #json_path = r"output.json"
        #f = open(json_path,)
        #data = json.load(f)
        #output = json.dumps(data)
        #response = requests.post(callback_url_output, data=output, headers=headers)
        #print(response.text)
        return 'success', 200
    except:
        'bad request!', 400
if __name__ == '__main__':
    app.run()
