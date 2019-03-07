# coding: utf-8

import ui, console, time, motion
import threading, queue
from contextlib import closing

from datetime import datetime
import re, urllib.request, socket
import urllib

import os

from flask import Flask, request, Response, abort
from flask import send_from_directory

import mimetypes


import wkwebview


static_file_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'web/static')



from objc_util import *


import requests
from threading import Timer
import httplib2
from urllib.parse import urlparse

import math
import json, os

theHttpPort = 8080
theThread = None
theApp = Flask(__name__)

MB = 1 << 20
BUFF_SIZE = 10 * MB

# setting routes
@theApp.route("/", methods=['GET'])
def serve_home():
    return send_from_directory(static_file_dir, 'index.html')

@theApp.route('/stream/<path:path>', methods=['GET'])
def stream_file_in_dir(path):    
    fullpath = os.path.join(static_file_dir, "stream",path)
    if not os.path.isfile(fullpath): abort(404)
    start, end = get_range(request)
    return partial_response(fullpath, start, end)
        
@theApp.route('/<path:path>', methods=['GET'])
def serve_file_in_dir(path):
    if not os.path.isfile(os.path.join(static_file_dir, path)): abort(404)
    return send_from_directory(static_file_dir, path)

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

# streaming implementation...
def partial_response(path, start, end=None):
    file_size = os.path.getsize(path)

    # Determine (end, length)
    if end is None:
        end = start + BUFF_SIZE - 1
    end = min(end, file_size - 1)
    end = min(end, start + BUFF_SIZE - 1)
    length = end - start + 1

    # Read file
    with open(path, 'rb') as fd:
        fd.seek(start)
        bytes = fd.read(length)
    assert(len(bytes) == length)

    response = Response(
        bytes,
        206,
        mimetype=mimetypes.guess_type(path)[0],
        direct_passthrough=True,
    )
    response.headers.add(
        'Content-Range', 'bytes {0}-{1}/{2}'.format(
            start, end, file_size,
        ),
    )
    response.headers.add(
        'Accept-Ranges', 'bytes'
    )
    response.headers.add(
        'Access-Control-Allow-Origin', '*'
    )
    response.headers.add(
        'Vary', 'Accept-Encoding'
    )
    return response


def get_range(request):
    range = request.headers.get('Range')
    m = re.match('bytes=(?P<start>\d+)-(?P<end>\d+)?', range)
    if m:
        start = m.group('start')
        end = m.group('end')
        start = int(start)
        if end is not None:
            end = int(end)
        return start, end
    else:
        return 0, None


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



# webview delegate ...
class MyWebViewDelegate (object):
    def __init__(self, webview):
        self.wv = webview
    def webview_should_start_load(self, webview, url, nav_type):
        if url.startswith('ios-log'):
            txt = urllib.parse.unquote(url)
            # hiding some messages 
            if 'Invalid timestamps detected.' in txt:
                pass
            else:
                print(txt)
        return True
    def webview_did_start_load(self, webview):
        pass

    def webview_did_finish_load(self, webview):
        print("webview_did_finish_load")
        
    def webview_did_fail_load(self, webview, error_code, error_msg):
        pass

# the main class
class MyWebVRView(ui.View):
    def __init__(self, url):
        self.finished = False
        self.start_workerThread()
        self.width, self.height = ui.get_window_size()
        self.background_color= 'black'
        # the webview
        self.wv = wkwebview.WKWebView(frame=self.bounds, flex='WH')
        self.wv.delegate = MyWebViewDelegate(self.wv)
        
        self.wv.background_color= 'black'
        self.add_subview(self.wv)        

        bi_back = ui.ButtonItem(image=ui.Image.named('iob:ios7_arrow_back_32'), action=self.goBack)
        bi_forward = ui.ButtonItem(image=ui.Image.named('iob:ios7_arrow_forward_32'), action=self.goForward)
        self.right_button_items = [bi_forward, bi_back]
        
        self.clearCache()
        self.loadURL(url)

        # launch the layout
        self.present("full_screen", hide_title_bar=False)

    
    def goBack(self, bi):
        self.wv.go_back()

    def goForward(self, bi):
        self.wv.go_forward()
        
    # here we observe the exit
    def will_close(self):
       self.finished = True
       
    # some thread management used to
    # react to the remote change
    # of the current url
    def start_workerThread(self):
        global theThread
        theThread = workerThread()
        theThread.start()


    def stop_workerThread(self):
        if theThread is None:
            return
        theThread.stop()

    # main loop...
    def run(self):
        while not self.finished:
            time.sleep(1.0/60)
        self.stop_workerThread()


    def clearCache(self):
        js_code = """window.location.reload(true);"""
        res=self.wv.eval_js(js_code)        

    def loadURL(self, url):
        self.wv.load_url(url, no_cache=True)
    
        
        

if __name__ == '__main__':
    # disable the ios screensaver
    console.set_idle_timer_disabled(True)
    
    #access to localhost
    url = "http://localhost:%d/" % theHttpPort
    
    # fasten your seatbelts, start the engine and let's get doing!...
    MyWebVRView(url).run()
    
    # restore the ios screensaver
    console.set_idle_timer_disabled(False)
