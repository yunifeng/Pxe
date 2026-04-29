"""节点状态监控"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Node
from app.node.ssh import exec_command

OFFLINE_THRESHOLD = 3


def check_node_status(node: Node, fail_count: int = 0) -> dict:
    """通过 SSH 检查节点状态"""
    try:
        result = exec_command(node.ip, "echo ok")
        if result["exit_code"] == 0:
            node.status = "online"
            node.last_heartbeat = datetime.now(timezone.utc)
            return {"id": node.id, "status": "online"}
    except Exception:
        pass
    new_fail = fail_count + 1
    if new_fail >= OFFLINE_THRESHOLD:
        node.status = "offline"
    return {"id": node.id, "status": node.status}


def check_all_nodes(db: Session = None) -> list:
    """批量检查所有节点"""
    sess = db or next(get_db())
    try:
        nodes = sess.query(Node).all()
        results = []
        for node in nodes:
            result = check_node_status(node)
            results.append(result)
        sess.commit()
        return results
    finally:
        if not db:
            sess.close()
