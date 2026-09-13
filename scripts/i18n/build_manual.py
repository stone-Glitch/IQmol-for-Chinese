# -*- coding: utf-8 -*-
"""生成 IQmol 中文版用户手册（自包含 HTML，图片 base64 内嵌）。
源：IQmol3/doc/IQmolUserGuide.tex (v3.2, 2025, Andrew Gilbert)
术语对齐：/workspace/IQmol3/translations/zh_CN.ts 汉化术语表
"""
import os, base64, re

DOC = "/workspace/IQmol3/doc"
OUT = "/workspace/docs/IQmol用户手册.html"

def b64(path):
    p = os.path.join(DOC, path)
    if not os.path.exists(p):
        return ""
    with open(p, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")

def img(tag):
    # tag 形如 figures/Viewer.png
    return f'<img class="fig" src="{b64(tag)}" alt="{os.path.basename(tag)}"/>'

# 用 [[FIG:figures/X.png]] 占位，渲染时替换
CN = r"""__BODY__"""

def render(body):
    def rep(m):
        return img(m.group(1))
    return re.sub(r'\[\[FIG:([^\]]+)\]\]', rep, body)

CSS = """
:root{--blue:#1f6fb8;--ink:#1a1a1a;--muted:#555;--bg:#fff;--line:#e3e8ee;}
* {box-sizing:border-box;}
body{font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;color:var(--ink);
  background:var(--bg);margin:0;line-height:1.75;font-size:16px;}
header.cover{text-align:center;padding:64px 24px 40px;border-bottom:4px solid var(--blue);margin-bottom:32px;}
header.cover h1{font-size:34px;margin:18px 0 6px;letter-spacing:1px;}
header.cover .sub{color:var(--muted);font-size:15px;}
header.cover img{width:120px;}
nav.toc{background:#f6f9fc;border:1px solid var(--line);border-radius:10px;padding:20px 28px;margin:0 32px 40px;max-width:920px;}
nav.toc h2{margin:0 0 12px;font-size:18px;color:var(--blue);}
nav.toc ol{margin:0;padding-left:22px;}
nav.toc li{margin:4px 0;}
nav.toc a{color:#234;text-decoration:none;}
nav.toc a:hover{text-decoration:underline;}
main{max-width:920px;margin:0 auto;padding:0 32px 80px;}
h2.sec{border-left:6px solid var(--blue);padding-left:14px;margin:48px 0 18px;font-size:26px;color:var(--blue);}
h3.sub{margin:30px 0 12px;font-size:20px;color:#16324f;}
h4.subsub{margin:22px 0 8px;font-size:17px;color:#234;}
p{margin:12px 0;}
ul,ol{padding-left:26px;}
li{margin:6px 0;}
.figure{text-align:center;margin:22px 0;}
.figure img{max-width:100%;border:1px solid var(--line);border-radius:6px;background:#fff;padding:6px;}
.cap{color:var(--muted);font-size:14px;margin-top:8px;}
kbd,.ui{background:#eef3f8;border:1px solid #cdd9e5;border-radius:4px;padding:1px 7px;font-family:inherit;font-size:14px;color:#16324f;}
.path{background:#f3f5f7;border:1px solid var(--line);border-radius:4px;padding:2px 8px;font-family:"Cascadia Code",Consolas,monospace;font-size:14px;}
pre.code{background:#0f1b29;color:#e6edf3;border-radius:8px;padding:16px 18px;overflow:auto;font-size:13.5px;line-height:1.5;}
.menu{color:var(--blue);font-weight:600;}
hr.sec-line{border:none;border-top:2px solid var(--blue);margin:8px auto;width:80%;}
.note{background:#fff8e6;border-left:4px solid #e0a800;padding:10px 14px;border-radius:4px;color:#5c4a00;}
footer{text-align:center;color:var(--muted);font-size:13px;padding:24px;border-top:1px solid var(--line);}
"""

# ----- 封面 -----
cover = f"""
<header class="cover">
{img('figures/Crown.png')}
<h1>IQmol 使用简介</h1>
<div class="sub">v3.2 (2025) &nbsp;·&nbsp; Andrew Gilbert</div>
</header>
"""

# ----- 目录 -----
toc = """
<nav class="toc">
<h2>目录</h2>
<ol>
<li><a href="#s1">简介</a>
  <ol><li><a href="#s1-1">安装</a></li><li><a href="#s1-2">概述</a></li></ol></li>
<li><a href="#s2">构建分子</a>
  <ol>
   <li><a href="#s2-1">添加原子与片段</a></li>
   <li><a href="#s2-2">使用分子力学优化结构</a></li>
   <li><a href="#s2-3">对称化结构</a></li>
   <li><a href="#s2-4">指定几何参数</a></li>
   <li><a href="#s2-5">操作与选择分子</a></li>
   <li><a href="#s2-6">添加额外构象</a></li>
  </ol></li>
<li><a href="#s3">运行 Q-Chem 计算</a>
  <ol><li><a href="#s3-1">QUI（Q-Chem 用户界面）</a></li>
      <li><a href="#s3-2">作业监视器</a></li>
      <li><a href="#s3-3">配置服务器</a></li></ol></li>
<li><a href="#s4">分析结果</a>
  <ol>
   <li><a href="#s4-1">分子表面</a></li>
   <li><a href="#s4-2">从检查点文件绘制分子轨道</a></li>
   <li><a href="#s4-3">其他轨道与密度</a></li>
   <li><a href="#s4-4">导出立方体文件数据</a></li>
   <li><a href="#s4-5">可视化立方体文件数据</a></li>
   <li><a href="#s4-6">轨道动画</a></li>
   <li><a href="#s4-7">势能面</a></li>
   <li><a href="#s4-8">振动频率</a>
     <ol><li><a href="#s4-8-1">同位素取代</a></li></ol></li>
   <li><a href="#s4-9">NMR 谱</a></li>
  </ol></li>
<li><a href="#s5">外观</a>
  <ol>
   <li><a href="#s5-1">视图相机</a></li>
   <li><a href="#s5-2">裁剪平面</a></li>
   <li><a href="#s5-3">着色器</a></li>
   <li><a href="#s5-4">导出 POV-Ray 文件</a></li>
  </ol></li>
<li><a href="#s6">样例图像</a></li>
</ol>
</nav>
"""

# ===== 正文（逐章中文翻译）=====
body = ""

# --- 1 Introduction ---
body += """
<section id="s1">
<h2 class="sec">1 简介</h2>
<p><b>IQmol</b> 是一款开源的分子编辑器与可视化软件包，可运行于 Windows、Mac OS X 和 Linux。它能读取多种化学文件格式，包括 xyz、cml、pdb、mol、fchk、立方体（cube）数据以及 Q-Chem 的输入/输出文件。它还包含一个自由形式的分子构建器，可用于创建任意分子结构。这些结构可使用分子力学力场进行优化，并可对称化以确保结构具有正确的点群对称性。此外还内置分子与官能团库，便于构建更复杂的分子。</p>
<p>IQmol 能够显示多种分子性质，包括原子电荷、偶极矩和简正模式。可以显示多种表面，包括分子轨道、（自旋）密度和范德华表面。这些表面能够根据任意标量场（如静电势）着色。还支持振动频率、反应路径与优化路径的动画。</p>
<p>IQmol 可以独立运行，同时也被编写为能与 <b>Q-Chem</b>（<span class="path">https://www.q-chem.com</span>）计算化学软件包无缝协作。其内置的综合输入文件生成器——<b>Q-Chem 用户界面（QUI）</b>——提供了对 Q-Chem 中绝大多数可用选项的访问，并以直观的分层方式呈现。生成的输入文件可提交到已安装 Q-Chem 的本地或远程服务器。特别地，还提供一个公开可访问的服务器，允许在不购买和安装 Q-Chem 的情况下运行小规模（限制约 10 分钟）的量子化学计算。</p>

<h3 class="sub" id="s1-1">1.1 安装</h3>
<p>最新版 IQmol 可从以下网站下载：</p>
<p style="text-align:center"><span class="path">https://www.iqmol.org/downloads.html</span></p>
<p><b>Mac (OS X)</b>：提供磁盘映像文件。下载后双击挂载，将应用程序复制到"应用程序"目录或其他任意位置。</p>
<p><b>Windows</b>：提供安装程序，引导完成安装流程，并在桌面创建程序快捷方式。</p>
<p><b>Linux</b>：现已提供 <span class="path">.deb</span> 与 <span class="path">.rpm</span> 软件包，可用 <span class="path">dpkg</span> 或 <span class="path">yum</span> 安装：</p>
<pre class="code">sudo dpkg -i iqmol_x.x.x.deb
sudo apt-get install -f</pre>
<p>第二条命令用于解决 Qt 库依赖（你可能尚未安装）。</p>
<pre class="code">sudo yum install iqmol-x.x.x.x86_64.rpm</pre>
<p>注意：上述两种情况都需要 root 权限。</p>

<h3 class="sub" id="s1-2">1.2 概述</h3>
<div class="figure">[[FIG:figures/Viewer.png]]
<div class="cap">图 1.1　IQmol 主窗口</div></div>
<p>主 IQmol 窗口如图 1.1 所示，由以下主要部分组成：</p>
<ul>
<li><b>视图（Viewer）</b>是窗口的主要区域，可在此查看并与分子交互。</li>
<li><b>工具栏（Toolbar）</b>位于顶部，提供常用命令，并可在不同视图模式间切换，包括<span class="ui">操作</span> [[FIG:figures/ManipulateButton.png]]、<span class="ui">选择</span> [[FIG:figures/SelectButton.png]] 与<span class="ui">构建</span> [[FIG:figures/BuildButton.png]]。</li>
<li><b>模型视图（Model View）</b>面板以分层方式显示该分子可用的数据。</li>
<li><b>历史（History）</b>面板位于左下角，列出最近可撤销的操作，可点击这些操作或使用<span class="menu">编辑 ▸ 撤销</span>菜单项执行撤销。</li>
</ul>
<p><b>模型视图（MV）</b>控制视图中显示哪些对象，并允许访问这些对象的配置选项。可见性由关联的复选框控制：取消勾选会使该项及其所有子项隐藏。若某项没有复选框（如化学键），则其可见性只能由层次结构中更高层级的项来控制。</p>
<p>许多对象的外观可通过在 MV 中<b>双击</b>该项来配置。例如，双击分子名称会打开"配置分子"对话框，允许更改分子结构的显示方式：</p>
<div class="figure">[[FIG:figures/MoleculeConfigurator.png]]
<div class="cap">图 1.2　配置分子对话框</div></div>
<p>注意，同一视图窗口中可同时查看多个分子，且每个分子的外观可分别配置。</p>
<div class="figure">[[FIG:figures/CHF3-balls.png]] [[FIG:figures/CHF3-wire.png]] [[FIG:figures/CHF3-space.png]] [[FIG:figures/CHF3-tubes.png]] [[FIG:figures/CHF3-moly.png]]
<div class="cap">图 1.3　分子结构的渲染风格：球棍、线框、空间填充、管状与塑料</div></div>
</section>
"""

# --- 2 Building Molecules ---
body += """
<section id="s2">
<h2 class="sec">2 构建分子</h2>

<h3 class="sub" id="s2-1">2.1 添加原子与片段</h3>
<p>默认情况下 IQmol 以构建模式打开，工具栏中<span class="ui">构建</span>按钮 [[FIG:figures/BuildButton.png]] 周围的红色边框即表示此状态。默认构建原子由<span class="ui">构建原子</span>按钮 [[FIG:figures/BuildAtomButton.png]] 指示，点击该按钮可更改构建元素——将弹出元素周期表供选择所需元素类型。</p>
<p>在空白的视图窗口中点击，将创建当前构建元素的一个原子。点击现有原子并拖动鼠标可添加新原子并与之成键。要创建互不相连的原子，需在点击视图窗口时按住 <span class="kbd">alt</span> 修饰键（注意：部分 Linux 窗口管理器将 <span class="kbd">alt</span> 用于其他用途，可在<span class="menu">系统设置 ▸ 键盘 ▸ 快捷键</span>中修改此行为）。</p>
<p>键级可通过在两次现有原子之间点击并拖动来提高：若两原子间原本无键则创建新键，否则提高键级。要降低键级，须先删除该键再新建。</p>
<div class="figure">[[FIG:figures/Cdouble.png]]
<div class="cap">图 2.1　提高键级</div></div>
<p>添加官能团：点击<span class="ui">构建片段</span>按钮 [[FIG:figures/BuildFragButton.png]]，确保选中<span class="ui">官能团</span>单选按钮，再从菜单中选择所需基团。基团的添加方式与原子相同（即点击并拖动）。空价由黄色键指示，显示基团将连接的位置。</p>
<div class="figure">[[FIG:figures/FunctionalGroup.png]]
<div class="cap">图 2.2　点击"添加片段"按钮时弹出的构建片段窗口</div></div>
<p>也可通过点击<span class="ui">构建片段</span>按钮 [[FIG:figures/BuildFragButton.png]]、确保选中<span class="ui">分子</span>单选按钮、再从菜单中选择所需分子，将整个分子添加到体系中。务必点击<span class="ui">选择</span>，否则构建选择不会更新。与其他构建模式不同，点击视图窗口任意位置即会添加所选分子（无需鼠标修饰键），便于快速添加同种多个分子（如用于溶剂化），但这会改变通常的鼠标行为。若不小心添加了过多分子，可使用<span class="menu">编辑 ▸ 撤销</span>菜单项。添加分子时若点击并按住，可在加入全局坐标系之前改变新添加分子的局部取向。</p>
<p>分子骨架绘制完成后，可点击<span class="ui">添加氢原子</span>按钮 [[FIG:figures/AddHydrogensButton.png]]，自动为所有未填满价键的位置添加氢原子。</p>

<h3 class="sub" id="s2-2">2.2 使用分子力学优化结构</h3>
<p>IQmol 的构建器是自由形式的，因此初始结构可能看起来有些歪斜。要改善几何结构，点击<span class="ui">最小化能量</span>按钮 [[FIG:figures/MinimizeEnergyButton.png]]，使用分子力学（MM）力场优化几何。默认力场为通用力场（UFF）<a href="#ref-UFF">[1]</a>，其优点是对几乎整个元素周期表都有定义。然而 UFF 对含氢键的体系表现不佳，此时建议使用<span class="menu">构建 ▸ 选择力场</span>菜单项更换力场。</p>
<div class="figure">[[FIG:figures/ForceFieldMenu.png]]
<div class="cap">图 2.3　更改分子力学力场</div></div>

<h3 class="sub" id="s2-3">2.3 对称化结构</h3>
<p>若你的分子具有对称性，MM 优化不太可能得到具有所需对称性的结构。此时，可用<span class="menu">构建 ▸ 对称化分子</span>菜单项将近似对称的结构对称化。若要寻找很高的对称性，可能需要通过<span class="menu">构建 ▸ 设置对称容差</span>菜单项放宽容差——放松容差可让程序移动核坐标的幅度更大，从而找到对称结构。</p>
<p>IQmol 使用由 Tullio Pilati 与 Alessandra Forni 编写的 Symmol 程序<a href="#ref-SymMol">[2]</a>的改进版本来对称化分子结构。</p>

<h3 class="sub" id="s2-4">2.4 指定几何参数</h3>
<p>可通过先选择相关原子、再使用<span class="menu">构建 ▸ 设置几何约束</span>菜单项，为几何参数设定具体数值。将弹出一个对话框，允许将该参数设为<b>固定</b>、<b>约束</b>或<b>扫描</b>。约束参数适用于后续的 MM 优化，若请求了优化作业，还会传入 Q-Chem 输入文件；扫描选项也会为扫描作业传入 Q-Chem。</p>
<div class="figure">[[FIG:figures/ConstraintDialog.png]]
<div class="cap">图 2.4　设置几何约束的对话框</div></div>
<p>约束类型取决于所选原子数：</p>
<ol>
<li>固定原子位置</li>
<li>原子间距离（或选择单键）</li>
<li>键角</li>
<li>扭转（二面）角</li>
</ol>
<p>活动约束在视图中可见，可通过点击 MV 中相邻的复选框停用。</p>

<h3 class="sub" id="s2-5">2.5 操作与选择分子</h3>
<p>IQmol 设计上最适合使用三键鼠标或触控板。若使用 Mac 触控板，建议前往<span class="menu">系统偏好设置 ▸ 触控板</span>启用辅助点击。</p>
<p>点击工具栏中的<span class="ui">操作</span>按钮 [[FIG:figures/ManipulateButton.png]] 激活<b>操作模式</b>，实现以下鼠标功能：</p>
<ul>
<li><b>左键拖动</b>：旋转分子视图。</li>
<li><b>中键拖动</b>：放大 / 缩小。</li>
<li><b>右键拖动</b>：平移分子视图。</li>
</ul>
<p>也可以独立于其余部分地操作分子的一部分：先做出选择，再按住 <span class="kbd">ctrl</span>（Mac 上为 <span class="kbd">command</span>）修饰键，鼠标移动将只影响所选原子：</p>
<ul>
<li><b>左键拖动</b>：绕所选原子的中心旋转。</li>
<li><b>右键拖动</b>：平移所选原子。</li>
</ul>
<p>若只选择了单根键，鼠标移动的效果为：</p>
<ul>
<li><b>左键拖动</b>：绕键轴旋转。</li>
<li><b>右键拖动</b>：改变键长。</li>
</ul>
<p>点击工具栏中的<span class="ui">选择</span>按钮 [[FIG:figures/SelectButton.png]] 激活<b>选择模式</b>，实现以下功能：</p>
<ul>
<li><b>左键</b>：将原子或键加入选择。</li>
<li><b>点击并拖动</b>：创建选择矩形，矩形内的所有原子与键均加入选择。</li>
<li><b>右键</b>：从选择中移除原子或键。</li>
</ul>
<p>也可通过<span class="menu">编辑</span>菜单下的选项实现全选、全不选与反选。</p>

<h3 class="sub" id="s2-6">2.6 添加额外构象</h3>
<p>为设置使用冻结字符串法（FSM）的作业，需要两个构象，分别对应字符串的初、末几何。构建好第一个几何后，可在 MV 中右键点击分子名称，弹出包含"复制几何"选项的上下文菜单。选择该菜单项后，MV 中会出现一个含两个（相同）几何的"几何"项。可通过在 MV 中选择第二个几何、并在视图中使用 <span class="kbd">ctrl</span>（Mac 上为 <span class="kbd">command</span>）修饰键操作所选原子来修改它。若在 QUI 中将"计算"选项选为"冻结字符串"（见下一节），则两个几何都会被包含进输入文件的 <span class="path">$molecule</span> 段，以 <span class="path">****</span> 分隔。</p>
<div class="figure">[[FIG:figures/MoleculeContext.png]]
<div class="cap">图 2.5　分子上下文菜单</div></div>
</section>
"""

# --- 3 Running Q-Chem ---
body += """
<section id="s3">
<h2 class="sec">3 运行 Q-Chem 计算</h2>

<h3 class="sub" id="s3-1">3.1 QUI（Q-Chem 用户界面）</h3>
<p>IQmol 内置了用于 Q-Chem 计算的输入文件生成器——<b>QUI</b>，可通过<span class="menu">计算 ▸ Q-Chem 设置</span>菜单访问。</p>
<div class="figure">[[FIG:figures/QUI.png]]
<div class="cap">图 3.1　Q-Chem 用户界面（QUI）对话框</div></div>
<p>QUI 对话框左侧包含设置计算的控件，以分层方式呈现：最常用选项位于面板顶部，其他相关选项随所选作业类型出现在下部。更高级的选项可通过"高级"选项卡访问。生成的输入文件会回显在 QUI 右侧的面板中。</p>
<p>点击<span class="ui">提交</span>按钮将在所选服务器上启动作业。作业完成后（对远程服务器）会提示复制结果，之后结果将自动载入 IQmol。当分子被计算结果更新后，MV 中分子名称旁会出现<span class="ui">收藏</span>图标 [[FIG:figures/Favourites.png]]。</p>

<h3 class="sub" id="s3-2">3.2 作业监视器</h3>
<p>可通过<span class="menu">计算 ▸ 作业监视器</span>菜单项监视已提交的作业。这会弹出作业监视器对话框，显示作业进度信息。在作业监视器中右键点击某一行会弹出上下文菜单，可终止或查询运行中的作业，以及打开已完成的作业。</p>
<div class="figure">[[FIG:figures/JobMonitor.png]]
<div class="cap">图 3.2　作业监视器对话框。右键点击所选作业会弹出含附加选项的上下文菜单</div></div>
<p>若作业状态为"错误"，将鼠标悬停在状态上会显示错误信息。或者，双击该作业会打开输出文件（若可用），可能提供作业失败原因的额外信息。双击已完成的作业会从服务器复制结果（若尚未复制）并重新载入主 IQmol 窗口。</p>

<h3 class="sub" id="s3-3">3.3 配置服务器</h3>
<p>默认情况下，IQmol 配置为将作业提交到位于加利福尼亚州 Pleasanton 的 Q-Chem 服务器。这是一个公开可用的服务器，供任何希望在购买 Q-Chem 软件之前运行测试计算的人使用。提交到该服务器的作业可访问 Q-Chem 中完整的电子结构方法套件，但时间限制为 10 分钟。</p>
<p>可配置额外的服务器以访问装有 Q-Chem 的其他计算机。这些计算机可以是本地服务器（即与运行 IQmol 的机器相同），也可以是通过 SSH 连接的远程服务器。要添加额外服务器，请进入<span class="menu">计算 ▸ 编辑服务器</span>菜单项并点击<span class="ui">加号</span>按钮 [[FIG:figures/PlusButton.png]]。</p>
<div class="figure">[[FIG:figures/ServerDialog.png]]
<div class="cap">图 3.3　服务器配置对话框</div></div>
<p>配置服务器所需的信息取决于其类型，但每种情况都有默认选项。以下列出最低应考虑的内容：</p>
<ul>
<li><b>本地</b>：将队列系统设为"Basic"，除非你确定机器上运行着排队软件。确保 <span class="path">QC</span> 与 <span class="path">QCSCRATCH</span> 变量在运行文件模板（点击"配置"按钮访问）中设为正确值。</li>
<li><b>SSH</b>：需要通过 SSH 连接目标机器，因此需提供目标机器的主机名与账户。将认证组合框设为"密码提示"，除非你已设置了替代的认证协议。根据目标主机的设置，运行文件模板可能需要一些编辑才能工作，但这会因机器而异。</li>
<li><b>HTTP</b>：默认选项应当适用。注意在 Windows 上应使用 HTTP（v2.8 中为默认），而在 Mac 与 Linux 上可使用 HTTPS（未来版本将作为默认）。</li>
</ul>
</section>
"""

# --- 4 Analyzing Results ---
body += """
<section id="s4">
<h2 class="sec">4 分析结果</h2>
<p>IQmol 可读取多种文件类型，并允许用户可视化其中的许多结果。单个文件可通过<span class="menu">文件 ▸ 打开</span>菜单项打开，或拖放到视图窗口。目录也可通过<span class="menu">文件 ▸ 打开目录</span>菜单项打开，或拖放到视图窗口。</p>
<p>打开目录可同时加载与某分子关联的多个文件，例如 Q-Chem 输出文件与格式化检查点文件。目录名决定分子的基名，IQmol 会加载该目录内所有基名匹配的文件。</p>
<div class="figure">[[FIG:figures/OpenDir.png]]
<div class="cap">图 4.1　示例：打开 Aniline 目录会将该目录下的 Aniline.ESP.cube、Aniline.FChk、Aniline.inp 与 Aniline.out 文件一并载入同一分子。notes.txt 文件因基名不同而会被忽略</div></div>

<h3 class="sub" id="s4-1">4.1 分子表面</h3>
<p>无需先执行量子化学计算即可生成若干分子表面，包括：范德华表面、前分子（pro-molecule）表面，以及离子密度叠加（SID）表面。SID 表面类似于前分子表面，但它根据原子的原子电荷对密度进行缩放，可能对带电体系给出更准确的密度表示。</p>
<p>要绘制这类赝密度表面，双击 MV 中与该分子关联的"表面"项。</p>

<h3 class="sub" id="s4-2">4.2 从检查点文件绘制分子轨道</h3>
<p>绘制分子轨道（MO）需要格式化检查点文件（扩展名为 <span class="path">.fchk</span>），当从 IQmol 运行 Q-Chem 计算时默认会生成该文件（GUI rem 变量应设为 2）。打开 fchk 文件后，MV 中"表面"项下会出现"正则轨道"项。双击该项会弹出"添加表面"对话框：</p>
<div class="figure">[[FIG:figures/MolecularOrbitalsConfigurator.png]]
<div class="cap">图 4.2　"添加表面"对话框可绘制 MO 与（自旋）密度</div></div>
<p>"添加表面"对话框允许计算 MO、总密度与自旋密度。可排队多个表面同时计算，这样更高效，因为壳层数据只需计算一次。表面的质量、颜色与不透明度都可在对话框中设置，且这些设置的更改会作为默认值保存到偏好中，供后续生成的任何表面使用。</p>
<p>注意：质量刻度上的每一格对应的网格点数约为前一格的 4 倍，因此计算时间也约为其 4 倍。还需注意，密度需要计算壳层对数值，比 MO（仅需壳层值）昂贵得多。在大多数情况下，双击"表面"项得到的赝密度（如前分子密度）能提供几乎相同的密度表面，但成本低得多。</p>
<div class="figure">[[FIG:figures/Orbital.png]]
<div class="cap">图 4.3　苯胺的一个分子轨道示例</div></div>
<p>计算完成后，各表面作为子项出现在 MV 中，双击 MV 中的该项可进一步配置。</p>
<p>"添加表面"对话框右侧面板还包含一个交互式能级图。可用鼠标滚轮（或等效操作）对垂直刻度进行缩放，左键拖动可平移刻度。左键单击可选择单个轨道，所选轨道的能量将显示在图的下方（如图 4.2 所示）。</p>

<h3 class="sub" id="s4-3">4.3 其他轨道与密度</h3>
<p>除基于正则轨道的轨道与密度外，若已执行相应计算，也可可视化其他轨道与密度，包括：定域轨道、自然跃迁轨道、自然键轨道，以及附着/脱离密度。</p>
<div class="figure">[[FIG:figures/LocalizedBonds.png]]
<div class="cap">图 4.4　乙烯中定域的 σ 键轨道</div></div>
<p>戴森（Dyson）轨道也可显示，既可来自检查点文件（需 Q-Chem ≥ v5.1），也可使用旧版 Q-Chem 从输出文件得到。在后一种情况下，应将 <span class="path">PRINT_GENERAL_BASIS</span> 选项设为 true，以便 IQmol 生成基函数数据。</p>
<pre class="code">$rem
   METHOD               = EOM_CCSD
   BASIS                = cc-pVTZ
   EOM_EA_BETA          = [1,1,1,0]
   CC_DO_DYSON          = TRUE
   GUI                  = 2
   PRINT_GENERAL_BASIS  = TRUE   ! 仅 Q-Chem &lt; v5.1 时需要
$end</pre>
<p>若可用，戴森轨道会出现在模型视图的"表面"项下，行为类似于正则轨道。</p>

<h3 class="sub" id="s4-4">4.4 导出立方体文件数据</h3>
<p>每个表面都需要在三维网格上生成数据，这些数据在内部存储，以便对同一表面的后续计算（例如使用不同等值）快得多。要查看存储了哪些网格数据，请在 MV 中右键点击 MO 表面项以弹出上下文菜单，选择"显示网格信息"菜单项会弹出网格信息对话框：</p>
<div class="figure">[[FIG:figures/GridInfo.png]]
<div class="cap">图 4.5　网格信息对话框显示正在存储的数据，并提供以立方体文件格式导出数据的选项</div></div>
<p>从此对话框可导出包含网格数据的立方体文件。右键点击所需网格会弹出含"导出立方体文件"选项的上下文菜单。"切换相位"项会交换数据的正负号，在比较相位（任意）不同的 MO 时可能有用。立方体文件可保存供以后绘图，避免重新计算数据，或读入其他绘图软件包。下节将介绍这一点。</p>

<h3 class="sub" id="s4-5">4.5 可视化立方体文件数据</h3>
<p>立方体文件包含体数据，如电子密度、分子轨道或静电势（ESP）。由于数据已预先计算，用它们生成表面非常快。打开立方体文件后，MV 中会出现"立方体数据"项，双击该项会弹出"添加表面"对话框，可请求一个等值面（图 4.6）。<b>有符号</b>复选框会生成对应于 ± 指定等值的两个等值面，对 MO 与自旋密度这类数据应勾选此项。</p>
<div class="figure">[[FIG:figures/AddSurface.png]]
<div class="cap">图 4.6　用于立方体数据文件的"添加表面"对话框</div></div>
<p>立方体文件数据也可用于为表面着色。这需要两个立方体文件（一个含表面数据，另一个含用于着色的属性），或一个立方体文件加一个检查点文件。两种情况下，都需用上文介绍的<span class="menu">文件 ▸ 打开目录</span>菜单项将两个文件载入同一分子。</p>
<p>创建表面后，双击表面项会弹出"配置表面"对话框：</p>
<div class="figure">[[FIG:figures/SurfaceConfigurator.png]]
<div class="cap">图 4.7　配置表面对话框，显示可将立方体数据作为属性选项</div></div>
<p>"属性"组合框会将立方体数据作为选项之一，选择它会使表面按立方体文件中的数据着色。点击渐变框内部可改变渐变颜色。</p>
<div class="figure">[[FIG:figures/ESP.png]]
<div class="cap">图 4.8　按静电势着色的苯胺电子密度图</div></div>

<h3 class="sub" id="s4-6">4.6 轨道动画</h3>
<p>可创建轨道动画，例如观看反应过程中前沿轨道的演化，或自洽场（SCF）计算中轨道的弛豫。关键帧应保存为单个目录下的立方体文件数据。立方体文件的基名需与目录名匹配，例如：</p>
<pre class="code">relaxation/relaxation.Frame.1.cube
relaxation/relaxation.Frame.2.cube</pre>
<p>按第 4 节所述打开该目录，右键点击 MV 中出现的第一个立方体文件项，即可访问表面动画器对话框：</p>
<div class="figure">[[FIG:figures/SurfaceAnimationMenu.png]]
<div class="cap">图 4.9　表面动画器菜单</div></div>
<p>该对话框如图 4.10 所示，可用于调整关键帧顺序与动画设置，包括插值帧数（值越大结果越平滑，但耗时更长）。按<span class="ui">计算</span>生成每一帧，单帧可在 MV 中访问。使用播放选项运行动画，并按需用<span class="ui">录制</span>按钮 [[FIG:figures/RecordButton.png]] 录制。</p>
<div class="figure">[[FIG:figures/AnimationDialog.png]]
<div class="cap">图 4.10　表面动画对话框</div></div>

<h3 class="sub" id="s4-7">4.7 势能面</h3>
<p>若干计算类型提供关于势能面（PES）的信息，包括几何优化、PES 扫描、反应路径与过渡态搜索。打开包含这类作业类型的 Q-Chem 输出文件时，MV 中会出现"几何"项，双击该项可弹出"几何"对话框。</p>
<div class="figure">[[FIG:figures/PesScan.png]]
<div class="cap">图 4.11　"几何"对话框，显示所选几何</div></div>
<p>该路径可在视图中用播放按钮动画化，也可从表格或通过选择能量图上的点来选定单个帧。视图窗口会自动更新为相应结构。与 MO 能级图一样，能量图也可缩放与滚动。</p>
<p>路径也可从 XYZ 文件读入，格式就是常规 XYZ 文件的拼接：</p>
<pre class="code">5
-291.77177
Si  0.71979   -0.08082   -0.76577
H   0.73262   -1.27801    0.22990
H   1.10451    0.93673    0.34825
H  -1.32980    0.23894   -0.28240
H  -1.22713    0.18317    0.47002
5
-291.76961
Si  0.67218   -0.07483   -0.72935
H   0.73053   -1.29428    0.22634
H   1.10815    0.95270    0.34714
H  -1.29502    0.23567   -0.33016
H  -1.19409    0.17584    0.49156
....</pre>
<p>首行给出原子数，第二行（注释行）必须包含相应的能量，之后各行列出体系中每个原子的 xyz 坐标。此模式按你拥有的帧数重复。</p>

<h3 class="sub" id="s4-8">4.8 振动频率</h3>
<p>振动频率可从 Q-Chem 输出文件读入，作为"频率"项出现在 MV 中。选择 MV 中关联的频率项，可可视化其简正模式向量。</p>
<div class="figure">[[FIG:figures/VibMode.png]]
<div class="cap">图 4.12　乙酸中指示一个简正模式的箭头</div></div>
<p>双击 MV 中的某个频率会使分子按所选模式振动。双击 MV 中的"频率"项会弹出"振动频率"对话框：</p>
<div class="figure">[[FIG:figures/Frequencies.png]]
<div class="cap">图 4.13　振动频率对话框</div></div>
<p>该对话框包含一个脉冲谱，显示各频率的位置与相对强度。可在谱上点击空心圆选择单个模式，这同时会更新视图窗口中的所选模式。脉冲可用高斯函数或洛伦兹函数展宽，得到更真实的谱形；右键点击谱图可弹出上下文菜单导出图像。</p>
<p>谱的水平刻度可缩放（用鼠标滚轮）与平移（左键拖动），以查看更细的细节。</p>

<h4 class="subsub" id="s4-8-1">4.8.1 同位素取代</h4>
<p>IQmol 可轻松地为 Q-Chem 振动频率计算设置同位素取代循环。先在视图中选择要取代的原子，再选择<span class="menu">构建 ▸ 设置同位素</span>菜单项。将弹出对话框，允许更改所选原子的同位素，以及更改用于计算热化学数据的压力与温度。</p>
<div class="figure">[[FIG:figures/IsotopeDialog.png]]
<div class="cap">图 4.14　同位素取代对话框，允许为所选原子指定非默认质量。注意每种元素类型只允许一个非默认质量</div></div>
<p>选定质量后点击确定，MV 中会出现包含取代信息的"同位素"项。双击 MV 中相应的"取代"项可编辑或检查。通过选择不同的原子和/或不同的质量，可设置不同的取代，它们将在 Q-Chem 频率计算中循环执行。每个取代循环只需在 Hessian 对角化前重新加权，因此一旦计算出 Hessian，就能非常快地获得多个循环。</p>

<h3 class="sub" id="s4-9">4.9 NMR 谱</h3>
<p>IQmol 可可视化 NMR 屏蔽常数与化学位移。必须先运行一个 Q-Chem 计算（<span class="path">JOB_TYPE = NMR</span>）并将输出文件载入 IQmol。屏蔽常数可作为视图中的原子标签显示，方法是选择<span class="menu">显示 ▸ 原子标签 ▸ NMR</span>。</p>
<div class="figure">[[FIG:figures/NmrDisplay.png]]
<div class="cap">图 4.15　显示 NMR 屏蔽常数的丙醇</div></div>
<p>MV 中会出现一个 NMR 项，双击该项会弹出 NMR 谱对话框。</p>
<div class="figure">[[FIG:figures/NmrConfigurator.png]]
<div class="cap">图 4.16　NMR 谱对话框</div></div>
<p>可显示多种谱（¹H、¹³C 等），若对给定理论水平有参考物质（如 TMS），也可显示化学位移。选择表中的行还会高亮视图中相应的原子，便于识别。若绘制了脉冲谱，也可通过选择脉冲来识别产生该信号的原子。</p>
<p>与振动频率谱一样，NMR 谱可通过右键点击图像弹出上下文菜单导出。</p>
</section>
"""

# --- 5 Appearance ---
body += """
<section id="s5">
<h2 class="sec">5 外观</h2>

<h3 class="sub" id="s5-1">5.1 视图相机</h3>
<p>查看分子时，原子与表面的坐标固定在世界参考系中。用鼠标操作分子（见第 2.5 节）时，实际改变的是相机的位置与朝向。若需要对相机进行更精确的控制（例如重现某张特定图像），可通过<span class="menu">显示 ▸ 相机</span>菜单项配置相机。默认相机使用透视投影以获得更好的景深感知，但也可按需选择正交投影。</p>
<div class="figure">[[FIG:figures/CameraDialog.png]]
<div class="cap">图 5.1　配置相机对话框可对视图相机的位置与朝向进行精确控制</div></div>

<h3 class="sub" id="s5-2">5.2 裁剪平面</h3>
<p>提供了一个全局裁剪平面，可通过在 MV 中启用"全局"下的"裁剪平面"项来查看。裁剪平面有助于显示表面信息而不遮挡底层分子结构。选中时，裁剪平面可使用第 2.5 节所述的操作选择模式任意平移与旋转。或者，双击 MV 中的"裁剪平面"项打开配置对话框，可精确设定其朝向。</p>
<div class="figure">[[FIG:figures/ClippingPlane.png]]
<div class="cap">图 5.2　裁剪后的密度表面，使底层分子结构更易看清</div></div>
<p>单个表面也可被裁剪：在表面配置器对话框中勾选"裁剪"复选框（见图 4.7）。表面一旦被裁剪，即使取消 MV 中"裁剪平面"项的复选框将其隐藏，裁剪平面仍保持活动。</p>

<h3 class="sub" id="s5-3">5.3 着色器</h3>
<p>IQmol 使用 GLSL 着色器增强视图的外观。可通过<span class="menu">显示 ▸ 外观</span>菜单项启用着色器并选择"着色器"面板。</p>
<div class="figure">[[FIG:figures/ShaderDialog.png]]
<div class="cap">图 5.3　配置着色器选项</div></div>
<p>各项着色器选项的更改会立即生效，并可点击<span class="ui">保存为默认</span>保存为默认。某些着色器关联有多个灯光，可将其打开或关闭以获得不同的光照效果。</p>

<h3 class="sub" id="s5-4">5.4 导出 POV-Ray 文件</h3>
<p>IQmol 可生成供外部 POV-Ray 软件包使用的场景文件（<span class="path">.pov</span>）。POV-Ray 使用光线追踪算法生成极高质量与高分辨率的图像。POV-Ray 是开源的，但存在一些带有预编译二进制文件的官方与非官方软件包，测试时使用的是 Mac 版 MegaPOV。二进制文件可从以下站点下载：</p>
<ul>
<li>Mac：<span class="path">http://megapov.inetart.net/povrayunofficial_mac</span></li>
<li>Windows：<span class="path">http://www.povray.org/download</span></li>
</ul>
<p>要导出场景文件，使用<span class="menu">编辑 ▸ 生成 POV-Ray 输入</span>菜单项。场景文件是包含 POV-Ray 程序指令的纯文本，用户可在处理前编辑以进行微调。IQmol 可对分子应用若干效果（如表面纹理），这些可通过外观对话框（<span class="menu">显示 ▸ 外观</span>菜单项）配置。</p>
<div class="figure">[[FIG:figures/POVRayDialog.png]]
<div class="cap">图 5.4　外观对话框，显示 POV-Ray 场景文件的选项</div></div>
<p>注意，IQmol 会尽量生成与视图窗口中所显示内容尽可能匹配的场景文件。但光照、颜色与相机角度可能存在微小差异，可能需要一些试错才能获得满意的图像。特别是 Gamma 值可能需要试验，并且根据为场景选择的是亮背景还是暗背景，可能需要更改环境光与漫反射光（通过着色器选项）。</p>
</section>
"""

# --- 6 Sample Images ---
body += """
<section id="s6">
<h2 class="sec">6 样例图像</h2>
<p>以下是一些可用 IQmol 的着色器与渲染选项生成的图像示例。其中大多数只是屏幕截图，但中间一行的第 3、4、5 块是通过对 IQmol 生成的场景文件运行 POV-Ray 得到的。</p>
<div class="figure">
[[FIG:figures/gallery/g13_sm.png]] [[FIG:figures/gallery/g14_sm.png]] [[FIG:figures/gallery/g15_sm.png]] [[FIG:figures/gallery/g16_sm.png]] [[FIG:figures/gallery/g21_sm.png]]<br/>
[[FIG:figures/gallery/g10_sm.png]] [[FIG:figures/gallery/g11_sm.png]] [[FIG:figures/gallery/g12_sm.png]] [[FIG:figures/gallery/g17_sm.png]] [[FIG:figures/gallery/g25_sm.png]]<br/>
[[FIG:figures/gallery/g1_sm.png]] [[FIG:figures/gallery/g4_sm.png]] [[FIG:figures/gallery/g23_sm.png]] [[FIG:figures/gallery/g26_sm.png]] [[FIG:figures/gallery/g24_sm.png]]<br/>
[[FIG:figures/gallery/g7_sm.png]] [[FIG:figures/gallery/g5_sm.png]] [[FIG:figures/gallery/g3_sm.png]] [[FIG:figures/gallery/g20_sm.png]] [[FIG:figures/gallery/g6_sm.png]]<br/>
[[FIG:figures/gallery/g2_sm.png]] [[FIG:figures/gallery/g9_sm.png]] [[FIG:figures/gallery/g8_sm.png]] [[FIG:figures/gallery/g18_sm.png]] [[FIG:figures/gallery/g19_sm.png]]
<div class="cap">图 6.1　IQmol 渲染样例图集</div></div>

<div class="note" id="ref-UFF">[1] A. R. Rappé, C. J. Casewit, K. S. Colwell, W. A. Goddard III, W. M. Skiff, UFF: A full periodic table force field for molecular mechanics and molecular dynamics simulations, <i>J. Am. Chem. Soc.</i> <b>114</b>, 10024 (1992).</div>
<div class="note" id="ref-SymMol">[2] T. Pilati, A. Forni, Symmol: a program for solving the subgroup of the full molecular symmetry point group, <i>J. Appl. Cryst.</i> <b>33</b>, 417 (2000).</div>
</section>
"""

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>IQmol 使用简介（中文版用户手册 v3.2）</title>
<style>{CSS}</style>
</head>
<body>
{cover}
{toc}
<main>
{body}
</main>
<footer>
本中文手册译自官方英文用户指南 <i>IQmolUserGuide.tex</i>（v3.2, 2025, Andrew Gilbert）。<br/>
术语参照全国科学技术名词审定委员会规范与项目汉化术语表。版权归原作者所有。
</footer>
</body>
</html>
"""

html = render(html)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print("生成完成:", OUT, "大小:", len(html), "字节")
# 校验所有占位符已替换
left = re.findall(r'\[\[FIG:[^\]]+\]\]', html)
print("未替换占位符数:", len(left))
