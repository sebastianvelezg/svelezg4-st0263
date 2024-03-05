import os
import dotenv
import subprocess

def load_environment_variables(peer_number):
    if peer_number in ["1", "2", "3"]:
        env_file = os.path.join("env", f".env_peer{peer_number}")
        dotenv.load_dotenv(env_file)
    else:
        print(f"Invalid peer number: {peer_number}")
        exit(1)

def start_peer(peer_number):
    print(f"Starting peer {peer_number} server...")
    server_process = subprocess.Popen(['python3', 'Pserver.py'])
    
    print(f"Starting peer {peer_number} client...")
    client_process = subprocess.Popen(['python3', 'Pclient.py'])

    client_process.wait()
    server_process.terminate()
    server_process.wait()

if __name__ == "__main__":
    choice = input("Choose the peer (1, 2, or 3): ").strip()
    load_environment_variables(choice)
    start_peer(choice)
