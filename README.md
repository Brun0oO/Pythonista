# Pythonista
Here you can find things about Pythonista (a complete development environment for writing Python™ scripts on your iPad or iPhone).

## webVR
As it's currently difficult to watch web VR content in full screen on iOS devices, i created this tool.
It has some hidden features ;o)

![Live session](https://cloud.githubusercontent.com/assets/10347315/26284635/88eb498a-3e40-11e7-8798-8961e92da0cd.gif)

* Some gestures allow you to adjust the presentation (vertical offset and scaling).

* A long press allows you to deactivate momentarily the previous gestures and gives access to the web view content through touch events.

* You can change the current content using a remote web browser connected to your iOS device.

* The tool detects sketchfab content and activates automatically its VR view. A same mechanism exists for A-frame content but it's more experimental.

## ARKit

My first attempt to use the ARKit framework within iOS 11 Beta...  
**!! Caution, slippery floor !!**  
**Work in progress**

## RShell

If you want to access to your stash opened on your iOS device from your desktop, you can use this script.  
You have to download it on your bin stash directory and call it from the stash prompt simply by using rshell with -l as argument.

```
  stash> rshell -l
```

Then, on your desktop, install this script and call it with the ip address of your iOS device as argument and let the magic happen...
```
  $> rshell 192.168.0.40
```

Personally, on my desktop, I prefer to call it from my PyCharm IDE because its console is smarter than the standard terminal to use the backspace key for example...

![Live session](https://user-images.githubusercontent.com/10347315/28498512-80baefa0-6f9f-11e7-8bf3-b9519a5fe4c3.gif)
