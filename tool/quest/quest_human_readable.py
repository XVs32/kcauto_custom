import json


def convert_requirements_ids(requirements_list, lookup_table):
    """
    Traverses a list of requirements to find and convert integer IDs to strings
    based on a provided lookup table. This function is specific to the
    'requirements' list structure.

    Args:
        requirements_list (list): The list of requirement dictionaries.
        lookup_table (dict): The dictionary for ID lookup, where keys are integer IDs
                             and values are string names.

    Returns:
        list: The modified requirements list with IDs converted.
    """
    for requirement in requirements_list:
        if "id" in requirement and isinstance(requirement["id"], list):
            converted_ids = []
            for id_num in requirement["id"]:
                if id_num in lookup_table:
                    converted_ids.append(lookup_table[id_num])
                else:
                    print(f"Warning: ID {id_num} not found in the lookup table.")
                    converted_ids.append(id_num)  # Keep the original if not found
            requirement["id"] = converted_ids
    return requirements_list


def main():
    """
    Main function to load JSON data from files, perform the ID conversion,
    and save the results to a new file.
    """
    try:
        # Load the lookup table from ship_name.json
        with open("../../reference/ship_name_api.json", "r", encoding="utf-8") as f:
            lookup_list = json.load(f)

        # Convert the list of dictionaries into a dictionary for faster lookup
        id_lookup = {item["id"]: item["name"] for item in lookup_list}

        # Load the data to be converted from quest.json
        with open("../../data/quests/quests.json", "r", encoding="utf-8") as f:
            json_data = json.load(f)

        print("Original JSON data from quest.json:")
        print(json.dumps(json_data, indent=2))

        # Perform the conversion only on the 'requirements' sections
        for key in json_data:
            entry = json_data[key]
            if (
                "fleet_composition" in entry
                and "requirements" in entry["fleet_composition"]
            ):
                entry["fleet_composition"]["requirements"] = convert_requirements_ids(
                    entry["fleet_composition"]["requirements"], id_lookup
                )

        # Write the converted data to a new human-readable JSON file
        output_filename = "./quest_human_readable.json"
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        print(f"\nConverted JSON data has been saved to '{output_filename}'")

    except FileNotFoundError as e:
        print(f"Error: One of the required files was not found: {e}")
    except json.JSONDecodeError:
        print(
            "Error: Could not decode one of the JSON files. Please check the file content for errors."
        )


if __name__ == "__main__":
    main()
