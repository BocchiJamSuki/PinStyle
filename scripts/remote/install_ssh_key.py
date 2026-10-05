"""One-time: install this laptop's SSH public key on the GPU server.

The password is read with getpass (or from the PINSTYLE_SSH_PASSWORD env var) and is
never printed, logged or stored. After this, use key-based SSH only.

Usage: python scripts/remote/install_ssh_key.py --host connect.westb.seetacloud.com --port 39283
"""

from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path

import paramiko


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--user", default="root")
    ap.add_argument("--pubkey", default=str(Path.home() / ".ssh" / "id_ed25519.pub"))
    args = ap.parse_args()

    pub = Path(args.pubkey).read_text().strip()
    password = os.environ.get("PINSTYLE_SSH_PASSWORD") or getpass.getpass("Server password: ")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(args.host, port=args.port, username=args.user, password=password,
                   look_for_keys=False, allow_agent=False, timeout=20)
    del password
    cmd = (
        "mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys && "
        f"grep -qxF '{pub}' ~/.ssh/authorized_keys || echo '{pub}' >> ~/.ssh/authorized_keys; "
        "chmod 600 ~/.ssh/authorized_keys && echo KEY_INSTALLED"
    )
    _, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    client.close()
    print(out or err)


if __name__ == "__main__":
    main()
