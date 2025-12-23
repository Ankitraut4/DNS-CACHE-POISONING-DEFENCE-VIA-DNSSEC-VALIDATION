#!/usr/bin/env python3
from flask import Flask, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return send_file('index.html')

if __name__ == '__main__':
    print("=" * 60)
    print("🏦 REAL WEBSITE - Running on 10.0.1.20:80")
    print("=" * 60)
    app.run(host='0.0.0.0', port=80, debug=False)
