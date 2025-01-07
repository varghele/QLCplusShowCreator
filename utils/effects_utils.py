import os
import ast


def list_effects_in_directory(directory):
    effects_dict = {}

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read())

                    # Get module name without .py extension
                    module_name = os.path.splitext(file)[0]

                    # Get all function definitions
                    functions = [node.name for node in ast.walk(tree)
                                 if isinstance(node, ast.FunctionDef)]

                    if functions:
                        effects_dict[module_name] = functions

                except Exception as e:
                    print(f"Error parsing {file_path}: {e}")

    return effects_dict


# To load and use the effects later:
def load_effect(module_name, effect_name):
    try:
        # Import the module dynamically
        import importlib
        module = importlib.import_module(f"effects.{module_name}")

        # Get the function from the module
        if hasattr(module, effect_name):
            return getattr(module, effect_name)
        else:
            print(f"Effect {effect_name} not found in {module_name}")
            return None

    except ImportError as e:
        print(f"Error importing module {module_name}: {e}")
        return None


# Usage example:
def setup_effects_combo(self, combo_box):
    effects = list_effects_in_directory("path/to/effects/directory")

    # Add empty option first
    combo_box.addItem("")

    # Add effects organized by module
    for module, functions in effects.items():
        for func in functions:
            combo_box.addItem(f"{module}.{func}")
