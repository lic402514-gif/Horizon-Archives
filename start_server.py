import subprocess,sys,os,time
# Kill existing uvicorn on port 8000
subprocess.run(['taskkill','/F','/IM','python.exe'],capture_output=True)
time.sleep(2)
# Start server
os.chdir(r'C:\Users\Lucian\personal-library')
proc=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','0.0.0.0','--port','8000'],
    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
time.sleep(3)
# Test
import urllib.request
try:
    r=urllib.request.urlopen('http://localhost:8000/api/health',timeout=5)
    print(f'Server started OK (pid={proc.pid})')
except Exception as e:
    print(f'Start failed: {e}')
