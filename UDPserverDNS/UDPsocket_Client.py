import socket

HEADER = 64
FORMAT = 'utf-8'
PORT = 4022
SERVER = socket.gethostbyname(socket.gethostname())
DISCONNECT_MESSAGE = "!DISCONNECT"
ADDR = (SERVER, PORT)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Stream socket for TCP - AF_INET is for IPv4 over the internet
client.connect(ADDR) # Connect to the server

def send(msg): # defining the function to send a message to the server
    message = msg.encode(FORMAT) # encode the message to bytes using UTF-8 encoding
    msg_length = len(message) # get the length of the message
    send_length = str(msg_length).encode(FORMAT) # encode the message length to bytes using UTF-8 encoding
    send_length += b' ' * (HEADER - len(send_length)) # pad the message length to the header size
    client.send(send_length) # send the message length to the server
    client.send(message) # send the actual message to the server
    print(client.recv(2048).decode(FORMAT)) # receive the response from the server and decode it to a string using UTF-8 encoding

send("Hello World!") # send a test message to the server
input() # wait for user input before sending the next message
send("Hello Everyone!") # send another test message to the server
input() # wait for user input before sending the next message
send(DISCONNECT_MESSAGE) # send the disconnect message to the server to close the connection
