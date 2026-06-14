import socket
import threading

HEADER = 64
FORMAT = 'utf-8'
PORT = 4022
SERVER = socket.gethostbyname(socket.gethostname())
DISCONNECT_MESSAGE = "!DISCONNECT"
ADDR = (SERVER, PORT)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Stream socket for TCP - AF_INET is for IPv4 over the internet
server.bind(ADDR) # Bind works on a tuple of (IP, PORT). so anything connecting to that address will be connected to this socket

def handle_client(conn, addr): # handle the individual client connection to the server
    print(f"[NEW CONNECTION] {addr} connected.") # print the address of the new connection
    connected = True
    while connected:
        msg_length = conn.recv(HEADER).decode(FORMAT) # receive the message length from the client. This is a blocking function that waits for a message to be received. The message length is sent as a string, so we decode it to get the integer value. decodes the bytes object to a string using UTF-8 encoding
        if msg_length: # if the message length is not empty, we convert it to an integer and receive the actual message from the client
            msg_length = int(msg_length) # convert the message length to an integer
            msg = conn.recv(msg_length).decode(FORMAT) # receive the actual message from the client
            if msg == DISCONNECT_MESSAGE: # if the message is the disconnect message, we set connected to False to break the loop and close the connection
                connected = False
            print(f"[{addr}] {msg}")
            conn.send("Message received".encode(FORMAT)) # send a response back to the client to acknowledge that the message was received
    
    conn.close() # close the connection when done

def start(): # defining the function to start the server
    server.listen() # listen for new connections
    print(f"[STARTING] Server is starting on {SERVER}")
    while True:
        conn, addr = server.accept() # accept() is a blocking function that waits for a new connection. When a new connection is made, it returns a new socket object (conn) and the address of the client (addr)
        thread = threading.Thread(target=handle_client, args=(conn, addr)) # when a new connection is made, we pass the connection to "handle_client" function with a new thread so that the server can continue to listen for new connections while handling the current one
        thread.start() # start the new thread
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}") # print the number of active connections. We subtract 1 because the main thread is also counted in active_count()

print(f"[LISTENING] Server is listening on {SERVER}")
start() # start the server