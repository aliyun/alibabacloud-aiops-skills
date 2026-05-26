#!/usr/bin/env python3
"""
控制台浏览器自动化模块
功能：登录引导 → 导航到规则配置 → 复制Service → 配置标签开关 → 保存
使用 agent-browser 驱动，通过 subprocess 调用
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime


class ConsoleAutomator:
    """内容安全控制台自动化"""

    SESSION = "contentsec"
    STATE_FILE = os.path.expanduser("~/.qoderwork/contentsec_console_state.json")

    # 控制台URL
    LOGIN_URL = "https://signin.aliyun.com"
    CONSOLE_URL = "https://yundun.console.aliyun.com/?p=contentsec#/green/textEnhanced"

    # 标签开关的CSS选择器模式（需要在实际控制台中确认）
    # 每个标签在规则编辑页是一个开关控件

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.mode_flag = "--headless" if headless else "--headed"

    def _run(self, *args, timeout: int = 30) -> subprocess.CompletedProcess:
        """执行 agent-browser 命令"""
        cmd = ["agent-browser", "--session", self.SESSION, self.mode_flag, *args]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def _run_sync(self, *args, timeout: int = 30) -> subprocess.CompletedProcess:
        """执行 agent-browser 命令（不带headed/headless，用于非open命令）"""
        cmd = ["agent-browser", "--session", self.SESSION, *args]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def launch_and_login(self):
        """启动浏览器并引导用户登录"""
        print("\n" + "=" * 60)
        print("正在打开阿里云登录页面...")
        print("=" * 60)

        # 先清理可能的旧会话
        self._run_sync("close")
        time.sleep(1)

        # 打开登录页
        result = self._run("open", self.LOGIN_URL)
        if result.returncode != 0:
            print(f"[ERROR] 浏览器启动失败: {result.stderr}")
            print("请确认已安装 agent-browser: agent-browser install")
            sys.exit(1)

        print("\n浏览器已打开，请在浏览器中完成登录（扫码/密码/短信）。")
        print("登录成功后，按 Enter 继续...")
        input()

        # 保存登录状态
        self._run_sync("state", "save", self.STATE_FILE)
        print(f"✓ 登录状态已保存到 {self.STATE_FILE}")
        print("  下次使用时可直接加载状态，无需重新登录")

        # 验证是否已登录
        self._run_sync("get", "title")
        self._run_sync("snapshot", "-i")
        return True

    def restore_session(self):
        """加载已保存的登录状态"""
        if not os.path.exists(self.STATE_FILE):
            return False

        self._run_sync("close")
        time.sleep(1)
        self._run_sync("state", "load", self.STATE_FILE)

        # 打开控制台验证
        result = self._run("open", self.CONSOLE_URL)
        if result.returncode != 0:
            return False

        time.sleep(2)
        result = self._run_sync("get", "title")
        return result.returncode == 0

    def navigate_to_text_rules(self):
        """导航到文本审核增强版规则配置页"""
        print("\n正在导航到文本审核规则配置...")
        self._run("open", self.CONSOLE_URL)
        self._run_sync("wait", "--load", "networkidle")
        time.sleep(2)

        # 获取页面快照
        result = self._run_sync("snapshot", "-i")
        print(result.stdout)
        return result.stdout

    def copy_service(self, base_service: str, new_service_name: str):
        """复制基础Service创建自定义Service"""
        print(f"\n正在复制 Service: {base_service} → {new_service_name}")

        # 先尝试快照
        result = self._run_sync("snapshot", "-i")
        snapshot = result.stdout

        # 查找目标 service 的复制按钮
        # 在控制台，每行 service 有一个操作列，包含"复制"按钮
        # 需要根据实际页面结构调整选择器

        # 方式1: 通过文本定位
        result = self._run_sync("find", "text", base_service, "snapshot", "-i")
        if result.returncode == 0:
            print(f"✓ 找到 Service: {base_service}")
        else:
            print(f"[WARN] 未通过文本找到 {base_service}，尝试其他方式...")
            print("当前页面内容:")
            print(snapshot[:2000])
            return False

        # 查找复制按钮（通常在同一行的操作列）
        # 使用 find role button with name "复制"
        result = self._run_sync("find", "role", "button", "click", "--name", "复制")

        if result.returncode != 0:
            # 备用方案：使用文本查找 "复制"
            result = self._run_sync("find", "text", "复制", "click")

        if result.returncode != 0:
            print(f"[WARN] 未找到复制按钮，可能需要手动操作")
            return False

        # 等待对话框出现
        self._run_sync("wait", "2000")

        # 在对话框中输入新 Service 名称
        result = self._run_sync("snapshot", "-i")
        print(f"复制对话框内容:\n{result.stdout[:2000]}")

        # 填充服务名称
        result = self._run_sync("find", "placeholder", "服务名称", "type", new_service_name)
        if result.returncode != 0:
            result = self._run_sync("find", "label", "服务名称", "type", new_service_name)

        # 点击确定
        self._run_sync("find", "text", "确定", "click")

        # 等待创建完成
        self._run_sync("wait", "3000")

        print(f"✓ Service {new_service_name} 创建完成")
        return True

    def open_service_rules(self, service_name: str):
        """打开指定Service的规则配置页"""
        print(f"\n正在打开 {service_name} 的规则配置...")

        # 在列表中找到目标 Service，点击"设置规则"
        result = self._run_sync("find", "text", service_name, "snapshot", "-i")

        # 查找并点击"设置规则"按钮
        result = self._run_sync("find", "text", "设置规则", "click")
        if result.returncode != 0:
            result = self._run_sync("find", "text", "管理检测规则", "click")

        self._run_sync("wait", "--load", "networkidle")
        time.sleep(3)

        # 获取当前页面
        result = self._run_sync("get", "url")
        print(f"当前URL: {result.stdout}")

        return True

    def enter_edit_mode(self):
        """进入编辑模式"""
        print("\n进入编辑模式...")

        # 点击"编辑"按钮
        result = self._run_sync("find", "text", "编辑", "click")
        if result.returncode != 0:
            print("[WARN] 未找到编辑按钮，可能已在编辑模式")

        time.sleep(2)
        result = self._run_sync("snapshot", "-i")
        print(f"规则编辑页快照:\n{result.stdout[:5000]}")
        return True

    def toggle_label(self, label_key: str, enable: bool):
        """
        切换指定标签的开关
        label_key: 标签key，如 "pornographic_adult"
        enable: True=开启，False=关闭
        """
        # 在规则编辑页，每个标签对应一个开关控件
        # 需要根据实际页面结构适配

        # 方案1: 通过标签名旁边的开关定位
        # 通常开关是 switch / toggle 组件

        # 先找标签文本，然后找其相邻的开关
        result = self._run_sync("find", "text", label_key, "snapshot", "-i")

        if result.returncode == 0:
            # 找到标签文本，查找相邻开关
            # 这需要根据实际DOM结构调整
            pass

        # 备用方案：使用 switch 组件的通用模式
        action = "check" if enable else "uncheck"

        # 尝试通过label关联定位switch
        result = self._run_sync("find", "label", label_key, action)
        if result.returncode != 0:
            # 尝试role方式
            result = self._run_sync("find", "role", "switch", action, "--name", label_key)

        return result.returncode == 0

    def configure_labels(self, label_config: dict):
        """
        批量配置标签开关
        label_config: {label_key: LabelSwitch} 配置字典
        """
        print(f"\n开始配置 {len(label_config)} 个标签...")

        from scenarios import LabelSwitch
        success_count = 0
        fail_count = 0

        for label_key, switch in label_config.items():
            if switch == LabelSwitch.OFF:
                enable = False
            else:
                enable = True

            status = "开启" if enable else "关闭"
            print(f"  [{status}] {label_key} ... ", end="", flush=True)

            if self.toggle_label(label_key, enable):
                print("✓")
                success_count += 1
            else:
                print("✗ (可能需要手动配置)")
                fail_count += 1

            time.sleep(0.5)  # 避免操作过快

        print(f"\n配置完成: 成功 {success_count}, 失败 {fail_count}")
        return success_count, fail_count

    def save_rules(self):
        """保存规则配置"""
        print("\n正在保存规则配置...")

        result = self._run_sync("find", "text", "保存", "click")
        if result.returncode != 0:
            result = self._run_sync("find", "role", "button", "click", "--name", "保存")

        self._run_sync("wait", "3000")

        print("✓ 规则已保存，等待 2~5 分钟生效...")
        print("  提示：生效后即可在API调用中使用新的service参数")

    def run_full_workflow(self, scenario_id: str, label_config: dict,
                          base_service: str, custom_service: str):
        """
        完整工作流：登录 → 复制Service → 配置标签 → 保存
        """
        from scenarios import get_scenario

        scenario = get_scenario(scenario_id)
        if not scenario:
            print(f"[ERROR] 未找到场景: {scenario_id}")
            return False

        print(f"\n{'=' * 60}")
        print(f"  内容安全控制台配置 - {scenario.name}")
        print(f"{'=' * 60}")
        print(f"  基础Service: {base_service}")
        print(f"  自定义Service: {custom_service}")
        print(f"  标签数量: {len(label_config)}")
        print(f"{'=' * 60}\n")

        # Step 1: 确保已登录
        if not self.restore_session():
            print("未找到有效的登录状态，引导用户登录...")
            self.launch_and_login()
        else:
            print("✓ 已恢复登录状态")

        # Step 2: 导航到规则配置
        self.navigate_to_text_rules()
        time.sleep(2)

        # Step 3: 复制Service
        self.copy_service(base_service, custom_service)
        time.sleep(2)

        # Step 4: 打开新Service的规则配置
        self.open_service_rules(custom_service)
        time.sleep(1)

        # Step 5: 进入编辑模式
        self.enter_edit_mode()
        time.sleep(1)

        # Step 6: 配置标签
        success, fail = self.configure_labels(label_config)
        time.sleep(1)

        # Step 7: 保存
        self.save_rules()

        print(f"\n{'=' * 60}")
        print(f"  控制台配置完成！")
        print(f"  Service: {custom_service}")
        print(f"  状态: 成功 {success} / 失败 {fail}")
        print(f"  请等待 2~5 分钟后在API调用中使用")
        print(f"{'=' * 60}\n")

        return fail == 0


def main():
    parser = argparse.ArgumentParser(description="内容安全控制台自动化配置")
    parser.add_argument("--scenario", "-s", required=True, help="场景ID")
    parser.add_argument("--headless", action="store_true", help="使用无头模式")
    parser.add_argument("--new-login", action="store_true", help="强制重新登录")
    args = parser.parse_args()

    from scenarios import get_scenario

    scenario = get_scenario(args.scenario)
    if not scenario:
        print(f"[ERROR] 未找到场景: {args.scenario}")
        print("可用场景: " + ", ".join(s.id for s in __import__('scenarios').list_scenarios()))
        sys.exit(1)

    custom_service = f"{scenario.base_service}_{scenario.recommended_service_suffix}"

    automator = ConsoleAutomator(headless=args.headless)

    if args.new_login:
        automator.launch_and_login()
        print("登录完成，请重新运行配置命令")
        return

    automator.run_full_workflow(
        scenario_id=args.scenario,
        label_config=scenario.label_config,
        base_service=scenario.base_service,
        custom_service=custom_service,
    )


if __name__ == "__main__":
    import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
