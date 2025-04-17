import socket
import time
import os

time.sleep(5) 

hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)

print(f"Hostname: {hostname} / IP Address: {ip_address}", flush=True)

router_links = os.environ.get('router_links')
for link in router_links.split(','):
  try:
    print(f"Router link: {link} -> {socket.gethostbyname(link)}", flush=True)
  except socket.gaierror:
    print(f"Router link: {link} -> Not found", flush=True)

while True:
  time.sleep(1)