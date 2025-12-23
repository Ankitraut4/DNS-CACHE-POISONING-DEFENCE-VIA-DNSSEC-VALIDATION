# DNS Cache Poisoning Lab with Real & Fake Websites

This lab demonstrates DNS cache poisoning attacks with actual websites - showing how attackers can redirect users from legitimate sites to fake phishing sites.

## 🏗️ Architecture

### Components:
1. **Real Website** (10.0.1.20:80) - Legitimate banking website
2. **Fake Website** (10.0.100.100:80) - Phishing/malicious copy
3. **Authoritative DNS** (10.0.1.10) - DNS server for example.com with DNSSEC support
4. **Resolver DNS** (10.0.0.53) - Caching DNS resolver with DNSSEC validation
5. **Attacker** (10.0.2.100) - Performs DNS poisoning
6. **Frontend UI** (localhost:3000) - Control interface with DNSSEC panel
7. **Backend API** (localhost:5001) - Attack orchestration and DNSSEC management

### Network: 10.0.0.0/16
- Real Website: 10.0.1.20
- Fake Website: 10.0.100.100
- Authoritative DNS: 10.0.1.10
- Resolver DNS: 10.0.0.53
- Attacker: 10.0.100.100

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js (for frontend)
- Python 3 (for backend)

### 1. Start the Infrastructure
```bash
# Start all containers
docker-compose up -d
# Verify all containers are running
docker-compose ps
```

### 2. Start the Backend API
```bash
cd attacker
python3 -m venv env 
source env/bin/activate 
pip install flask flask_cors 
python3 poison.py
```
The API will run on `http://localhost:5001`

### 3. Start the Frontend UI
```bash
cd frontend
npm install
npm run dev
```
The UI will open at `http://localhost:5173`

## 🎯 How to Use

### Normal Operation (Before Attack)
1. Click **"Query DNS"** in the UI
2. You'll see: `www.example.com resolves to: 10.0.1.20`
3. Visit the real website: `http://localhost:8080`
   - Green/purple theme
   - Shows IP: 10.0.1.20
   - Secure banking interface

### Execute the Attack
1. Click **"Start Attack"**
2. Watch the attack logs appear
3. Click **"Query DNS"** again
4. You'll now see: `www.example.com resolves to: 10.0.100.100` ⚠️
5. Visit the fake website: `http://localhost:8081`
   - Red theme with warnings
   - Shows IP: 10.0.100.100
   - Phishing interface that steals credentials


### Reset to Normal
Click **"Reset"** to restore the original DNS records and return to normal operation.

Before Poisoning
<img width="388" height="320" alt="image" src="https://github.com/user-attachments/assets/7f2898a6-ad68-471b-a0d2-e1e374c586ec" />

After Poisoning
<img width="377" height="242" alt="image" src="https://github.com/user-attachments/assets/63bdbb77-f4be-4138-bef1-d47f5b01e196" />


## 🔐 DNSSEC Security (NEW!)

This lab now includes full DNSSEC implementation to demonstrate how DNS Security Extensions prevent cache poisoning attacks.

### Enable DNSSEC Protection:

1. Click **"Show DNSSEC Panel"** in the UI
2. Click **"Setup DNSSEC"** to generate keys and sign the zone
3. Click **"Check Status"** to verify DNSSEC is enabled
4. Click **"Verify Signatures"** to test validation

### What DNSSEC Does:

- **Cryptographically signs** DNS records
- **Validates** responses to ensure authenticity
- **Prevents** attackers from forging DNS responses

DNSSEC ENABLED
<img width="435" height="302" alt="image" src="https://github.com/user-attachments/assets/892bf36a-d8c5-444d-975c-73435879472f" />

<img width="480" height="387" alt="image" src="https://github.com/user-attachments/assets/142ba08c-744e-4235-b88e-dd0dff599eda" />



