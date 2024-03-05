import os
import logging
import grpc
import requests
import p2p_pb2
import p2p_pb2_grpc
from concurrent import futures
import json

GRPC_PORT = os.getenv('GRPC_PORT')
SERVER_URL = os.getenv('SERVER_URL')
SERVER_PORT = os.getenv('SERVER_PORT')

logging.basicConfig(level=logging.INFO)

class FileServiceImpl(p2p_pb2_grpc.FileServiceServicer):
    def ListFiles(self, request, context):
        logging.info(f"Received ListFiles request from {context.peer()}")
        response = requests.get(f'http://{SERVER_URL}:{SERVER_PORT}/list_files')
        if response.status_code == 200:
            files = response.json()
            logging.info(f"Sending file list to {context.peer()}: {files}")
            return p2p_pb2.ListFilesResponse(files=[p2p_pb2.File(filename=file['filename'], fileurl=file['fileurl']) for file in files])
        else:
            logging.error(f"Failed to retrieve file list from server for {context.peer()}")
            context.abort(grpc.StatusCode.INTERNAL, "Failed to retrieve file list from server")

    def RequestFile(self, request, context):
        logging.info(f"Received RequestFile for '{request.filename}' from {context.peer()}")
        
        peer_files_json = f"{request.username}files.json"
        try:
            with open(peer_files_json, 'r') as f:
                peer_files = json.load(f)
                file_info = next((item for item in peer_files if item['filename'] == request.filename), None)
                if not file_info:
                    logging.error(f"File {request.filename} not found in {request.username}'s file list.")
                    return
        except FileNotFoundError:
            logging.error(f"No file list found for {request.username} in {peer_files_json}.")
            return
        except Exception as e:
            logging.error(f"Error reading {request.username}files.json: {e}")
            return
        
        response_content = f"Filename: {file_info['filename']}, FileURL: {file_info['fileurl']}".encode()
        yield p2p_pb2.FileChunk(content=response_content)

        logging.info(f"Returned file info for '{request.filename}' to {request.username}")

    def DiscoverFile(self, request, context):
        logging.info(f"Received DiscoverFile for '{request.filename}' from {context.peer()}")
        response = requests.post(f'http://{SERVER_URL}:{SERVER_PORT}/discover_file', json={'filename': request.filename})
        if response.status_code == 200:
            peers_info = response.json()
            peer_addresses = [f"{peer['username']} {peer['grpc_url']}:{peer['grpc_port']}" for peer in peers_info]
            peer_addresses_json = json.dumps(peer_addresses) 
            logging.info(f"File '{request.filename}' discovered on peers: {', '.join(peer_addresses)} for {context.peer()}")
            return p2p_pb2.DiscoverFileResponse(peerAddresses=peer_addresses_json)
        else:
            logging.info(f"File '{request.filename}' not found for {context.peer()}")
            context.abort(grpc.StatusCode.NOT_FOUND, "File not found")

    def ListAllFiles(self, request, context):
        logging.info(f"Received ListAllFiles request from {context.peer()}")
        response = requests.get(f'http://{SERVER_URL}:{SERVER_PORT}/list_files')
        if response.status_code == 200:
            files = response.json()
            logging.info(f"Sending all file list to {context.peer()}: {files}")
            return p2p_pb2.ListAllFilesResponse(files=[p2p_pb2.File(filename=file['filename'], fileurl=file['fileurl']) for file in files])
        else:
            logging.error(f"Failed to retrieve all file list from server for {context.peer()}")
            context.abort(grpc.StatusCode.INTERNAL, "Failed to retrieve all file list from server")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    p2p_pb2_grpc.add_FileServiceServicer_to_server(FileServiceImpl(), server)
    server.add_insecure_port(f'[::]:{GRPC_PORT}')
    server.start()
    logging.info(f'Server listening on port {GRPC_PORT}')
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
