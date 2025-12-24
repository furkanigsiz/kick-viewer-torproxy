# Kick Viewer Bot (Tor Proxy)

Tor-based viewer bot for Kick.com. Uses Docker containers to run multiple Tor instances and increases viewer count through WebSocket connections.

## Requirements

- Python 3.8+
- Docker Desktop
- Windows 10/11

## Installation

```bash
git clone https://github.com/furkanigsiz/kick-viewer-torproxy.git
cd kick-viewer-torproxy
pip install -r requirements.txt
```

## Files

| File | Description |
|------|-------------|
| `kick.py` | Original version, uses local Tor instances on Windows |
| `kickdocker.py` | Docker version, 1 Tor instance per container |
| `kickdocker2.py` | Multi-Tor Docker, 6 Tor instances per container |
| `kickdocker3.py` | Lightweight version, 3 Tor instances per container |

## Usage

### kickdocker2.py (Recommended)

```bash
python kickdocker2.py
```

1. Enter container count (e.g. 15)
2. Enter base port (default: 19050)
3. Wait 45 seconds for Tor bootstrap
4. Enter channel name

Example output:
```
[*] Token settings: Pool=500, Wait=150, Producers=60
[*] Creating 15 containers (6 Tor instances each)...
[*] Container 1/15 ports 19050-19055... OK
...
[+] Created 15 containers with 90 total ports
[*] Waiting 45s for Tor instances to bootstrap...

Channel: xqc
```

### kickdocker3.py (Lightweight Version)

```bash
python kickdocker3.py
```

Uses less RAM, allows more containers. 30 containers = 90 ports.

### kickdocker.py (Simple Version)

```bash
python kickdocker.py
```

Single Tor instance per container. More stable but less efficient.

## Performance Comparison

| Version | For 90 Ports | RAM Usage | Stability |
|---------|--------------|-----------|-----------|
| kickdocker.py | 90 containers | High | Very stable |
| kickdocker2.py | 15 containers | Medium | Stable |
| kickdocker3.py | 30 containers | Low | Stable |

## Customization

### Ports Per Container

In `kickdocker2.py` or `kickdocker3.py`:

```python
PORTS_PER_CONTAINER = 6  # Change to your desired value
```

After changing, update the corresponding Dockerfile and start-tor script:

**Dockerfile.multitor:**
```dockerfile
EXPOSE 9050-9055  # Adjust based on port count
```

**start-tor.sh:**
```bash
for i in 0 1 2 3 4 5; do  # Adjust based on port count
```

### Connection Settings

```python
CONNS_PER_PORT = 120      # Max connections per port
TOKEN_POOL_SIZE = 500     # Token pool size
TOKEN_PRODUCERS = 60      # Token producer thread count
PONG_TIMEOUT = 180        # Connection timeout (seconds)
```

## Troubleshooting

### Tor Bootstrap Error

```
Problem bootstrapping. Stuck at 50% (loading_descriptors)
```

Solution: Reduce container count or increase wait time.

### Token Pool Draining Fast

Increase `TOKEN_PRODUCERS` value or raise `TOKEN_POOL_SIZE`.

### Connections Not Increasing

Check `CONNS_PER_PORT` value. Increase if too low.

## Stats Explained

```
[+] Containers: 15 | Ports: 90
[+] Conn: 5994 | Attempts: 8457
[+] Pings: 51182 | Heartbeats: 8351 | Time: 323s
[+] Viewers: 3220 | Stream: 87792781
[+] Errors: 64
[+] TokenPool: 16 | Hits: 8458 | Miss: 19
```

- Conn: Active WebSocket connections
- Attempts: Total connection attempts
- Viewers: Viewer count shown by Kick
- Errors: Failed connection count
- TokenPool: Ready tokens in pool

## Cleanup

Containers are automatically cleaned up on Ctrl+C. For manual cleanup:

```bash
docker rm -f $(docker ps -aq --filter "name=multitor")
```

## License

MIT

---

If you found this project useful, don't forget to give it a star.
