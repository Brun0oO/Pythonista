# coding: utf-8

from objc_util import *

load_framework('ARKit')

ARWorldTrackingSessionConfiguration, ARSessionConfiguration, ARSession = map(ObjCClass,['ARWorldTrackingSessionConfiguration','ARSessionConfiguration','ARSession'])

@on_main_thread
def main():
    if ARWorldTrackingSessionConfiguration.isSupported:
        configuration = ARWorldTrackingSessionConfiguration.alloc()
    else:
        configuration = ARSessionConfiguration.alloc()

    arSession = ARSession.alloc()


    arSession.delegate = self
    print(dir(arSession))


if __name__ == '__main__':
    main()
