import sys
import time
import random
import datetime
import threading
import asyncio
import json
import os
import subprocess
from threading import Thread
from queue import Queue, Empty
import tls_client

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

try:
    import aiohttp
    from aiohttp_socks import ProxyConnector
    FULL_SUPPORT = True
except ImportError:
    FULL_SUPPORT = False

CLIENT_TOKEN = "e1393935a959b4020a4491574f6490129f678acdaa92760471263db43487f823"
DOCKER_IMAGE = "multitor:latest"
CONTAINER_PREFIX = "multitor_"
PORTS_PER_CONTAINER = 6
CONNS_PER_PORT = 120
BASE_TOKEN_POOL_SIZE = 500
BASE_INITIAL_POOL_WAIT = 150
BASE_TOKEN_PRODUCERS = 60
TOKEN_POOL_SIZE = 500
INITIAL_POOL_WAIT = 150
TOKEN_PRODUCERS = 60

def calculate_token_settings(num_containers):
    global TOKEN_POOL_SIZE, INITIAL_POOL_WAIT, TOKEN_PRODUCERS
    if num_containers <= 15:
        TOKEN_POOL_SIZE = BASE_TOKEN_POOL_SIZE
        INITIAL_POOL_WAIT = BASE_INITIAL_POOL_WAIT
        TOKEN_PRODUCERS = BASE_TOKEN_PRODUCERS
    else:
        extra = num_containers - 15
        TOKEN_POOL_SIZE = BASE_TOKEN_POOL_SIZE + (extra * 50)
        INITIAL_POOL_WAIT = BASE_INITIAL_POOL_WAIT + (extra * 20)
        TOKEN_PRODUCERS = BASE_TOKEN_PRODUCERS + (extra * 5)
PONG_TIMEOUT = 180

channel = ""
channel_id = None
stream_id = None
stop = False
start_time = None
lock = threading.Lock()
connections = 0
attempts = 0
pings = 0
heartbeats = 0
viewers = 0
last_check = 0
ws_errors = 0
token_queue = Queue()
token_hits = 0
token_misses = 0
containers = []
all_ports = []

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        return result.returncode == 0, result.stdout.strip()
    except:
        return False, ""

def build_image():
    print("[*] Building multitor image...")
    success, _ = run_cmd("docker build -t multitor:latest -f Dockerfile.multitor .")
    return success

def create_container(index, base_port):
    name = f"{CONTAINER_PREFIX}{index}"
    run_cmd(f"docker rm -f {name}")
    port_mappings = " ".join([f"-p {base_port + i}:{9050 + i}" for i in range(PORTS_PER_CONTAINER)])
    cmd = f"docker run -d --name {name} {port_mappings} {DOCKER_IMAGE}"
    success, _ = run_cmd(cmd)
    if success:
        containers.append(name)
        for i in range(PORTS_PER_CONTAINER):
            all_ports.append(base_port + i)
        return True
    return False

def cleanup_containers():
    for name in containers:
        run_cmd(f"docker rm -f {name}")

def get_random_port():
    if all_ports:
        return random.choice(all_ports)
    return 9050

def get_proxy_dict(port=None):
    p = port or get_random_port()
    return {"http": f"socks5://127.0.0.1:{p}", "https": f"socks5://127.0.0.1:{p}"}

def clean_channel_name(name):
    if "kick.com/" in name:
        parts = name.split("kick.com/")
        ch = parts[1].split("/")[0].split("?")[0]
        return ch.lower()
    return name.lower()

def get_channel_info(name):
    global channel_id, stream_id
    try:
        s = tls_client.Session(client_identifier="chrome_120", random_tls_extension_order=True)
        if all_ports:
            s.proxies = get_proxy_dict()
        s.headers.update({'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'})
        response = s.get(f'https://kick.com/api/v2/channels/{name}', timeout_seconds=30)
        if response.status_code == 200:
            data = response.json()
            channel_id = data.get("id")
            if 'livestream' in data and data['livestream']:
                stream_id = data['livestream'].get('id')
            return channel_id
    except Exception as e:
        print(f"Error: {e}")
    return None


def fetch_token(port=None):
    try:
        s = tls_client.Session(client_identifier="chrome_120", random_tls_extension_order=True)
        if all_ports:
            s.proxies = get_proxy_dict(port)
        s.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0',
        })
        s.get("https://kick.com", timeout_seconds=20)
        s.headers["X-CLIENT-TOKEN"] = CLIENT_TOKEN
        response = s.get('https://websockets.kick.com/viewer/v1/token', timeout_seconds=20)
        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("token")
    except:
        pass
    return None

def token_producer():
    global stop
    while not stop:
        try:
            if token_queue.qsize() < TOKEN_POOL_SIZE:
                port = get_random_port()
                token = fetch_token(port)
                if token:
                    token_queue.put((token, port))
            else:
                time.sleep(0.05)
        except:
            pass

def get_token_from_pool():
    global token_hits, token_misses
    try:
        token, port = token_queue.get(timeout=0.1)
        with lock:
            token_hits += 1
        return token, port
    except Empty:
        with lock:
            token_misses += 1
        return None, None

def get_viewer_count():
    global viewers, last_check
    if not stream_id:
        return 0
    try:
        s = tls_client.Session(client_identifier="chrome_120", random_tls_extension_order=True)
        if all_ports:
            s.proxies = get_proxy_dict()
        s.headers.update({'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0 Chrome/120.0.0.0'})
        response = s.get(f"https://kick.com/current-viewers?ids[]={stream_id}", timeout_seconds=15)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                viewers = data[0].get('viewers', 0)
                last_check = time.time()
    except:
        pass
    return viewers

def show_stats():
    global stop
    print("\n\n\n\n\n\n")
    os.system('cls' if os.name == 'nt' else 'clear')
    while not stop:
        try:
            if time.time() - last_check >= 5:
                get_viewer_count()
            with lock:
                elapsed = datetime.datetime.now() - start_time if start_time else datetime.timedelta(0)
                duration = f"{int(elapsed.total_seconds())}s"
            print("\033[6A", end="")
            print(f"\033[2K\r[+] Containers: \033[32m{len(containers)}\033[0m | Ports: \033[32m{len(all_ports)}\033[0m")
            print(f"\033[2K\r[+] Conn: \033[32m{connections}\033[0m | Attempts: \033[32m{attempts}\033[0m")
            print(f"\033[2K\r[+] Pings: \033[32m{pings}\033[0m | Heartbeats: \033[32m{heartbeats}\033[0m | Time: \033[32m{duration}\033[0m")
            print(f"\033[2K\r[+] Viewers: \033[32m{viewers}\033[0m | Stream: \033[32m{stream_id or 'N/A'}\033[0m")
            print(f"\033[2K\r[+] Errors: \033[31m{ws_errors}\033[0m")
            print(f"\033[2K\r[+] TokenPool: \033[32m{token_queue.qsize()}\033[0m | Hits: \033[32m{token_hits}\033[0m | Miss: \033[31m{token_misses}\033[0m")
            sys.stdout.flush()
            time.sleep(1)
        except:
            time.sleep(1)

async def ws_handler(session, token):
    global connections, pings, heartbeats, ws_errors, stop
    connected = False
    ws = None
    try:
        url = f"wss://websockets.kick.com/viewer/v1/connect?token={token}"
        ws = await session.ws_connect(url, timeout=aiohttp.ClientTimeout(total=30))
        with lock:
            connections += 1
        connected = True
        
        subscribe = {"event": "pusher:subscribe", "data": {"auth": "", "channel": f"channel.{channel_id}"}}
        await ws.send_str(json.dumps(subscribe))
        
        if stream_id:
            chatroom_sub = {"event": "pusher:subscribe", "data": {"auth": "", "channel": f"chatrooms.{channel_id}.v2"}}
            await ws.send_str(json.dumps(chatroom_sub))
        
        handshake = {"type": "channel_handshake", "data": {"message": {"channelId": channel_id}}}
        await ws.send_str(json.dumps(handshake))
        with lock:
            heartbeats += 1
        
        last_activity = time.time()
        last_ping = 0
        while not stop:
            try:
                now = time.time()
                if now - last_ping >= 20:
                    await ws.send_str(json.dumps({"event": "pusher:ping", "data": {}}))
                    with lock:
                        pings += 1
                    last_ping = now
                
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=5)
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        last_activity = time.time()
                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        break
                except asyncio.TimeoutError:
                    pass
                
                if time.time() - last_activity > PONG_TIMEOUT:
                    break
            except:
                break
    except:
        with lock:
            ws_errors += 1
    finally:
        if ws and not ws.closed:
            try:
                await ws.close()
            except:
                pass
        if connected:
            with lock:
                connections = max(0, connections - 1)


async def run_port_pool(port, target_count):
    global stop, attempts
    try:
        connector = ProxyConnector.from_url(f'socks5://127.0.0.1:{port}', limit=target_count, limit_per_host=target_count)
    except:
        return
    
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            active_tasks = set()
            
            while not stop:
                done = {t for t in active_tasks if t.done()}
                active_tasks -= done
                
                slots = target_count - len(active_tasks)
                pool_size = token_queue.qsize()
                
                if pool_size < 20:
                    await asyncio.sleep(0.5)
                    continue
                
                batch_size = min(slots, 10) if pool_size > 100 else min(slots, 5) if pool_size > 30 else min(slots, 2)
                
                for _ in range(batch_size):
                    if stop:
                        break
                    token, _ = get_token_from_pool()
                    if not token:
                        break
                    with lock:
                        attempts += 1
                    task = asyncio.create_task(ws_handler(session, token))
                    active_tasks.add(task)
                    await asyncio.sleep(0.05)
                
                await asyncio.sleep(0.3)
    except:
        pass

def port_worker(port, count):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_port_pool(port, count))
    except:
        pass
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.run_until_complete(loop.shutdown_asyncgens())
        except:
            pass
        loop.close()

def run(channel_name):
    global channel, start_time, channel_id, stop
    channel = clean_channel_name(channel_name)
    start_time = datetime.datetime.now()
    
    print(f"[*] Getting channel info for: {channel}")
    channel_id = get_channel_info(channel)
    if channel_id:
        print(f"[+] Channel ID: {channel_id}")
    if stream_id:
        print(f"[+] Stream ID: {stream_id}")
    
    print("[*] Starting token producers...")
    for _ in range(TOKEN_PRODUCERS):
        Thread(target=token_producer, daemon=True).start()
    print("[*] Filling token pool...")
    while token_queue.qsize() < INITIAL_POOL_WAIT:
        time.sleep(0.3)
        print(f"\r[*] Tokens: {token_queue.qsize()}/{INITIAL_POOL_WAIT}", end="")
    print(f"\n[+] Token pool ready: {token_queue.qsize()}")
    
    Thread(target=show_stats, daemon=True).start()
    
    threads = []
    for port in all_ports:
        if stop:
            break
        t = Thread(target=port_worker, args=(port, CONNS_PER_PORT), daemon=True)
        threads.append(t)
        t.start()
        time.sleep(0.02)
    
    while not stop:
        time.sleep(60)
    
    for t in threads:
        t.join(timeout=1)

if __name__ == "__main__":
    try:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=== Kick Viewer Bot (Multi-Tor Docker) ===\n")
        
        if not FULL_SUPPORT:
            print("\033[31m[!] pip install aiohttp aiohttp-socks\033[0m")
            sys.exit(1)
        
        success, _ = run_cmd("docker --version")
        if not success:
            print("\033[31m[!] Docker not found!\033[0m")
            sys.exit(1)
        
        if not build_image():
            print("\033[31m[!] Failed to build image\033[0m")
            sys.exit(1)
        
        num_containers = int(input("Number of containers (e.g. 10): ").strip() or "10")
        base_port = int(input("Base port (default 19050): ").strip() or "19050")
        
        calculate_token_settings(num_containers)
        print(f"[*] Token settings: Pool={TOKEN_POOL_SIZE}, Wait={INITIAL_POOL_WAIT}, Producers={TOKEN_PRODUCERS}")
        
        print(f"\n[*] Creating {num_containers} containers ({PORTS_PER_CONTAINER} Tor instances each)...")
        for i in range(num_containers):
            container_base = base_port + (i * PORTS_PER_CONTAINER)
            print(f"[*] Container {i+1}/{num_containers} ports {container_base}-{container_base + PORTS_PER_CONTAINER - 1}...", end="")
            if create_container(i, container_base):
                print(" OK")
            else:
                print(" FAILED")
        
        print(f"\n[+] Created {len(containers)} containers with {len(all_ports)} total ports")
        print("[*] Waiting 45s for Tor instances to bootstrap...")
        time.sleep(45)
        
        channel_input = input("\nChannel: ").strip()
        if not channel_input:
            cleanup_containers()
            sys.exit(1)
        
        run(channel_input)
    except KeyboardInterrupt:
        stop = True
        print("\n[*] Cleaning up containers...")
        cleanup_containers()
        print("Stopped.")
        sys.exit(0)
