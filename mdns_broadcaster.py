import socket
from zeroconf import IPVersion, ServiceInfo, Zeroconf

def get_ip_address():
    """Gets the local IP address of the machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def start_mdns_broadcast(host_name="tumitumi", port=5000):
    ip_address = get_ip_address()
    desc = {'version': '1.0.0'}

    info = ServiceInfo(
        "_http._tcp.local.",
        f"{host_name}._http._tcp.local.",
        addresses=[socket.inet_aton(ip_address)],
        port=port,
        properties=desc,
        server=f"{host_name}.local.",
    )

    zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
    print(f"Registrazione servizio mDNS: {host_name}.local ({ip_address}:{port})")
    try:
        # Use allow_name_change=True to handle duplicates gracefully
        zeroconf.register_service(info, allow_name_change=True)
    except Exception as e:
        print(f"Errore registrazione mDNS (probabile ricaricamento): {e}")

    return zeroconf, info

if __name__ == '__main__':
    # Test stand-alone
    zc, info = start_mdns_broadcast()
    try:
        input("Broadcasting tumitumi.local... Premi invio per fermare.\n")
    finally:
        zc.unregister_service(info)
        zc.close()
