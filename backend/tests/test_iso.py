"""ISO 管理 CRUD 测试"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import IsoImage
from app.pxe.iso import list_images, register_image, remove_image
from app.exceptions import PxeException

# 测试数据库
test_engine = create_engine(
    "sqlite:///file::memory:?cache=shared",
    connect_args={"check_same_thread": False},
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

from app import models  # noqa: F401


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    with test_engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        for table in Base.metadata.tables.values():
            conn.execute(text(f'DELETE FROM "{table.name}"'))
        conn.execute(text("PRAGMA foreign_keys=ON"))


class TestIsoCRUD:
    """ISO 镜像管理测试"""

    def test_register_and_list(self, tmp_path):
        iso_file = tmp_path / "test.iso"
        iso_file.write_bytes(b"fake-iso")
        db = TestSession()
        result = register_image("Test ISO", str(iso_file), "x86_64", db=db)
        assert result["name"] == "Test ISO"
        assert result["arch"] == "x86_64"
        images = list_images(db=db)
        assert len(images) == 1
        assert images[0]["name"] == "Test ISO"
        db.close()

    def test_register_nonexistent_file(self):
        db = TestSession()
        with pytest.raises(PxeException) as exc:
            register_image("Test", "/nonexistent.iso", db=db)
        assert exc.value.code == "FILE_NOT_FOUND"
        db.close()

    def test_remove_image(self):
        db = TestSession()
        img = IsoImage(name="To Remove", local_path="/tmp/test.iso", arch="x86_64")
        db.add(img)
        db.commit()
        db.refresh(img)
        remove_image(img.id, db)
        remaining = db.query(IsoImage).all()
        assert len(remaining) == 0
        db.close()

    def test_remove_nonexistent(self):
        db = TestSession()
        with pytest.raises(PxeException) as exc:
            remove_image(999, db)
        assert exc.value.code == "IMAGE_NOT_FOUND"
        db.close()
