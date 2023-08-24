import json


def load_json_body_from_file(file_name: str):
    """
    Load the contents of the file with the provided name and return as a json object.
    :param file_name: The name of the file.
    :return: The contents of the file.
    """
    with open(file_name, 'r') as file:
        data = file.read()

    return json.loads(data)
