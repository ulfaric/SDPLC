import socket
from datetime import datetime

# Define the server address and port
server_address = ('192.168.5.3', 12345)  # Replace with your Linux server's IP address

# Create a TCP socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
    # Connect to the server
    client_socket.connect(server_address)

    # Receive the time from the server
    server_time = client_socket.recv(1024).decode()

    # Get the current time on the Windows machine
    windows_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

    # Print both times
    print(f"Server time: {server_time}")
    print(f"Windows time: {windows_time}")

    # Calculate the time difference
    server_time_dt = datetime.strptime(server_time, '%Y-%m-%d %H:%M:%S.%f')
    windows_time_dt = datetime.strptime(windows_time, '%Y-%m-%d %H:%M:%S.%f')
    time_difference = windows_time_dt - server_time_dt

    print(f"Time difference: {time_difference}")
