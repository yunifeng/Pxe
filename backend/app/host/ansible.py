"""Ansible 集成"""
import subprocess

from app.exceptions import PxeException


def run_playbook(host: str, playbook: str, extra_vars: dict = None) -> str:
    """执行 Playbook"""
    cmd = ["ansible-playbook", playbook, "-l", host]
    if extra_vars:
        var_str = ",".join(f"{k}={v}" for k, v in extra_vars.items())
        cmd.extend(["-e", var_str])
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise PxeException("ANSIBLE_ERROR", f"Playbook 执行失败: {e.stderr.strip()}")


def run_module(host: str, module: str, args: str = "") -> dict:
    """执行单个模块"""
    cmd = f"ansible {host} -m {module}"
    if args:
        cmd += f" -a '{args}'"
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60, shell=True)
        return {"stdout": result.stdout, "exit_code": 0}
    except subprocess.CalledProcessError as e:
        return {"stdout": e.stdout, "stderr": e.stderr, "exit_code": e.returncode}
