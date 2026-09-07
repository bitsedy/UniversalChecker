"""
CheckerPay Ghana - Development & Production Server Launcher
Usage:
    python run_server.py
"""

import uvicorn
import os
import sys

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    # Ensure current directory is in PYTHONPATH
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))

    # 0.0.0.0 binds across all interfaces, but Windows browsers cannot connect
    # to 0.0.0.0 when clicked as a URL. Use 127.0.0.1 for clickable terminal links.
    display_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host

    print("=" * 60)
    print("[GH] CheckerPay Ghana - Result Checker Reseller Platform")
    print("=" * 60)
    print(f"Server Interface:  http://{host}:{port} (Listening on all interfaces)")
    print(f"Storefront:        http://{display_host}:{port} (or http://localhost:{port})")
    print(f"Self-Service:      http://{display_host}:{port}/lookup")
    print(f"Portal Guides:     http://{display_host}:{port}/guides")
    print(f"Admin Operations:  http://{display_host}:{port}/admin")
    print(f"API Documentation: http://{display_host}:{port}/docs")
    print(f"Health Check:      http://{display_host}:{port}/health")
    print("=" * 60)

    uvicorn.run(
        "checker_platform.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )
