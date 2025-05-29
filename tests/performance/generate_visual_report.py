#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成可视化并发测试报告
提供直观的HTML报告，证明并发能力和内容正确性
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List


def generate_html_report(report_data: Dict, output_file: str):
    """生成HTML可视化报告"""

    html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>邮件系统并发测试报告</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            border-bottom: 3px solid #007acc;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #007acc;
            margin: 0;
            font-size: 2.5em;
        }}
        .header .subtitle {{
            color: #666;
            font-size: 1.2em;
            margin-top: 10px;
        }}
        .section {{
            margin: 30px 0;
            padding: 20px;
            border-left: 4px solid #007acc;
            background: #f9f9f9;
        }}
        .section h2 {{
            color: #007acc;
            margin-top: 0;
            display: flex;
            align-items: center;
        }}
        .section h2::before {{
            content: "📊";
            margin-right: 10px;
            font-size: 1.2em;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #007acc;
        }}
        .metric-label {{
            color: #666;
            margin-top: 5px;
        }}
        .success {{
            color: #28a745;
        }}
        .warning {{
            color: #ffc107;
        }}
        .error {{
            color: #dc3545;
        }}
        .evidence-list {{
            list-style: none;
            padding: 0;
        }}
        .evidence-list li {{
            padding: 10px;
            margin: 5px 0;
            background: white;
            border-left: 4px solid #28a745;
            border-radius: 4px;
        }}
        .evidence-list li::before {{
            content: "✅";
            margin-right: 10px;
        }}
        .sample-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
        }}
        .sample-table th,
        .sample-table td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        .sample-table th {{
            background: #007acc;
            color: white;
        }}
        .sample-table tr:nth-child(even) {{
            background: #f9f9f9;
        }}
        .check-mark {{
            color: #28a745;
            font-weight: bold;
        }}
        .x-mark {{
            color: #dc3545;
            font-weight: bold;
        }}
        .timing-chart {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .progress-bar {{
            width: 100%;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #007acc, #28a745);
            transition: width 0.3s ease;
        }}
        .content-preview {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 15px;
            margin: 10px 0;
            font-family: monospace;
            font-size: 0.9em;
            max-height: 200px;
            overflow-y: auto;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 邮件系统并发测试报告</h1>
            <div class="subtitle">高并发能力验证与内容完整性分析</div>
            <div class="subtitle">测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>

        {generate_summary_section(report_data)}
        {generate_concurrency_section(report_data)}
        {generate_timing_section(report_data)}
        {generate_content_section(report_data)}
        {generate_evidence_section(report_data)}
        {generate_samples_section(report_data)}

        <div class="footer">
            <p>📧 邮件系统并发测试报告 | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_template)


def generate_summary_section(report_data: Dict) -> str:
    """生成摘要部分"""
    summary = report_data.get("test_summary", {})

    return f"""
    <div class="section">
        <h2>测试摘要</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value success">{summary.get('successful_sent', 0)}</div>
                <div class="metric-label">成功发送</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{summary.get('total_received', 0)}</div>
                <div class="metric-label">成功接收</div>
            </div>
            <div class="metric-card">
                <div class="metric-value success">{summary.get('matched_emails', 0)}</div>
                <div class="metric-label">正确匹配</div>
            </div>
            <div class="metric-card">
                <div class="metric-value {'success' if summary.get('match_rate', 0) >= 95 else 'warning'}">{summary.get('match_rate', 0):.1f}%</div>
                <div class="metric-label">匹配率</div>
            </div>
        </div>
        
        <div class="progress-bar">
            <div class="progress-fill" style="width: {summary.get('match_rate', 0)}%"></div>
        </div>
        <p style="text-align: center; margin-top: 10px;">邮件匹配成功率: {summary.get('match_rate', 0):.1f}%</p>
    </div>
    """


def generate_concurrency_section(report_data: Dict) -> str:
    """生成并发性能部分"""
    evidence = report_data.get("concurrency_evidence", {})
    timing = report_data.get("timing_analysis", {})

    evidence_items = ""
    for point in evidence.get("evidence_points", []):
        evidence_items += f"<li>{point}</li>"

    return f"""
    <div class="section">
        <h2>并发性能证据</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{evidence.get('actual_concurrent_users', 0)}</div>
                <div class="metric-label">并发用户数</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{timing.get('send_rate', 0):.1f}</div>
                <div class="metric-label">发送速率(邮件/秒)</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{evidence.get('thread_pool_size', 0)}</div>
                <div class="metric-label">线程池大小</div>
            </div>
            <div class="metric-card">
                <div class="metric-value {'success' if timing.get('is_concurrent', False) else 'error'}">
                    {'✅ 是' if timing.get('is_concurrent', False) else '❌ 否'}
                </div>
                <div class="metric-label">真正并发</div>
            </div>
        </div>
        
        <ul class="evidence-list">
            {evidence_items}
        </ul>
    </div>
    """


def generate_timing_section(report_data: Dict) -> str:
    """生成时间分析部分"""
    timing = report_data.get("timing_analysis", {})
    dist = timing.get("time_distribution", {})

    return f"""
    <div class="section">
        <h2>时间分布分析</h2>
        <div class="timing-chart">
            <p><strong>发送时间窗口:</strong> {timing.get('first_send_time', 'N/A')} - {timing.get('last_send_time', 'N/A')}</p>
            <p><strong>总耗时:</strong> {timing.get('total_send_duration', 0):.2f} 秒</p>
            
            <div style="margin: 20px 0;">
                <h4>时间分布 (证明并发性):</h4>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
                    <div class="metric-card">
                        <div class="metric-value success">{dist.get('under_1s', 0)}</div>
                        <div class="metric-label">< 1秒</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{dist.get('1s_to_3s', 0)}</div>
                        <div class="metric-label">1-3秒</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{dist.get('3s_to_5s', 0)}</div>
                        <div class="metric-label">3-5秒</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value warning">{dist.get('over_5s', 0)}</div>
                        <div class="metric-label">> 5秒</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """


def generate_content_section(report_data: Dict) -> str:
    """生成内容完整性部分"""
    content = report_data.get("content_integrity", {})

    return f"""
    <div class="section">
        <h2>内容完整性验证</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{content.get('total_checked', 0)}</div>
                <div class="metric-label">检查邮件数</div>
            </div>
            <div class="metric-card">
                <div class="metric-value success">{content.get('integrity_passed', 0)}</div>
                <div class="metric-label">完整性通过</div>
            </div>
            <div class="metric-card">
                <div class="metric-value {'success' if content.get('integrity_rate', 0) >= 90 else 'warning'}">{content.get('integrity_rate', 0):.1f}%</div>
                <div class="metric-label">完整性率</div>
            </div>
            <div class="metric-card">
                <div class="metric-value {'success' if content.get('sender_accuracy', 0) >= 95 else 'warning'}">{content.get('sender_accuracy', 0):.1f}%</div>
                <div class="metric-label">发送者准确率</div>
            </div>
        </div>
        
        <div class="progress-bar">
            <div class="progress-fill" style="width: {content.get('integrity_rate', 0)}%"></div>
        </div>
        <p style="text-align: center; margin-top: 10px;">内容完整性: {content.get('integrity_rate', 0):.1f}%</p>
    </div>
    """


def generate_evidence_section(report_data: Dict) -> str:
    """生成证据汇总部分"""
    summary = report_data.get("test_summary", {})
    content = report_data.get("content_integrity", {})
    timing = report_data.get("timing_analysis", {})

    criteria = [
        (
            "邮件匹配率 ≥ 95%",
            summary.get("match_rate", 0) >= 95.0,
            f"{summary.get('match_rate', 0):.1f}%",
        ),
        (
            "内容完整性 ≥ 90%",
            content.get("integrity_rate", 0) >= 90.0,
            f"{content.get('integrity_rate', 0):.1f}%",
        ),
        (
            "发送者准确性 ≥ 95%",
            content.get("sender_accuracy", 0) >= 95.0,
            f"{content.get('sender_accuracy', 0):.1f}%",
        ),
        (
            "真正并发处理",
            timing.get("is_concurrent", False),
            "✅ 是" if timing.get("is_concurrent", False) else "❌ 否",
        ),
    ]

    criteria_rows = ""
    for criterion, passed, value in criteria:
        status_class = "success" if passed else "error"
        status_icon = "✅" if passed else "❌"
        criteria_rows += f"""
        <tr>
            <td>{criterion}</td>
            <td class="{status_class}">{status_icon}</td>
            <td>{value}</td>
        </tr>
        """

    return f"""
    <div class="section">
        <h2>验证标准汇总</h2>
        <table class="sample-table">
            <thead>
                <tr>
                    <th>验证标准</th>
                    <th>通过状态</th>
                    <th>实际值</th>
                </tr>
            </thead>
            <tbody>
                {criteria_rows}
            </tbody>
        </table>
    </div>
    """


def generate_samples_section(report_data: Dict) -> str:
    """生成样例展示部分"""
    content = report_data.get("content_integrity", {})
    samples = content.get("content_samples", [])[:5]  # 只显示前5个
    detailed = report_data.get("detailed_results", {}).get("sample_emails", [])[
        :10
    ]  # 前10个

    sample_content = ""
    for i, sample in enumerate(samples, 1):
        sample_content += f"""
        <div style="margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 8px;">
            <h4>📧 邮件样例 #{sample['number']:03d}</h4>
            <p><strong>主题:</strong> {sample['subject']}</p>
            <p><strong>完整性:</strong> <span class="{'check-mark' if sample['integrity_passed'] else 'x-mark'}">{'✅ 通过' if sample['integrity_passed'] else '❌ 失败'}</span></p>
            <p><strong>发送者:</strong> <span class="{'check-mark' if sample['sender_correct'] else 'x-mark'}">{'✅ 正确' if sample['sender_correct'] else '❌ 错误'}</span></p>
            <div class="content-preview">
                <strong>内容预览:</strong><br>
                {sample['content_preview']}
            </div>
        </div>
        """

    detailed_rows = ""
    for sample in detailed:
        detailed_rows += f"""
        <tr>
            <td>{sample['email_number']:03d}</td>
            <td class="{'check-mark' if sample['subject_correct'] else 'x-mark'}">{'✅' if sample['subject_correct'] else '❌'}</td>
            <td class="{'check-mark' if sample['all_markers_found'] else 'x-mark'}">{'✅' if sample['all_markers_found'] else '❌'}</td>
            <td>{sample.get('sender_email', '')[:30]}...</td>
            <td>{sample['size_bytes']}</td>
        </tr>
        """

    return f"""
    <div class="section">
        <h2>邮件内容样例</h2>
        {sample_content}
        
        <h3>前10封邮件详细验证表</h3>
        <table class="sample-table">
            <thead>
                <tr>
                    <th>编号</th>
                    <th>主题正确</th>
                    <th>内容完整</th>
                    <th>发送者</th>
                    <th>大小(字节)</th>
                </tr>
            </thead>
            <tbody>
                {detailed_rows}
            </tbody>
        </table>
    </div>
    """


def main():
    """主函数 - 用于独立运行生成报告"""
    # 查找最新的验证报告文件
    test_output_dir = Path("test_output")
    if not test_output_dir.exists():
        print("❌ 未找到test_output目录，请先运行并发测试")
        return

    # 查找最新的详细验证报告
    report_files = list(test_output_dir.glob("detailed_verification_report_*.json"))
    if not report_files:
        print("❌ 未找到验证报告文件，请先运行并发测试")
        return

    latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
    print(f"📊 正在处理报告文件: {latest_report}")

    # 读取报告数据
    with open(latest_report, "r", encoding="utf-8") as f:
        report_data = json.load(f)

    # 生成HTML报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_file = test_output_dir / f"visual_report_{timestamp}.html"

    generate_html_report(report_data, str(html_file))

    print(f"✅ 可视化报告已生成: {html_file}")
    print(f"🌐 请在浏览器中打开查看详细的并发测试证据")

    # 尝试自动打开浏览器
    try:
        import webbrowser

        webbrowser.open(f"file://{html_file.absolute()}")
        print("🔗 已尝试在默认浏览器中打开报告")
    except:
        print("💡 请手动在浏览器中打开HTML文件")


if __name__ == "__main__":
    main()
