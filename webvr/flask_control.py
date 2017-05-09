#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2012 James Percent <james@syndeticlogic.org>
#
import logging
import urllib
import os
import sys
import subprocess
import time
from flask import request
from multiprocessing import Process, Queue
#
# This module consists of 2 classes: FlaskMonitor and FlaskController.  An
# instance of FlaskController can be used to start and stop a flask web service.
# The FlaskController creates a FlaskMonitor that can return request data.  The
# FlaskController creates a separate process to run the flask web service and
# uses Python IPC to control it.
#
# For more information see http://github.com/jpercent/flask-control
#
class FlaskMonitor(object):
    def __init__(self, Q, app):
        super(FlaskMonitor, self).__init__()
        self.Q = Q
        self.app = app
    def after_request(self, response=None):
        try:
            self.Q.put(request.data)
        except:
            logging.error('failed to post request data')
        return response
        
def start_flask(Q, get_app, sync_request_data):
    app = get_app()
    fm = FlaskMonitor(Q, app)
    if sync_request_data == True:
        app.after_request(fm.after_request)
    app.run(host='0.0.0.0')    
        
class FlaskController(object):
    def __init__(self, get_app, sync_request_data=None):
        self.Q = Queue()
        self.flask_process = Process(target=start_flask, args=(self.Q, get_app, sync_request_data))
        self.start = self.flask_process.start
        self.await = self.flask_process.join
        self.terminate = self.flask_process.terminate
        self.next = self.Q.get
        
    def stop(self):
        time.sleep(5)
        self.terminate()
        self.await()
        
