# coding: utf-8

# This tool allows to open webvr content in true fullscreen mode on iOS devices using Pythonista.
# Two vr contents are available :
# - the first one comes from sketchfab and displays a 3D room.
# - the second one comes from https://github.com/ryanbetts/dayframe .
# It uses the web framework 'AFrame' for building vr experiences. The "more one thing" is the emulation of a daydream controller.
# (when you choose this demo, try to use an other phone with a web browser opened on https://dayframe-demo.herokuapp.com/remote
# but as this is a public demo and as the author mentioned it : only one person at a time can control the remote. If you join, you will disconnect the previously connected remote)
# Three secret features are also available :
# - you can trigger an url page loading on your device using a remote web browser connected to this device
# - you can adjust the vertical offset and the scale of the web rendering using gestures (find them !). All adjustments are stored so if an url is reloaded, there are applyed again automatically...
# - if you need to interact with the web view, make a long press until you feel a vibration, then you have 10 seconds to manipulate it before the top view takes the control again. You will feel a new vibration, and the top view will catch again the touch events (vertical offset and scale gestures)

import ui, console, time, motion
import threading, queue
from contextlib import closing

from datetime import datetime
import re, urllib.request, socket

from flask import Flask, request, render_template

from objc_util import *
import ctypes
c=ctypes.CDLL(None)

def vibrate():
    p = c.AudioServicesPlaySystemSound
    p.restype, p.argtypes = None, [ctypes.c_int32]
    vibrate_id=0x00000fff
    p(vibrate_id)

import requests
from threading import Timer
import httplib2
from urllib.parse import urlparse

from Gestures import Gestures
import math
import json, os
REGISTRY_PATH='./data/registry.txt'

theDemoURLs = ["https://sketchfab.com/models/311d052a9f034ba8bce55a1a8296b6f9/embed?autostart=1&cardboard=1","https://dayframe-demo.herokuapp.com/scene"]
theHttpPort = 8080
theThread = None
theSharing = {}
theLock = threading.RLock()
theApp = Flask(__name__)


@theApp.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('control.html')
    else:
        theLock.acquire()
        try:
            q = theSharing['queue']
            obj = q.get()
            obj.next_url = request.form['command']
            q.task_done()
        finally:
            theLock.release()
        return render_template('control.html')


LAST_REQUEST_MS = 0
@theApp.before_request
def update_last_request_ms():
    global LAST_REQUEST_MS
    LAST_REQUEST_MS = time.time() * 1000

@theApp.route('/seriouslykill', methods=['POST'])
def seriouslykill():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return "Shutting down..."

@theApp.route('/kill', methods=['POST'])
def kill():
    last_ms = LAST_REQUEST_MS
    def shutdown():
        if LAST_REQUEST_MS <= last_ms:  # subsequent requests abort shutdown
            requests.post('http://localhost:%d/seriouslykill' % theHttpPort)
        else:
            pass

    Timer(1.0, shutdown).start()  # wait 1 second
    return "Shutting down..."

def get_local_ip_addr(): # Get the local ip address of the device
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Make a socket object
    s.connect(('8.8.8.8', 80)) # Connect to google
    ip = s.getsockname()[0] # Get our IP address from the socket
    s.close() # Close the socket
    return ip # And return the IP address

def check_if_url_is_valid(value):
    h = httplib2.Http()
    value = unshorten_url(value)
    resp = h.request(value, 'HEAD')
    return int(resp[0]['status']) < 400

def unshorten_url(url):
    r = requests.head(url, allow_redirects=True)
    return r.url



# thread worker
class workerThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True

    def run(self):
        NSNetService = ObjCClass('NSNetService')  # Bonjour publication
        service = NSNetService.alloc().initWithDomain_type_name_port_('', '_http._tcp', 'iOS webVR Viewer', theHttpPort)
        try:
            service.publish()
            theApp.run(host='0.0.0.0', port=theHttpPort) 
        finally:
            service.stop()
            service.release()

    def stop(self):
        requests.post('http://localhost:%d/kill' % theHttpPort)



# As it's important to hold the phone in landscape mode before creating the view,
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
        # the webview
        self.wv = ui.WebView(frame=self.bounds)
        self.wv.background_color= 'black'
        self.finished = False
        self.current_url = None
        self.next_url = ""
        self.start_workerThread()
        self.add_subview(self.wv)
        # a top view for catching gesture events
        self.gv = ui.View(frame=self.bounds)
        self.gv.alpha = 0.05
        self.gv.background_color = 'white'
        self.add_subview(self.gv)
        self.gv.bring_to_front()
        # some variables for setting the layout
        self.ty=-27
        self.sx=1
        self.applyVerticalOffset()
        self.applyScale()
        # view adjustment per url are saved here
        self.registry={}
        self.readRegistry()
        # gesture setup
        g = Gestures()
        g.add_pan(self.gv, self.pan_handler,1,1)
        g.add_pinch(self.gv, self.pinch_handler)
        g.add_long_press(self.gv, self.long_press_handler)
        # launch the layout
        self.present("full_screen", hide_title_bar=True, orientations=['landscape'])
        # load the url
        self.loadURL(url)
        
    def get_pan_x_limits(self):
        range = self.width*0.1
        x_min= (self.width-range)*0.5
        x_max = (self.width+range)*0.5       
        return x_min, x_max
        
    def pan_handler(self, data):
        # get the safe area for this gesture
        x_min, x_max = self.get_pan_x_limits()
        x = data.location.x
        if (x >= x_min) and (x <= x_max):
            self.ty += int(data.velocity.y*1.0/50)
            self.applyVerticalOffset()
            self.saveInfoToRegistry(self.current_url, self.ty, self.sx)
        
    
    def pinch_handler(self, data):
        self.sx += data.velocity/50
        self.applyScale()
        self.saveInfoToRegistry(self.current_url, self.ty, self.sx)
     
     
    def long_press_handler(self, data):
        # get the safe area for this gesture
        x_min, x_max = self.get_pan_x_limits()
        x = data.location.x
        if (x <= x_min) or (x >= x_max):       
            if data.state==Gestures.BEGAN:
                # a little feedback...
                vibrate()
                # ...and we disable the top view using the alpha parameter of this view
                self.gv.alpha = 0
                ui.delay(self.restoreAlpha, 10)
        
        
    def restoreAlpha(self):
        # restore the alpha parameter of the top view. Notice, it's a small small value ;)
        self.gv.alpha=0.05
        vibrate()
        
    # small persistent storage mechanism   
    def writeRegistry(self):
        with open(REGISTRY_PATH, 'w') as outfile:
            json.dump(self.registry, outfile, indent=2, sort_keys=True)
        
        
    def readRegistry(self):
        directory = os.path.dirname(REGISTRY_PATH)
        if not os.path.exists(directory):           
            os.makedirs(directory)
            return
        if os.path.exists(REGISTRY_PATH):
            with open(REGISTRY_PATH) as json_file:
                self.registry = json.load(json_file)
            
        
    def readInfoFromRegistry(self, url):
        key = self.buildKeyFromURL(url)
        if key in self.registry:
            return self.registry[key]
        return (self.ty, self.sx)
    
    def saveInfoToRegistry(self, url, pos, scale):
        key = self.buildKeyFromURL(url)
        self.registry[key] = (pos,scale)
        self.writeRegistry()
  
    # create a key from an url
    def buildKeyFromURL(self, url):
        pos = url.find("://")
        tokens = url[pos+3:].split('/')
        return tokens[0]
        
    # a little function to set the web view layout
    def applyVerticalOffset(self):
        self.wv.y = self.ty  
          
    def applyScale(self):
        self.wv.transform = ui.Transform().scale(self.sx, self.sx)

    # here we observe the exit
    def will_close(self):
       self.finished = True

    # some thread management used to
    # react to the remote change
    # of the current url
    def start_workerThread(self):
        global theThread
        global theSharing
        with theLock:
            theSharing['queue'] = queue.Queue(1)
        theThread = workerThread()
        theThread.start()


    def stop_workerThread(self):
        if theThread is None:
            return
        theThread.stop()
        while theThread and theThread.isAlive():
            with theLock:
                q = theSharing['queue']
                if q.empty():
                    q.put(self)
            time.sleep(1.0/60)

    # this method allows to maintain a communication with the worker thread using a queue 
    def update(self):
        url = ""
        with theLock:
            q = theSharing['queue']
            if q.empty():
                q.put(self)
            url = self.next_url
        if url != "":
            self.loadURL(url)

    def run(self):
        while not self.finished:
            self.update()
            time.sleep(1.0/60)
        self.stop_workerThread()



    def loadURL(self, url):
        if url=="": # force reload/refresh the current url
            url=self.current_url
            self.current_url=None
            
        url = self.patch_SKETCHFAB_page(url)
        if check_if_url_is_valid(url):
            if self.current_url is None or (self.current_url != url):
                print("loading %s" % url)
                self.current_url = url
                self.wv.load_url(self.current_url)
                self.patch_AFRAME_page()
                self.ty, self.sx = self.readInfoFromRegistry(url)
                self.applyVerticalOffset()
                self.applyScale()

    # The following function returns the given url but in case of a sketchfab url, it adds the auto cardboard view parameter at the end of string...
    def patch_SKETCHFAB_page(self, url):
        result = url.lower()
        if result.startswith("https://sketchfab.com/models/"):
            if not result.endswith("/embed?autostart=1&cardboard=1"):
                result += "/embed?autostart=1&cardboard=1"
        return result


        
    # An other trick in case of a aframe url, it will inject a custom javascript code in order to force the enterVR trigger...
    # but sometimes, the following hack seems to be wrong...
    # The screen stays in desktop mode, you have to restart the demo or click on the cardboard icon.
    # Perhaps, my delay is too short or something goes wrong with the browser cache...
    
    def patch_AFRAME_page(self):
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
    # disable the ios screensaver
    console.set_idle_timer_disabled(True)
    
    # ask the user for the first url loading.
    # he has the choice between a sketchfab or an a-frame scene
    demoID = console.alert('Select a demo','(%s:%d)'% (get_local_ip_addr(), theHttpPort),'sketchfab','a-frame')
    url = theDemoURLs[demoID-1]
    
    # it's very important to hold the phone in landscape mode before the ui.view creation so ...
    waitForLandscapeMode()

    # fasten your seatbelts, start the engine and let's get doing!...
    MyWebVRView(url).run()
    
    # restore the ios screensaver
    console.set_idle_timer_disabled(False)
