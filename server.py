import socket
import json
import argparse
import logging
import select
import struct
import time
import threading
from message import UnencryptedIMMessage





def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', '-p', 
        dest="port", 
        type=int, 
        default='9999',
        help='port number to listen on')
    parser.add_argument('--loglevel', '-l', 
        dest="loglevel",
        choices=['DEBUG','INFO','WARN','ERROR', 'CRITICAL'], 
        default='INFO',
        help='log level')
    args = parser.parse_args()
    return args


def main():
    args = parseArgs()    

    # set up logging
    log = logging.getLogger("myLogger")
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
    level = logging.getLevelName(args.loglevel)
    log.setLevel(level)
    log.info(f"running with {args}")
    
    log.debug("waiting for new clients...")
    serverSock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    serverSock.bind(("",args.port))
    serverSock.listen()

    clientList = []

    try:
        while True:
            
            readable, _, _ = select.select([serverSock] + clientList, [], [])

            for source in readable:
                # new connection coming
                if source == serverSock:
                    c, addr = serverSock.accept()
                    log.info(f"New client connected: {addr}")
                    clientList.append(c)
                else:
                    
                    try:
                        # Receive the message length
                        length_data = source.recv(4)
                        if not length_data:
                            log.error("Client disconnected")
                            clientList.remove(source)
                            source.close()
                            continue
                        if len(length_data) < 4:
                            log.error("Incomplete message length received")
                            continue

                        # Unpack the message length
                        msg_size = struct.unpack('!L', length_data)[0]

                        # Receive the full message
                        buffer = b""
                        while len(buffer) < msg_size:
                            extra = source.recv(msg_size - len(buffer))
                            if not extra:
                                log.error("Client disconnected")
                                clientList.remove(source)
                                source.close()
                                continue 
                            buffer += extra

                        # Parse the message
                        message = UnencryptedIMMessage()
                        message.parseJSON(buffer)
                        log.info(f"Received: {message}")

                        if message.msg.lower() == "quit":  # Client wants to disconnect
                            log.info(f"Client {source.getpeername()} disconnected.")
                            clientList.remove(source)  # Remove this client from the list
                            source.close()  # Close this client's socket
                            continue
                        
                        # Broadcast the message to all other clients
                        packed_size, json_data = message.serialize()
                        for client in clientList:
                            if client is not source:
                                try:
                                    client.sendall(packed_size + json_data)
                                except Exception as e:
                                    log.error(f"Error sending to a client: {e}")
                                    clientList.remove(client)
                                    client.close()
                    except ConnectionResetError as e:
                        # Handle client disconnection
                        log.warning(f"Client disconnected: {e}")
                        clientList.remove(source)
                        source.close()

    except KeyboardInterrupt:
        log.info("Shut down time!")  
    finally:
        # Close all connections
        for c in clientList:
            c.close()
        serverSock.close()
   

if __name__ == "__main__":
    exit(main())

