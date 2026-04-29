"""PXE Agent CLI 入口 - 供 Master 通过 SSH 调用"""
import argparse
import json
import sys


def _parse_json_stdin(default=None):
    if not sys.stdin.isatty():
        try:
            return json.loads(sys.stdin.read())
        except (json.JSONDecodeError, KeyboardInterrupt):
            return default or {}
    return default or {}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pxe-agent", description="PXE Agent CLI")
    subparsers = parser.add_subparsers(dest="command")

    # status
    subparsers.add_parser("status", help="List nodes and their status")

    # pxe-config
    subparsers.add_parser("pxe-config", help="Get current PXE configuration")

    # bmc-list
    subparsers.add_parser("bmc-list", help="List BMC information")

    # bmc-power
    bmc_power = subparsers.add_parser("bmc-power", help="Control BMC power")
    bmc_power.add_argument("--bmc-id", type=int, required=True)
    bmc_power.add_argument("--action", required=True, choices=["on", "off", "restart", "cycle"])

    # install-task
    install_task = subparsers.add_parser("install-task", help="Manage install tasks")
    install_task.add_argument("--action", required=True, choices=["create", "get", "retry"])
    install_task.add_argument("--task-id", type=int)
    install_task.add_argument("--host-id", type=int)
    install_task.add_argument("--iso-id", type=int)
    install_task.add_argument("--template-id", type=int)
    install_task.add_argument("--node-id", type=int)

    # file-sync
    file_sync = subparsers.add_parser("file-sync", help="Sync files to agent")
    file_sync.add_argument("--file-ids", type=int, nargs="+", required=True)

    # log
    log_parser = subparsers.add_parser("log", help="Show recent log lines")
    log_parser.add_argument("--lines", type=int, default=100)

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Collect extra params from stdin (JSON)
    stdin_data = _parse_json_stdin({})

    try:
        from app.node.agent import (
            handle_bmc_list,
            handle_bmc_power,
            handle_file_sync,
            handle_install_task,
            handle_log,
            handle_pxe_config,
            handle_status,
        )

        if args.command == "status":
            result = handle_status()
        elif args.command == "pxe-config":
            result = handle_pxe_config()
        elif args.command == "bmc-list":
            result = handle_bmc_list()
        elif args.command == "bmc-power":
            result = handle_bmc_power(args.bmc_id, args.action)
        elif args.command == "install-task":
            params = {
                "host_id": args.host_id or stdin_data.get("host_id"),
                "iso_id": args.iso_id or stdin_data.get("iso_id"),
                "template_id": args.template_id or stdin_data.get("template_id"),
                "node_id": args.node_id or stdin_data.get("node_id"),
            }
            result = handle_install_task(args.action, args.task_id, params)
        elif args.command == "file-sync":
            result = handle_file_sync(args.file_ids)
        elif args.command == "log":
            result = handle_log(args.lines)
        else:
            _error(f"Unknown command: {args.command}")
            return

        json.dump({"success": True, "data": result}, sys.stdout)
    except SystemExit:
        raise
    except Exception as e:
        _error(str(e))


def _error(msg: str):
    json.dump({"success": False, "error": msg}, sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
