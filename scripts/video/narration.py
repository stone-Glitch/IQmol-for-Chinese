#!/usr/bin/env python3
# ============================================================================
# narration.py —— 全片中文旁白生成（edge-tts 神经网络女声）
#
# 用法：
#   python3 scripts/video/narration.py            # TTS 全部 + 合成旁白轨
#   python3 scripts/video/narration.py --mix-only # 仅用已生成的 n*.mp3 合成旁白轨
#   python3 scripts/video/narration.py --check    # 只校验字数/时长，不调用 TTS
#
# 设计：
#   成片 90.44s，按画面子段把解说词切成 7 段，每段用 adelay 固定放到
#   它在成片里的"起点"（对齐信息卡/录屏切换），再 amix 成一条连续旁白轨。
#
#   为什么不连续串联、而是固定起点？—— 固定起点能精确卡在画面变化点
#   （比如 34.24s 进段4 建模、44.24s 进计算），旁白和画面始终对得上；
#   串联方案会让旁白时间轴随每段实长漂移，越往后越错位。
#
#   实测 XiaoxiaoNeural 中文语速 ≈ 4.3~4.8 字/秒（首轮 report.json 实量）。
#   每段字数据此反推，使其略小于所在画面子段的容量（留 1s 以上余量），
#   避免溢出到下一段。溢出检查看运行后的 report.json，不要只信估算。
#
# 输出：
#   /tmp/iqmol_narr/n{0..6}.mp3   各段原始语音
#   /tmp/iqmol_narr/vn.m4a        合成后的连续旁白轨（44.1k mono aac）
#   /tmp/iqmol_narr/report.json   每段 {file, start, dur}（供合成脚本读取）
# ============================================================================
import subprocess, json, os, sys

VOICE = "zh-CN-XiaoxiaoNeural"
OUT = "/tmp/iqmol_narr"
os.makedirs(OUT, exist_ok=True)

# (全局起点秒, 文案)
# 时间轴依据 compose_bili.sh 的 SEG 拼接（实测各段时长）：
#   s1  0.00–12.72   开场（hook1/hook2/term 卡 + 中英对照/分屏/hero）
#   s2  12.72–25.72  痛点（pain1/pain2 卡 + 原段2）
#   s3  25.72–34.24  英→中转折
#   s4  34.24–68.24  gain1卡(2.2s) + 建模a(8s) + 计算b(8s) + 可视化c(11.8s) + 数据条(4s)
#                    → 段内真实切换点：36.44 / 44.44 / 52.44 / 64.24
#   s5  68.24–90.44  结尾引导卡(2.2s) + 收尾卡(二维码三连)
#
# ⚠️ 每句旁白必须卡在**它描述的画面真正出现**的起点上，不能压在信息卡上：
#    初版 n3 从 34.24 起播"建个分子很简单"，但 34.24–36.44 画面是 gain1 功能卡
#    （"建模·计算·可视化"大字），观众听着"建分子"看着大字卡——声画两张皮。
#    2026-10-03 拆成两句：34.24 念卡片文字呼应，36.44 建模录屏开始才讲建分子。
SEGMENTS = [
    (0.00,  "这是 IQmol，一款开源的量子化学可视化软件。我们把整个界面都汉化了——四百多个菜单、对话框、按钮和提示，全部变成中文。"),
    (12.72, "做计算化学的你，可能早受够了满屏的英文菜单。看不懂的选项、记不住的术语，每点一步都要停下查词典。"),
    (25.72, "现在不一样了。一键切换，整个软件就是全中文界面，从菜单到提示，处处熟悉。"),
    (34.24, "建模、计算、可视化。"),
    # n3a 实测 2.86s（顿号停顿拖长），溢出 gain1 卡 0.66s——n3b 不能从 36.44 起，
    # 否则两句叠音。移到 37.20（n3a 结束后 0.1s，建模画面已开始 0.8s，观感自然）。
    (37.20, "建个分子很简单：打开元素周期表，点选原子，拖一下就画出化学键。"),
    (44.44, "要做计算，进菜单选 Q-Chem，参数面板一目了然，填好就能提交任务。"),
    (52.44, "结果出来后，直接用鼠标旋转、缩放分子，实时查看三维结构，渲染流畅不卡顿。"),
    (68.24, "我们不只是翻译界面，更把'弛豫密度''冻结核近似'这些术语，都按计算化学的标准译法写进软件。IQmol 中文版完全免费、开源，点个关注，主页就能下载。"),
]

TOTAL = 92.0  # 旁白轨统一裁剪到这个长度（>= 成片总长即可）


def gen(i: int, text: str):
    mp3 = f"{OUT}/n{i}.mp3"
    subprocess.run([sys.executable, "-m", "edge_tts", "--voice", VOICE,
                    "--text", text, "--write-media", mp3], check=True)
    d = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", mp3]))
    return mp3, d


def main():
    args = sys.argv[1:]
    check_only = "--check" in args
    mix_only = "--mix-only" in args

    report = []
    if not mix_only:
        print("=== 旁白分段（voice=%s, 语速≈4.84字/秒）===" % VOICE)
        for i, (start, text) in enumerate(SEGMENTS):
            nxt = SEGMENTS[i + 1][0] if i + 1 < len(SEGMENTS) else TOTAL
            if check_only:
                d = len(text) / 4.84
                mp3, real = "(skip)", d
            else:
                mp3, d = gen(i, text)
                real = d
            end = start + real
            over = end - nxt
            flag = f"  ⚠️溢出 {over:.2f}s 到下一段!" if over > 0.05 else ""
            print(f"  n{i}: 起点{start:6.2f} 容量{nxt-start:5.2f}s 字数{len(text):3d} "
                  f"实长{real:6.2f}s 结束{end:6.2f}{flag}")
            report.append({"file": mp3, "start": start, "dur": real})
        json.dump(report, open(f"{OUT}/report.json", "w"), indent=2)
    else:
        report = json.load(open(f"{OUT}/report.json"))

    if check_only and not mix_only:
        return

    # ---- 合成连续旁白轨：每段 adelay 到其起点，再 amix ----
    fcp = []
    for i, x in enumerate(report):
        ms = int(x["start"] * 1000)
        fcp.append(f"[{i}:a]aformat=sample_fmts=fltp:sample_rates=44100:"
                   f"channel_layouts=mono,adelay={ms}|{ms}[a{i}]")
    # ⚠️ 各段 filter 之间、以及段与 amix 之间都必须用分号分隔，
    #    否则 ffmpeg 会把 "...[a6]amix=..." 当成 trailing garbage 解析失败。
    amix = "".join(f"[a{i}]" for i in range(len(report)))
    amix += f"amix=inputs={len(report)}:normalize=0[narr]"
    cmd = ["ffmpeg", "-y", "-nostdin"]
    for x in report:
        cmd += ["-i", x["file"]]
    cmd += ["-filter_complex", ";".join(fcp) + ";" + amix,
            "-map", "[narr]", "-t", str(TOTAL),
            "-c:a", "aac", "-b:a", "192k", f"{OUT}/vn.m4a"]
    subprocess.run(cmd, check=True)
    print(f"\n✅ 生成完毕：{OUT}/vn.m4a（连续旁白轨）")
    print(f"   各段原始语音：{OUT}/n{{0..{len(report)-1}}}.mp3")


if __name__ == "__main__":
    main()
