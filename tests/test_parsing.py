from pathlib import Path

import pytest

from codewarden.parsing.parser import parse_file, parse_source

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_python_imports_extracted():
    parsed = parse_file(FIXTURES / "user_controller.py")
    assert parsed.language == "python"

    modules = {(imp.module, tuple(imp.names)) for imp in parsed.imports}
    assert ("", ("json",)) in modules
    assert ("typing", ("Optional",)) in modules
    assert ("services.user_service", ("UserService",)) in modules
    # aliased import: `UserRecord as UserRow` -> the original imported name is tracked
    assert ("db.models.orm", ("UserRecord",)) in modules


def test_python_classes_and_methods_extracted():
    parsed = parse_file(FIXTURES / "user_controller.py")
    assert len(parsed.classes) == 1
    controller = parsed.classes[0]
    assert controller.name == "UserController"
    assert set(controller.method_names) == {"__init__", "get_user", "create_user"}


def test_python_functions_extracted_with_parent_class():
    parsed = parse_file(FIXTURES / "user_controller.py")
    by_name = {f.name: f for f in parsed.functions}

    assert by_name["get_user"].parent_class == "UserController"
    assert by_name["create_user"].parent_class == "UserController"
    assert by_name["health_check"].parent_class is None
    assert "def health_check" in by_name["health_check"].source


def test_python_function_line_numbers_are_sane():
    parsed = parse_file(FIXTURES / "user_controller.py")
    by_name = {f.name: f for f in parsed.functions}
    health_check = by_name["health_check"]
    assert health_check.start_line < health_check.end_line
    # health_check is defined near the end of the fixture file
    assert health_check.start_line > 15


def test_typescript_imports_extracted():
    parsed = parse_file(FIXTURES / "user_controller.ts")
    assert parsed.language == "typescript"

    modules = {(imp.module, tuple(imp.names)) for imp in parsed.imports}
    assert ("../services/userService", ("UserService",)) in modules
    assert ("express", ("* as express",)) in modules


def test_typescript_classes_and_methods_extracted():
    parsed = parse_file(FIXTURES / "user_controller.ts")
    assert len(parsed.classes) == 1
    controller = parsed.classes[0]
    assert controller.name == "UserController"
    assert set(controller.method_names) == {"constructor", "getUser", "createUser"}


def test_typescript_functions_extracted_with_parent_class():
    parsed = parse_file(FIXTURES / "user_controller.ts")
    by_name = {f.name: f for f in parsed.functions}

    assert by_name["getUser"].parent_class == "UserController"
    assert by_name["healthCheck"].parent_class is None


def test_unsupported_extension_raises():
    with pytest.raises(ValueError):
        parse_source("foo.rb", "puts 'hi'")
