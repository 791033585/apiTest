import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.case_generator import AiCaseGenerator
from ai.case_normalizer import normalize_cases
from ai.llm_client import DeepSeekClient
from core.case_writer import ExcelCaseWriter
from core.openapi_serialization import imported_from_dict


def main() -> None:
    parser = argparse.ArgumentParser(description="调用 DeepSeek 生成接口测试用例")
    parser.add_argument("--input", required=True, help="统一接口定义 JSON")
    parser.add_argument("--output", required=True, help="AI JSON 输出路径")
    parser.add_argument("--excel-output", required=True, help="Excel 用例输出路径")
    parser.add_argument("--requirement", default="", help="测试要求")
    parser.add_argument(
        "--operation-id",
        default="",
        help="只为指定 operation_id 生成用例；不传时生成所有接口",
    )
    parser.add_argument(
        "--max-cases-per-interface",
        type=int,
        default=20,
        help="单个接口最多生成多少条用例，默认 20",
    )
    args = parser.parse_args()

    imported = imported_from_dict(json.loads(Path(args.input).read_text(encoding="utf-8")))
    generator = AiCaseGenerator(
        DeepSeekClient.from_env(),
        max_cases_per_interface=args.max_cases_per_interface,
    )
    if args.operation_id:
        output = generator.generate_one(imported, args.operation_id, args.requirement)
    else:
        output = generator.generate(imported, args.requirement)
    cases = normalize_cases(output)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    ExcelCaseWriter.write(cases, args.excel_output)
    print(f"生成 AI 用例: {len(cases)} 条")
    print(f"JSON 输出: {output_path}")
    print(f"Excel 输出: {args.excel_output}")


if __name__ == "__main__":
    main()
