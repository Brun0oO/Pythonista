# coding: utf-8


from objc_util import *
import ui
import os
import sys
#from myDebugToolKit import *

load_framework('SceneKit')
load_framework('ARKit')

# Some 'constants' used by ARkit
# But i can't transfer them to the ARKit framework, why ?????
ARWorldAlignmentGravity = 0
ARWorldAlignmentGravityAndHeading = 1
ARWorldAlignmentCamera = 2
    
ARPlaneDetectionNone = 0
ARPlaneDetectionHorizontal = 1 << 0
ARPlaneDetectionVertical = 1 << 1

ARSCNDebugOptionNone = 0 
ARSCNDebugOptionShowWorldOrigin = 1 << 0
ARSCNDebugOptionShowFeaturePoints = 1 << 1
    



SCNScene = ObjCClass('SCNScene')
ARSCNView = ObjCClass('ARSCNView')
ARWorldTrackingConfiguration = ObjCClass('ARWorldTrackingConfiguration')
ARSession = ObjCClass('ARSession')
UIViewController = ObjCClass('UIViewController')
ARPlaneAnchor = ObjCClass('ARPlaneAnchor')



# I should refactor te following line in a class but I need to learn more the create_objcc_class function 
sceneview = None   

# Here two little set up functions used by the main class
def createSampleScene():
    # an empty scene
    scene = SCNScene.scene()
    return scene


def createARSceneView(x, y, w, h, debug=True):
    v = ARSCNView.alloc().initWithFrame_((CGRect(CGPoint(x, y), CGSize(w, h))))
    v.setShowsStatistics_(debug)
    # Problem here... feature points are not shown.... despite the method call
    v.setDebugOptions_(ARSCNDebugOptionShowWorldOrigin |ARSCNDebugOptionShowFeaturePoints)  
    return v

# Some callback definitions used by create_objc_class
def CustomViewController_touchesBegan_withEvent_(_self, _cmd, _touches, event):
    touches = ObjCInstance(_touches)
    for t in touches:
        loc = t.locationInView_(sceneview)
        sz = ui.get_screen_size()
        print(loc)

def CustomViewController_viewWillAppear_(_self, _cmd, animated):    
    configuration = ARWorldTrackingConfiguration.alloc().init()
    # Another problem here...constants aren't well communicated... (my assumption...)  
    configuration.setPlaneDetection_ (ARPlaneDetectionHorizontal)
    configuration.setWorldAlignment_(ARWorldAlignmentGravityAndHeading)
    
    session = sceneview.session()
    session.runWithConfiguration_(configuration)


def CustomViewController_viewWillDisappear_(_self, _cmd, animated):
    session = sceneview.session()   
    session.pause()
    

def MyARSCNViewDelegate_renderer_didAdd_for_(_self, _cmd, scenerenderer, node, anchor):
    if not isinstance(anchor, (ARPlaneAnchor)):
        return
    # to be implemented...

# The main class...
class MyARView(ui.View):
    def __init__(self):
        global sceneview
        self.flex = 'WH'
        
        screen = ui.get_screen_size()

        # set up the scene
        scene = createSampleScene()

        # set up the ar scene view delegate
        methods = [MyARSCNViewDelegate_renderer_didAdd_for_]
        protocols = ['ARSCNViewDelegate']
        MyARSCNViewDelegate = create_objc_class('MyARSCNViewDelegate', NSObject, methods=methods, protocols=protocols)
        delegate = MyARSCNViewDelegate.alloc().init()

        # set up the ar scene view
        sceneview = createARSceneView(0, 0, screen.width, screen.height)
        sceneview.scene = scene
        sceneview.delegate = delegate
        

        # set up the custom view controller
        methods = [CustomViewController_touchesBegan_withEvent_,            CustomViewController_viewWillAppear_, CustomViewController_viewWillDisappear_]
        protocols = []
        CustomViewController = create_objc_class('CustomViewController', UIViewController, methods=methods, protocols=protocols)
        cvc = CustomViewController.new().init().autorelease()
        cvc.view = sceneview
        

        # last set up
        self_objc = ObjCInstance(self)
        self_objc.addSubview_(sceneview)
 
        # workaround : I need to call manually viewWillAppear as otherwise my callback is not called...
        cvc.viewWillAppear_(False)
        

    def will_close(self):
        session = sceneview.session()
        session.pause()


@on_main_thread
def main():
    v = MyARView()
    v.present('full_screen', hide_title_bar=True)

if __name__ == '__main__':
    main()
