import socket
import requests
from django.core.management.base import BaseCommand
from ServerList.models import Server, FetchLog
from django.utils import timezone
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db import transaction

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
                     f"loc=TestLocation,sernum=FFFFFFF,HHMM=0000,d=1A2B3C4D,v=071DFC29,w=1A2B3C4D")
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
    data = data.decode('latin1').replace('\x00', '')  # Clean up null characters
    details = {}

    if data.startswith("#name="):  # Check for the expected beginning of the response
        segments = data.split(" //")
        for index, segment in enumerate(segments):
            if "name=" in segment and index == 0:
                details['name'] = segment.split("name=")[1].split("[world=")[0].strip()
                if "[world=" in segment:
                    details['world'] = segment.split("[world=")[1].split("]")[0].strip()
            elif "ules: " in segment and index == 1:
                details['rules'] = segment.split("ules: ")[1].strip()
            elif index == 5 and "remix" in segment.lower():
                details['server_type'] = "ReMix"
        # Default to Mix if ReMix tag was not found in the specific index
        details.setdefault('server_type', "Mix")

    return details

def query_server(ip, port, players):
    # Create a new socket for each server query
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(1.0)
        send_alias_str("P", ip, port, sock)

        try:
            server_data, _ = sock.recvfrom(1024)
            server_details = parse_server_info(server_data)
            return {
                'ip_address': ip,
                'port': port,
                'players': players,
                'name': server_details.get('name', 'Unknown Server'),
                'world': server_details.get('world', ''),
                'rules': server_details.get('rules', ''),
                'server_type': server_details.get('server_type', 'Mix')
            }
        except socket.timeout:
            print(f"[WARNING] Server {ip}:{port} timed out.")
            return None

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

            # Shared list to collect server details
            server_details_list = []

            # Use ThreadPoolExecutor to query multiple servers concurrently
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(query_server, ip, port, players): (ip, port) for ip, port, players in server_list}
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        server_details_list.append(result)

            # Perform a bulk update to the database in a single transaction
            with transaction.atomic():
                for server_details in server_details_list:
                    Server.objects.update_or_create(
                        ip_address=server_details['ip_address'],
                        port=server_details['port'],
                        defaults={
                            'players': server_details['players'],
                            'name': server_details['name'],
                            'world': server_details['world'],
                            'rules': server_details['rules'],
                            'server_type': server_details['server_type']
                        }
                    )

            self.stdout.write(f"[{datetime.now()}] All server data saved.")
        
        except socket.timeout:
            self.stdout.write("No response from master server within the timeout period.")
        
        finally:
            # Update or create the fetch timestamp
            FetchLog.objects.update_or_create(id=1, defaults={'last_fetched': timezone.now()})
            sock.close()
            self.stdout.write("Fetch timestamp updated.")
