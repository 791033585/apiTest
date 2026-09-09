from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape


OUTPUT = Path(__file__).parents[1] / "data" / "api_cases.xlsx"

HEADERS = [
    "id", "module", "feature", "story", "title", "method", "path",
    "headers", "params", "data", "json", "files", "check", "expected",
    "extract", "sql_check", "enabled",
]

ROWS = [
    ["1", "认证", "登录", "正常登录", "管理员登录成功", "POST", "/login", "{}", "{}", "{}", '{"username":"admin","password":"123456"}', "{}", "$.msg", "登录成功", "TOKEN=$.data.token\nUSER_ID=$.data.user.id", "", True],
    ["2", "认证", "登录", "错误密码", "登录失败", "POST", "/login", "{}", "{}", "{}", '{"username":"admin","password":"wrong"}', "{}", "status_code", 401, "", "", True],
    ["3", "用户管理", "查询用户", "查询成功", "获取用户列表成功", "GET", "/users", '{"Authorization":"Bearer {{TOKEN}}"}', '{"page":1,"page_size":10}', "{}", "{}", "{}", "$.msg", "获取用户列表成功", "", "", True],
    ["4", "用户管理", "查询用户", "查询详情", "获取指定用户成功", "GET", "/users/{{USER_ID}}", '{"Authorization":"Bearer {{TOKEN}}"}', "{}", "{}", "{}", "{}", "$.data.id", 1, "", "", True],
    ["5", "用户管理", "修改用户", "修改成功", "设置用户状态成功", "PUT", "/users/{{USER_ID}}/state", '{"Authorization":"Bearer {{TOKEN}}"}', "{}", "{}", '{"state":true}', "{}", "$.msg", "设置状态成功", "", "", True],
    ["6", "权限", "用户列表", "缺少 Token", "未授权访问", "GET", "/users", "{}", "{}", "{}", "{}", "{}", "status_code", 401, "", "", True],
    ["7", "演示", "断言", "错误预期", "故意失败的断言示例", "GET", "/users", '{"Authorization":"Bearer {{TOKEN}}"}', "{}", "{}", "{}", "{}", "$.msg", "这是错误预期", "", "", False],
]


def column_name(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def cell(reference: str, value: object) -> str:
    if value is None or value == "":
        return f'<c r="{reference}"/>'
    if isinstance(value, bool):
        return f'<c r="{reference}" t="b"><v>{1 if value else 0}</v></c>'
    if isinstance(value, (int, float)):
        return f'<c r="{reference}"><v>{value}</v></c>'
    text = escape(str(value)).replace("\n", "&#10;")
    return f'<c r="{reference}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def sheet_xml() -> str:
    xml_rows = []
    for row_number, row in enumerate([HEADERS, *ROWS], start=1):
        cells = "".join(
            cell(f"{column_name(column_number)}{row_number}", value)
            for column_number, value in enumerate(row, start=1)
        )
        xml_rows.append(f'<row r="{row_number}">{cells}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(xml_rows)}</sheetData>'
        '</worksheet>'
    )


FILES = {
    "[Content_Types].xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>''',
    "_rels/.rels": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>''',
    "xl/workbook.xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="api_cases" sheetId="1" r:id="rId1"/></sheets>
</workbook>''',
    "xl/_rels/workbook.xml.rels": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>''',
}


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED) as archive:
        for name, content in FILES.items():
            archive.writestr(name, content)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml())
    print(f"created {OUTPUT}")


if __name__ == "__main__":
    main()

