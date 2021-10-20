# -*- coding: utf-8 -*-
"""
Created on Wed Oct 20 12:01:00 2021

@author: malis
"""

from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/test')
def index():
    return jsonify({"message": "Music Scheduling"})

if __name__ == '__main__':
    app.run()