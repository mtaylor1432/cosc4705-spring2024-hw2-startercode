"""
A skeleton from which you should write your client.
"""


import socket
import json
import argparse
import logging
import select
import sys
import threading
import time
import datetime
import struct

from message import UnencryptedIMMessage


def parseArgs():
    """
    parse the command-line arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', '-p', 
        dest="port", 
        type=int, 
        default='9999',
        help='port number to connect to')
    parser.add_argument('--server', '-s', 
        dest="server", 
        required=True,
        help='server to connect to')       
    parser.add_argument('--nickname', '-n', 
        dest="nickname", 
        required=True,
        help='nickname')                
    parser.add_argument('--loglevel', '-l', 
        dest="loglevel",
        choices=['DEBUG','INFO','WARN','ERROR', 'CRITICAL'], 
        default='INFO',
        help='log level')
    args = parser.parse_args()
    return args    


def main():
    args = parseArgs()

    # set up the logger
    log = logging.getLogger("myLogger")
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
    level = logging.getLevelName(args.loglevel)
    
    log.setLevel(level)
    print(f"running with {args}")
    
    log.debug(f"connecting to server {args.server}")
    try:
        s = socket.create_connection((args.server,args.port))
        print("connected to server")

    except:
        log.error("cannot connect")
        exit(1)

    # here's a nice hint for you...
    readSet = [s] + [sys.stdin]
    
    try:
        nickname = args.nickname
        print(f"Nickname has been set to: {nickname}")
        
        while True:
            readable, _, _ = select.select(readSet, [], [])
            
            for source in readable:
                
                if source == s:
                    try:
                            # Receive the length of the message
                            length_data = s.recv(4)
                            if not length_data:
                                print("Failed to get message length.")
                                return
                            
                            # unpack
                            message_length = struct.unpack('!L', length_data)[0]
    
                            # recieve message
                            json_data = b""
                            while len(json_data) < message_length:
                                remaining_data = s.recv(message_length - len(json_data))
                                if not remaining_data:
                                    print("Connection closed.")
                                    return
                                json_data += remaining_data
   
                            # Parse the JSON data into an UnencryptedIMMessage
                            message = UnencryptedIMMessage()
                            message.parseJSON(json_data)
    
                            # Display the message
                            print(f"{message.nick}: {message.msg}")  
                    except:
                        log.error("Error receiving message.")
                        return
                        
                    
                elif source == sys.stdin:
                    try:
                        # get message from client
                        user_input = sys.stdin.readline().strip()
                        
                        if not user_input:
                            continue  # this skips empty input hopefully
                        
                        if user_input.lower() == "quit":
                            print("Quitting...")
                            s.close() 
                            return
                        
                        message = UnencryptedIMMessage(nickname=nickname, msg=user_input)

                        # Serialize the message using the serialize method
                        packed_size, json_data = message.serialize() 
    
                        # Send the packed size indicating the length of the message
                        s.sendall(packed_size)
    
                        # Send the actual JSON message
                        s.sendall(json_data)
                        # print(f"You: {user_input}")

                        
                    except Exception as e:
                        log.error(f"Error sending message: {e}")
                        return  

    except:
        log.error("something went wrong...")
    finally:
        s.close()
        log.info("Connection closed.")

if __name__ == "__main__":
    exit(main())

