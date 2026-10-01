import os
import time
import random
from pymemcache.client.hash import HashClient
from colorama import init, Fore, Style

init(autoreset=True)

# -------------------------------------------------------------------
# Configuration & Setup
# -------------------------------------------------------------------

MEMCACHED_NODES_ENV = os.getenv('MEMCACHED_NODES', 'localhost:11211,localhost:11212,localhost:11213')
ALL_NODES = [(host, int(port)) for host, port in [n.split(':') for n in MEMCACHED_NODES_ENV.split(',')]]

active_nodes = ALL_NODES.copy()
client = None

def get_alive_nodes():
    """Pings all known nodes and returns a list of the ones currently alive."""
    from pymemcache.client.base import Client
    alive = []
    for node in ALL_NODES:
        try:
            c = Client(node, connect_timeout=0.5, timeout=0.5)
            c.version()
            alive.append(node)
            c.close()
        except Exception:
            pass
    return alive

def rebalance_cluster():
    """Rebuilds the HashClient with only the currently alive nodes."""
    global active_nodes, client
    print(f"{Fore.RED}\n[CLUSTER ALERT] Node failure detected! Rebalancing hash ring...{Style.RESET_ALL}")
    
    alive = get_alive_nodes()
    if not alive:
        print(f"{Fore.RED}[FATAL] All Memcached nodes are dead!{Style.RESET_ALL}")
        active_nodes = []
        client = None
        return
        
    if set(alive) != set(active_nodes):
        active_nodes = alive
        print(f"{Fore.YELLOW}[SYSTEM] Rebuilding Consistent Hash Ring with active nodes: {active_nodes}{Style.RESET_ALL}")
        # ignore_exc=False is critical here so exceptions bubble up and we can trigger this rebalance
        client = HashClient(active_nodes, connect_timeout=1, timeout=1, ignore_exc=False)
        print(f"{Fore.GREEN}[SYSTEM] Cluster successfully rebalanced!{Style.RESET_ALL}\n")

# Initialize cluster on startup
print(f"{Fore.YELLOW}[SYSTEM] Waiting 3 seconds for Memcached nodes to boot...{Style.RESET_ALL}")
time.sleep(3)
active_nodes = get_alive_nodes()
if active_nodes:
    client = HashClient(active_nodes, connect_timeout=1, timeout=1, ignore_exc=False)
    print(f"{Fore.CYAN}[SYSTEM] Initialized Memcached HashClient with nodes: {active_nodes}{Style.RESET_ALL}")
else:
    print(f"{Fore.RED}[FATAL] No nodes available at startup.{Style.RESET_ALL}")

# -------------------------------------------------------------------
# Application Logic
# -------------------------------------------------------------------

def query_database_for_user(user_id):
    print(f"{Fore.YELLOW}[DB]   -> Simulating slow DB query for {user_id}...{Style.RESET_ALL}")
    time.sleep(1.5)
    return f"UserData_for_{user_id}_(loaded_from_db)"

def get_user_profile(user_id):
    """
    Cache-Aside pattern with explicit Self-Healing failover.
    Returns: (data, is_hit)
    """
    global client
    key = f"user_profile:{user_id}"
    
    if not client:
        return query_database_for_user(user_id), False
        
    # 1. Try to get data from Cache
    try:
        start_time = time.time()
        cached_data = client.get(key)
    except Exception as e:
        print(f"{Fore.RED}[WARN] Cache GET failed: {e}{Style.RESET_ALL}")
        rebalance_cluster()
        cached_data = None

    if cached_data:
        # Cache Hit!
        elapsed = time.time() - start_time
        print(f"{Fore.GREEN}[HIT]  -> Found '{key}' in Cache! (Took {elapsed:.4f}s){Style.RESET_ALL}")
        return cached_data.decode('utf-8'), True
    else:
        # Cache Miss
        print(f"{Fore.MAGENTA}[MISS] -> '{key}' not in Cache.{Style.RESET_ALL}")
        data = query_database_for_user(user_id)
        
        # 2. Store it in the cache for future requests
        if client:
            try:
                client.set(key, data, expire=300)
                print(f"{Fore.BLUE}[SET]  -> Saved '{key}' to Memcached cluster.{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}[WARN] Cache SET failed: {e}{Style.RESET_ALL}")
                rebalance_cluster()
                # Retry SET once after the hash ring has been rebuilt
                if client:
                    try:
                        client.set(key, data, expire=300)
                        print(f"{Fore.BLUE}[SET]  -> Retry successful! Saved to a surviving node.{Style.RESET_ALL}")
                    except Exception:
                        pass
                        
        return data, False

# -------------------------------------------------------------------
# Main Simulation Loop
# -------------------------------------------------------------------

if __name__ == "__main__":
    print(f"{Fore.CYAN}\n==================================================")
    print(f" Memcached Distributed Simulator Started! ")
    print(f" Press Ctrl+C to exit.")
    print(f"==================================================\n{Style.RESET_ALL}")
    
    user_ids = [f"U{i:03d}" for i in range(1, 11)]
    request_count = 0
    hit_count = 0
    miss_count = 0
    
    try:
        while True:
            target_user = random.choice(user_ids)
            request_count += 1
            
            print(f"\n{Fore.WHITE}[#{request_count}] Requesting Profile for {target_user} ---{Style.RESET_ALL}")
            
            # Fetch data and track stats
            _, is_hit = get_user_profile(target_user)
            if is_hit:
                hit_count += 1
            else:
                miss_count += 1
            
            if request_count % 10 == 0:
                hit_rate = (hit_count / request_count) * 100
                print(f"\n{Fore.CYAN}[STATS] After {request_count} requests: "
                      f"Hits={hit_count}, Misses={miss_count}, Hit Rate={hit_rate:.1f}%{Style.RESET_ALL}")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        if request_count > 0:
            hit_rate = (hit_count / request_count) * 100
            print(f"\n{Fore.CYAN}==================================================")
            print(f" FINAL STATS")
            print(f" Total Requests: {request_count}")
            print(f" Cache Hits:     {hit_count}")
            print(f" Cache Misses:   {miss_count}")
            print(f" Hit Rate:       {hit_rate:.1f}%")
            print(f"=================================================={Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}Shutting down simulator gracefully...{Style.RESET_ALL}")
