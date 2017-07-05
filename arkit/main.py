# coding: utf-8

from objc_util import *

load_framework('ARKit')

SCNScene, SCNNode, SCNLookAtConstraint = map(ObjCClass, ['SCNScene', 'SCNNode', 'SCNLookAtConstraint'])

ARWorldTrackingSessionConfiguration, ARSessionConfiguration, ARSession = map(ObjCClass,['ARWorldTrackingSessionConfiguration','ARSessionConfiguration','ARSession'])

def renderer_didAdd_for_(_self, _cmd, renderer, node, anchor):
    pass


methods = [renderer_didAdd_for_]
protocols = ['ARSCNViewDelegate']
MyARKitDelegate = create_objc_class('MyARKitDelegate', NSObject, methods=methods, protocols=protocols)


@on_main_thread
def main():
    if ARWorldTrackingSessionConfiguration.isSupported:
        configuration = ARWorldTrackingSessionConfiguration.alloc()
    else:
        configuration = ARSessionConfiguration.alloc()

    arSession = ARSession.alloc()


    #arSession.delegate = MyARKitDelegate.alloc().init()
    #print(dir(arSession))

    print(dir(SCNScene))

    exit()

    main_view = ui.View()
    main_view_objc = ObjCInstance(main_view)
    scene_view = SCNView.alloc().initWithFrame_options_(((0,0),(400, 400)), None).autorelease()
    scene_view.setAutoresizingMask_(18)
    scene_view.setAllowsCameraControl_(True)
    main_view_objc.addSubview_(scene_view)
    main_view.name = 'ARKit Demo'

    scene = SCNScene.scene("assets/dragon/main.scn")
    scene_view.setScene_(scene)

    main_view.present()


if __name__ == '__main__':
    main()
