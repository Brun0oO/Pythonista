# coding: utf-8

import ui, console, time, motion
import threading, queue
from contextlib import closing

from datetime import datetime
import re, urllib.request

from flask import Flask
from flask import request


import requests
from threading import Timer

import random

cache = {}
lock_cache = threading.RLock()

app = Flask(__name__)
@app.route("/")
def hello():
    lock_cache.acquire()
    try:
        q = cache['q']
        obj = q.get()
        obj.text = 'hello'
        q.task_done()
    finally:
        lock_cache.release()
    #obj = self.q.get()
    #obj.text = str(random.randint(1,1000))
    #self.q.task_done()
    return "Hello World!"
 

# This demo allows to open webvr content in true fullscreen mode in Pythonista.
# Two vr contents are available :
# - the first one comes from sketchfab and displays a 3D room.
# - the second one comes from https://github.com/ryanbetts/dayframe .
# It uses a web framework for building vr experiences. The more one thing is the emulation of a daydream controller.
# (when you choose this demo, try to use an other phone with a web browser opened on https://dayframe-demo.herokuapp.com/remote)

demoURL = ["https://sketchfab.com/models/311d052a9f034ba8bce55a1a8296b6f9/embed?autostart=1&cardboard=1","https://dayframe-demo.herokuapp.com/scene"]

theThread = None

OUTPUT_TEMPLATE = u"""\
Number of threads: {}
Queue size: {}
Frame number: {}
Last polled: {}
Current time: {}
"""



LAST_REQUEST_MS = 0
@app.before_request
def update_last_request_ms():
    global LAST_REQUEST_MS
    LAST_REQUEST_MS = time.time() * 1000
    
@app.route('/seriouslykill', methods=['POST'])
def seriouslykill():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return "Shutting down..."
    
@app.route('/kill', methods=['POST'])
def kill():
    last_ms = LAST_REQUEST_MS
    def shutdown():
        if LAST_REQUEST_MS <= last_ms:  # subsequent requests abort shutdown
            requests.post('http://localhost:5000/seriouslykill')
        else:
            pass

    Timer(1.0, shutdown).start()  # wait 1 second
    return "Shutting down..."



# thread worker
class workerThread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.finished = False
        self.daemon = True
        
        


    def run(self):
        app.run(host='0.0.0.0', port=5000)
        print("stopped")

    def stop(self):
        self.finished = True
        requests.post('http://localhost:5000/kill')
        
        





# as it's important to hold in landscape mode the phone before creating the view,
# a dedicated function has been created...
def waitForLandscapeMode():
    msg = 'Please, hold your phone in landscape mode'
    console.hud_alert(msg, duration = 3)
    motion.start_updates()
    try:
        count=0
        while True:
            x, y, z = motion.get_gravity()
            count+=1
            if count>2:
                if abs(x) > abs(y):
                    break
                else:
                    console.hud_alert(msg, duration = 2)
            time.sleep(0.5)
    finally:
        motion.stop_updates()
    time.sleep(1)

# the main class
class MyWebVRView(ui.View):
    def __init__(self, url):

        self.width, self.height = ui.get_window_size()
        self.background_color= 'black'
        self.wv = ui.WebView(frame=self.bounds)
        self.finished = False
        self.text = "Waiting..."
        self.numframe = 0
        self.start_workerThread()

        # for an iphone 6S plus, a small vertical offset needs to be set
        trans = ui.Transform().translation(0,-27)
        sx = 1.07 # and a small scale (almost for sketchfab can be ignored for an aframe page)
        scale = ui.Transform().scale(sx,sx)
        self.wv.transform = trans.concat(scale)

        self.wv.load_url(url)
        self.add_subview(self.wv)

        self.present("full_screen", hide_title_bar=True, orientations=['landscape'])

        self.loadURL(url)


    def will_close(self):
       self.finished = True
        
    def start_workerThread(self):
        global app
        global theThread
        with lock_cache:
            cache['q'] = queue.Queue(1)
        theThread = workerThread()
        theThread.start()
        
        
    def stop_workerThread(self):
        global theThread
        if theThread is None:
            return
        theThread.stop()
        while theThread and theThread.isAlive():
            with lock_cache:
                q = cache['q']
                if q.empty():
                    q.put(self)
            time.sleep(1.0/60)

            
    def update(self):
        self.numframe += 1
        now = datetime.utcnow().strftime('%b. %d, %H:%M:%S UTC')
        with lock_cache:
            q = cache['q']
            if q.empty():
                q.put(self)

            #for t in threading.enumerate():
            #    print(t.name)
            output = OUTPUT_TEMPLATE.format(
            threading.active_count(), q.qsize(), self.numframe, self.text, now)
            print(output)

    def run(self):
        while not self.finished:
            self.update()
            time.sleep(1.0/60)
        self.stop_workerThread()
 

            
    def loadURL(self, url):
        url = self.patch_SKETCHFAB_page(url)
        self.wv.load_url(url)
        self.patch_AFRAME_page()

    # in case of a sketchfab url, add the auto cardboard view parameter at the end of string...
    def patch_SKETCHFAB_page(self, url):
        result = url.lower()
        if result.startswith("https://sketchfab.com/models/"):
            if not result.endswith("/embed?autostart=1&cardboard=1"):
                result += "/embed?autostart=1&cardboard=1"
        return result

    # in case of a aframe url, inject a custom javascript code in order to force the enterVR trigger...
    def patch_AFRAME_page(self):
        # but sometimes, the following hack seems to be wrong...
        # The screen stays in desktop mode, you have to restart the demo or click on the cardboard icon.
        # Perhaps, my delay is too short or something goes wrong with the browser cache...
        js_code = """
function customEnterVR () {
  var scene = document.getElementById('scene');
  if (scene) {
    if (scene.hasLoaded) {
      scene.enterVR();
    } else {
      scene.addEventListener('loaded', scene.enterVR);
    }
  }
}
customEnterVR();
        """
        searchITEM = "scene"
        searchID = self.wv.evaluate_javascript('document.getElementById("%s").id' % searchITEM)
        searchCount = 0
        while not searchID == "%s" % searchITEM:
            time.sleep(1)  # wait for 1 second before searching again
            searchID = self.wv.evaluate_javascript('document.getElementById("%s").id' % searchITEM)
            searchCount += 1
            if searchCount>2:  # max two attempts...
                break
        if searchID == searchITEM:
            res=self.wv.eval_js(js_code)

if __name__ == '__main__':
    demoID = console.alert('Select a demo','','sketchfab','a-frame')
    url = demoURL[demoID-1]

    waitForLandscapeMode()
    
    MyWebVRView(url).run()
    

