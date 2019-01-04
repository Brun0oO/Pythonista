# coding: utf-8
import objc_util

from objc_util import *
import ui
import os
import sys

#from myDebugToolKit import *
import time
from enum import IntFlag


load_framework('SceneKit')
load_framework('ARKit')

# Some 'constants' used by ARkit
# But i can't transfer them to the ARKit framework, why ?????

class ARWorldAlignment(IntFlag):
    ARWorldAlignmentGravity = 0
    ARWorldAlignmentGravityAndHeading = 1
    ARWorldAlignmentCamera = 2

class ARPlaneDetection(IntFlag):
    ARPlaneDetectionNone = 0
    ARPlaneDetectionHorizontal = 1 << 0
    ARPlaneDetectionVertical = 1 << 1

# Work In Progress here, I'm deciphering the arkit constants...
#class ARSCNDebugOption(IntFlag):
#    ARSCNDebugOptionNone = 0
#    ARSCNDebugOptionShowWorldOrigin = int("ffffffff80000000", 16)
#    ARSCNDebugOptionShowFeaturePoints = int("ffffffff40000000", 16)

class ARSessionRunOptions(IntFlag):
    ARSessionRunOptionsNone                     = 0
    ARSessionRunOptionResetTracking             = 1 << 0
    ARSessionRunOptionRemoveExistingAnchors     = 1 << 1


NSError = ObjCClass('NSError')
SCNScene = ObjCClass('SCNScene')
ARSCNView = ObjCClass('ARSCNView')
ARWorldTrackingConfiguration = ObjCClass('ARWorldTrackingConfiguration')
ARSession = ObjCClass('ARSession')
UIViewController = ObjCClass('UIViewController')
ARPlaneAnchor = ObjCClass('ARPlaneAnchor')



# I should refactor te following line in a class but I need to learn more the create_objcc_class function
sceneview = None

# Here some set up functions used by the main class
def createSampleScene():
    # an empty scene
    scene = SCNScene.scene()
    return scene

def setDebugOptions(arscn):
    # Work In Progress Here, I'm trying to decipher the arkit constants...
    #val = ARSCNDebugOption.ARSCNDebugOptionShowWorldOrigin | ARSCNDebugOption.ARSCNDebugOptionShowFeaturePoints
    val = int("fffffffffc000000", 16) # this value is a combination of ShowWorldOrigin and ShowFeaturePoints flags, but I can't isolate each flags....
    print('Before calling setDebugOptions_(%s) : debugOptions=%s' %(hex(val), hex(arscn.debugOptions())))
    arscn.setDebugOptions_(val)
    print('After calling setDebugOptions_(%s) : debugOptions=%s' % (hex(val),hex(arscn.debugOptions())))


def createARSceneView(x, y, w, h, debug=True):
    v = ARSCNView.alloc().initWithFrame_((CGRect(CGPoint(x, y), CGSize(w, h))))
    v.setShowsStatistics_(debug) # I love statistics...
    return v

# Some callback definitions used by create_objc_class
def CustomViewController_touchesBegan_withEvent_(_self, _cmd, _touches, event):
    touches = ObjCInstance(_touches)
    for t in touches:
        loc = t.locationInView_(sceneview)
        sz = ui.get_screen_size()
        print(loc)

@on_main_thread
def runARSession(arsession):
    arconfiguration = ARWorldTrackingConfiguration.alloc().init()
    arconfiguration.setPlaneDetection_ (ARPlaneDetection.ARPlaneDetectionHorizontal)
    arconfiguration.setWorldAlignment_(ARWorldAlignment.ARWorldAlignmentGravity) # I do not use ARWorldAlignmentGravityAndHeading anymore because on my device, sometimes it fails to initialize the ar session because of an unitialized sensor (error 102). I think my magnetic phone casing plays tricks on me...

    arsession.runWithConfiguration_options_(arconfiguration, ARSessionRunOptions.ARSessionRunOptionResetTracking | ARSessionRunOptions.ARSessionRunOptionRemoveExistingAnchors )

    time.sleep(0.5) # Let the system breathe ;o) Ok, that's the workarround I found to retrieve the ar session configuration (otherwise I got None)....
    print('configuration',arsession.configuration()) # Very usefull for the debuging (at least for me !)


def CustomViewController_viewWillAppear_(_self, _cmd, animated):
    return

def CustomViewController_viewWillDisappear_(_self, _cmd, animated):
    session = sceneview.session()
    session.pause()

def MyARSCNViewDelegate_renderer_didAdd_for_(_self, _cmd, scenerenderer, node, anchor):
    if not isinstance(anchor, (ARPlaneAnchor)):
        return
    # to be implemented...


def MyARSCNViewDelegate_session_didFailWithError_(_self,_cmd,_session,_error):
    print('error',_error,_cmd,_session)
    err_obj=ObjCInstance(_error)
    print(err_obj) # Again, very usefull for the debuging...

# The main class...
class MyARView(ui.View):
    def __init__(self):
        super().__init__(self)


    @on_main_thread
    def initialize(self):
        global sceneview
        self.flex = 'WH'

        screen = ui.get_screen_size()

        # set up the scene
        scene = createSampleScene()

        # set up the ar scene view delegate
        methods = [MyARSCNViewDelegate_renderer_didAdd_for_,MyARSCNViewDelegate_session_didFailWithError_]
        protocols = ['ARSCNViewDelegate']
        MyARSCNViewDelegate = create_objc_class('MyARSCNViewDelegate', NSObject, methods=methods, protocols=protocols)
        delegate = MyARSCNViewDelegate.alloc().init()

        # set up the ar scene view
        sceneview = createARSceneView(0, 0, screen.width, screen.height)
        sceneview.scene = scene
        sceneview.setDelegate_(delegate)


        # set up the custom view controller
        methods = [CustomViewController_touchesBegan_withEvent_, CustomViewController_viewWillAppear_, CustomViewController_viewWillDisappear_]
        protocols = []
        CustomViewController = create_objc_class('CustomViewController', UIViewController, methods=methods, protocols=protocols)
        cvc = CustomViewController.alloc().init()
        cvc.view = sceneview


        # internal kitchen
        self_objc = ObjCInstance(self)
        self_objc.nextResponder().addChildViewController_(cvc)
        self_objc.addSubview_(sceneview)
        cvc.didMoveToParentViewController_(self_objc)

        # here, we try...
        runARSession(sceneview.session()) # I call here this function because I'm trying to find the best place to run the ar session...

        setDebugOptions(sceneview) # I call here this function because I'm trying to find the best place to set the debuging options....

    def will_close(self):
        session = sceneview.session()
        session.pause()



if __name__ == '__main__':
    v = MyARView()
    v.present('full_screen', hide_title_bar=True, orientations=['portrait'])
    v.initialize()
