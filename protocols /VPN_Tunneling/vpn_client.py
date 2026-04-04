import socket

def send_tunneled_data(message, server_host='127.0.0.1', server_port=65432):
    # Create a UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        # Encapsulation
        # In a real VPN, you would also encrypt the 'payload' here
        payload = message.encode()
        
        print(f"Encapsulating and sending to {server_host}:{server_port}")
        s.sendto(payload, (server_host, server_port))

if __name__ == "__main__":
    msg = "Secret internal network data!"
    send_tunneled_data(msg)