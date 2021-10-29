import json
import pyscipopt
import requests
import pandas as pd
from flask import Flask, request, jsonify
from mip_optimization import Optimization
app = Flask(__name__)

@app.route('/api',methods=['POST'])
def index():
    try:
        record = json.loads(request.data)
        print(record)
        schedule_id=record["schedule_id"]
        TOKEN=record["X-AUTH-TOKEN"]
        headers = {"X-AUTH-TOKEN": TOKEN}
        callback_url_input = record["callback_url_input"]
        callback_url_input = callback_url_input+"?id="+str(schedule_id)
        response = requests.get(callback_url_input,headers=headers)
        data=response.json()
        print(data["status"])
        if data["status"]==200:
            get_all_status = r"http://api.sciffer.com/musicschedulerreferences/api/1/status/getall"
            TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMiIsInRlbmFudF9pZCI6IjIiLCJuYmYiOjE2MzQyMDExNDAsImV4cCI6MTYzNjc5MzE0MCwiaWF0IjoxNjM0MjAxMTQwfQ.iCPRaFLFXmxky0vHO18zYeYJZ9fR_zKt8X1WOdAtFZg"
            headers = {"X-AUTH-TOKEN": TOKEN}
            response = requests.get(get_all_status,headers=headers)
            all_status=pd.DataFrame(response.json()["data"]['status'])
            sch_hist = len(data['scheduleData']["schedule_history"])
            lines = ["request received-"+str(schedule_id)]
            with open('readme.txt', 'a') as f:
                f.writelines('\n'.join(lines)+ '\n')
            status_id = Optimization(data,sch_hist,all_status,schedule_id,headers)
            lines = ["model run completed-"+str(schedule_id)]
            with open('readme.txt', 'a') as f:
                f.writelines('\n'.join(lines)+ '\n')
            try:
                callback_url_output = record["callback_url_output"]
                headers['Content-Type']='application/json'
                json_path = r"output.json"
                f = open(json_path,)
                data = json.load(f)
                output = json.dumps(data)
                response = requests.post(callback_url_output, data=output, headers=headers)
                lines = ["request completed-"+str(schedule_id)]
                print(response.text)
                with open('readme.txt', 'a') as f:
                    f.writelines('\n'.join(lines)+ '\n')  
            except:
                print("Infeasible")
            return 'success', 200
        else:
            'bad request!', 400    
    except: 
        'bad request!', 400

        
if __name__ == '__main__':
    app.run()