from utils.effects_utils import list_effects_in_directory
import json

def main():
    # Get the effects directory to create the effects dictionary
    print("Checking for new effects")
    effects_dir = "effects"
    effects_dict = list_effects_in_directory(effects_dir)

    with open(f'{effects_dir}/effects.json', 'w') as f:
        json.dump(effects_dict, f, indent=2)


if __name__ == "__main__":
    main()