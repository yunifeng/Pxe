"""模板管理逻辑测试"""
import json
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.exceptions import PxeException
from app.models import Template
from app.template.preseed import create_template, get_template, list_templates, update_template, delete_template, render_template, BUILTIN_TEMPLATES

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


# Patch get_db in the preseed module so create/get/update/delete use our test session
def _test_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


class TestBuiltinTemplates:
    def test_has_ubuntu_template(self):
        assert len(BUILTIN_TEMPLATES) >= 1
        assert BUILTIN_TEMPLATES[0]["type"] == "user-data"
        assert "defaults" in BUILTIN_TEMPLATES[0]


class TestTemplateCRUD:
    @patch("app.template.preseed.get_db", side_effect=_test_get_db)
    def test_create_template(self, mock_db):
        tmpl = create_template("test", "preseed", "hello {{ name }}", {"name": "world"})
        assert tmpl["name"] == "test"
        assert tmpl["type"] == "preseed"
        assert tmpl["defaults"] == {"name": "world"}

    @patch("app.template.preseed.get_db", side_effect=_test_get_db)
    def test_get_template(self, mock_db):
        tmpl = create_template("test", "kickstart", "%packages\nvim\n%end")
        tid = tmpl["id"]
        result = get_template(tid)
        assert result["name"] == "test"
        assert result["content"] == "%packages\nvim\n%end"

    @patch("app.template.preseed.get_db", side_effect=_test_get_db)
    def test_get_nonexistent_raises(self, mock_db):
        with pytest.raises(PxeException) as exc:
            get_template(999)
        assert exc.value.code == "TEMPLATE_NOT_FOUND"

    @patch("app.template.preseed.get_db", side_effect=_test_get_db)
    def test_list_templates(self, mock_db):
        db = TestSession()
        create_template("a", "preseed", "x")
        create_template("b", "kickstart", "y")
        result = list_templates(db=db)
        assert len(result) == 2
        ks = list_templates(type="kickstart", db=db)
        assert len(ks) == 1
        assert ks[0]["name"] == "b"
        db.close()

    @patch("app.template.preseed.get_db", side_effect=_test_get_db)
    def test_update_template(self, mock_db):
        tmpl = create_template("old", "preseed", "x")
        tid = tmpl["id"]
        result = update_template(tid, name="new", content="updated")
        assert result["name"] == "new"
        assert result["content"] == "updated"

    @patch("app.template.preseed.get_db", side_effect=_test_get_db)
    def test_update_nonexistent_raises(self, mock_db):
        with pytest.raises(PxeException) as exc:
            update_template(999, name="x")
        assert exc.value.code == "TEMPLATE_NOT_FOUND"

    @patch("app.template.preseed.get_db", side_effect=_test_get_db)
    def test_delete_template(self, mock_db):
        tmpl = create_template("tmp", "preseed", "x")
        tid = tmpl["id"]
        delete_template(tid)
        with pytest.raises(PxeException):
            get_template(tid)


class TestRenderTemplate:
    @patch("app.template.preseed.get_db", side_effect=_test_get_db)
    def test_render_with_variables(self, mock_db):
        tmpl = create_template("r", "preseed", "Host: {hostname}, User: {username}")
        tid = tmpl["id"]
        result = render_template(tid, {"hostname": "srv01", "username": "admin"})
        assert "srv01" in result
        assert "admin" in result

    @patch("app.template.preseed.get_db", side_effect=_test_get_db)
    def test_render_missing_variable_raises(self, mock_db):
        tmpl = create_template("r", "preseed", "X: {missing}")
        tid = tmpl["id"]
        # Pass a dict with a different key so .format raises KeyError
        with pytest.raises(PxeException) as exc:
            render_template(tid, {"other": "val"})
        assert exc.value.code == "RENDER_ERROR"

    @patch("app.template.preseed.get_db", side_effect=_test_get_db)
    def test_render_without_variables(self, mock_db):
        tmpl = create_template("r", "preseed", "static content")
        tid = tmpl["id"]
        result = render_template(tid)
        assert result == "static content"
