import json
from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({"message": "hello world"})

if __name__ == '__main__':
    app.run()
