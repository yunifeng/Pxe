"""仓库管理测试"""
import os
from unittest.mock import patch, mock_open

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.exceptions import PxeException
from app.filemgr.repo import list_files, upload_file, remove_file
from app.models import FileInfo
from app.database import Base

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


class TestListFiles:
    def test_list_all_files(self):
        db = TestSession()
        db.add(FileInfo(name="a.sh", type="script", path="script/a.sh", category="script"))
        db.commit()
        result = list_files(db=db)
        assert len(result) == 1
        assert result[0]["name"] == "a.sh"
        db.close()

    def test_list_by_category(self):
        db = TestSession()
        db.add(FileInfo(name="a.sh", type="script", path="script/a.sh", category="script"))
        db.add(FileInfo(name="b.yml", type="config", path="config/b.yml", category="config"))
        db.commit()
        result = list_files(category="script", db=db)
        assert len(result) == 1
        assert result[0]["category"] == "script"
        db.close()

    def test_invalid_category_returns_all(self):
        db = TestSession()
        db.add(FileInfo(name="a.sh", type="script", path="script/a.sh", category="script"))
        db.commit()
        result = list_files(category="invalid", db=db)
        assert len(result) == 1
        db.close()


class TestUploadFile:
    def test_upload_success(self):
        db = TestSession()
        with patch("os.makedirs"), patch("builtins.open", mock_open()):
            result = upload_file("test.sh", b"echo hi", "script", db=db)
        assert result["name"] == "test.sh"
        assert result["size"] == 7  # len(b"echo hi") == 7
        db.close()

    def test_invalid_category_raises(self):
        db = TestSession()
        with pytest.raises(PxeException) as exc:
            upload_file("x", b"", "bad_category", db=db)
        assert exc.value.code == "INVALID_CATEGORY"
        db.close()


class TestRemoveFile:
    def test_remove_success(self):
        db = TestSession()
        fi = FileInfo(name="a.sh", type="script", path="script/a.sh", category="script")
        db.add(fi)
        db.commit()
        fid = fi.id
        with patch("os.path.exists", return_value=False):
            remove_file(fid, db=db)
        assert db.query(FileInfo).filter_by(id=fid).first() is None
        db.close()

    def test_remove_nonexistent_raises(self):
        db = TestSession()
        with pytest.raises(PxeException) as exc:
            remove_file(999, db=db)
        assert exc.value.code == "FILE_NOT_FOUND"
        db.close()
