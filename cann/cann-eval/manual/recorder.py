# manual/recorder.py
import datetime
import json
import os
import sys
import time

STEPS = [
    ("learn", "1.1", "Google 搜索 CANN 相关信息，找到官方文档"),
    ("learn", "1.2", "验证官方文档链接可访问，找到 Quick Start"),
    ("learn", "1.3", "搜索 Qwen2 CANN 部署文档链接"),
    ("get_docker", "2.1", "执行 docker pull ascendai/cann:latest"),
    ("get_docker", "2.2", "启动容器，验证 CANN 版本信息"),
    ("get_docker", "2.3", "容器内 source set_env.sh && atc --help"),
    ("get_runpkg", "3.1", "从 hiascend.com 找到 .run 包下载链接并下载"),
    ("get_runpkg", "3.2", "执行 .run --install，记录结果"),
    ("get_runpkg", "3.3", "（若安装成功）source set_env.sh && atc --help"),
    ("use_quickstart", "4.1", "容器内 source set_env.sh"),
    ("use_quickstart", "4.2", "容器内 atc --help，验证工具链"),
    ("use_qwen2", "5.1", "pip install modelscope transformers torch torch-npu"),
    ("use_qwen2", "5.2", "modelscope download Qwen2-0.5B"),
    ("use_qwen2", "5.3", "运行推理命令，记录结果"),
]


def _prompt_breakpoint() -> dict | None:
    note = input("  输入断点备注（留空跳过）：").strip()
    if not note:
        return None
    sev_input = input("  严重程度 [0=P0 阻断 / 1=P1 绕路可过 / 2=P2 轻微，默认 1]：").strip()
    sev = {"0": "P0", "1": "P1", "2": "P2"}.get(sev_input, "P1")
    cause = input("  原因（可选）：").strip()
    solution = input("  解决方案（可选）：").strip()
    return {"severity": sev, "phenomenon": note, "cause": cause, "solution": solution}


def main():
    print("=" * 60)
    print("CANN 易用性评估 — 人工辅助录制模式")
    print("=" * 60)
    print("按步骤逐一操作，每步完成后按 Enter 记录时间。\n")

    results: dict[str, dict] = {}
    all_breakpoints: list[dict] = []
    current_stage = None
    stage_start = None

    for stage_name, step_id, description in STEPS:
        if stage_name != current_stage:
            if current_stage is not None:
                results[current_stage]["stage_end"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            current_stage = stage_name
            stage_start = time.monotonic()
            results[stage_name] = {
                "stage_start": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "steps": [],
                "breakpoints": [],
            }
            print(f"\n{'='*40}")
            stage_labels = {
                "learn": "了解阶段", "get_docker": "获取阶段（Docker）",
                "get_runpkg": "获取阶段（.run 包）",
                "use_quickstart": "使用阶段（Quick Start）", "use_qwen2": "使用阶段（Qwen2-0.5B）",
            }
            print(f"  {stage_labels.get(stage_name, stage_name)}")
            print(f"{'='*40}\n")

        print(f"[步骤 {step_id}] {description}")
        input("  > 按 Enter 开始操作...")
        t0 = time.monotonic()

        input("  > 操作完成后按 Enter...")
        elapsed = round(time.monotonic() - t0, 1)

        bp = _prompt_breakpoint()
        if bp:
            all_breakpoints.append({"stage": stage_name, **bp})
            results[stage_name]["breakpoints"].append(bp)
            print(f"  ⚠ 断点 {bp['severity']} 已记录")

        results[stage_name]["steps"].append({
            "step_id": step_id,
            "description": description,
            "elapsed_s": elapsed,
        })
        print(f"  ✓ 耗时: {int(elapsed//60)}m{int(elapsed%60)}s\n")

    if current_stage:
        results[current_stage]["stage_end"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    report = {
        "test_date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "mode": "manual",
        "environment": {"note": "手动录制，请手动填写环境信息"},
        "stages": results,
        "breakpoints": all_breakpoints,
    }

    # 保存报告
    date_str = datetime.date.today().isoformat()
    os.makedirs("reports", exist_ok=True)
    json_path = f"reports/manual-{date_str}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"录制完成！报告已保存：{json_path}")
    print(f"断点数量：{len(all_breakpoints)}")
    print(f"{'='*60}")
    return report


if __name__ == "__main__":
    main()
