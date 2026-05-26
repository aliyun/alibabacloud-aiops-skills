#!/usr/bin/env python3
"""
内容安全自动化测试 - 一站式入口脚本
整合：场景选择 → 凭证验证 → 控制台配置 → 测试运行 → 标注 → 报告

用法:
  python cst.py init              # 初始化：验证凭证链
  python cst.py configure <场景>   # 控制台配置标签开关
  python cst.py test <样本>        # 运行审核测试
  python cst.py annotate [文件]    # 人工标注
  python cst.py report [文件]      # 生成对齐报告
  python cst.py guardrail         # AI安全护栏效果测试
  python cst.py status            # 查看当前状态
  python cst.py full <场景> <样本>  # 完整流程：配置→测试→报告
"""
import argparse
import json
import os
import sys
import subprocess
from datetime import datetime

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(SKILL_DIR, "results")
SAMPLES_DIR = os.path.join(SKILL_DIR, "samples")
STATE_FILE = os.path.expanduser("~/.qoderwork/contentsec_console_state.json")


def ensure_results_dir():
    os.makedirs(RESULTS_DIR, exist_ok=True)


def run_python(script: str, *args, capture: bool = False) -> int:
    """运行 Python 脚本"""
    cmd = [sys.executable, os.path.join(SKILL_DIR, script)] + list(args)
    result = subprocess.run(cmd, cwd=SKILL_DIR, capture_output=capture, text=True)
    if not capture:
        print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="")
    return result.returncode


def cmd_init(args):
    """初始化：验证凭证链连通性"""
    print("=" * 60)
    print("  内容安全自动化测试 - 初始化")
    print("=" * 60)

    print("\n正在通过默认凭证链验证连通性...\n")

    rc = run_python("verify_auth.py")
    if rc == 0:
        # 保存配置状态
        state = {
            "initialized_at": datetime.now().isoformat(),
            "verified": True,
        }
        state_path = os.path.join(RESULTS_DIR, "cst_state.json")
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)
        print(f"\n✓ 初始化完成，状态已保存")
    else:
        print(f"\n✗ 验证失败，请检查凭证链配置和权限设置")
        sys.exit(1)


def cmd_configure(args):
    """控制台配置：浏览器自动化"""
    from scenarios import get_scenario, list_scenarios

    scenario = get_scenario(args.scenario)
    if not scenario:
        print(f"[ERROR] 未找到场景: {args.scenario}")
        print("\n可用场景:")
        for s in list_scenarios():
            print(f"  {s.id:30s} {s.name}")
        sys.exit(1)

    custom_service = f"{scenario.base_service}_{scenario.recommended_service_suffix}"

    print("=" * 60)
    print(f"  控制台配置 - {scenario.name}")
    print("=" * 60)
    print(f"  基础Service:  {scenario.base_service}")
    print(f"  自定义Service: {custom_service}")
    print(f"  标签数量:    {len(scenario.label_config)}")
    print("=" * 60)

    # 展示配置矩阵
    run_python("scenario_manager.py", "show", args.scenario)

    if not args.yes:
        confirm = input("\n是否继续执行控制台配置？(y/N) ")
        if confirm.lower() != "y":
            print("已取消")
            return

    # 执行浏览器自动化
    headless_flag = "--headless" if args.headless else ""
    cmd = [
        sys.executable,
        os.path.join(SKILL_DIR, "console_automator.py"),
        "--scenario", args.scenario,
    ]
    if args.headless:
        cmd.append("--headless")
    if args.new_login:
        cmd.append("--new-login")

    subprocess.run(cmd, cwd=SKILL_DIR)


def cmd_test(args):
    """运行审核测试"""
    sample_path = args.samples

    if not os.path.exists(sample_path):
        print(f"[ERROR] 样本文件不存在: {sample_path}")
        sys.exit(1)

    # 构建测试命令
    cmd = [
        sys.executable, os.path.join(SKILL_DIR, "main.py"),
        "run", "--samples", sample_path,
        "--concurrent", str(args.concurrent or 10),
    ]

    if args.services:
        cmd.extend(["--text-services", args.services])
    if args.format:
        cmd.extend(["--format", args.format])

    subprocess.run(cmd, cwd=SKILL_DIR)


def cmd_annotate(args):
    """人工标注"""
    results_file = args.file
    if not results_file:
        # 自动找到最新的结果文件
        latest = _find_latest_results()
        if not latest:
            print("[ERROR] 未找到测试结果文件")
            sys.exit(1)
        results_file = latest
        print(f"使用最新结果文件: {results_file}")

    cmd = [
        sys.executable, os.path.join(SKILL_DIR, "main.py"),
        "annotate", "--file", results_file,
    ]
    if args.annotator:
        cmd.extend(["--annotator", args.annotator])

    subprocess.run(cmd, cwd=SKILL_DIR)


def cmd_report(args):
    """生成对齐分析报告"""
    results_file = args.file
    if not results_file:
        latest = _find_latest_annotated()
        if not latest:
            print("[ERROR] 未找到已标注的结果文件")
            sys.exit(1)
        results_file = latest
        print(f"使用最新已标注文件: {results_file}")

    cmd = [
        sys.executable, os.path.join(SKILL_DIR, "main.py"),
        "report", "--file", results_file,
    ]
    if args.output:
        cmd.extend(["--output", args.output])

    subprocess.run(cmd, cwd=SKILL_DIR)


def cmd_status(args):
    """查看当前状态"""
    from scenarios import list_scenarios

    ensure_results_dir()
    state_path = os.path.join(RESULTS_DIR, "cst_state.json")

    print("=" * 60)
    print("  内容安全自动化测试 - 状态")
    print("=" * 60)

    # 凭证链状态
    try:
        from alibabacloud_credentials.client import Client as CredClient
        cred = CredClient()
        print(f"\n  凭证链: ✓ 已配置")
    except Exception:
        print(f"\n  凭证链: ✗ 未配置")

    # 初始化状态
    if os.path.exists(state_path):
        with open(state_path) as f:
            state = json.load(f)
        print(f"  初始化时间: {state.get('initialized_at', 'N/A')}")
        print(f"  验证状态: {'✓' if state.get('verified') else '✗'}")
    else:
        print(f"  初始化时间: 未初始化")
        print(f"  运行 python cst.py init 进行初始化")

    # 控制台登录状态
    if os.path.exists(STATE_FILE):
        print(f"  控制台登录: ✓ 有保存的会话")
    else:
        print(f"  控制台登录: 无保存的会话（首次需要手动登录）")

    # 可用场景
    print(f"\n  可用场景 ({len(list_scenarios())}):")
    for s in list_scenarios():
        print(f"    {s.id:30s} {s.name}")

    # 最近的结果文件
    if os.path.exists(RESULTS_DIR):
        files = sorted(os.listdir(RESULTS_DIR), reverse=True)[:5]
        if files:
            print(f"\n  最近的结果文件:")
            for f in files:
                full_path = os.path.join(RESULTS_DIR, f)
                size = os.path.getsize(full_path)
                size_str = f"{size/1024:.1f}KB" if size > 1024 else f"{size}B"
                print(f"    {f} ({size_str})")


def cmd_guardrail(args):
    """AI安全护栏效果测试（query_security_check / response_security_check）"""
    print("=" * 60)
    print("  AI安全护栏效果测试")
    print("=" * 60)

    cmd = [sys.executable, os.path.join(SKILL_DIR, "ai_guardrail.py")]
    if args.service:
        cmd.extend(["--service", args.service])
    if args.samples:
        cmd.extend(["--samples", args.samples])
    if args.output:
        cmd.extend(["--output", args.output])
    if getattr(args, "format", None):
        cmd.extend(["--format", args.format])

    subprocess.run(cmd, cwd=SKILL_DIR)


def cmd_full(args):
    """完整流程：控制台配置 → 测试 → 标注 → 报告"""
    print("\n" + "=" * 60)
    print("  完整工作流：配置 → 测试 → 标注 → 报告")
    print("=" * 60 + "\n")

    scenario = args.scenario
    samples = args.samples

    # Step 1: 控制台配置
    print(">>> Step 1/3: 控制台配置标签开关")
    configure_cmd = [
        sys.executable, os.path.join(SKILL_DIR, "console_automator.py"),
        "--scenario", scenario,
    ]
    rc = subprocess.run(configure_cmd, cwd=SKILL_DIR).returncode
    if rc != 0 and not args.skip_configure:
        print("控制台配置失败，是否继续测试？(y/N)")
        if input().lower() != "y":
            return

    # Step 2: 运行测试
    print("\n>>> Step 2/3: 运行审核测试")
    test_cmd = [
        sys.executable, os.path.join(SKILL_DIR, "main.py"),
        "run", "--samples", samples,
    ]
    custom_service = f"{args.base_service}_{scenario}"
    test_cmd.extend(["--text-services", custom_service])
    subprocess.run(test_cmd, cwd=SKILL_DIR)

    # Step 3: 标注（可选）
    print("\n>>> Step 3/3: 人工标注（可选）")
    if not args.skip_annotate:
        latest = _find_latest_results()
        if latest:
            print(f"找到最新结果: {latest}")
            annotate_cmd = [
                sys.executable, os.path.join(SKILL_DIR, "main.py"),
                "annotate", "--file", latest,
            ]
            if args.annotator:
                annotate_cmd.extend(["--annotator", args.annotator])
            subprocess.run(annotate_cmd, cwd=SKILL_DIR)


def _find_latest_results(pattern: str = "results_batch_*.json") -> str:
    """找到最新的结果文件"""
    import glob
    files = glob.glob(os.path.join(RESULTS_DIR, "results_batch_*.json"))
    if not files:
        # 尝试匹配任意JSON
        files = glob.glob(os.path.join(RESULTS_DIR, "results_*.json"))
    return sorted(files, reverse=True)[0] if files else ""


def _find_latest_annotated() -> str:
    """找到最新的已标注文件"""
    import glob
    files = glob.glob(os.path.join(RESULTS_DIR, "annotated_*.xlsx"))
    if not files:
        files = glob.glob(os.path.join(RESULTS_DIR, "annotated_*.json"))
    if not files:
        files = glob.glob(os.path.join(RESULTS_DIR, "annotated_*.csv"))
    return sorted(files, reverse=True)[0] if files else ""


def main():
    os.chdir(SKILL_DIR)  # 确保始终在skill目录中运行

    parser = argparse.ArgumentParser(
        description="内容安全自动化测试 - 一站式入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    # init
    subparsers.add_parser("init", help="初始化：验证凭证链连通性")

    # configure
    conf = subparsers.add_parser("configure", help="控制台配置标签开关")
    conf.add_argument("scenario", help="场景ID")
    conf.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    conf.add_argument("--headless", action="store_true", help="无头模式")
    conf.add_argument("--new-login", action="store_true", help="强制重新登录")

    # test
    test = subparsers.add_parser("test", help="运行审核测试")
    test.add_argument("samples", help="样本文件路径")
    test.add_argument("--services", help="指定服务列表，逗号分隔")
    test.add_argument("--concurrent", "-c", type=int, default=10, help="并发数")
    test.add_argument("--format", "-f", choices=["xlsx", "csv", "json"])

    # annotate
    ann = subparsers.add_parser("annotate", help="人工标注")
    ann.add_argument("--file", "-f", help="结果文件（默认使用最新）")
    ann.add_argument("--annotator", "-a", help="标注人姓名")

    # report
    rep = subparsers.add_parser("report", help="生成对齐分析报告")
    rep.add_argument("--file", "-f", help="已标注文件（默认使用最新）")
    rep.add_argument("--output", "-o", help="输出路径")

    # status
    subparsers.add_parser("status", help="查看当前状态")

    # guardrail
    guard = subparsers.add_parser("guardrail", help="AI安全护栏效果测试")
    guard.add_argument("--service", "-s", choices=["query", "response", "all"],
                       default="all", help="测试服务: query=输入检测, response=生成检测, all=全部")
    guard.add_argument("--samples", help="自定义样本JSON文件路径")
    guard.add_argument("--output", "-o", help="结果输出文件路径")
    guard.add_argument("--format", "-f", choices=["xlsx", "json"], default=None,
                       help="输出格式 (默认json，可选xlsx)")

    # full
    full = subparsers.add_parser("full", help="完整流程")
    full.add_argument("scenario", help="场景ID")
    full.add_argument("samples", help="样本文件路径")
    full.add_argument("--base-service", default="ugc_moderation_byllm",
                      help="基础Service名")
    full.add_argument("--annotator", "-a", help="标注人姓名")
    full.add_argument("--skip-configure", action="store_true", help="跳过控制台配置")
    full.add_argument("--skip-annotate", action="store_true", help="跳过标注")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cmd_map = {
        "init": cmd_init,
        "configure": cmd_configure,
        "test": cmd_test,
        "annotate": cmd_annotate,
        "report": cmd_report,
        "status": cmd_status,
        "guardrail": cmd_guardrail,
        "full": cmd_full,
    }

    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
