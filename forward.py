#!/usr/bin/env python3.9
import socket
import subprocess
import threading
import os
import signal
import time
import http.server
import socketserver

HOST = '0.0.0.0'  # all interfaces
LISTEN_PORT = 8090  # Port to listen on
TARGET_PORT = 8091  # Port to redirect connections to
HEALTH_PORT = 8092  # Port to listen on for health check
PROGRAM = ['/bin/bash', '/usr/bin/stream.sh']
TIMEOUT = 60
connections = 0
connLock = threading.Lock()
process = None  # To hold the subprocess reference

def handle_client(conn):
    global connections, process, startingp
    with connLock:
        connections += 1
        print(f'Active connections: {connections}')
    
    if connections == 1:
        # Start the external program on the target port
        process = subprocess.Popen(PROGRAM, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
        print(f"Starting process {process.pid}")
        startingp = True

    if startingp:
        time.sleep(5)
        startingp = False

    conn.settimeout(TIMEOUT)  # Set timeout on client socket

    # Connect to the target port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as target_conn:
        target_conn.connect((HOST, TARGET_PORT))
        target_conn.settimeout(TIMEOUT)  # Set timeout on target socket
        
        # Redirect data between the client and the target port
        clientConn = threading.Thread(target=forward_data, args=(conn, target_conn))
        ffConn = threading.Thread(target=forward_data, args=(target_conn, conn))

        # start all threads
        clientConn.start()
        ffConn.start()

        # wait for ffConn to finish
        ffConn.join()

        try:
            conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass  # Socket may already be closed or in invalid state
        conn.close()
        try:
            target_conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass  # Socket may already be closed or in invalid state
        target_conn.close()
        with connLock:
            if connections>1:
                connections -= 1
        print(f'Active connections: {connections}')
        if connections == 1:
            time.sleep(60) # add 1 minute timeout
            with connLock:
                if connections>0:
                    connections -= 1
                    print(f'Active connections: {connections}')
                    if connections == 0: # Kill only if after one minute still zero connections
                        try:
                            print(f"Killing process {process.pid}")
                            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                            print("Process terminated.")
                        except Exception as e:
                            print(f"Unable to kill {process.pid} because {e}")


def forward_data(source, target):
    try:
        while True:
            data = source.recv(4096)  # Read data from the source
            if not data:
                break  # Exit if no data is received
            target.sendall(data)  # Send the data to the target socket
    except ConnectionAbortedError:
        print("Connection was aborted.")
    except socket.timeout:
        print(f"No data received for {TIMEOUT} seconds, closing")
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

# Health check HTTP server handler
class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"health ok\n")

    def log_message(self, format, *args):
        # Override to suppress default logging
        return


def run_health_server():
    with socketserver.TCPServer((HOST, HEALTH_PORT), HealthHandler) as httpd:
        print(f"Health check server listening on {HOST}:{HEALTH_PORT}...")
        httpd.serve_forever()


if __name__ == "__main__":
    # Start main server in a separate thread
    main_thread = threading.Thread(target=main, daemon=True)
    main_thread.start()

    # Run the healthcheck server in the main thread (or you can also run in another thread)
    run_health_server()
