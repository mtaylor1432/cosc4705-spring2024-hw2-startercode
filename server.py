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
    
    # log.debug("waiting for new clients...")
    # socket.socket creates a new socket object and binds it to the specified port
    serverSock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    serverSock.bind(("",args.port))
    # this can hold maximum number of clients
    serverSock.listen()

    # holds the list of clients connected to the server
    clientList = []

    try:
        while True:
            
            # select.select() is used to wait until there is data to read from a socket
            readable, _, _ = select.select([serverSock] + clientList, [], [])

            # loop through all the sockets that are readable
            for source in readable:
                # new connection coming
                if source == serverSock:
                    c, addr = serverSock.accept()
                    log.info(f"New client connected: {addr}")
                    clientList.append(c)
                # existing client sending a message
                else:
                    
                    try:
                        # Receive the message length
                        length_data = source.recv(4)
                        # If the client disconnected for any reason
                        if not length_data:
                            log.error("Client disconnected")
                            clientList.remove(source)
                            source.close()
                            continue
                        # If the message length is less than 4 bytes, it is incomplete
                        if len(length_data) < 4:
                            log.error("Incomplete message length received")
                            # remember: continue command is used to skip the rest of the code inside the loop for the current iteration
                            continue

                        # Unpack the message length to convert it to an integer
                        msg_size = struct.unpack('!L', length_data)[0]

                        # Receive the full message
                        # buffer is used to store the message
                        buffer = b""
                        # While the buffer is less than the message size, keep receiving data
                        while len(buffer) < msg_size:
                            # extra is used to store the data received
                            extra = source.recv(msg_size - len(buffer))
                            # If the client disconnected for any reason
                            if not extra:
                                log.error("Client disconnected")
                                clientList.remove(source)
                                source.close()
                                # continue command again!
                                continue 
                            # Add the received data to the buffer
                            buffer += extra

                        # Parse the message using message.py
                        message = UnencryptedIMMessage()
                        # parsing means to convert the data into a format that the program can understand
                        message.parseJSON(buffer)
                        # log.info(f"Received: {message}")

                        # If the message is "quit", the client wants to disconnect
                        if message.msg.lower() == "quit":  
                            log.info(f"Client {source.getpeername()} disconnected.")
                            # Remove this client from the list
                            clientList.remove(source)
                            # Close this client's socket  
                            source.close()  
                            continue
                        
                        # Broadcast the message to all other clients with serialized message which is the packed size and json data??
                        packed_size, json_data = message.serialize()
                        for client in clientList:
                            # only send to clients that are not the source
                            if client is not source:
                                try:
                                    # sendall sends the message to the client
                                    client.sendall(packed_size + json_data)
                                # If there is an error sending to a client, remove the client from the list and close the connection
                                except Exception as e:
                                    log.error(f"Error sending to a client: {e}")
                                    clientList.remove(client)
                                    client.close()
                    # If there is an error receiving the message, remove the client from the list and close the connection
                    except ConnectionResetError as e:
                        # Handle client disconnection
                        log.warning(f"Client disconnected: {e}")
                        clientList.remove(source)
                        source.close()
    # If the server is shut down, close all connections and the server socket
    except KeyboardInterrupt:
        log.info("Shut down time!")  
    finally:
        # Close all connections
        for c in clientList:
            c.close()
        serverSock.close()
   
if __name__ == "__main__":
    exit(main())

