#!/usr/bin/env python2
# coding: utf-8

# RSHELL is a remote interactive access to Stash (a bash like shell for Pythonista).
# It's based on the Guido Wesdorp's work for its remote interactive shell (ripshell).

from __future__ import print_function
import socket
import sys
import traceback
import thread
import time



class config:
    server_ip = '0.0.0.0'
    port = 10101

__version__ = '1.0'

# get the local ip address of the current device
def get_local_ip_addr():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # make a socket object
    s.connect(('8.8.8.8', 80))  # connect to google ;o)
    ip = s.getsockname()[0]  # get our IP address from the socket
    s.close()  # close the socket
    return ip  # and return the IP address


class STDFilePointers:
    def __init__(self, conn):
        self.conn = conn

    def write(self, s):
        self.conn.send(s)

    def read(self, l):
        r = self.conn.recv(l)
        if r:
            return r
        return ' '

    def readlines(self):
        data = []
        while 1:
            c = self.read(1)
            if c == '\n':
                line = ''.join(data)
                # well..here a little hack in order to intercept a quit command from the client....
                if line == 'quit':
                    raise SystemExit('quit')
                line += '\n'
                return line
            data.append(c)

#
# The server
#
# Launch Pythonista on your iOS device
# Execute launch_stash.py
# Type rshell.py
# Look at the printed ip address on the console ;o)
#
class RSHELLServer:
    banner = (  'RShell Server v%s\n'
                'Type "help", "version" for more information.\n\n'
                '**To stop the server: quit\n'
                % ( __version__)
            )

    # open a socket and start waiting for connections
    def __init__(self, config):
        self.config = config
        self.sock = s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind((config.server_ip, config.port))
            s.listen(1)
            while 1:
                conn, addr = s.accept()
                print('Connection from', addr)
                self.handle(conn, addr)
                conn.close()
                print('Connection closed')
        finally:
            print('Closing')
            s.close()

    # handle a new connection
    def handle(self, conn, addr):
        backup_stdin = sys.stdin
        backup_stdout = sys.stdout
        backup_stderr = sys.stderr
        stdfps = STDFilePointers(conn)
        sys.stdin = stdfps
        sys.stdout = stdfps
        sys.stderr = stdfps
        try:
            try:
                command = conn.recv(1)
                # dispatch depending on command (first char sent should be '-'
                # for the interactive interpreter loop, 'x' for executing code)
                if command == '-':
                    self.interpreterloop(conn, addr)
                else:
                    print('Unexpected input, exiting...')
            except SystemExit as e:
                # raise a SystemExit with message 'quit' to stop the server
                # from a client
                if str(e) == 'quit':
                    print('Stopping server')  # this string will be intercepted by the client...
                    raise  # kill the server
                print('SystemExit')
            except:
                exc, e, tb = sys.exc_info()
                try:
                    print('%s - %s' % (exc, e))
                    print('\n'.join(traceback.format_tb(tb)))
                except:
                    pass
                del tb
                print('Exception:', exc, '-', e, file=sys.__stdout__)
        finally:
            sys.stdin = backup_stdin
            sys.stdout = backup_stdout  #sys.__stdout__
            sys.stderr = backup_stderr  #sys.__stderr__

    # interpreter loop
    def interpreterloop(self, conn, addr):
        _stash = globals()['_stash']
        _, current_state = _stash.runtime.get_current_worker_and_state()
        print(self.banner)
        while (1):
            _stash(sys.stdin.readlines(), persistent_level=1)
            time.sleep(0.5)

#
# The Client
#
# On your desktop, execute rshell.py ###.###.###.### (with the ip address of your server)
# Then, you can type stash commands on the console and wait for their completion on your iOS device.
# Their output is automatically displayed on your console.
# Your desktop and your iOS device need to be on the same local network.
#
class RSHELLClient:
    # connect to the server and start the session
    def __init__(self, server_ip, config):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            s.settimeout(10.0)  # 10 second timeout for connect
            try:
                s.connect((server_ip, config.port))
            except socket.error as msg:
                print("Couldn't connect with the socket-server: %s" % msg)
                sys.exit(1)
            s.settimeout(None)

            self.interpreterloop(s)
        except SystemExit as e:
            if str(e) == 'quit':
                print('Stopping client')
                raise  # kill the client
            print('SystemExit')
        finally:
            s.close()

    def interpreterloop(self, sock):
        sock.send(b'-')  # tell the server we want to get a prompt
        thread.start_new_thread(self.readloop, (sock,))
        self.writeloop(sock)

    def readloop(self, sock):
        while 1:
            try:
                sock.send(sys.stdin.read(1))
            except socket.error:
                return

    def writeloop(self, sock):
        while 1:
            c = sock.recv(1)
            if not c:
                break

            # try to decode ANSI color sequences
            # need to use a buffer and apply a string replace before display the string
            end_main_loop = False
            buffer = ""
            while c != '\n':
                buffer += c
                c = sock.recv(1)
                if not c:
                    end_main_loop = True
                    break
            if not end_main_loop:
                # here an other hack in order to intercept the end of the server
                if buffer == "Stopping server":  # sent from the server
                    raise SystemExit('quit')  # kill the client
                buffer += '\n'


            buffer = buffer.replace('\xc2\x9b', '\033[')

            sys.stdout.write(buffer)
            sys.stdout.flush()

            if end_main_loop:
                break

if __name__ == '__main__':
    from optparse import OptionParser
    usage = ('usage: %prog [-p] -l | remote_server\n'
            '\n'
            'RSHELL allows you to access STASH running on a remote\n'
            'iOS device over an unencrypted socket. Use RSHELL in listening mode\n'
            '(use -l) or to connect to a RSHELL server')
    parser = OptionParser(usage)
    parser.add_option('-l', '--listen', action='store_true', dest='listen', default=False,
                            help='Listen for a remote connection' )
    parser.add_option('-p', '--port', action='store', type='int', dest='port', default=config.port,
                            help='port for rshell to use')
    (options, args) = parser.parse_args()
    if options.port <= 0 or options.port >= 65535:
        parser.error('Invalid port specified')
    if options.listen:
        if len(args) > 0:
            parser.error("-l cannot use be specified with a hostname")
        local_ip = get_local_ip_addr()
        print('RShell server listening on %s:%d' % (local_ip, options.port))
        config.port = options.port
        # blocks until done
        RSHELLServer(config)

    elif len(args) == 1:
        config.server_ip = args[0]
        config.port = options.port
        # blocks until done
        RSHELLClient(config.server_ip, config)
    else:
        parser.error('Invalid arguments specified.')
