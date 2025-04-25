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

def get_routers():
    """Lê nomes dos containers router via os.popen."""
    out = os.popen("docker ps --filter 'name=router' --format '{{.Names}}'").read()
    return sorted(out.splitlines())

def extract_num(name):
    """Remove prefix 'router' e retorna só o número."""
    pre = name.split('-')[1]
    result = pre.split('router')[1]
    return result
        

def ping_task(frm, to, ip, results, lock_thread):
    """Thread worker: executa ping e armazena resultado."""
    start = time.time()
    cmd = f"docker exec {frm} ping -c1 -W0.1 {ip} > /dev/null 2>&1"
    print(f"{Colors.YELLOW}{cmd}{Colors.NC}")
    code = os.system(cmd)
    elapsed = time.time() - start
    success = (code == 0)
    
    with lock_thread:
        results.append((frm, to, success, elapsed))


def main():
    routers = get_routers()
    if not routers:
        print(f"{Colors.RED}Erro: nenhum roteador rodando. Execute 'make up'.{Colors.NC}")
        return

    tasks = [(f, t, f"172.20.{extract_num(t)}.3") for f in routers for t in routers if f != t]
    
    print(f"{Colors.MAGENTA}Iniciando {len(tasks)} pings com até {MAX_WORKERS} threads paralelas...{Colors.NC}")
    
    results = []
    threads = []
    lock_thread = threading.Lock()

    for frm, to, ip in tasks:
        while len(threads) >= MAX_WORKERS:
            threads = [thr for thr in threads if thr.is_alive()]
            time.sleep(0.01)

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
        print(f"\n{Colors.CYAN}=== Roteador {frm} ==={Colors.NC}")
        
        for to, ok, tempo in summary[frm]:
            status_color = Colors.GREEN if ok else Colors.RED
            status = "OK" if ok else "Falha"
            
            print(f"{status_color}{frm} -> {to}: {status} (Tempo: {tempo:.2f}s){Colors.NC}")
            total_ok += ok

    print(f"\n{Colors.YELLOW}Total geral: {total_ok}/{total} conexões bem-sucedidas{Colors.NC}")

if __name__ == "__main__":
    main()
