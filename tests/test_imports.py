import importlib


def test_entrypoint_and_packages_importable() -> None:
    modules = [
        "main",
        "handlers.common",
        "handlers.user",
        "handlers.admin",
        "keyboards.inline",
        "utils.texts",
    ]
    for module_name in modules:
        importlib.import_module(module_name)
