import json

# Define the input and output file paths
INPUT_FILE_PATH = "../data/temp/get_data_ship.json"
OUTPUT_FILE_PATH = "ship_name_api.json"


def extract_data_from_json_file(input_path, output_path):
    """
    Reads a JSON file, extracts 'api_id' and 'api_name' from each object,
    and writes the results to a new JSON file with keys 'id' and 'name'.
    It ignores any entry where the 'api_id' is greater than 1500.

    Args:
        input_path (str): The path to the input JSON file.
        output_path (str): The path to the output text file.
    """
    try:
        # Read the JSON data from the input file
        print(f"Reading data from {input_path}...")
        with open(input_path, "r", encoding="utf-8") as infile:
            data_string = infile.read()
            # We assume it's a single, valid JSON array string for this task.
            json_data = json.loads(data_string)

        # Check if the parsed data is a list
        if not isinstance(json_data, list):
            print("Error: The file does not contain a valid JSON list.")
            return

        # Prepare a list to hold the extracted dictionaries
        extracted_items = []
        for item in json_data:
            # Check if the required keys exist and if the api_id is not greater than 1500
            if "api_id" in item and "api_name" in item and item["api_id"] <= 1500:
                extracted_items.append({"id": item["api_id"], "name": item["api_name"]})
            else:
                # Provide a specific warning for items that are being ignored
                if "api_id" in item and item["api_id"] > 1500:
                    print(
                        f"Warning: Skipping item with api_id > 1500: {item['api_id']}"
                    )
                else:
                    print(
                        f"Warning: Skipping item as 'api_id' or 'api_name' key is missing."
                    )

        # Write the extracted data to the output file as a JSON array
        print(f"Writing extracted data to {output_path}...")
        with open(output_path, "w", encoding="utf-8") as outfile:
            # Use json.dumps to write the list of dictionaries as a formatted JSON string
            json.dump(extracted_items, outfile, indent=4, ensure_ascii=False)

        print("Extraction complete. Check the output file for the results.")

    except FileNotFoundError:
        print(f"Error: The file {input_path} was not found.")
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from the file {input_path}.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


# Run the extraction function
if __name__ == "__main__":
    extract_data_from_json_file(INPUT_FILE_PATH, OUTPUT_FILE_PATH)
