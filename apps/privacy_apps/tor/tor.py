""" This module is made for proof-of-concept purposes only.
It will be re-written and its security will be tested.

It doesn't guarantee your privacy and wasn't tested for leaks in any way.
It just shows a working Tor control app to demo ZeroPhone capabilities,
as well as to discuss application UX."""

#TODO:
#-Compile new Tor version for Raspbian
#- Find a usable Tor-supporting request module for Python that doesn't require monkeypatching

#You mgith want to do pip install requests -U and pip install pysocks stem, if the script doesn't work for you.

#Snippets taken from:
#STEM Pyhon library
#https://github.com/jamesacampbell/python-examples/
#http://stackoverflow.com/questions/18561778/how-do-i-get-the-ip-address-of-the-tor-entry-node-in-use
#... some other places - lost links =(


from stem.control import Controller
from stem import Signal, CircStatus
import requests
import socks
import socket

from zpui_lib.helpers import setup_logger

logger = setup_logger(__name__, "info")

socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)

def getaddrinfo(*args):
  return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (args[0], args[1]))]

def monkeypatch_socket(func):
  def wrapper(*args, **kwargs):
    socket._socket_ = socket.socket
    socket.socket = socks.socksocket
    result = func(*args, **kwargs)
    socket.socket = socket._socket_
    return result
  return wrapper

def monkeypatch_getaddrinfo(func):
  def wrapper(*args, **kwargs):
    socket._getaddrinfo_ = socket.getaddrinfo
    socket.getaddrinfo = getaddrinfo
    result = func(*args, **kwargs)
    socket.getaddrinfo = socket._getaddrinfo_
    return result
  return wrapper


#Python - even monkeypatching is beautiful.


@monkeypatch_socket
def get_external_ip():
  proxies = {
    'http': 'socks5://localhost:9050',
    'https': 'socks5://localhost:9050'
  }
  r = requests.Session()
  response = r.get("http://httpbin.org/ip", proxies=proxies)
  ip_str = response.json()['origin']
  return ip_str

@monkeypatch_socket
@monkeypatch_getaddrinfo
def get_duckduckgo():
  ddg = requests.get('http://3g2upl4pq6kufc4m.onion')
  return ddg

def get_entry_ips():
  with Controller.from_socket_file(path = "/tmp/tor/socket") as controller:
    controller.authenticate()  
    circ_descriptions = {}
    for circ in controller.get_circuits():
      if circ.status != CircStatus.BUILT:
        continue  # skip circuits that aren't yet usable
      entry_fingerprint = circ.path[0][0]
      entry_descriptor = controller.get_network_status(entry_fingerprint, None)
      if entry_descriptor:
        circ_descriptions[circ.id] = str(entry_descriptor.address)
  return circ_descriptions

def renew_connection():
    with Controller.from_socket_file(path = "/tmp/tor/socket") as controller:
        controller.authenticate()
        controller.signal(Signal.NEWNYM)	

def get_traffic_info():
    with Controller.from_socket_file(path = "/tmp/tor/socket") as controller:
      controller.authenticate()  
      bytes_read = controller.get_info("traffic/read")
      bytes_written = controller.get_info("traffic/written")
    return (bytes_read, bytes_written)

def tor_is_available():
    try:
        Controller.from_socket_file(path = "/tmp/tor/socket")
    except:
        return False
    else:
        return True

def main():
    info = get_traffic_info
    logger.info("My Tor relay has read %s bytes and written %s." % info )
    logger.info(get_external_ip())
    logger.info(get_entry_ips())
    ddg = get_duckduckgo()	
    logger.debug(ddg.content[:100])

    #desc = controller.get_hidden_service_descriptor('3g2upl4pq6kufc4m') #not supported in Raspbian Tor
  

if __name__ == "__main__":
    main()
