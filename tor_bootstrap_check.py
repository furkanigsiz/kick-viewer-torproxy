import time
import sys

try:
    from stem.control import Controller
    STEM_OK = True
except ImportError:
    STEM_OK = False

CONTROL_PORTS = [9051, 9061, 9071, 9081, 9091, 9101, 9111, 9121, 9131, 9141, 9151, 9161]
PASSWORD = ""
TIMEOUT = 120
CHECK_INTERVAL = 2

def get_bootstrap_status(port):
    try:
        with Controller.from_port(port=port) as ctrl:
            ctrl.authenticate(password=PASSWORD) if PASSWORD else ctrl.authenticate()
            bootstrap = ctrl.get_info("status/bootstrap-phase")
            if "PROGRESS=" in bootstrap:
                progress = int(bootstrap.split("PROGRESS=")[1].split(" ")[0])
                return progress
    except:
        pass
    return 0

def main():
    if not STEM_OK:
        print("[!] stem not installed, waiting 30s...")
        time.sleep(30)
        return
    
    start = time.time()
    ready_ports = set()
    
    while time.time() - start < TIMEOUT:
        statuses = []
        for port in CONTROL_PORTS:
            progress = get_bootstrap_status(port)
            if progress == 100:
                ready_ports.add(port)
            statuses.append(progress)
        
        bar_width = 20
        lines = []
        for i, (port, progress) in enumerate(zip(CONTROL_PORTS, statuses)):
            filled = int(bar_width * progress / 100)
            bar = "█" * filled + "░" * (bar_width - filled)
            status = "\033[32m✓\033[0m" if progress == 100 else "\033[33m…\033[0m"
            lines.append(f"  Tor {i+1:2d} (:{port}) [{bar}] {progress:3d}% {status}")
        
        ready = len(ready_ports)
        total = len(CONTROL_PORTS)
        
        print(f"\033[{total + 2}A", end="")
        print(f"\033[2K\r[*] Bootstrap Progress ({ready}/{total} ready, {int(time.time() - start)}s elapsed)")
        for line in lines:
            print(f"\033[2K\r{line}")
        print(f"\033[2K\r")
        sys.stdout.flush()
        
        if ready == total:
            print(f"\033[32m[+] All {total} Tor instances ready!\033[0m")
            return
        
        time.sleep(CHECK_INTERVAL)
    
    print(f"\033[33m[!] Timeout: {len(ready_ports)}/{len(CONTROL_PORTS)} ready\033[0m")

if __name__ == "__main__":
    print("\n" * (len(CONTROL_PORTS) + 2))
    main()
