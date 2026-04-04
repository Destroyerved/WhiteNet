import socket

def start_server(host='127.0.0.1', port=65432):
    # Create a UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((host, port))
        print(f"VPN Server listening on {host}:{port}...")

        while True:
            # Receive encapsulated data
            data, addr = s.recvfrom(1024)
            print(f"Received tunnel packet from {addr}")
            
            # Decapsulation (Extraction)
            original_message = data.decode()
            print(f"Decapsulated Message: {original_message}")

if __name__ == "__main__":
    start_server()