# coding: utf-8

from objc_util import *
import ui

load_framework('ARKit')

SCNView, SCNScene, SCNNode, SCNLookAtConstraint = map(ObjCClass, ['SCNView', 'SCNScene', 'SCNNode', 'SCNLookAtConstraint'])

ARWorldTrackingSessionConfiguration, ARSessionConfiguration, ARSession = map(ObjCClass,['ARWorldTrackingSessionConfiguration','ARSessionConfiguration','ARSession'])

def renderer_didAdd_for_(_self, _cmd, renderer, node, anchor):
    pass


methods = [renderer_didAdd_for_]
protocols = ['ARSCNViewDelegate']
MyARKitDelegate = create_objc_class('MyARKitDelegate', NSObject, methods=methods, protocols=protocols)

dragonNode = SCNNode.node()

def loadDragon():
    global dragonNode
    dragonScene = SCNScene.sceneNamed_("assets/dragon/dragon.scn")
    dragonNode = dragonScene.rootNode.childNodeWithName_recursively_("dragon", True)

@on_main_thread
def main():
    if ARWorldTrackingSessionConfiguration.isSupported:
        configuration = ARWorldTrackingSessionConfiguration.alloc()
    else:
        configuration = ARSessionConfiguration.alloc()

    arSession = ARSession.alloc()


    arSession.delegate = MyARKitDelegate.alloc().init()

    main_view = ui.View()
    main_view_objc = ObjCInstance(main_view)
    scene_view = SCNView.alloc().initWithFrame_options_(((0,0),(400, 400)), None).autorelease()
    scene_view.setAutoresizingMask_(18)
    scene_view.setAllowsCameraControl_(True)
    main_view_objc.addSubview_(scene_view)
    main_view.name = 'ARKit Demo'

    scene = SCNScene.sceneNamed_("assets/dragon/main.scn")
    scene_view.setScene_(scene)

    loadDragon()

    main_view.present()


if __name__ == '__main__':
    main()
