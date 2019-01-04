# My debug toolkit...
# It allows me to copy some usefull informations to the clipboard.
# Then, I use the free ios app ´CloudClip' to share these informations with my desktop.
from objc_util import *
from objc_util import class_copyMethodList, method_getName, sel_getName, free,ObjCInstanceMethodProxy, objc_getClass

import clipboard
import inspect
from datetime import datetime
import sound
from inspect import signature

def info(obj, obj_name, private=False):
    if obj_name in globals():
        beep()
    callerframerecord = inspect.stack()[1]
    frame = callerframerecord[0]
    info = inspect.getframeinfo(frame)
    filename = info.filename
    filename = filename[filename.find('Documents'):]
    function = info.function
    lineno = info.lineno
    content = ''
    if inspect.ismodule(obj) or inspect.isclass(obj):
        methods = dir(obj)
        for method in methods:
            to_be_added = True
            if not private: 
                to_be_added = not(method.startswith('__') and method.endswith('__'))
            if to_be_added:
                if content != '':
                    content += '\n'
                content += '#\t'+ method
        content = '# List of its public method(s) :\n'+content
    elif inspect.ismethod(obj) or inspect.isfunction(obj):
        content = str(signature(obj))
    elif isinstance(obj, (ObjCClass)) or isinstance(obj, (ObjCInstance)):
        methods = inspectObjc(obj)
        for method in methods:
            if content != '':
                content += '\n'
            content += '#\t'+method
        content = '# List of its method(s) :\n'+content
    timestamp = str(datetime.now())
    text = "# timestamp = %s\n" % timestamp
    text += "# filename = %s\n" % filename
    text += "# function = %s\n" % function
    text += "# line number = %d\n" % lineno
    text += "# Inspected object = '%s'\n" % obj_name
    text += "# Type(object) = %s\n" % type(obj)
    text += content
    clipboard.set(text)

def inspectObjc(obj):
    if isinstance(obj, (ObjCClass)):
        name = obj.class_name.decode('utf-8')
    elif isinstance(obj, (ObjCInstance)):
        name = obj._get_objc_classname().decode('utf-8')
    elif isinstance(obj, (str)):
        name = obj
    else:
        # not supported !
        return []

    py_methods = []
    c = ObjCClass(name)
    num_methods = c_uint(0)
    method_list_ptr = class_copyMethodList(c.ptr, byref(num_methods))
    for i in range(num_methods.value):
        selector = method_getName(method_list_ptr[i])
        sel_name = sel_getName(selector)
        if not isinstance(sel_name, str):
            sel_name = sel_name.decode('ascii')
        py_method_name = sel_name.replace(':','_')
        if '.' not in py_method_name:
            py_methods.append(py_method_name)
            
    free(method_list_ptr)
    return py_methods

def beep():
    sound.play_effect('Ding_3', volume=1.0)
