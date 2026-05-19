import importlib
import inspect
import pkgutil

from orion.commands.base import BaseCommand


def load_commands() -> list[BaseCommand]:
    commands = []
    package_name = "orion.commands"
    package = importlib.import_module(package_name)

    for module_info in pkgutil.iter_modules(package.__path__):
        module_name = module_info.name

        # ignorar archivos que no son comandos ejecutables
        if module_name in {"base", "registry", "__init__"}:
            continue

        full_module_name = f"{package_name}.{module_name}"
        module = importlib.import_module(full_module_name)

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if not issubclass(obj, BaseCommand):
                continue

            if obj is BaseCommand:
                continue

            # solo clases definidas en ese módulo
            if obj.__module__ != full_module_name:
                continue

            commands.append(obj())

    # orden estable por nombre de clase
    commands.sort(key=lambda c: c.__class__.__name__)
    return commands