import os
import sys
import socket
import logging
import json
import subprocess
import threading
from smbclient import listdir, register_session, delete_session

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_local_subnet():
    """Determine local subnet (e.g., 192.168.1.0/24)"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ".".join(ip.split(".")[:-1]) + ".0/24"
    except:
        return "192.168.1.0/24"

def scan_smb_hosts():
    """Use nmap to find hosts with SMB port (445) open."""
    subnet = get_local_subnet()
    logger.info(f"🔍 Scanning subnet {subnet} for SMB hosts...")
    
    try:
        # Fast scan for port 445
        cmd = ["nmap", "-p", "445", "--open", "-n", subnet]
        output = subprocess.check_output(cmd, text=True)
        
        hosts = []
        for line in output.split("\n"):
            if "Nmap scan report for" in line:
                hosts.append(line.split()[-1])
        return hosts
    except Exception as e:
        logger.error(f"Nmap scan failed: {e}")
        return []

def get_shares_on_host(ip):
    """Enumerate all shares on a host using smbclient CLI."""
    shares = []
    try:
        # -L: list shares, -N: no password
        cmd = ["smbclient", "-L", ip, "-N", "-g"] # -g for parsable output
        output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
        
        for line in output.split("\n"):
            # Format: Disk|ShareName|Comment
            parts = line.split("|")
            if len(parts) >= 2 and parts[0] == "Disk":
                shares.append(parts[1])
    except Exception as e:
        # Fallback to common names if enumeration fails
        return ["HIS", "DATA", "his", "data", "DB", "db"]
    return shares

def check_his_in_host(ip):
    """Check a host for all accessible shares and identify those with HIS data."""
    discovered = [] # List of {"path": str, "has_his": bool}
    
    # 1. Get all available shares
    shares = get_shares_on_host(ip)
    
    try:
        # Try guest session
        register_session(ip, username="", password="")
        
        for share in shares:
            try:
                path = f"\\\\{ip}\\{share}"
                # Look for CO03L.DBF in the root of the share
                contents = listdir(path)
                has_his = False
                if any(f.upper() == "CO03L.DBF" for f in contents):
                    logger.info(f"✨ FOUND HIS FOLDER: {path}")
                    has_his = True
                else:
                    # Look one level deeper
                    for item in contents:
                        try:
                            subpath = os.path.join(path, item).replace('/', '\\')
                            subcontents = listdir(subpath)
                            if any(sf.upper() == "CO03L.DBF" for sf in subcontents):
                                logger.info(f"✨ FOUND HIS FOLDER (DEEP): {subpath}")
                                discovered.append({"path": subpath, "has_his": True})
                        except:
                            continue
                
                discovered.append({"path": path, "has_his": has_his})
            except:
                # Share might be listed but not accessible via guest
                continue
                
    except Exception as e:
        pass
    finally:
        try:
            delete_session(ip)
        except:
            pass
    return discovered

def auto_discover_his():
    """Main discovery routine."""
    hosts = scan_smb_hosts()
    results = []
    
    threads = []
    def worker(ip):
        host_results = check_his_in_host(ip)
        if host_results:
            results.extend(host_results)

    for host in hosts:
        t = threading.Thread(target=worker, args=(host,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Sort results so HIS folders are at the top
    results.sort(key=lambda x: x['has_his'], reverse=True)
    
    print(json.dumps({"success": True, "discovered_shares": results}))
    return results

if __name__ == "__main__":
    auto_discover_his()
