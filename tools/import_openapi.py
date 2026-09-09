import argparse
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.case_writer import ExcelCaseWriter
from core.openapi_case_generator import OpenApiCaseGenerator
from core.openapi_importer import OpenApiImporter


def serialize(value):
    if hasattr(value, "__dataclass_fields__"):
        return {name: serialize(getattr(value, name)) for name in value.__dataclass_fields__}
    if isinstance(value, list):
        return [serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="导入 Swagger/OpenAPI 并生成基础接口测试用例")
    parser.add_argument("--input", required=True, help="OpenAPI/Swagger JSON 或 YAML 文件")
    parser.add_argument("--output", required=True, help="统一接口定义 JSON 输出路径")
    parser.add_argument("--excel-output", help="基础 Excel 测试用例输出路径")
    args = parser.parse_args()

    imported = OpenApiImporter.from_file(args.input).parse()
    cases = OpenApiCaseGenerator().generate(imported)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(serialize(imported), ensure_ascii=False, indent=2), encoding="utf-8")

    if args.excel_output:
        ExcelCaseWriter.write(cases, args.excel_output)

    methods = Counter(interface.method for interface in imported.interfaces)
    disabled = sum(not case.enabled for case in cases)
    print(f"识别接口: {len(imported.interfaces)} 个")
    print("方法统计: " + ", ".join(f"{method}={count}" for method, count in sorted(methods.items())))
    print(f"生成基础用例: {len(cases)} 条")
    print(f"需要人工确认: {disabled} 条")
    print(f"接口定义输出: {output}")
    if args.excel_output:
        print(f"Excel 用例输出: {args.excel_output}")
    for warning in imported.warnings:
        print(f"警告: {warning}")


if __name__ == "__main__":
    main()
