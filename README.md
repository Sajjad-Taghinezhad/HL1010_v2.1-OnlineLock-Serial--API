# HL1010_v2.1-OnlineLock-Serial--API
Opening locks using HL1010_v2.1 serial device through Web API 

--- 
## Installation  



```
git clone https://github.com/Sajjad-Taghinezhad/HL1010_v2.1-OnlineLock-Serial--API.git
cd HL1010_v2.1-OnlineLock-Serial--API
```
Change the `app.conf` to match your needs.

```
python3 -m venv .venv
pip3 install -r requirements.txt
python3 NetLock.py
```

---

## Usage 

http://ip:port/open/<device address\>/\<lock number\> 

e.g : `HTTP://localhost:5555/open/01/12`
