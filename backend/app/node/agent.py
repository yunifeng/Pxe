"""Agent 本地 CLI 工具"""
from sqlalchemy.orm import Session

import json
import sys


def handle_status(db: Session = None) -> dict:
    from app.database import get_db
    from app.models import Node

    sess = db or next(get_db())
    try:
        nodes = sess.query(Node).all()
        return {
            "nodes": [
                {
                    "id": n.id,
                    "hostname": n.hostname,
                    "ip": n.ip,
                    "mode": n.mode,
                    "status": n.status,
                    "last_heartbeat": n.last_heartbeat.isoformat() if n.last_heartbeat else None,
                }
                for n in nodes
            ]
        }
    finally:
        if not db:
            sess.close()


def handle_pxe_config(db: Session = None) -> str:
    from app.pxe.dnsmasq import get_config
    return get_config()


def handle_bmc_list(db: Session = None) -> list:
    from app.database import get_db
    from app.models import BmcInfo

    sess = db or next(get_db())
    try:
        bmcs = sess.query(BmcInfo).all()
        return [
            {
                "id": b.id,
                "hostname": b.hostname,
                "bmc_ip": b.bmc_ip,
                "protocol": b.protocol,
                "power_status": b.power_status,
            }
            for b in bmcs
        ]
    finally:
        if not db:
            sess.close()


def handle_bmc_power(bmc_id: int, action: str, db: Session = None) -> dict:
    from app.database import get_db
    from app.models import BmcInfo

    sess = db or next(get_db())
    try:
        bmc = sess.query(BmcInfo).filter_by(id=bmc_id).first()
        if not bmc:
            raise Exception("BMC not found")
        info = {
            "bmc_ip": bmc.bmc_ip,
            "username": bmc.username,
            "password": bmc.password,
        }
        handler = (
            __import__("app.bmc.redfish_handler", fromlist=[""])
            if bmc.protocol == "redfish"
            else __import__("app.bmc.ipmi_handler", fromlist=[""])
        )
        getattr(handler, f"power_{action}")(info)
        return {"success": True}
    finally:
        if not db:
            sess.close()


def handle_install_task(action: str, task_id: int = None, params: dict = None, db: Session = None) -> dict:
    from app.pxe.tasks import complete_task, create_task, get_task, retry_task

    if action == "create" and params:
        return create_task(params.get("host_id"), params.get("iso_id"), params.get("template_id"), params.get("node_id"), db)
    elif action == "get":
        return get_task(task_id, db)
    elif action == "retry":
        return retry_task(task_id, db)
    else:
        raise Exception(f"Unknown action: {action}")


def handle_file_sync(file_ids: list, db: Session = None) -> dict:
    from app.database import get_db
    from app.models import FileInfo

    sess = db or next(get_db())
    try:
        files = sess.query(FileInfo).filter(FileInfo.id.in_(file_ids)).all()
        synced = 0
        for f in files:
            f.sync_status = "synced"
            synced += 1
        sess.commit()
        return {"synced": synced}
    finally:
        if not db:
            sess.close()


def handle_log(lines: int = 100) -> str:
    import os
    from app.config import settings

    log_file = os.path.join(settings.log_dir, "pxe.log")
    try:
        with open(log_file, "r") as f:
            all_lines = f.readlines()
        return "".join(all_lines[-lines:])
    except FileNotFoundError:
        return ""


def main():
    """CLI 入口 - JSON 输入/输出"""
    if len(sys.argv) < 2:
        json.dump({"error": "Usage: pxe-agent <command> [args...]"}, sys.stderr)
        sys.exit(1)
    command = sys.argv[1]
    input_data = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {}

    try:
        if command == "status":
            result = handle_status()
        elif command == "pxe-config":
            result = handle_pxe_config()
        elif command == "bmc-list":
            result = handle_bmc_list()
        elif command == "bmc-power":
            result = handle_bmc_power(input_data.get("bmc_id"), input_data.get("action"))
        elif command == "install-task":
            result = handle_install_task(
                input_data.get("action"),
                input_data.get("task_id"),
                input_data.get("params"),
            )
        elif command == "file-sync":
            result = handle_file_sync(input_data.get("file_ids", []))
        elif command == "log":
            result = handle_log(input_data.get("lines", 100))
        else:
            json.dump({"error": f"Unknown command: {command}"}, sys.stderr)
            sys.exit(1)
        json.dump({"success": True, "data": result}, sys.stdout)
    except Exception as e:
        json.dump({"success": False, "error": str(e)}, sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
