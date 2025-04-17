import socket
import time
import os

hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)

print(f"Hostname: {hostname} / IP Address: {ip_address}")

while True:
  time.sleep(1)