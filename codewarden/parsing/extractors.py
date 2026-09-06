"""Language-specific extraction of imports/functions/classes from a
tree-sitter parse tree into the model types in codewarden/parsing/model.py.
"""
from __future__ import annotations

from tree_sitter import Node

from codewarden.parsing.model import ClassInfo, FunctionInfo, ImportInfo


def _text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8")


# --------------------------------------------------------------------------
# Python
# --------------------------------------------------------------------------


def _python_import_names(node: Node, source: bytes) -> tuple[str, list[str]]:
    """Return (module, names) for an import_statement / import_from_statement."""
    if node.type == "import_statement":
        dotted_names = [c for c in node.children if c.type == "dotted_name"]
        aliased = [c for c in node.children if c.type == "aliased_import"]
        names = [_text(n, source) for n in dotted_names]
        names += [_text(n.child_by_field_name("name"), source) for n in aliased if n.child_by_field_name("name")]
        return "", names

    if node.type == "import_from_statement":
        module_node = node.child_by_field_name("module_name")
        module = _text(module_node, source) if module_node else ""
        name_nodes = [
            c
            for c in node.children
            if c.type in ("dotted_name", "aliased_import", "wildcard_import")
            and c != module_node
        ]
        names = []
        for n in name_nodes:
            if n.type == "wildcard_import":
                names.append("*")
            elif n.type == "aliased_import":
                target = n.child_by_field_name("name")
                names.append(_text(target, source) if target else _text(n, source))
            else:
                names.append(_text(n, source))
        return module, names

    return "", []


def extract_python(root: Node, source: bytes) -> tuple[list[ImportInfo], list[FunctionInfo], list[ClassInfo]]:
    imports: list[ImportInfo] = []
    functions: list[FunctionInfo] = []
    classes: list[ClassInfo] = []

    def walk(node: Node, current_class: str | None) -> None:
        if node.type in ("import_statement", "import_from_statement"):
            module, names = _python_import_names(node, source)
            imports.append(
                ImportInfo(
                    module=module,
                    names=names,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    raw_text=_text(node, source),
                )
            )
            return

        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            class_name = _text(name_node, source) if name_node else "<anonymous>"
            method_names: list[str] = []
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    if child.type == "function_definition":
                        fn_name_node = child.child_by_field_name("name")
                        if fn_name_node:
                            method_names.append(_text(fn_name_node, source))
            classes.append(
                ClassInfo(
                    name=class_name,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    method_names=method_names,
                )
            )
            for child in node.children:
                walk(child, class_name)
            return

        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            fn_name = _text(name_node, source) if name_node else "<anonymous>"
            functions.append(
                FunctionInfo(
                    name=fn_name,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    parent_class=current_class,
                    source=_text(node, source),
                )
            )
            for child in node.children:
                walk(child, current_class)
            return

        for child in node.children:
            walk(child, current_class)

    walk(root, None)
    return imports, functions, classes


# --------------------------------------------------------------------------
# TypeScript
# --------------------------------------------------------------------------


def _ts_import_module_and_names(node: Node, source: bytes) -> tuple[str, list[str]]:
    string_node = next((c for c in node.children if c.type == "string"), None)
    module = ""
    if string_node is not None:
        fragment = next((c for c in string_node.children if c.type == "string_fragment"), None)
        module = _text(fragment, source) if fragment else _text(string_node, source).strip("'\"")

    names: list[str] = []
    clause = next((c for c in node.children if c.type == "import_clause"), None)
    if clause is not None:
        for c in clause.children:
            if c.type == "identifier":
                names.append(_text(c, source))
            elif c.type == "namespace_import":
                ns_id = next((g for g in c.children if g.type == "identifier"), None)
                names.append(f"* as {_text(ns_id, source)}" if ns_id else "*")
            elif c.type == "named_imports":
                for spec in c.children:
                    if spec.type == "import_specifier":
                        ids = [g for g in spec.children if g.type == "identifier"]
                        if ids:
                            names.append(_text(ids[-1], source))
    return module, names


def extract_typescript(root: Node, source: bytes) -> tuple[list[ImportInfo], list[FunctionInfo], list[ClassInfo]]:
    imports: list[ImportInfo] = []
    functions: list[FunctionInfo] = []
    classes: list[ClassInfo] = []

    def walk(node: Node, current_class: str | None) -> None:
        if node.type == "import_statement":
            module, names = _ts_import_module_and_names(node, source)
            imports.append(
                ImportInfo(
                    module=module,
                    names=names,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    raw_text=_text(node, source),
                )
            )
            return

        if node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            class_name = _text(name_node, source) if name_node else "<anonymous>"
            method_names: list[str] = []
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    if child.type == "method_definition":
                        fn_name_node = child.child_by_field_name("name")
                        if fn_name_node:
                            method_names.append(_text(fn_name_node, source))
            classes.append(
                ClassInfo(
                    name=class_name,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    method_names=method_names,
                )
            )
            for child in node.children:
                walk(child, class_name)
            return

        if node.type in ("function_declaration", "method_definition"):
            name_node = node.child_by_field_name("name")
            fn_name = _text(name_node, source) if name_node else "<anonymous>"
            functions.append(
                FunctionInfo(
                    name=fn_name,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    parent_class=current_class,
                    source=_text(node, source),
                )
            )
            for child in node.children:
                walk(child, current_class)
            return

        for child in node.children:
            walk(child, current_class)

    walk(root, None)
    return imports, functions, classes
