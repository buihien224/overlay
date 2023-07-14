import argparse
import xml.dom.minidom

def format_xml(file_path):
    # Đọc nội dung file XML
    with open(file_path, 'r') as file:
        xml_content = file.read()

    # Tạo đối tượng DOM từ nội dung XML
    dom = xml.dom.minidom.parseString(xml_content)

    # Định dạng lại XML
    formatted_xml = dom.toprettyxml(indent='    ')

    # Ghi lại nội dung đã định dạng vào file
    with open(file_path, 'w') as file:
        file.write(formatted_xml)

# Tạo và cấu hình đối tượng argparse
parser = argparse.ArgumentParser(description='Format XML file')
parser.add_argument('file', metavar='FILE', help='Path to the XML file')

# Phân tích các đối số dòng lệnh
args = parser.parse_args()

# Gọi hàm format_xml với đường dẫn tới file XML từ đối số dòng lệnh
format_xml(args.file)