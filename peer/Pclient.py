import os
import requests
import json
import threading
import time
import grpc
import p2p_pb2
import p2p_pb2_grpc
import logging


SERVER_URL = os.getenv('SERVER_URL')
SERVER_PORT = os.getenv('SERVER_PORT')
GRPC_URL = os.getenv('GRPC_URL')
GRPC_PORT = os.getenv('GRPC_PORT')

files = []

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def manage_user_files(username, new_file=None):
    filename = f"{username}files.json"
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            user_files = json.load(f)
    else:
        user_files = []

    if new_file:
        user_files.append(new_file)
        with open(filename, 'w') as f:
            json.dump(user_files, f, indent=4)

def login(username, password):
    response = requests.post(f'http://{SERVER_URL}:{SERVER_PORT}/login', json={'username': username, 'password': password, 'grpc_url': GRPC_URL, 'grpc_port': GRPC_PORT})
    if response.status_code == 200:
        manage_user_files(username)
        print(response.json()['message'])
        return True
    else:
        print("Login failed")
        return False
    
def logout(username):
    response = requests.post(f'http://{SERVER_URL}:{SERVER_PORT}/logout', json={'username': username})
    if response.status_code == 200:
        print(response.json()['message'])
    else:
        print("Logout failed")

def send_heartbeat(username):
    while True:
        try:
            response = requests.post(f'http://{SERVER_URL}:{SERVER_PORT}/heartbeat', json={'username': username})
            if response.status_code != 200:
                print("Failed to send heartbeat")
            time.sleep(8)
        except Exception as e:
            print(f"Error sending heartbeat: {e}")
            break

def list_active_peers():
    response = requests.get(f'http://{SERVER_URL}:{SERVER_PORT}/list_peers')
    if response.status_code == 200:
        peers = response.json()
        print("Active peers:")
        for peer in peers:
            print(f"Username: {peer['username']}, gRPC URL: {peer['grpc_url']}, gRPC Port: {peer['grpc_port']}, Status: {peer['status']}, Number of Files: {peer['num_files']}")
        return peers
    else:
        print("Failed to retrieve list of peers")
    
def upload_file(username, filename=None, fileurl=None):
    if not filename or not fileurl:
        filename = input("Enter the filename: ")
        fileurl = input("Enter the file URL: ")

    new_file = {'filename': filename, 'fileurl': fileurl}
    manage_user_files(username, new_file)

    response = requests.post(f'http://{SERVER_URL}:{SERVER_PORT}/upload_file', json={'username': username, 'filename': filename, 'fileurl': fileurl})
    if response.status_code == 200:
        print(response.json()['message'])
    else:
        print("Failed to upload file")

def list_all_files():
    response = requests.get(f'http://{SERVER_URL}:{SERVER_PORT}/list_files')
    if response.status_code == 200:
        files = response.json()
        if files:
            seen_files = set()
            for i, file in enumerate(files, start=1):
                if file['filename'] not in seen_files:
                    print(f"{i}. Filename: {file['filename']}, URL: {file['fileurl']}, Peers: {file['count']}")
                    seen_files.add(file['filename'])
            return files
        else:
            print("No files available.")
            return []
    else:
        print("Failed to retrieve list of files.")
        return []

def list_peers_from_peer(peer):
    with grpc.insecure_channel(f"{peer['grpc_url']}:{peer['grpc_port']}") as channel:
        stub = p2p_pb2_grpc.FileServiceStub(channel)
        response = stub.ListPeers(p2p_pb2.ListPeersRequest())
        print("Peers from peer:", (f"{peer['grpc_url']}:{peer['grpc_port']}"))
        for peer in response.peers:
            print(peer.peerAddress)

def list_files_from_peer(selected_peer):
    with grpc.insecure_channel(f"{selected_peer['grpc_url']}:{selected_peer['grpc_port']}") as channel:
        stub = p2p_pb2_grpc.FileServiceStub(channel)
        try:
            response = stub.ListAllFiles(p2p_pb2.ListAllFilesRequest())
            files = []
            print("Files available:")
            for i, file in enumerate(response.files, start=1):
                stub = p2p_pb2_grpc.FileServiceStub(channel)
                peers_with_file = discover_file_from_peer(stub, file.filename)
                peer_count = len(peers_with_file) if peers_with_file else 0
                print(f"{i}. Filename: {file.filename}, URL: {file.fileurl}, Peers: {peer_count}")
                files.append({'filename': file.filename, 'fileurl': file.fileurl, 'peer_count': peer_count})
            return files
        except grpc.RpcError as e:
            print(f"Failed to list files from peer: {e}")
            return []

def discover_file_from_peer(stub, filename):
    try:
        response = stub.DiscoverFile(p2p_pb2.DiscoverFileRequest(filename=filename))
        if response.peerAddresses:
            peer_info = json.loads(response.peerAddresses)
            logging.info(f"Discovered peers: {peer_info}")
            return peer_info
        else:
            logging.info("Received an empty response for peer addresses.")
            return None
    except json.JSONDecodeError as e:
        logging.error(f"JSON decoding failed for string: {response.peerAddresses}, Error: {e}")
        return None
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return None

def download_file_from_peer( username, selected_peer, filename, fileurl):
    peer_address = f"{selected_peer['grpc_url']}:{selected_peer['grpc_port']}"
    with grpc.insecure_channel(peer_address) as channel:
        stub = p2p_pb2_grpc.FileServiceStub(channel)
        file_chunks = stub.RequestFile(p2p_pb2.RequestFileRequest(filename=filename, fileurl=fileurl, username=selected_peer['username']))

        decoded_filename = None
        decoded_fileurl = None

        for chunk in file_chunks:
            decoded_content = chunk.content.decode()
            decoded_filename, decoded_fileurl = decoded_content.split(", ")
            decoded_filename = decoded_filename.split(": ")[1]
            decoded_fileurl = decoded_fileurl.split(": ")[1]
            break  

        if decoded_filename and decoded_fileurl:
            print(f"Downloaded '{decoded_filename}' with URL '{decoded_fileurl}' from peer: {selected_peer['username']} at {peer_address}")
            upload_file( username, decoded_filename, decoded_fileurl)

        else:
            print("Failed to decode filename and fileurl from the received file chunk.")


def main():
    print("...Login to your account...")
    username = input("Enter username: ")
    password = input("Enter password: ")
    if login(username, password):
        heartbeat_thread = threading.Thread(target=send_heartbeat, args=(username,))
        heartbeat_thread.daemon = True 
        heartbeat_thread.start()
        
        connection_target = None

        while True:
            clear_screen()
            if not connection_target:
                print("Connect to Server or Peer?")
                print("1. Server")
                print("2. Peer")
                connection_choice = input("Connect to (1) Server or (2) Peer?: ").strip()

                if connection_choice == "1":
                    connection_target = 'server'
                elif connection_choice == "2":
                    peers = list_active_peers()
                    for index, peer in enumerate(peers, start=1):
                        print(f"{index}. {peer['username']} - {peer['grpc_url']}:{peer['grpc_port']}")
                    peer_choice = int(input("Choose a peer to connect to by number: "))
                    selected_peer = peers[peer_choice - 1]
                    connection_target = 'peer'


            elif connection_target == 'server':
                print(f"...|  Connected as: {username}  |...")
                print(f"...|  To server |...")
                print(f"...|  {SERVER_URL}:{SERVER_PORT}  |...")
                print("Options:\n")
                print("1. Upload a file")
                print("2. List active peers")
                print("3. List all available files")
                print("4. Change connection")
                print("5. Exit")

                choice = input("Enter choice: ")
                if choice == "1":
                    upload_file(username)
                    input("\nPress Enter to continue...")
                elif choice == "2":
                    list_active_peers()
                    input("\nPress Enter to continue...")
                elif choice == "3":  
                    print("Available files:")
                    files = list_all_files()
                    if not files:
                        print("No files available.")
                    input("\nPress Enter to continue...")
                elif choice == "4":
                    connection_target = None 
                elif choice == "5":
                    logout(username)
                    break

            elif connection_target == 'peer':
                print(f"...| Connected as: {username} |...")
                print(f"...| To Peer: {selected_peer['username']} |...")
                print(f"...| {selected_peer['grpc_url']}:{selected_peer['grpc_port']} |...")
                print("Peer Options:\n")
                print("1. List files from peer")
                print("2. Download file from peer")
                print("3. Upload a file")
                print("4. Change connection")
                print("5. Exit")

                peer_action = input("Enter choice: ")

                if peer_action == "1":
                    list_files_from_peer(selected_peer)
                    input("\nPress Enter to continue...")
                elif peer_action == "2":
                    files = list_files_from_peer(selected_peer)
                    if files:
                        file_index = int(input("\nSelect the file number to download: ")) - 1
                        if 0 <= file_index < len(files):
                            selected_file = files[file_index]
                            filename = selected_file['filename']
                            fileurl = selected_file['fileurl']
                            peer_grpc_url = selected_peer['grpc_url']
                            peer_grpc_port = selected_peer['grpc_port']

                            channel = grpc.insecure_channel(f'{peer_grpc_url}:{peer_grpc_port}')
                            stub = p2p_pb2_grpc.FileServiceStub(channel)
                            peers_with_file = discover_file_from_peer(stub, filename)

                            if peers_with_file:
                                print(f"\nPeers that have '{filename}':")
                                for index, peer_str in enumerate(peers_with_file, start=1):
                                    peer_username, address = peer_str.split(' ', 1)
                                    grpc_url, grpc_port = address.split(':', 1)
                                    print(f"{index}. Username: {peer_username}, Address: {grpc_url}:{grpc_port}")

                                peer_index = int(input("\nSelect a peer to download from by number: ")) - 1
                                if 0 <= peer_index < len(peers_with_file):
                                    peer_str = peers_with_file[peer_index]
                                    peer_username, address = peer_str.split(' ', 1)
                                    grpc_url, grpc_port = address.split(':', 1)
                                    selected_peer = {'username': peer_username, 'grpc_url': grpc_url, 'grpc_port': grpc_port}

                                    print(f"\nAttempting to download '{filename}' from {selected_peer['username']} at {selected_peer['grpc_url']}:{selected_peer['grpc_port']}...")
                                    download_file_from_peer(username, selected_peer, filename, fileurl)
                                else:
                                    print("Invalid peer selection.")

                            else:
                                print("No peers found with the selected file.")
                        else:
                            print("Invalid file selection.")
                    input("\nPress Enter to continue...")
                elif peer_action == "3":
                    upload_file(username)
                    input("\nPress Enter to continue...")
                elif peer_action == "4":
                        connection_target = None
                elif peer_action == "5":
                    logout(username)
                    break
                else:
                    print("Invalid option.")
                    input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()