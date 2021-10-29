# -*- coding: utf-8 -*-
"""
Created on Fri Oct 29 17:00:36 2021
@author: malis
"""
import flask
app = flask.Flask("after_response")
import traceback
from werkzeug.wsgi import ClosingIterator
from flask import request
import json
import requests
import pandas as pd
from mip_optimization import Optimization

class AfterResponse:
    def __init__(self, app=None):
        self.callbacks = []
        if app:
            self.init_app(app)

    def __call__(self, callback):
        self.callbacks.append(callback)
        return callback

    def init_app(self, app):
        # install extension
        app.after_response = self

        # install middleware
        app.wsgi_app = AfterResponseMiddleware(app.wsgi_app, self)

    def flush(self):
        for fn in self.callbacks:
            try:
                fn()
            except Exception:
                traceback.print_exc()

class AfterResponseMiddleware:
    def __init__(self, application, after_response_ext):
        self.application = application
        self.after_response_ext = after_response_ext

    def __call__(self, environ, after_response):
        iterator = self.application(environ, after_response)
        try:
            return ClosingIterator(iterator, [self.after_response_ext.flush])
        except Exception:
            traceback.print_exc()
            return iterator
        

AfterResponse(app)
@app.after_response
def optimize():
    print(record)
    schedule_id=record["schedule_id"]
    TOKEN=record["auth_token"]
    headers = {"X-AUTH-TOKEN": TOKEN}
    callback_url_input = record["callback_url_input"]
    callback_url_input = callback_url_input+"?id="+str(schedule_id)
    response = requests.get(callback_url_input,headers=headers)
    data=response.json()
    print(data["status"])
    if data["status"]==200:
        get_all_status = r"http://api.sciffer.com/musicschedulerreferences/api/1/status/getall"
        #TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMiIsInRlbmFudF9pZCI6IjIiLCJuYmYiOjE2MzQyMDExNDAsImV4cCI6MTYzNjc5MzE0MCwiaWF0IjoxNjM0MjAxMTQwfQ.iCPRaFLFXmxky0vHO18zYeYJZ9fR_zKt8X1WOdAtFZg"
        headers = {"X-AUTH-TOKEN": TOKEN}
        response = requests.get(get_all_status,headers=headers)
        all_status=pd.DataFrame(response.json()["data"]['status'])
        sch_hist = len(data['scheduleData']["schedule_history"])
        lines = ["request received-"+str(schedule_id)]
        with open('readme.txt', 'a') as f:
            f.writelines('\n'.join(lines)+ '\n')
        Optimization(data,sch_hist,all_status,schedule_id,headers)
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

@app.route('/api',methods=['POST'])
def main():
    global record
    record = json.loads(request.data)
    return "Success"

if __name__ == '__main__':
    app.run()