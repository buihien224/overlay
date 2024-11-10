import xml.etree.ElementTree as ET
import argparse
import xml.dom.minidom as minidom
import os
import re

def is_md5(value):
    # Check if the value matches an MD5 pattern (32 hex characters)
    return bool(re.fullmatch(r"[a-fA-F0-9]{32}", value))


def parse_xml(file_path):
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        strings = {}
        plurals = {}

        for child in root:
            if child.tag == 'string' and 'name' in child.attrib:
                strings[child.attrib['name']] = child.text
            elif child.tag == 'plurals' and 'name' in child.attrib:
                items = {item.attrib['quantity']: item.text for item in child if 'quantity' in item.attrib}
                plurals[child.attrib['name']] = items

        return strings, plurals
    except ET.ParseError as e:
        print(f"Error parsing XML file: {file_path}. Error: {e}")
        return {}, {}


def should_skip_value(value):
    # Check for excluded conditions in the value
    if value is None or (len(value) == 1 and value.isalpha()) or value.startswith(('@', 'com.')) or value.isdigit() or is_md5(value):
        return True
    for char in ['$','%',':','-','.', '_']:
        if char in value and ' ' not in value:
            return True
    if not any(char.isalpha() for char in value):
        return True
    return False


def find_missing_translations(base_file, translation_file, output_file):
    base_strings, base_plurals = parse_xml(base_file)
    translation_strings, translation_plurals = parse_xml(translation_file)

    excluded_prefixes = ('earthly_', 'miuix_', 'mtrl_', 'path_', 'solar_', 'androidx_', 'abc_', 'library_android', 
                         'material_', 'fab_', 'chinese_', 'fmt_', 'btn_', 'm3_', 'abc_','create_table', 'preference_key', 'api_key', 'create_talbe', '.firebase.', 'google_', 'pref_key', 'preference_category_')

    missing_strings = {
        key: value for key, value in base_strings.items()
        if key not in translation_strings
        and not any(key.startswith(prefix) for prefix in excluded_prefixes)
        and not should_skip_value(value)
    }

    missing_plurals = {
        key: value for key, value in base_plurals.items()
        if key not in translation_plurals
        and not any(key.startswith(prefix) for prefix in excluded_prefixes)
        and all(v is not None and not v.startswith('@') and not v.startswith('com.') for v in value.values())
    }

    if missing_strings or missing_plurals:
        root = ET.Element("resources")
        
        for key, value in missing_strings.items():
            string_element = ET.SubElement(root, "string", name=key)
            string_element.text = value

        for key, value in missing_plurals.items():
            plurals_element = ET.SubElement(root, "plurals", name=key)
            for quantity, text in value.items():
                item_element = ET.SubElement(plurals_element, "item", quantity=quantity)
                item_element.text = text

        rough_string = ET.tostring(root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml_as_string = reparsed.toprettyxml(indent="  ")

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(pretty_xml_as_string)

        print(f"Missing translations have been written to {output_file}.")
    else:
        print("No missing translations found.")


def minimum_string(file_path, output_file):
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        filtered_root = ET.Element("resources")

        excluded_prefixes = ('earthly_', 'miuix_', 'mtrl_', 'path_', 'solar_', 'androidx_', 'abc_', 'library_android', 
                             'material_', 'fab_', 'chinese_', 'fmt_', 'btn_', 'm3_', 'abc_','create_table', 'preference_key', 'api_key', 'create_talbe', '.firebase.', 'google_', 'pref_key', 'preference_category_')

        for child in root:
            if child.tag == 'string' and 'name' in child.attrib:
                value = child.text
                key = child.attrib['name']
                if not any(key.startswith(prefix) for prefix in excluded_prefixes) and not should_skip_value(value):
                    string_element = ET.SubElement(filtered_root, "string", name=key)
                    string_element.text = value
            elif child.tag == 'plurals' and 'name' in child.attrib:
                key = child.attrib['name']
                items = {item.attrib['quantity']: item.text for item in child if 'quantity' in item.attrib}
                if not any(key.startswith(prefix) for prefix in excluded_prefixes) and all(
                        v is not None and not v.startswith('@') and not v.startswith('com.') for v in items.values()):
                    plurals_element = ET.SubElement(filtered_root, "plurals", name=key)
                    for quantity, text in items.items():
                        item_element = ET.SubElement(plurals_element, "item", quantity=quantity)
                        item_element.text = text

        rough_string = ET.tostring(filtered_root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml_as_string = reparsed.toprettyxml(indent="  ")

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(pretty_xml_as_string)

        print(f"Filtered content has been written to {output_file}.")
    except ET.ParseError as e:
        print(f"Error parsing XML file: {file_path}. Error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find missing translations or filter XML content.")
    parser.add_argument("action", choices=["find_missing", "minimum_string"], help="Action to perform.")
    parser.add_argument("file", help="Path to the base XML file.")
    parser.add_argument("translation_file", nargs="?", help="Path to the translation XML file (required for 'find_missing').")

    args = parser.parse_args()

    if args.action == "find_missing" and args.translation_file:
        translation_file_name = os.path.basename(args.translation_file)
        output_file = f"overlay_{translation_file_name}"
        find_missing_translations(args.file, args.translation_file, output_file)
    elif args.action == "minimum_string":
        output_file = f"filtered_{os.path.basename(args.file)}"
        minimum_string(args.file, output_file)
    else:
        print("Invalid arguments. Use 'find_missing' with both files or 'minimum_string' with one file.")
