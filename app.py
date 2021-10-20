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
    return "Success"

if __name__ == '__main__':
    app.run()
