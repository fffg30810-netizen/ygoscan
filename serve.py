#!/usr/bin/env python3
"""Server HTTPS locale per provare l'app sul telefono nella stessa rete Wi-Fi (la camera del browser
richiede HTTPS). Certificato self-signed generato con openssl (Git for Windows lo include):
il telefono mostra un avviso la prima volta -> "Avanzate" -> "Procedi".

  python serve.py            ->  https://<ip-del-pc>:8443
"""
import http.server, os, socket, ssl, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
CERT, KEY = os.path.join(HERE, "data", "dev-cert.pem"), os.path.join(HERE, "data", "dev-key.pem")
if not os.path.exists(CERT):
    os.makedirs(os.path.dirname(CERT), exist_ok=True)
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", KEY, "-out", CERT,
                    "-days", "365", "-subj", "/CN=ygoscan"], check=True)
os.chdir(os.path.join(HERE, "docs"))
srv = http.server.ThreadingHTTPServer(("0.0.0.0", 8443), http.server.SimpleHTTPRequestHandler)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(CERT, KEY)
srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
ip = socket.gethostbyname(socket.gethostname())
print(f"YGO Scan:  https://{ip}:8443   (Ctrl+C per fermare)")
srv.serve_forever()
