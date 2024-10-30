import socket
import requests
from django.core.management.base import BaseCommand
from ServerList.models import Server, FetchLog, MasterServer
from django.utils import timezone
from datetime import datetime

# ---------------------------- #
# Function to fetch master IP and port from config
# ---------------------------- #
def get_master_ip_port(config_url):
    try:
        response = requests.get(config_url)
        response.raise_for_status()
        for line in response.text.splitlines():
            if line.startswith("master="):
                master_info = line.split('=')[1]
                master_ip, master_port = master_info.split(':')
                print(f"[INFO] Retrieved Master IP: {master_ip}, Port: {master_port}")
                return master_ip, int(master_port)
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch master server config: {e}")
        return None, None

# ---------------------------- #
# Send alias string to query server
# ---------------------------- #
def send_alias_str(alias_type, ip, port, sock):
    # Construct the alias message based on the alias type
    alias_message = (f"{alias_type}alias=fetch,name=TestName,email=test@example.com,"
                     f"loc=TestLocation,sernum=FFFFFF,HHMM=0000,d=1A2B3C4D,v=071DFC29,w=1A2B3C4D")
    sock.sendto(alias_message.encode('utf-8'), (ip, port))
    print(f"[INFO] Sent alias '{alias_type}' to {ip}:{port}")

# ---------------------------- #
# Parse response from master server
# ---------------------------- #
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
            print(f"[INFO] Server found - IP: {ip}, Port: {port}, Players: {players}")
    return servers

# ---------------------------- #
# Parse individual server information
# ---------------------------- #
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
                # Concatenate "ReMix" with any version information found
                details['version'] = "ReMix " + segment.split("ReMix")[1].strip()
            else:
                details['version'] = "Mix"  # Default to Mix if 'ReMix' tag is missing

    return details

# ---------------------------- #
# Fetch and Update Online Player Counts
# ---------------------------- #
def update_online_player_count(server_ip, server_port, sock):
    send_alias_str("Q", server_ip, server_port, sock)
    
    try:
        data, _ = sock.recvfrom(1024)
        serial_numbers = data.decode().lstrip("Q").split(",")
        
        # Filter for valid entries: allow hexadecimal or entries starting with "SOUL"
        serial_numbers = [
            sn for sn in serial_numbers if sn and 
            (all(c in '0123456789ABCDEF' for c in sn.upper()) or sn.startswith("SOUL"))
        ]
        
        return len(serial_numbers)
    except socket.timeout:
        print(f"[WARNING] Timeout while fetching player count from {server_ip}:{server_port}")
        return 0

# ---------------------------- #
# Django Command to Fetch Data
# ---------------------------- #
class Command(BaseCommand):
    help = "Fetch server data from all active WoS master servers and save to the database"

    def handle(self, *args, **options):
        # Clear old server data before fetching fresh data
        Server.objects.all().delete()
        self.stdout.write(f"[{timezone.now()}] Cleared old server data.")

        # Retrieve active master servers, ordered by priority
        active_masters = MasterServer.objects.filter(is_active=True).order_by('priority')
        if not active_masters:
            self.stdout.write("No active master servers found.")
            return

        # Loop over each active master server to attempt fetching data
        for master in active_masters:
            self.stdout.write(f"Attempting to fetch from master server {master.ip_address}:{master.port}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            
            try:
                # Send inquiry to the current master server
                send_alias_str("?", master.ip_address, master.port, sock)
                data, addr = sock.recvfrom(4096)
                server_list = parse_master_response(data)

                # Loop over each server entry and fetch additional details and player count
                for ip, port, players in server_list:
                    send_alias_str("P", ip, port, sock)

                    try:
                        # Receive and parse server data
                        server_data, server_addr = sock.recvfrom(1024)
                        server_details = parse_server_info(server_data)

                        # Fetch online player count using "Q" alias
                        player_count = update_online_player_count(ip, port, sock)

                        # Save or update server data in the database with actual player count
                        Server.objects.update_or_create(
                            ip_address=ip,
                            port=port,
                            defaults={
                                'players': player_count,  # Set the accurate player count here
                                'name': server_details.get('name', 'Unknown Server'),
                                'world': server_details.get('world', ''),
                                'rules': server_details.get('rules', ''),
                                'server_type': server_details.get('version', 'Mix'),  # Set server type
                                'master_server': master  # Link server to the master server
                            }
                        )
                        self.stdout.write(f"[{datetime.now()}] Server data saved for {ip}:{port} with {player_count} players")

                    except socket.timeout:
                        # Server did not respond within the timeout
                        Server.objects.update_or_create(
                            ip_address=ip,
                            port=port,
                            defaults={
                                'players': players,
                                'name': f"Waiting for Server Ping from {ip}:{port}",
                                'world': '',
                                'rules': '',
                                'server_type': 'Mix',
                                'master_server': master
                            }
                        )
                        self.stdout.write(f"[{datetime.now()}] No response from {ip}:{port}; marked as waiting.")

            except socket.timeout:
                self.stdout.write(f"No response from master server {master.ip_address}:{master.port}.")
            finally:
                sock.close()

        # Update or create the fetch timestamp
        FetchLog.objects.update_or_create(id=1, defaults={'last_fetched': timezone.now()})
        self.stdout.write("Fetch timestamp updated.")