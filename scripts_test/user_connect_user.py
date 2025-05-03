import os
import threading
import time

# Cores para output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[0;33m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    NC = '\033[0m'

CPU_COUNT = os.cpu_count() or 1
MAX_WORKERS = CPU_COUNT * 4

def get_users():
    """Lê nomes dos containers host via os.popen."""
    out = os.popen("docker ps --filter 'name=host' --format '{{.Names}}'").read()
    return sorted(out.splitlines())

def extract_num_host(name):
    """
    Remove prefix 'host' e retorna só o número.
    exemplo:
      nome: 'prova_1_rayner-host11-1
      resultado: 1, 1
    """
    pre = name.split('-')[1]
    result = pre.split('host')[1]
    result1 = result[:-1]
    result2 = result[-1]
    return result1, result2
   

def ping_task(frm, to, ip, results, lock_thread):
    """Thread worker: executa ping e armazena resultado."""
    start = time.time()
    cmd = f"docker exec {frm} ping -c 1 -W 0.1 {ip} > /dev/null 2>&1"
    print(f"{Colors.YELLOW}{cmd}{Colors.NC}")

    code = os.system(cmd)
    elapsed = time.time() - start
    success = (code == 0)

    with lock_thread:
        results.append((frm, to, success, elapsed))


def main():
    users = get_users()
    if not users:
        print(f"{Colors.RED}Erro: nenhum host rodando. Execute 'make up'.{Colors.NC}")
        return
    
    tasks = [(frm, to, f"172.20.{extract_num_host(to)[0]}.1{extract_num_host(to)[1]}") for frm in users for to in users if frm != to]
    
    results = []
    threads = []
    lock_thread = threading.Lock()
    
    for frm, to, ip in tasks:
        while len(threads) >= MAX_WORKERS:
            threads = [thr for thr in threads if thr.is_alive()]

        thread = threading.Thread(target=ping_task, args=(frm, to, ip, results, lock_thread))
        thread.start()
        threads.append(thread)
    
    for thread in threads:
        thread.join()
    
    summary = {}
    
    for frm, to, ok, tempo in results:
        summary.setdefault(frm, []).append((to, ok, tempo))
    
    total_ok = 0
    total = len(results)
    
    for frm in sorted(summary):
        print(f"\n{Colors.CYAN}=== Host {frm} ==={Colors.NC}")
        
        for to, ok, tempo in summary[frm]:
            status_color = Colors.GREEN if ok else Colors.RED
            status = "OK" if ok else "Falha"
            
            print(f"{status_color}{frm} -> {to}: {status} ({tempo:.2f}s){Colors.NC}")
            if ok:
                total_ok += 1
            
    print(f"\n{Colors.MAGENTA}Total de pings: {total}, Sucessos: {total_ok}, Falhas: {total - total_ok}{Colors.NC}")

if __name__ == "__main__":
    main()
