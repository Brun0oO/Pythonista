// debug_utils.js
// 1) custom console object
console = new Object();
console.log = function(log) {
  // create then remove an iframe, to communicate with webview delegate
  var iframe = document.createElement("IFRAME");
  iframe.setAttribute("src", "ios-log:" + log);
  document.documentElement.appendChild(iframe);
  iframe.parentNode.removeChild(iframe);
  iframe = null;    
};
// TODO: give each log level an identifier in the log
console.debug = console.log;
console.info = console.log;
console.warn = console.log;
console.error = console.log;

// 2) custom onerror, which logs info about the error
   window.onerror = (function(error, url, line,col,errorobj) {
   console.log("error: "+error+"%0Aurl:"+url+" line:"+line+"col:"+col+"stack:"+errorobj);})

console.log("logging activated");
