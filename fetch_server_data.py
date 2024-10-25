import socket
import requests
from django.core.management.base import BaseCommand
from ServerList.models import Server
from django.utils import timezone
from datetime import datetime

def get_master_ip_port(config_url):
    try:
        response = requests.get(config_url)
        response.raise_for_status()
        for line in response.text.splitlines():
            if line.startswith("master="):
                master_info = line.split('=')[1]
                master_ip, master_port = master_info.split(':')
                return master_ip, int(master_port)
    except requests.RequestException as e:
        print(f"Failed to fetch master server config: {e}")
        return None, None

def send_alias_str(alias_type, ip, port, sock):
    alias_message = (f"{alias_type}alias=fetch,name=TestName,email=test@example.com,"
                     f"loc=TestLocation,sernum=123456,HHMM=0000,d=data1,v=data2,w=data3")
    sock.sendto(alias_message.encode('utf-8'), (ip, port))

def parse_master_response(data):
    servers = []
    entry_size = 12
    num_entries = len(data) // entry_size
    for i in range(num_entries):
        offset = i * entry_size
        ip_bytes = data[offset:offset+4]
        port_bytes = data[offset+4:offset+6]
        players_bytes = data[offset+6:offset+8]
        ip = socket.inet_ntoa(ip_bytes)
        port = int.from_bytes(port_bytes, "little")
        players = int.from_bytes(players_bytes, "little")
        
        if 1024 <= port <= 65535 and not ip.startswith("3.3."):
            servers.append((ip, port, players))
    return servers

def parse_server_info(data):
    data = data.decode('latin1').replace('\x00', '')
    details = {}

    if data.startswith("#name="):
        segments = data.split(" //")
        for segment in segments:
            if "name=" in segment:
                details['name'] = segment.split("name=")[1].split("[world=")[0].strip()
                if "[world=" in segment:
                    details['world'] = segment.split("[world=")[1].split("]")[0].strip()
            elif "ules: " in segment:
                details['rules'] = segment.split("ules: ")[1].strip()
            elif "ReMix" in segment:
                details['version'] = segment.strip()
    return details

class Command(BaseCommand):
    help = "Fetch server data from WoS master server and save to the database"

    def handle(self, *args, **options):
        config_url = "https://raw.githubusercontent.com/DeadRequiem/DeadRequiem.github.io/main/master_value.txt"
        master_ip, master_port = get_master_ip_port(config_url)
        if not master_ip or not master_port:
            self.stdout.write("Failed to get master server details.")
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)

        # Clear old server data before fetching fresh data
        Server.objects.all().delete()
        self.stdout.write(f"[{timezone.now()}] Cleared old server data.")

        try:
            # Send inquiry to the master server
            send_alias_str("?", master_ip, master_port, sock)
            data, addr = sock.recvfrom(4096)
            server_list = parse_master_response(data)

            # Loop over each server entry and fetch additional details
            for ip, port, players in server_list:
                send_alias_str("P", ip, port, sock)
                
                try:
                    while True:
                        # Receive and parse server data
                        server_data, server_addr = sock.recvfrom(1024)
                        server_details = parse_server_info(server_data)

                        # Save or update server data in the database
                        Server.objects.update_or_create(
                            ip_address=ip,
                            port=port,
                            defaults={
                                'players': players,
                                'name': server_details.get('name', 'Unknown Server'),
                                'world': server_details.get('world', ''),
                                'rules': server_details.get('rules', ''),
                                'version': server_details.get('version', '')
                            }
                        )
                        # Print only essential output
                        self.stdout.write(f"[{datetime.now()}] Server data saved for {ip}:{port}")
                except socket.timeout:
                    pass
        except socket.timeout:
            self.stdout.write("No response from master server within the timeout period.")
        finally:
            sock.close()
