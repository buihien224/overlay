import xml.etree.ElementTree as ET

# Đọc nội dung của hai tệp tin XML
with open('file1.xml', 'r', encoding='utf-8') as file1, open('file2.xml', 'r', encoding='utf-8') as file2:
    content1 = file1.read()
    content2 = file2.read()

# Tạo danh sách các phần tử 'name' từ hai tệp tin XML
def extract_names_and_values_from_xml(xml_content):
    root = ET.fromstring(xml_content)
    names_values = {}
    for string in root.findall('string'):
        name = string.get('name')
        value = string.text
        names_values[name] = value
    return names_values

names_values_file1 = extract_names_and_values_from_xml(content1)
names_values_file2 = extract_names_and_values_from_xml(content2)

# Tìm những phần tử có trong tệp tin 2 nhưng không có trong tệp tin 1
names_values_unique_to_file2 = {name: value for name, value in names_values_file2.items() if name not in names_values_file1}

# In ra các phần tử 'name' và 'giá trị' tương ứng của chúng có trong tệp tin 2 nhưng không có trong tệp tin 1
print("Các phần tử 'name' và 'giá trị' tương ứng có trong tệp tin 2 nhưng không có trong tệp tin 1:")
for name, value in names_values_unique_to_file2.items():
    print(f"Name: {name}, Giá trị: {value}")

# Ghi danh sách 'name' và 'giá trị' vào tệp tin XML mới
with open('output.xml', 'w', encoding='utf-8') as output_file:
    output_file.write('<resources>\n')
    for name, value in names_values_unique_to_file2.items():
        output_file.write(f'    <string name="{name}">{value}</string>\n')
    output_file.write('</resources>')

