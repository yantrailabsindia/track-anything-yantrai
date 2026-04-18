import socket

def check_ports(ip, ports):
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((ip, port))
            if result == 0:
                print(f"Port {port} is OPEN")
            else:
                pass

if __name__ == "__main__":
    ip = "192.168.1.12"
    ports = [80, 554, 8000, 8080, 8899, 37777, 34567]
    print(f"Checking ports on {ip}...")
    check_ports(ip, ports)
