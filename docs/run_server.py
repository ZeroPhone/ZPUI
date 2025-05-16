#!/usr/bin/env python

import os
import sys
import traceback

os.chdir('_build/html')

if os.fork():
    sys.exit()

from functools import partial
import contextlib

try:
    import http.server as server
    # ensure dual-stack is not disabled; ref #38907
    class DualStackServer(server.ThreadingHTTPServer):
        def server_bind(self):
            # suppress exception when protocol is IPv4
            with contextlib.suppress(Exception):
                self.socket.setsockopt(
                    socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            return super().server_bind()
    server.test(
        HandlerClass=partial(server.SimpleHTTPRequestHandler, directory=os.getcwd()),
        ServerClass=DualStackServer,
    )
except:
    traceback.print_exc()
    import SimpleHTTPServer
    SimpleHTTPServer.test()

