#!/usr/bin/env python3
"""
Web Server HTTP Minimale in Python
Serve file statici dalla cartella www/
"""

import socket
import threading
import os
import datetime
import mimetypes
from urllib.parse import unquote

class HTTPServer:
    def __init__(self, host='localhost', port=8080, webroot='www'):
        self.host = host
        self.port = port
        self.webroot = webroot
        self.socket = None
        
        # Configura MIME types
        mimetypes.init()
        
    def log_request(self, client_addr, method, path, status_code):
        """Registra le richieste HTTP"""
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {client_addr[0]}:{client_addr[1]} - {method} {path} - {status_code}")
    
    def get_mime_type(self, file_path):
        """Determina il MIME type del file"""
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'
    
    def build_response(self, status_code, content_type, body):
        """Costruisce la risposta HTTP"""
        status_messages = {
            200: 'OK',
            404: 'Not Found',
            500: 'Internal Server Error'
        }
        
        status_message = status_messages.get(status_code, 'Unknown')
        
        # Header HTTP
        response = f"HTTP/1.1 {status_code} {status_message}\r\n"
        response += f"Content-Type: {content_type}\r\n"
        response += f"Content-Length: {len(body)}\r\n"
        response += "Connection: close\r\n"
        response += "Server: Python-HTTP-Server/1.0\r\n"
        response += "\r\n"
        
        return response.encode('utf-8') + body
    
    def handle_request(self, request_data, client_addr):
        """Gestisce una singola richiesta HTTP"""
        try:
            # Parse della richiesta HTTP
            request_lines = request_data.decode('utf-8').split('\r\n')
            if not request_lines:
                return self.build_response(400, 'text/plain', b'Bad Request')
            
            # Prima riga: METHOD PATH HTTP/1.1
            request_line = request_lines[0]
            method, path, _ = request_line.split(' ', 2)
            
            # Supporta solo GET
            if method != 'GET':
                self.log_request(client_addr, method, path, 405)
                return self.build_response(405, 'text/plain', b'Method Not Allowed')
            
            # Decodifica URL
            path = unquote(path)
            
            # Rimuovi parametri query
            if '?' in path:
                path = path.split('?')[0]
            
            # Gestione della root
            if path == '/':
                path = '/index.html'
            
            # Costruisci il percorso del file
            file_path = os.path.join(self.webroot, path.lstrip('/'))
            
            # Verifica che il file sia nella webroot (sicurezza)
            file_path = os.path.abspath(file_path)
            webroot_abs = os.path.abspath(self.webroot)
            
            if not file_path.startswith(webroot_abs):
                self.log_request(client_addr, method, path, 403)
                return self.build_response(403, 'text/plain', b'Forbidden')
            
            # Verifica esistenza del file
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                self.log_request(client_addr, method, path, 404)
                return self.build_response(404, 'text/html', self.get_404_page())
            
            # Leggi il file
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                content_type = self.get_mime_type(file_path)
                self.log_request(client_addr, method, path, 200)
                return self.build_response(200, content_type, content)
                
            except IOError:
                self.log_request(client_addr, method, path, 500)
                return self.build_response(500, 'text/plain', b'Internal Server Error')
                
        except Exception as e:
            print(f"Errore nella gestione della richiesta: {e}")
            self.log_request(client_addr, 'ERROR', '/', 500)
            return self.build_response(500, 'text/plain', b'Internal Server Error')
    
    def get_404_page(self):
        """Pagina 404 personalizzata"""
        return b"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>404 - Pagina Non Trovata</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            text-align: center; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            height: 100vh;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: rgba(255,255,255,0.1);
            padding: 2rem;
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }
        h1 { font-size: 4rem; margin: 0; }
        p { font-size: 1.2rem; }
        a { color: #fff; text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>404</h1>
        <p>Pagina non trovata</p>
        <p><a href="/">Torna alla home</a></p>
    </div>
</body>
</html>"""
    
    def handle_client(self, client_socket, client_addr):
        """Gestisce un singolo client"""
        try:
            # Ricevi la richiesta
            request_data = client_socket.recv(4096)
            if request_data:
                response = self.handle_request(request_data, client_addr)
                client_socket.send(response)
        except Exception as e:
            print(f"Errore nella gestione del client {client_addr}: {e}")
        finally:
            client_socket.close()
    
    def start(self):
        """Avvia il server"""
        try:
            # Crea il socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind e listen
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            
            print(f"Server avviato su http://{self.host}:{self.port}")
            print(f"Serving files da: {os.path.abspath(self.webroot)}")
            print("Premi Ctrl+C per fermare il server\n")
            
            # Loop principale
            while True:
                client_socket, client_addr = self.socket.accept()
                
                # Gestisci il client in un thread separato
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_addr)
                )
                client_thread.daemon = True
                client_thread.start()
                
        except KeyboardInterrupt:
            print("\nServer fermato dall'utente")
        except Exception as e:
            print(f"Errore del server: {e}")
        finally:
            if self.socket:
                self.socket.close()

def main():
    # Crea la cartella www se non esiste
    if not os.path.exists('www'):
        print("Cartella 'www' non trovata. Creala e inserisci i file HTML/CSS.")
        return
    
    # Avvia il server
    server = HTTPServer()
    server.start()

if __name__ == '__main__':
    main()