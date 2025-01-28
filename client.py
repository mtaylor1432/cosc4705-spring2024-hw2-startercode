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
    # print(f"running with {args}")
    
    # log.debug(f"connecting to server {args.server}")
    try:
        # create a socket object to connect to the server
        s = socket.create_connection((args.server,args.port))
        # print("connected to server")

    except:
        log.error("cannot connect")
        exit(1)

    # here's a nice hint for you...
    # readSet is used in the select function?
    readSet = [s] + [sys.stdin]
    
    try:
        # set the nickname
        nickname = args.nickname
        # print(f"Nickname has been set to: {nickname}")
        
        while True:
            # select.select() is used to wait until there is data to read from a socket
            readable, _, _ = select.select(readSet, [], [])
            
            # loop through all the sockets that are readable
            for source in readable:
                
                # this means a new message is coming in
                if source == s:
                    try:
                            # get the length of the message with recv
                            length_data = s.recv(4)
                            if not length_data:
                                print("Failed to get message length.")
                                return
                            
                            # unpack to convert to integer
                            message_length = struct.unpack('!L', length_data)[0]
    
                            # do the process of recieving the message
                            json_data = b""
                            # keep receiving until the length of the message is reached
                            while len(json_data) < message_length:
                                # get the remaining data
                                remaining_data = s.recv(message_length - len(json_data))
                                # if there is no remaining data, the connection is closed
                                if not remaining_data:
                                    print("Connection closed.")
                                    return
                                # add the remaining data to the json data
                                json_data += remaining_data
   
                            # Parse the JSON data using message.py
                            message = UnencryptedIMMessage()
                            # parsing means to convert the data into a format that the program can understand
                            message.parseJSON(json_data)
    
                            # Display the message to the user
                            print(f"{message.nick}: {message.msg}")  
                    except:
                        log.error("Error receiving message.")
                        s.close()                    
                # this means the user is sending a message
                elif source == sys.stdin:
                    try:
                        # get the user input, strip means to remove any leading or trailing whitespace
                        user_input = sys.stdin.readline().strip()
                        
                        # if the user input is empty, skip it
                        if not user_input:
                             # this skips empty input hopefully
                            continue 
                        
                        # if the user input is quit, close the connection, not sure if that is the server or clients job
                        if user_input.lower() == "quit":
                            print("Quitting...")
                            s.close() 
                        
                        # Create a new message object 
                        message = UnencryptedIMMessage(nickname=nickname, msg=user_input)

                        # Serialize the message using the serialize method which returns a packed size and the JSON data i think
                        packed_size, json_data = message.serialize() 
    
                        # Send the packed size indicating the length of the message
                        s.sendall(packed_size)
    
                        # Send the actual JSON message
                        s.sendall(json_data)
                        # print(f"You: {user_input}")

                    except Exception as e:
                        log.error(f"Error sending message: {e}")
                        s.close()
  
    # if something goes wrong, close the connection
    except:
        log.error("something went wrong...")
    finally:
        s.close()
        log.info("Connection closed.")

if __name__ == "__main__":
    exit(main())

