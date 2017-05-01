# coding: utf-8

import ui, console, time, motion
import threading, Queue
from datetime import datetime
import re, urllib2

# This demo allows to open webvr content in true fullscreen mode in Pythonista.
# Two vr contents are available :
# - the first one comes from sketchfab and displays a 3D room.
# - the second one comes from https://github.com/ryanbetts/dayframe .
# It uses a web framework for building vr experiences. The more one thing is the emulation of a daydream controller.
# (when you choose this demo, try to use an other phone with a web browser opened on https://dayframe-demo.herokuapp.com/remote)

demoURL = ["https://sketchfab.com/models/311d052a9f034ba8bce55a1a8296b6f9/embed?autostart=1&cardboard=1","https://dayframe-demo.herokuapp.com/scene"]


OUTPUT_TEMPLATE = u"""\
Number of threads: {}
Queue size: {}
Frame number: {}
Last polled: {}
Current time: {}
"""

# thread worker
def worker(q):
    URL = 'http://tycho.usno.navy.mil/cgi-bin/timer.pl'
    RE_TIME = re.compile('<BR>(.*?)\t.*Universal Time')
    while True:
        obj = q.get()
        html = urllib2.urlopen(URL).read()
        obj.text = RE_TIME.search(html).group(1)
        q.task_done()



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

        # for an iphone 6S plus, a small vertical offset needs to be set
        trans=ui.Transform().translation(0,-27)
        sx = 1.07 # and a small scale (almost for sketchfab can be ignored for an aframe page)
        scale=ui.Transform().scale(sx,sx)
        self.wv.transform = trans.concat(scale)

        self.wv.load_url(url)
        self.add_subview(self.wv)

        self.present("full_screen", hide_title_bar=True, orientations=['landscape'])

        self.loadURL(url)

        self.text = "Waiting..."
        self.frame = 0
        self.q = Queue.Queue(1)
        t = threading.Thread(target=worker, args=(self.q,))
        t.daemon = True
        t.start()

    def update(self):
        self.frame += 1
        now = datetime.utcnow().strftime('%b. %d, %H:%M:%S UTC')
        if self.q.empty():
            self.q.put(self)

        output = OUTPUT_TEMPLATE.format(
            threading.active_count(), self.q.qsize(), self.frame, self.text,
            now
        )

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
    MyWebVRView(url)
