"""安装任务状态机测试"""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.exceptions import PxeException
from app.pxe.tasks import (
    complete_task,
    create_task,
    get_task,
    list_tasks,
    retry_task,
    update_progress,
)

test_engine = create_engine(
    "sqlite:///file::memory:?cache=shared",
    connect_args={"check_same_thread": False},
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

from app import models  # noqa: F401


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    with test_engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        for table in Base.metadata.tables.values():
            conn.execute(text(f'DELETE FROM "{table.name}"'))
        conn.execute(text("PRAGMA foreign_keys=ON"))


class TestTaskStateMachine:
    """任务状态机测试: pending -> running -> completed/failed"""

    def test_create_task_pending(self):
        db = TestSession()
        task = create_task(host_id=1, iso_id=1, db=db)
        assert task["status"] == "pending"
        assert task["progress"] == 0
        db.close()

    def test_update_progress_running(self):
        db = TestSession()
        task = create_task(host_id=1, iso_id=1, db=db)
        updated = update_progress(task["id"], 50, db)
        assert updated["status"] == "running"
        assert updated["progress"] == 50
        assert updated["started_at"] is not None
        db.close()

    def test_complete_success(self):
        db = TestSession()
        task = create_task(host_id=1, iso_id=1, db=db)
        update_progress(task["id"], 80, db)
        result = complete_task(task["id"], True, duration=300, db=db)
        assert result["status"] == "completed"
        assert result["progress"] == 100
        assert result["completed_at"] is not None
        db.close()

    def test_complete_failed(self):
        db = TestSession()
        task = create_task(host_id=1, iso_id=1, db=db)
        result = complete_task(task["id"], False, error="Disk failure", db=db)
        assert result["status"] == "failed"
        db.close()

    def test_retry_failed_task(self):
        db = TestSession()
        task = create_task(host_id=1, iso_id=1, db=db)
        complete_task(task["id"], False, error="Timeout", db=db)
        retried = retry_task(task["id"], db)
        assert retried["status"] == "pending"
        assert retried["progress"] == 0
        db.close()

    def test_retry_non_failed_raises(self):
        db = TestSession()
        task = create_task(host_id=1, iso_id=1, db=db)
        with pytest.raises(PxeException) as exc:
            retry_task(task["id"], db)
        assert exc.value.code == "INVALID_TASK_STATE"
        db.close()

    def test_list_tasks(self):
        db = TestSession()
        create_task(host_id=1, iso_id=1, db=db)
        create_task(host_id=2, iso_id=2, db=db)
        all_tasks = list_tasks(db=db)
        assert len(all_tasks) == 2
        db.close()

    def test_get_nonexistent_raises(self):
        db = TestSession()
        with pytest.raises(PxeException) as exc:
            get_task(999, db)
        assert exc.value.code == "TASK_NOT_FOUND"
        db.close()
