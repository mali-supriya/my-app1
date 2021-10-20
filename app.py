# -*- coding: utf-8 -*-
"""
Created on Wed Oct 20 12:01:00 2021

@author: malis
"""

from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({"message": "hello world"})

if __name__ == '__main__':
    app.run()