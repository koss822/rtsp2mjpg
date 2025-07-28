#!/usr/bin/env python
import socket
import subprocess
import threading
import os
import signal
import time
import uuid

HOST = '0.0.0.0'  # all interfaces
LISTEN_PORT = 8090  # Port to listen on
TARGET_PORT = 8091  # Port to redirect connections to
PROGRAM = ['/bin/bash', '/usr/bin/stream.sh']
connections = 0
lock = threading.Lock()
process = None  # To hold the subprocess reference

def handle_client(conn):
    global connections, process, startingp
    with lock:
        connections += 1
        print(f'Active connections: {connections}')
    
    if connections == 1:
        # Start the external program on the target port
        process = subprocess.Popen(PROGRAM)
        print(f"Starting process {process.pid}")
        startingp = True

    if startingp:
        time.sleep(5)
        startingp = False

    # Connect to the target port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as target_conn:
        target_conn.connect((HOST, TARGET_PORT))
        
        # Redirect data between the client and the target port
        threads = []
        threads.append(threading.Thread(target=forward_data, args=(conn, target_conn)))
        threads.append(threading.Thread(target=forward_data, args=(target_conn, conn)))

        # start all threads
        for thread in threads:
            thread.start()

        # wait for all threads to finish
        for thread in threads:
            thread.join()

        conn.close()
        target_conn.close()
        connections -= 1
        print(f'Active connections: {connections}')
        if connections == 0:
            time.sleep(60) # add 1 minute timeout
            if connections == 0: # Kill only if after one minute still zero connections
                print(f"Killing process {process.pid}")
                os.kill(process.pid, signal.SIGTERM)  # Terminate the subprocess


def forward_data(source, target):
    try:
        while True:
            data = source.recv(4096)  # Read data from the source
            if not data:
                break  # Exit if no data is received
            target.sendall(data)  # Send the data to the target socket
    except ConnectionAbortedError:
        print("Connection was aborted.")
    except Exception as e:
        print(e)

    

def main():
    global connkiller, startingp
    connkiller = {}
    startingp = False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, LISTEN_PORT))
        s.listen()
        print(f'Listening on {HOST}:{LISTEN_PORT}...')

        while True:
            conn, addr = s.accept()
            print(f'Connected by {addr}')
            threading.Thread(target=handle_client, args=(conn,)).start()

if __name__ == "__main__":
    main()
