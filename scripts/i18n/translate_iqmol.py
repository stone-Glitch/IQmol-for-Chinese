#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IQmol 全量 UI 字符串中译（V2）：已知译文 > 短语 > 单词组合 > 排除/保留
特殊处理：全大写缩写保留英文、HTML 富文本提取可见文本翻译、元素/同位素/溶剂名。
未命中且非技术串 -> unfinished 供人工复核。"""
import xml.etree.ElementTree as ET
import json, re

TS = "/workspace/IQmol3/translations/zh_CN_full.ts"
OUT = "/workspace/IQmol3/translations/zh_CN_new.ts"
KNOWN = json.load(open("/workspace/scripts/known_translations.json", encoding="utf-8"))

ELEMENTS = set("""H He Li Be B C N O F Ne Na Mg Al Si P E Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni
Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd
Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U
Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og""".split())
ELEMENT_CN = {
 'H':'氢','He':'氦','Li':'锂','Be':'铍','B':'硼','C':'碳','N':'氮','O':'氧','F':'氟','Ne':'氖',
 'Na':'钠','Mg':'镁','Al':'铝','Si':'硅','P':'磷','S':'硫','Cl':'氯','Ar':'氩','K':'钾','Ca':'钙',
 'Sc':'钪','Ti':'钛','V':'钒','Cr':'铬','Mn':'锰','Fe':'铁','Co':'钴','Ni':'镍','Cu':'铜','Zn':'锌',
 'Ga':'镓','Ge':'锗','As':'砷','Se':'硒','Br':'溴','Kr':'氪','Rb':'铷','Sr':'锶','Y':'钇','Zr':'锆',
 'Nb':'铌','Mo':'钼','Tc':'锝','Ru':'钌','Rh':'铑','Pd':'钯','Ag':'银','Cd':'镉','In':'铟','Sn':'锡',
 'Sb':'锑','Te':'碲','I':'碘','Xe':'氙','Cs':'铯','Ba':'钡','La':'镧','Ce':'铈','Pr':'镨','Nd':'钕',
 'Pm':'钷','Sm':'钐','Eu':'铕','Gd':'钆','Tb':'铽','Dy':'镝','Ho':'钬','Er':'铒','Tm':'铥','Yb':'镱',
 'Lu':'镥','Hf':'铪','Ta':'钽','W':'钨','Re':'铼','Os':'锇','Ir':'铱','Pt':'铂','Au':'金','Hg':'汞',
 'Tl':'铊','Pb':'铅','Bi':'铋','Po':'钋','At':'砹','Rn':'氡','Fr':'钫','Ra':'镭','Ac':'锕','Th':'钍',
 'Pa':'镤','U':'铀','Np':'镎','Pu':'钚','Am':'镅','Cm':'锔','Bk':'锫','Cf':'锎','Es':'锿','Fm':'镄',
 'Md':'钔','No':'锘','Lr':'铹','Rf':'𬬻','Db':'𬭛','Sg':'𬭛','Bh':'𬭚','Hs':'𬭛','Mt':'鿏','Ds':'𬭚',
 'Rg':'𬬭','Cn':'鿔','Nh':'鿭','Fl':'𫓧','Mc':'镆','Lv':'𬬹','Ts':'鿬','Og':'鿫'}

TECH_RE = re.compile(
    r'^(%|A|K|Mb|a\.u\.|atm|fps|pt|s|Å|Å|AMBERHOME|AO|AO2MO|API|ARI|AWS|BMP|GIF|PNG|JPG|'
    r'PDF|CSV|XYZ|MOL|PDB|CML|QML|SVG|TIFF|TGA|HDF5|SSH|SFTP|HTTP|HTTPS|PBS|SGE|SLURM|URL|'
    r'ID|UUID|TCP|IP|GPU|CPU|RAM|GB|TB|MB|KB|Hz|GHz|MHz|nm|pm|eV|kJ|kcal|mol|deg|rad|Da|'
    r'QHD|UHD|4K|2K|3D|2D|1D|WFN|MOLDEN|SDfile|SDFile|MDL|GEN_SCFMAN|EditConf|FFmpeg|'
    r'GroParser|OpenBabel|Q-Chem|Gromacs|Amber|OpenSSH)$', re.I)
RES_RE = re.compile(r'^\d{3,4}p(\s*\(.*\))?$')
VER_RE = re.compile(r'^[\d.]+$')
SYM_RE = re.compile(r'^[<>&]\w+;|^\(\w[\w\s:]*\)|^\*|^[+\-]$|^\.\.\.$|^\{\{')
FORMULA_RE = re.compile(r'^[A-Z][a-z]?\d*([A-Z][a-z]?\d*)*$')
OBJS = {'Form','centralWidget','verticalLayout','horizontalLayout','gridLayout','label',
        'pushButton','widget','scrollArea','frame','tabWidget','tableWidget','horizontalSpacer',
        'verticalSpacer','line','page','spinBox','comboBox','checkBox','groupBox','toolButton',
        'listWidget','treeWidget','textEdit','plainTextEdit','lineEdit','radioButton','dialogButtonBox'}

PHRASE = {
    # 标准 UI
    "About IQmol":"关于 IQmol","About":"关于","Apply":"应用","Abort":"中止","Back":"返回",
    "Basic":"基础","Background Color":"背景颜色","Background":"背景","Bigger text":"放大文字",
    "Black":"黑色","Blend":"混合","Border":"边框","Bounce":"弹跳","Browse":"浏览","Cancel":"取消",
    "OK":"确定","Close":"关闭","Configure":"配置","Config":"配置","Connect":"连接","Copy":"复制",
    "Cut":"剪切","Delete":"删除","Discard":"放弃","Done":"完成","Edit":"编辑","Exit":"退出",
    "Export":"导出","File":"文件","Finish":"完成","Help":"帮助","Hide":"隐藏","Import":"导入",
    "Insert":"插入","Load":"加载","New":"新建","Next":"下一步","No":"否","Open":"打开","Paste":"粘贴",
    "Preferences":"首选项","Previous":"上一步","Print":"打印","Quit":"退出","Redo":"重做",
    "Remove":"移除","Reset":"重置","Save As":"另存为","Save":"保存","Select All":"全选","Select":"选择",
    "Settings":"设置","Show":"显示","Stop":"停止","Submit":"提交","Undo":"撤销","Update":"更新",
    "Use":"使用","Yes":"是","Add":"添加","Clear":"清除","Refresh":"刷新","Default":"默认",
    "Enable":"启用","Disable":"禁用","None":"无","All":"全部","Automatic":"自动","Manual":"手动",
    "Custom":"自定义","Advanced":"高级","General":"常规",
    "Welcome to IQmol":"欢迎使用 IQmol","Save Changes?":"保存更改？","Full Screen":"全屏",
    "Reset View":"重置视图","Show Axes":"显示坐标轴","History:":"历史记录：","Loading":"正在加载",
    "Clear List":"清空列表","Use <esc> to exit full screen mode":"按 Esc 退出全屏模式",
    "Wonky molecule detected":"检测到异常分子","Do you want to proceed?":"是否继续？","(none)":"（无）",
    # 原子/结构
    "Atom Label":"原子标签","Atom Labels":"原子标签","Atom Number:":"原子序号：","Atom Radius":"原子半径",
    "Atom":"原子","Atoms":"原子","Atom 1":"原子 1","Atom 2":"原子 2","Atom 3":"原子 3","Atom 4":"原子 4",
    "Atom A":"原子 A","Atom B":"原子 B","Atom C":"原子 C","Atom D":"原子 D","Atom Indices":"原子索引",
    "Atomic Units":"原子单位","Element":"元素","Index":"序号","Mass":"质量","Partial Charge":"部分电荷",
    "Spin Densities":"自旋密度","Charge":"电荷","Bond Radius":"键半径","Bond":"键","Bonds":"键",
    "Bend":"弯曲","Angle Bisector":"角平分线","Stretch":"伸缩","Torsion":"扭转","Balls and Sticks":"球棍模型",
    "Reperceive Bonds":"重新识别键","Fill Valencies With Hydrogens":"用氢原子填充化合价",
    "Translate To Center":"平移到中心","Symmetrize Molecule":"分子对称化","Set Symmetry Tolerance":"设置对称容差",
    "Auto-detect Symmetry":"自动检测对称性","Reindex Atoms":"原子重新编号","Freeze Selected Atoms":"冻结所选原子",
    "Minimize Structure":"结构最小化","Select Force Field":"选择力场",
    # 计算/化学
    "Job Monitor":"任务监视器","Edit Servers":"编辑服务器","Servers":"服务器","Server":"服务器",
    "Queue":"队列","Submit Job":"提交任务","Job":"任务","Basis":"基组","Basis Set":"基组",
    "Basis Projection":"基组投影","Analytic Derivative Order":"解析导数阶","Analyze Amplitudes":"分析振幅",
    "Analyze Relaxed Density":"分析松弛密度","Algorithm":"算法","Ambient Occlusion":"环境光遮蔽",
    "Amplitude":"振幅","Antialias":"抗锯齿","Antialias Edges":"抗锯齿边缘","Appearance":"外观",
    "Array":"数组","Auto Rotation":"自动旋转","Authentication":"身份验证","Account name on the server":"服务器账户名",
    "Address:":"地址：","Address":"地址","API Gateway ID":"API 网关 ID","AO2MO Disk":"原子轨道到分子轨道变换磁盘",
    "AWS Config":"AWS 配置","Allow Molecular Re-orientation":"允许分子重新定向","Alpha":"Alpha",
    "Atoms within distance from current selection:":"距当前选区一定距离内的原子：","Animations:":"动画：",
    "Axes":"坐标轴","Camera":"相机","Surface":"表面","Surfaces":"表面","Molecular Surfaces":"分子表面",
    "Molecule":"分子","Molecules":"分子","Viewer":"查看器","Layer":"图层","Grid":"网格","Conformer":"构象",
    "Conformers":"构象","Isotope":"同位素","Isotopes":"同位素","Symmetry":"对称性","Geometry":"几何",
    "Orbital":"轨道","Orbitals":"轨道","Dipole":"偶极矩","Dipole Moment":"偶极矩","Excited States":"激发态",
    "Ground State":"基态","Vibrational":"振动","Vibration":"振动","Electronic":"电子","Frequencies":"频率",
    "Frequency":"频率","Gradient":"梯度","Energy":"能量","Density":"密度","Wavefunction":"波函数",
    "Eigenvector":"本征向量","Eigenvalue":"本征值","Hessian":"海森矩阵","NMR":"核磁共振","Spin":"自旋",
    "Mulliken":"Mulliken","Mulliken Decompositions":"Mulliken 分解","Cube Data":"立方体数据","Octree":"八叉树",
    "Clipping Plane":"裁剪平面","Constraint":"约束","Constraints":"约束","Geometric Constraint":"几何约束",
    "Scalar Constraint":"标量约束","Vector Constraint":"矢量约束","Info":"信息","File Configurator":"文件配置",
    "Protein Chain":"蛋白质链","Geminal Orbitals":"双生轨道","Vibronic":"电子振动","Excited":"激发",
    "Surface Animator":"表面动画器","Generate Conformers":"生成构象",
    # 面板 Configurator
    "Surface Configurator":"表面配置","Molecular Surfaces Configurator":"分子表面配置",
    "Symmetry Configurator":"对称性配置","NMR Configurator":"核磁共振配置","Orbitals Configurator":"轨道配置",
    "Frequencies Configurator":"频率配置","Info Configurator":"信息配置","Isotopes Configurator":"同位素配置",
    "Dipole Configurator":"偶极矩配置","Cube Data Configurator":"立方体数据配置",
    "Excited States Configurator":"激发态配置","Geminal Orbitals Configurator":"双生轨道配置",
    "Vibronic Configurator":"电子振动配置","Clipping Plane Configurator":"裁剪平面配置",
    "Octree Configurator":"八叉树配置","Geometry List Configurator":"几何列表配置",
    "Efp Fragment List":"有效片段势碎片列表","Protein Chain Configurator":"蛋白质链配置",
    "Axes Configurator":"坐标轴配置","Background Configurator":"背景配置","Axes Mesh Configurator":"坐标轴网格配置",
    # Qui
    "Input Dialog":"输入对话框","Option Database":"选项数据库","Option Editors":"选项编辑器",
    "Geometry Constraint":"几何约束","LJ Parameters":"Lennard-Jones 参数","Molecule Section":"分子段",
    "Rem Section":"纠错段","Read Input":"读取输入","Q-Chem Setup":"Q-Chem 设置","Q-Chem":"Q-Chem",
    "Add section to input file":"向输入文件添加段","Add Connectivity":"添加连接","Add Hydrogens":"添加氢原子",
    "Add To Queue":"加入队列","Calculate":"计算","Category":"类别","Center":"中心","Colors":"颜色",
    "Colors:":"颜色：","Colors: ":"颜色：","Commands":"命令","Compress":"压缩","Convergence":"收敛",
    "Convergence:":"收敛：","Coordinates":"坐标","Copy Results From Server":"从服务器复制结果",
    "Documentation":"文档","Dots":"点","Effects":"效果","Field of View":"视场","Fill":"填充","Final":"最终",
    "Font":"字体","Force Field":"力场","Build Mode (Alt)":"构建模式(Alt)","Boundary":"边界",
    "Bounding Box":"包围盒","Cartesian":"笛卡尔","Center Gradient":"中心梯度","Center Molecule":"分子居中",
    "Changes to the log file location require IQmol to be restarted":"日志文件位置更改后需重启 IQmol",
    "Charge Convergence":"电荷收敛","Check box":"复选框","Chem. Shift":"化学位移","Chemical formula:":"化学式：",
    "Cholesky Tolerance":"Cholesky 容差","Chroma":"色度","Circular Dichroism":"圆二色性","Closeness":"贴近度",
    "Co-planar":"共面","Cognito App Client ID":"Cognito 应用客户端 ID","Cognito User Pool ID":"Cognito 用户池 ID",
    "Combo box":"组合框","Complex Mix":"复合混合","Complex SCF":"复合 SCF","Configure Clipping Plane":"配置裁剪平面",
    "Configure EFP Fragments":"配置 EFP 碎片","Configure Mesh":"配置网格","Configure SSH":"配置 SSH",
    "Constrain":"约束","Connect To Atoms":"连接到原子","Contact your Q-Cloud administrator for the following settings:":"请联系您的 Q-Cloud 管理员获取以下设置：",
    "Continuous":"连续","Controls the speed of animation":"控制动画速度","Convergence":"收敛",
    "Crop Bounding Box":"裁剪包围盒","Cube File Frames":"立方体文件帧","Cubic":"立方体",
    "Cutoff Threshold:":"截断阈值：","Data Size (kB)":"数据大小(kB)","Davidson Iterations":"Davidson 迭代",
    "Davidson Options":"Davidson 选项","Debug":"调试","Decompositions":"分解","Default Force Field:":"默认力场：",
    "Denominator Thresh":"分母阈值","Deuterate":"氘代","Dielectric":"介电常数","Dihedral":"二面角",
    "Dipole Options":"偶极矩选项","Dipole moment:":"偶极矩：","Dipole:   ":"偶极矩：","Direct RI":"直接 RI",
    "Direct SCF":"直接 SCF","Direction":"方向","Disable Controls":"禁用控件","Disable Transparency":"禁用透明",
    "Dispersion Correction":"色散校正","Displacement":"位移","Distance between atom 1 and 2: ":"原子 1 与 2 之间的距离：",
    "Do not use ~ or environment variables":"请勿使用 ~ 或环境变量","Double spin box":"双精度微调框",
    "Doubles Guess Vectors":"双精度猜测向量","Dual Basis Energy":"双基组能量","Dummy Atom:":"虚原子：",
    "EFP Calculation":"EFP 计算","EFP Only Calculation (No QM)":"仅 EFP 计算(无 QM)","EFP Options":"EFP 选项",
    "EPAO Weights":"EPAO 权重","Edit Bounding Box":"编辑包围盒","Edit variable parameters:":"编辑可变参数：",
    "EditConf":"EditConf","Excited State Moments":"激发态矩","Fatal":"致命","Fast XC":"快速 XC",
    "FFmpeg Path":"FFmpeg 路径","Final / (cm⁻¹)":"最终 /(cm⁻¹)","Final Vibrational Analysis":"最终振动分析",
    "Finite Difference Stepsize":"有限差分步长","First Order":"一阶","First electronic state":"第一电子态",
    "Fix":"修复","Flourine (19F)":"氟(19F)","Fock Extrapolation Order":"福克外推阶","Follow Mode":"跟随模式",
    "3-Body interactions":"三体相互作用","1st DM":"一阶密度矩阵","2 Electron Transition Properties":"双电子跃迁性质",
    "A signed surface will disply both the \npositive and negative isosurfaces.  \nUncheck if only one surface is desired.":"带符号表面会同时显示正负等值面。若只需一个表面，请取消勾选。",
    "This is the directory on the server where calculations will be run.  \n\nUse PBS or SGE if there is a queue system on the server.  \nYou will be prompted for additional resource limits when \nsubmitting a job.\n\nUse Web for HTTP/HTTPS servers":"这是服务器上运行计算的目录。\n\n若服务器使用队列系统，请使用 PBS 或 SGE。\n提交任务时会提示您设置额外的资源限制。\n\n对 HTTP/HTTPS 服务器请使用 Web。",
    "Higher values will find more symmetric structures, but may lead to undesired changes in the geometry.":"较大的值会发现更多对称结构，但可能导致几何结构发生不期望的改变。",
    "This panel is never displayed, it \njust forms a container for the \nvarious EOM state specification \nwidgets.":"此面板从不显示，它只是\ntarious EOM 态定义控件的容器。",
    # 溶剂
    "Acetone":"丙酮","Acetonitrile":"乙腈","Ammonia":"氨","Benzene":"苯","Water":"水","Methanol":"甲醇",
    "Ethanol":"乙醇","Chloroform":"氯仿","Dichloromethane":"二氯甲烷","Toluene":"甲苯","Hexane":"己烷",
    "Carbon Tetracholoride":"四氯化碳","Carbon Tetrachloride":"四氯化碳",
    # 其它常见
    "Periodic Table":"元素周期表","Fragment Table":"片段表","About Dialog":"关于对话框",
    "Log Message":"日志消息","Progress":"进度","Color Dialog":"颜色对话框","Status":"状态",
    "Tool Tip":"工具提示","Camera Dialog":"相机对话框","Shader Dialog":"着色器对话框",
    "Snapshot Dialog":"快照对话框","Symmetry Tolerance":"对称容差","Shader Library":"着色器库",
    "Snapshot":"快照","Shader":"着色器","Server Configuration":"服务器配置",
    "Server Configuration List":"服务器配置列表","Ssh File Dialog":"SSH 文件对话框",
    "Queue Options":"队列选项","Queue Resources":"队列资源","AWS Configuration":"AWS 配置",
    "System Dependent":"系统相关","Network":"网络","Ssh Connection":"SSH 连接",
    "Amber Config":"Amber 配置","Amber System Builder":"Amber 系统构建器","Amber directory":"Amber 目录",
    "Amber directory not set":"未设置 Amber 目录","Gromacs Setup":"Gromacs 设置","Gromacs Config":"Gromacs 配置",
    "Edit Gromacs Config":"编辑 Gromacs 配置","Edit Gromacs Server":"编辑 Gromacs 服务器",
    "Edit Amber Config":"编辑 Amber 配置","Gromacs Server":"Gromacs 服务器","Parametrize Molecule":"分子参数化",
    # 计算参数（可译部分）
    "CC Memory":"CC 内存","CFMM Grain":"CFMM 粒度","CHELPG Charges":"CHELPG 电荷","CIS_GUESS_DISK":"CIS_GUESS_DISK",
    "CPSCF Segments":"CPSCF 段","DFPT Exchange":"DFPT 交换","DFPT Grid":"DFPT 网格","DIIS Method":"DIIS 方法",
    "DIIS Metric":"DIIS 度量","DIIS Options":"DIIS 选项","DIIS Size":"DIIS 大小","DIIS Start":"DIIS 起始",
    "DIIS Subspace":"DIIS 子空间","SCF Control":"SCF 控制","Use GEN_SCFMAN":"使用 GEN_SCFMAN",
    "NBO Analysis":"NBO 分析","NMR Chemical Shifts":"NMR 化学位移","RCA Print Level":"RCA 打印级别",
    "RCA Switch Thresh":"RCA 切换阈值","MOM Start Cycle":"MOM 起始循环","MOM Method":"MOM 方法",
    "Max RCA Cycles":"最大 RCA 循环","Max DIIS Cycles":"最大 DIIS 循环","SCF Guess Print":"SCF 猜测打印",
    "SCF Print":"SCF 打印","SCF Final Print":"SCF 最终打印","PDB Coordinates":"PDB 坐标",
    "WFN filename:":"WFN 文件名：","HFPT Basis":"HFPT 基组","PAO Algorithm":"PAO 算法","PAO Method":"PAO 方法",
    "MRXC Options":"MRXC 选项","Compute SSG Wavefunction":"计算 SSG 波函数","VCI Quanta":"VCI 量子",
    "NTO Pairs":"NTO 对","RMSD (High)":"RMSD(高)","MDL SDfile":"MDL SD 文件","Generate MOLDEN Input":"生成 MOLDEN 输入",
    "Compute Anharmonic Corrections":"计算非谐校正","Compute Full QM/MM Hessian":"计算完整 QM/MM 海森矩阵",
    "Compute Perturbations Singly":"单独计算微扰","Compute Vec-Mat Poduct By FD":"用有限差分计算向量-矩阵乘积",
    "Configuration Files (*.cfg)":"配置文件(*.cfg)","Copyright ©":"版权 ©",
    "Core Character":"核心特征","Counter Ions":"抗衡离子","Coupled Cluster":"耦合簇","Cavity Convergence":"空腔收敛",
    "Cavity Radius":"空腔半径","Center Molecule":"分子居中","Changes to the log file location require IQmol to be restarted":"日志文件位置更改后需重启 IQmol",
    "Check box":"复选框","Chemical formula:":"化学式：","Chroma":"色度","Closeness":"贴近度","Co-planar":"共面",
    "Complex Mix":"复合混合","Complex SCF":"复合 SCF","Configure EFP Fragments":"配置 EFP 碎片",
    "Constrain":"约束","Contact your Q-Cloud administrator":"请联系您的 Q-Cloud 管理员","Continuous":"连续",
    "Controls the speed of animation":"控制动画速度","Crop Bounding Box":"裁剪包围盒","Cube File Frames":"立方体文件帧",
    "Cubic":"立方体","Cutoff Threshold:":"截断阈值：","Data Size (kB)":"数据大小(kB)","Davidson Iterations":"Davidson 迭代",
    "Davidson Options":"Davidson 选项","Debug":"调试","Decompositions":"分解","Default Force Field:":"默认力场：",
    "Denominator Thresh":"分母阈值","Deuterate":"氘代","Dielectric":"介电常数","Dihedral":"二面角",
    "Dipole Options":"偶极矩选项","Dipole moment:":"偶极矩：","Dipole:   ":"偶极矩：","Direct RI":"直接 RI",
    "Direct SCF":"直接 SCF","Direction":"方向","Disable Controls":"禁用控件","Disable Transparency":"禁用透明",
    "Dispersion Correction":"色散校正","Displacement":"位移","Distance between atom 1 and 2: ":"原子 1 与 2 之间的距离：",
    "Do not use ~ or environment variables":"请勿使用 ~ 或环境变量","Double spin box":"双精度微调框",
    "Doubles Guess Vectors":"双精度猜测向量","Dual Basis Energy":"双基组能量","Dummy Atom:":"虚原子：",
    "EFP Calculation":"EFP 计算","EFP Only Calculation (No QM)":"仅 EFP 计算(无 QM)","EFP Options":"EFP 选项",
    "EPAO Weights":"EPAO 权重","Edit Bounding Box":"编辑包围盒","Edit variable parameters:":"编辑可变参数：",
    "EditConf":"EditConf","Excited State Moments":"激发态矩","Fatal":"致命","Fast XC":"快速 XC",
    "FFmpeg Path":"FFmpeg 路径","Final / (cm⁻¹)":"最终 /(cm⁻¹)","Final Vibrational Analysis":"最终振动分析",
    "Finite Difference Stepsize":"有限差分步长","First Order":"一阶","First electronic state":"第一电子态",
    "Fix":"修复","Flourine (19F)":"氟(19F)","Fock Extrapolation Order":"福克外推阶","Follow Mode":"跟随模式",
    "Boron (11B)":"硼(11B)","Carbon (13C)":"碳(13C)","Carbon (12C)":"碳(12C)","Hydrogen (1H)":"氢(1H)",
    "Nitrogen (14N)":"氮(14N)","Oxygen (17O)":"氧(17O)","Silicon (29Si)":"硅(29Si)","Phosphorus (31P)":"磷(31P)",
    "Sulfur (33S)":"硫(33S)","Chlorine (35Cl)":"氯(35Cl)","Fluorine (19F)":"氟(19F)",
    "Build Element":"构建元素","formula":"公式",
}

WORD = {
    "about":"关于","abort":"中止","accept":"接受","access":"访问","account":"账户","action":"操作",
    "add":"添加","advanced":"高级","algorithm":"算法","all":"全部","alpha":"Alpha","amber":"Amber",
    "analysis":"分析","analyze":"分析","angle":"角","animation":"动画","antialias":"抗锯齿","apply":"应用",
    "array":"数组","atom":"原子","atoms":"原子","attribute":"属性","auto":"自动","automatic":"自动",
    "axis":"轴","axes":"坐标轴","background":"背景","back":"返回","basic":"基础","basis":"基组",
    "behaviour":"行为","black":"黑色","blend":"混合","bond":"键","bonds":"键","border":"边框",
    "bounce":"弹跳","browse":"浏览","build":"构建","builder":"构建器","cancel":"取消","camera":"相机",
    "carbon":"碳","cartesian":"笛卡尔","cavity":"空腔","center":"中心","centre":"中心","charge":"电荷",
    "charges":"电荷","check":"检查","chem":"化学","chemical":"化学","cholesky":"Cholesky","chromatic":"色度",
    "circle":"圆","circular":"圆","clear":"清除","clip":"裁剪","clipping":"裁剪","close":"关闭",
    "cluster":"簇","color":"颜色","colour":"颜色","column":"列","command":"命令","commands":"命令",
    "comment":"注释","complex":"复合","compress":"压缩","config":"配置","configurator":"配置",
    "configure":"配置","connect":"连接","connection":"连接","connectivity":"连接","constrain":"约束",
    "constraint":"约束","constraints":"约束","contact":"联系人","content":"内容","control":"控制",
    "convergence":"收敛","converge":"收敛","coordinate":"坐标","coordinates":"坐标","copper":"铜",
    "copy":"复制","core":"核心","correction":"校正","corrections":"校正","cost":"开销","coupled":"耦合",
    "coupling":"耦合","cpu":"CPU","create":"创建","csv":"CSV","cube":"立方体","cubic":"立方体",
    "custom":"自定义","cut":"剪切","cutoff":"截断","cyan":"青","cycle":"循环","cycles":"循环",
    "data":"数据","database":"数据库","debug":"调试","default":"默认","delete":"删除","density":"密度",
    "depend":"依赖","derivative":"导数","description":"描述","detect":"检测","detection":"检测",
    "diag":"诊断","dialog":"对话框","dichroism":"二色性","dielectric":"介电常数","dihedral":"二面角",
    "difference":"差分","diff":"差分","direct":"直接","direction":"方向","directory":"目录","disable":"禁用",
    "displace":"位移","displacement":"位移","display":"显示","dispersion":"色散","distance":"距离",
    "done":"完成","dot":"点","dots":"点","double":"双","doubles":"双精度","dummy":"虚","edit":"编辑",
    "editor":"编辑器","edge":"边缘","edges":"边缘","effect":"效果","effects":"效果","eigen":"本征",
    "eigenvalue":"本征值","eigenvector":"本征向量","electric":"电","element":"元素","elements":"元素",
    "email":"电子邮件","embed":"嵌入","enable":"启用","energy":"能量","entered":"已输入","error":"错误",
    "escape":"退出","exchange":"交换","excitation":"激发","excited":"激发","exit":"退出","export":"导出",
    "expression":"表达式","extended":"扩展","extrapolation":"外推","field":"场","fields":"场","file":"文件",
    "files":"文件","filter":"过滤","final":"最终","finite":"有限","first":"第一","fit":"拟合","fix":"修复",
    "fixed":"固定","flag":"标志","flourine":"氟","fluorine":"氟","follow":"跟随","font":"字体",
    "force":"力","format":"格式","form":"表单","fragment":"片段","fragments":"片段","frame":"帧",
    "free":"自由","frequency":"频率","frequencies":"频率","gateway":"网关","general":"常规","geometry":"几何",
    "global":"全局","gradient":"梯度","grid":"网格","group":"组","groups":"组","guess":"猜测","gaussian":"高斯",
    "helium":"氦","hide":"隐藏","history":"历史记录","host":"主机","hostname":"主机名","hydrogen":"氢",
    "import":"导入","index":"索引","indices":"索引","information":"信息","init":"初始化","input":"输入",
    "insert":"插入","integral":"积分","interaction":"相互作用","interactions":"相互作用","interface":"接口",
    "iteration":"迭代","iterations":"迭代","job":"任务","jobs":"任务","key":"键","label":"标签",
    "labels":"标签","layer":"图层","layers":"图层","length":"长度","level":"级别","library":"库",
    "light":"光","line":"线","list":"列表","lithium":"锂","load":"加载","local":"本地","location":"位置",
    "log":"日志","magnetic":"磁","manual":"手动","mass":"质量","matrix":"矩阵","maximum":"最大",
    "max":"最大","memory":"内存","menu":"菜单","message":"消息","metal":"金属","method":"方法",
    "methods":"方法","metric":"度量","minimum":"最小","min":"最小","mode":"模式","model":"模型",
    "molecule":"分子","molecules":"分子","monitor":"监视器","mulliken":"Mulliken","name":"名称",
    "network":"网络","new":"新建","next":"下一步","nmr":"核磁共振","node":"节点","none":"无","normal":"法线",
    "normalmode":"简正模式","number":"序号","numbers":"序号","object":"对象","occlusion":"遮蔽",
    "octree":"八叉树","offer":"提供","offset":"偏移","open":"打开","operation":"操作","optimization":"优化",
    "optimize":"优化","option":"选项","options":"选项","order":"阶","orbital":"轨道","orbitals":"轨道",
    "orientation":"定向","origin":"原点","output":"输出","overview":"概览","page":"页","pair":"对",
    "pairs":"对","parallel":"并行","parameter":"参数","parameters":"参数","parent":"父级","paste":"粘贴",
    "path":"路径","pattern":"模式","pend":"待定","performance":"性能","perturbation":"微扰","perturbations":"微扰",
    "physics":"物理","point":"点","pointer":"指针","policy":"策略","port":"端口","position":"位置",
    "preference":"首选项","preferences":"首选项","previous":"上一步","preview":"预览","print":"打印",
    "priority":"优先级","problem":"问题","process":"进程","progress":"进度","product":"积","poduct":"积",
    "project":"项目","properties":"属性","property":"属性","protein":"蛋白质","protocol":"协议",
    "provider":"提供方","quality":"质量","quantum":"量子","queue":"队列","quit":"退出","radius":"半径",
    "range":"范围","ratio":"比例","read":"读取","record":"记录","redo":"重做","reference":"参考",
    "refresh":"刷新","region":"区域","register":"注册","relaxed":"松弛","remote":"远程","remove":"移除",
    "render":"渲染","report":"报告","reset":"重置","resource":"资源","resources":"资源","result":"结果",
    "results":"结果","restart":"重启","rotation":"旋转","row":"行","run":"运行","scale":"缩放",
    "scene":"场景","screen":"屏幕","script":"脚本","section":"段","segment":"段","segments":"段",
    "select":"选择","selection":"选区","server":"服务器","servers":"服务器","set":"设置","setting":"设置",
    "settings":"设置","shader":"着色器","shape":"形状","shell":"壳层","shift":"位移","show":"显示",
    "silicon":"硅","sign":"符号","signed":"带符号","single":"单","size":"大小","skip":"跳过",
    "snapshot":"快照","smooth":"平滑","solution":"解","source":"源","space":"空间","sphere":"球",
    "spin":"自旋","start":"开始","state":"态","states":"态","status":"状态","step":"步","steps":"步",
    "stiffness":"刚度","stop":"停止","store":"存储","structure":"结构","style":"样式","submit":"提交",
    "sub":"子","subspace":"子空间","sum":"和","support":"支持","surface":"表面","surfaces":"表面",
    "switch":"切换","symbol":"符号","symmetry":"对称性","symmetric":"对称","system":"系统","tensor":"张量",
    "test":"测试","text":"文字","threshold":"阈值","thresh":"阈值","time":"时间","title":"标题",
    "tool":"工具","tooltip":"工具提示","transform":"变换","transition":"跃迁","translate":"平移",
    "truncate":"截断","tolerance":"容差","total":"总计","torsion":"扭转","type":"类型","unitary":"幺正",
    "update":"更新","upload":"上传","user":"用户","value":"值","values":"值","variable":"变量",
    "variables":"变量","vector":"矢量","vectors":"矢量","version":"版本","view":"视图","viewer":"查看器",
    "warning":"警告","weight":"权重","weights":"权重","widget":"控件","window":"窗口","write":"写入",
    "zoom":"缩放","zone":"区域","molecular":"分子","re":"重新","perceive":"识别","reindex":"重新编号",
    "freeze":"冻结","minimize":"最小化","transl":"平移","symmetriz":"对称化","selected":"所选",
    "welcome":"欢迎","iqmol":"IQmol","changes":"更改","file":"文件","edit":"编辑","view":"视图",
    "cell":"晶胞","hydrogen":"氢","boron":"硼","nitrogen":"氮","oxygen":"氧","sulfur":"硫","chlorine":"氯",
    "phosphorus":"磷","fluorine":"氟","silicon":"硅","deuter":"氘","deuterate":"氘代",
}

SIG_PHRASE = [
  ("simple molecular builder", "IQmol 是一个使用 Qt 库编写的简易分子构建与可视化工具。以下库也被使用或集成到 IQmol 中：\n      <ul>\n         <li> <a href=\"http://www.libqglviewer.com/\">libQGLViewer</a>\n         <li> <a href=\"http://openbabel.org/\">Open Babel</a>\n         <li> <a href=\"http://www.boost.org/\">Boost Libraries</a>\n         <li> <a href=\"http://www.ccp14.ac.uk/ccp/web-mirrors/symmol/~pila/\">SymMol</a>\n      </ul>\n          Marching cubes 代码基于 \n      <a href=\"http://paulbourke.net/geometry/polygonise/\">Paul Bourke</a> 的算法，由 Klaus Miltenberger 博士改编。\n"),
  ("slider controls the magnitude", "此滑块控制位移矢量和动画的大小。"),
  ("inaccessible to the user", "此页面对用户不可见，\n它作为容器，包含\n由其他 rem 设置的控件。\n将来应移除。"),
  ("Amber directory is not set", "未设置 Amber 目录。请在“编辑 Amber 配置”对话框中设置。"),
  ("Maximum number of concurrent jobs", "最大并发任务数。\n注意：在 PBS 服务器上此设置被忽略。"),
  ("accessed by ${WALLTIME}", "此值可在运行文件模板中通过 ${WALLTIME} 访问"),
  ("accessed by ${MEMORY}", "此值可在运行文件模板中通过 ${MEMORY} 访问"),
  ("accessed by ${NCPUS}", "此值可在运行文件模板中通过 ${NCPUS} 访问"),
  ("accessed by ${SCRATCH}", "此值可在运行文件模板中通过 ${SCRATCH} 访问"),
  ("accessed by ${QUEUE}", "此值可在运行文件模板中通过 ${QUEUE} 访问"),
  ("simply runs the qchem command", "基本模式直接在服务器上运行 qchem 命令。\n\n若服务器有队列系统，请使用 PBS 或 SGE。\n提交任务时会提示您设置额外的资源限制。\n\n对 HTTP/HTTPS 服务器请使用 Web。"),
  ("PNG will give better quality", "PNG 质量更好，但可能导致影片文件更大"),
  ("SSH public key file", "SSH 公钥文件位置。通常\n与私钥文件名相同，但附加 .pub 后缀。"),
  ("SSH identity file", "SSH 身份文件位置。对于协议 1，通常位于\n$HOME/.ssh/identity；对于协议 2，通常位于\n$HOME/.ssh/id_rsa 或 $HOME/.ssh/id_dsa。"),
  ("known_hosts file", "这是 known_hosts 文件的位置。\n通常位于 $HOME/.ssh/known_hosts"),
  ("mesh decimation", "使用网格抽稀以降低表面网格的复杂度"),
  ("manual edits will be lost", "手动编辑将丢失。\n确定要继续吗？"),
  ("panel is never displayed", "此面板从不显示，它只是\n各种 EOM 态定义控件的容器。"),
  ("signed surface will disply", "带符号表面会同时显示正负等值面。若只需一个表面，请取消勾选。"),
  ("directory on the server where calculations will run", "这是服务器上运行计算的目录。\n\n若服务器使用队列系统，请使用 PBS 或 SGE。\n提交任务时会提示您设置额外的资源限制。\n\n对 HTTP/HTTPS 服务器请使用 Web。"),
  ("Higher values will find more symmetric", "较大的值会发现更多对称结构，但可能导致几何结构发生不期望的改变。"),
  ("Log file changes will not take effect until restart", "日志文件更改需重启后生效"),
  ("log file location require IQmol to be restarted", "日志文件位置更改后需重启 IQmol"),
]

EXTRA_WORD = {
  "backlight":"背光","base":"基组","bases":"基组","correlation":"相关","electron":"电子",
  "framerate":"帧率","functional":"泛函","geminal":"双生","generalized":"广义","generate":"生成",
  "geometries":"几何结构","guess":"猜测","height":"高度","hirshfeld":"Hirshfeld","hue":"色度",
  "identifier":"标识符","ignore":"忽略","image":"图像","impulse":"冲量","increase":"增加",
  "incremental":"增量","initial":"初始","inner":"内","integer":"整数","integrals":"积分",
  "integration":"积分","intensity":"强度","internal":"内部","interpolation":"插值","ion":"离子",
  "isometric":"等距","isosurface":"等值面","isovalue":"等值","kill":"终止","known":"已知",
  "lebedev":"Lebedev","left":"左","lightness":"明度","lights":"光源","linear":"线性","lines":"线",
  "logical":"逻辑","loop":"循环","lorentzian":"洛伦兹","lower":"较低","manipulate":"操作",
  "methane":"甲烷","multiplicity":"多重态","multipole":"多极","mutability":"可变性","negative":"负",
  "node":"节点","nonlocal":"非局域","note":"注意","occupied":"占据","omega":"Omega","opacity":"不透明度",
  "optical":"光学","orthographic":"正交","oversampling":"过采样","parametrize":"参数化","percentage":"百分比",
  "perpendicular":"垂直","perspective":"透视","plane":"平面","plastic":"塑料","play":"播放",
  "playback":"回放","plots":"绘图","polar":"极坐标","positive":"正","projection":"投影","pure":"纯",
  "relax":"松弛","residue":"残基","root":"根","rotational":"转动","singlet":"单重态","spectrum":"谱",
  "speed":"速度","stability":"稳定性","stepsize":"步长","template":"模板","translational":"平移",
  "velocity":"速度","virtual":"虚","aspect":"宽高比","concurrent":"并发","degree":"自由度",
  "freedom":"自由度","pointgroup":"点群","frozen":"冻结","orbs":"轨道","herzberg":"Herzberg",
  "franck":"Franck","condon":"Condon","fock":"福克","hartree":"哈特里",
}
WORD.update(EXTRA_WORD)

# ---- 第二批次：覆盖剩余单词变形 + 保留英文的输入关键字 ----
EXTRA_WORD2 = {
  "electronic":"电子","low":"低","foreground":"前景","forward":"前进","gdiis":"GDIIS",
  "subspace":"子空间","gases":"气体","geminal":"双生","generated":"生成","transformation":"变换",
  "browser":"浏览器","teller":"Teller","hessian":"海森矩阵","hexagonal":"六角","prism":"棱柱",
  "highlight":"高亮","hirshfeld":"Hirshfeld","inchi":"InChI","relaxation":"松弛","intens":"强度",
  "joblimit":"任务限制","libopt":"LibOpt","logging":"日志","enabled":"启用","make":"设置",
  "maxscf":"最大 SCF","generations":"代","dynamics":"动力学","move":"移动","down":"下","up":"上",
  "populations":"布居","derived":"推导","from":"从","children":"子项","virtuals":"虚轨道",
  "electrons":"电子","roscf":"ROSCF","perform":"执行","link":"连接","preserve":"保持","ratio":"比例",
  "pressure":"压力","private":"私","public":"公","proton":"质子","qcloud":"Q-Cloud","query":"查询",
  "fitting":"拟合","radii":"半径","radio":"单选","raman":"拉曼","reaction":"反应","pathway":"路径",
  "xyz":"XYZ","real":"实部","recompute":"重算","reconnect":"重新连接","recording":"录制",
  "reduced":"约化","active":"活性","current":"当前","slected":"所选","finished":"已完成","killed":"已终止",
  "reperceive":"重新识别","res":"收敛","restricted":"受限","kohn":"科恩","sham":"沙姆","rhombic":"菱",
  "dodecahedron":"十二面体","right":"右","gas":"气体","phase":"相","sample":"样本","picture":"图片",
  "factor":"因子","scaling":"缩放","scan":"扫描","scratch":"临时","seam":"接缝","second":"第二",
  "criterion":"准则","shielding":"屏蔽","simplify":"简化","singles":"单","smaller":"更小",
  "smoothness":"平滑度","precision":"精度","solvate":"溶剂化","solvent":"溶剂","sort":"排序",
  "filling":"填充","flip":"翻转","properties":"性质","static":"静态","strength":"强度","string":"字符串",
  "area":"面积","crossing":"交叉","swap":"交换","sybyl":"Sybyl","temperature":"温度","textures":"纹理",
  "contain":"包含","executable":"可执行","exist":"存在","theory":"理论","threads":"线程","ticks":"刻度",
  "topology":"拓扑","trace":"迹","tree":"树","triplet":"三重态","octahedron":"八面体","tubes":"管",
  "photon":"光子","absorption":"吸收","units":"单位","unrestricted":"非限制","interval":"间隔",
  "canonical":"正则","cartesians":"笛卡尔","dynamic":"动态","blurred":"模糊","lin":"Lin","smart":"智能",
  "spherical":"球","video":"视频","warn":"警告","web":"Web","white":"白色","width":"宽度",
  "wire":"线框","working":"工作","zpve":"ZPVE","checkpoint":"检查点","pov":"POV","ray":"Ray",
  "input":"输入","background":"背景","to":"到","note":"注意","notes":"备注","state":"态",
  "optimize":"优化","root":"根","shell":"壳层","singlet":"单重态","restricted":"受限",
  "kohn":"科恩","sham":"沙姆","rohf":"ROHF","uhf":"UHF","rhf":"RHF","spin":"自旋","flip":"翻转",
  "only":"仅","density":"密度","orbit":"轨道","coupling":"耦合","start":"开始","stop":"停止",
  "translate":"平移","show":"显示","previous":"上一步","next":"下一步","point":"点","plane":"平面",
}
EXTRA_PHRASE2 = {
  # Q-Chem / Amber / GROMACS 输入关键字与文件格式：保留英文（翻译会破坏输入文件）
  "DFT-D3":"DFT-D3","Gaff":"Gaff","Ghemical":"Ghemical","MMFF94s":"MMFF94s","MP2[V]":"MP2[V]",
  "POV-Ray":"POV-Ray","InChi":"InChI","LibOpt3":"LibOpt3","RI-J":"RI-J","RI-K":"RI-K",
  "SF-XCIS":"SF-XCIS","Z-matrix Input":"Z 矩阵输入","frcmod":"frcmod","mol2":"Mol2",
  "topol.top":"topol.top","posre.itp":"posre.itp","addIons":"addIons","addIons2":"addIons2",
  "addIonsRand":"addIonsRand","solvateBox":"solvateBox","solvateOct":"solvateOct","spc216":"spc216",
  "Sybyl Mol2":"Sybyl Mol2","X-Y Plane":"X-Y 平面","X-Z Plane":"X-Z 平面","Y-Z Plane":"Y-Z 平面",
  # 含 %1 占位符的长句（保留占位符）
  "The directory %1 does not contain the Amber executable.":"目录 %1 不包含 Amber 可执行文件。",
  "The directory %1 does not exist.":"目录 %1 不存在。",
  # 复合长标签
  "Reperceive bond for each conformer":"为每个构象重新识别键",
  "Select the displacement vector color":"选择位移矢量颜色",
  "Server mnemonic (does not have to match actual server name)":"服务器助记名（不必与真实服务器名一致）",
  "Server name or IP address":"服务器名称或 IP 地址",
  "Reverse file list order":"反转文件列表顺序","Reverses the loop at the end":"在循环末尾反转",
  "Remove slected server":"移除所选服务器",
  "Removes finished and killed jobs from the list":"从列表移除已完成和已终止的任务",
  "Remove current section from input file":"从输入文件移除当前段",
  "Use new EFP input format":"使用新 EFP 输入格式",
  "State To Optimize":"待优化态","State to optimize":"待优化态","State-to-State Properties":"态间性质",
  "Move to next frequency":"移到下一频率","Move to previous frequency":"移到上一频率",
  "Show next conformer":"显示下一构象","Show previous conformer":"显示上一构象",
  "Move selection down":"将选区下移","Move selection up":"将选区上移",
  "Move server down":"将服务器下移","Move server up":"将服务器上移",
  "Number of atoms:":"原子数：","Number of electrons:":"电子数：",
  "Number of Children":"子项数量","Number of Conformers":"构象数量","Number of Grids":"网格数量",
  "Number of Points":"点数","Number of Roots":"根数量","Number of Steps":"步数","Number of Virtuals":"虚轨道数",
  "Maximum Undo Level:":"最大撤销级别：","Maximum Generations":"最大代数","Max SCFs":"最大 SCF 步数",
  "Job Limit":"任务限制","Known Hosts":"已知主机","Host Address":"主机地址","IQmol Log Messages":"IQmol 日志消息",
  "IQmol Preferences":"IQmol 首选项","Help Browser":"帮助浏览器","Full Screen Mode":"全屏模式",
  "Foregound Color":"前景颜色","Foreground Color":"前景颜色","Front":"前面","Generate Checkpoint File":"生成检查点文件",
  "Generate POV-Ray File":"生成 POV-Ray 文件","Generated Input File:":"生成的输入文件：",
  "Grid Transformation":"网格变换","Gromacs Control":"Gromacs 控制","Guess Mix":"猜测混合",
  "Hessian Update":"海森矩阵更新","Hexagonal Prism":"六角棱柱","High":"高","Highlight":"高亮",
  "Hirshfeld populations":"Hirshfeld 布居","Include Background":"包含背景","Include Orbital Relaxation":"包含轨道松弛",
  "Include complete residues":"包含完整残基","Increase Printout":"增加打印输出","Increase Speed (and memory)":"提高速度（及内存）",
  "Incremental DFT":"增量 DFT","Initial / (cm⁻¹)":"初始 /(cm⁻¹)","Initial Hessian":"初始海森矩阵",
  "Initial Velocities":"初始速度","Integrals Buffer":"积分缓冲","Intens. (km/mol)":"强度(km/mol)",
  "Interpolation Frames":"插值帧","Isotopic Analysis":"同位素分析","Isotopic Mass":"同位素质量",
  "Large Molecule Methods":"大分子方法","Lebedev Grid":"Lebedev 网格","Linear Dependence":"线性依赖",
  "Logging Enabled":"已启用日志","Low":"低","Make Default":"设为默认","Modes":"模式","Molecular Dynamics":"分子动力学",
  "Mulliken Populations:":"Mulliken 布居：","Multi-resolution XC":"多分辨率 XC","Multipole Derived Charges":"多极推导电荷",
  "New Molecule From Selection":"从选区新建分子","Nodes":"节点","Note: Some structures may not be built correctly.":"注意：某些结构可能无法正确构建。",
  "Notes:":"备注：","Open Server Configuration":"打开服务器配置","Open-shell Singlet ROSCF":"开壳单重态 ROSCF",
  "Opt Method":"优化方法","Orbital(s):":"轨道：","Out of plane":"面外","Outer Radius":"外半径",
  "Perform Link-Atom Projection":"执行连接原子投影","Perturbation Batch Size":"微扰批大小","Phosphorous (31P)":"磷(31P)",
  "Points":"点","Points: θ":"点：θ","Positions File":"位置文件","Post Hartree Fock":"后哈特里-福克",
  "Preserve Aspect Ratio":"保持宽高比","Pressure":"压力","Print Geometry at Each Step":"每步打印几何",
  "Private Key":"私钥","Project Out Translational And Rotational Degrees Of Freedom":"投影掉平移与转动自由度",
  "Public Key":"公钥","Q-Cloud":"Q-Cloud","Q-Cloud Configuration":"Q-Cloud 配置","QChem Database File":"QChem 数据库文件",
  "Query":"查询","Query Job":"查询任务","Queue Info":"队列信息","RI Fitting Basis":"RI 拟合基组",
  "Radii":"半径","Radio button":"单选按钮","Raman":"拉曼","Raman (Å4 amu⁻¹)":"拉曼(Å⁴·amu⁻¹)","Raman Frequencies":"拉曼频率",
  "Re-generate SCF Guess at Each Step":"每步重新生成 SCF 猜测","Reaction Pathway":"反应路径","Read XYZ Input":"读取 XYZ 输入",
  "Recompute Hessian":"重算海森矩阵","Reconnect Servers":"重新连接服务器","Recording":"录制",
  "Reduced Active Space":"约化活性空间","Remove All Processes":"移除所有进程","Resource Limits":"资源限制",
  "Restricted Open-Shell Kohn-Sham":"受限开壳 Kohn-Sham","Reverse file list order":"反转文件列表顺序",
  "Rhombic Dodecahedron":"菱十二面体","Right":"右","Run gas phase":"运行气相","S<sub>6</sub>":"S₆","S<sub>8</sub>":"S₈","S<sub>r6</sub>":"Sᵣ₆",
  "SSH Agent":"SSH 代理","SSH File Locations":"SSH 文件位置","SSH Host Based":"SSH 基于主机","SSH Keyboard Interactive":"SSH 键盘交互",
  "SSH Prompt":"SSH 提示","SSH Public Key":"SSH 公钥","Sample":"样本","Save As Default":"设为默认","Save File":"保存文件",
  "Save G[Px] Data":"保存 G[Px] 数据","Save Input File":"保存输入文件","Save picture":"保存图片",
  "Scale Factor":"缩放因子","Scaling":"缩放","Scan":"扫描","Scratch":"临时目录","Search":"搜索",
  "Search for Seam Only":"仅搜索接缝","Second Basis":"第二基组","Second Order":"二阶","Second electronic state":"第二电子态",
  "Select the displacement vector color":"选择位移矢量颜色","Server mnemonic (does not have to match actual server name)":"服务器助记名（不必与真实服务器名一致）",
  "Server name or IP address":"服务器名称或 IP 地址","Set position of atom 1:":"设置原子 1 位置：",
  "Setup":"设置","Shell Pair Criterion:":"壳层对准则：","Shielding":"屏蔽","Shieldings":"屏蔽",
  "Show next conformer":"显示下一构象","Show previous conformer":"显示上一构象","Simplify Mesh":"简化网格",
  "Singles Guess Vectors":"单激发猜测向量","Singlets":"单重态","Skip CIS/RPA Calculation":"跳过 CIS/RPA 计算",
  "Smaller Hydrogen Atoms":"更小的氢原子","Smaller text":"缩小文字","Smoothness Precision:":"平滑精度：",
  "Solvate":"溶剂化","Solvent":"溶剂","Solvent Method":"溶剂方法","Solvent Model":"溶剂模型","Solvents":"溶剂",
  "Sort Criterion":"排序准则","Space Filling":"空间填充","Spin Flip":"自旋翻转","Spin box":"微调框",
  "Spin-Only Density":"仅自旋密度","Spin-Orbit Coupling":"自旋轨道耦合","Start and stop animation":"开始与停止动画",
  "State Mulliken Charges":"态 Mulliken 电荷","State To Optimize":"待优化态","State to optimize":"待优化态",
  "State-to-State Properties":"态间性质","Static Memory":"静态内存","Stops":"停止","Strength":"强度",
  "String":"字符串","Surface Area:":"表面积：","Surface Crossing":"表面交叉","Swap Colors":"交换颜色",
  "Swap Orbitals":"交换轨道","Symmetry Decompositions:":"对称性分解：","Temperature":"温度","Textures":"纹理",
  "The directory %1 does not contain the Amber executable.":"目录 %1 不包含 Amber 可执行文件。",
  "The directory %1 does not exist.":"目录 %1 不存在。","Theory":"理论","Threads":"线程","Thresholds":"阈值",
  "Ticks":"刻度","Top":"顶部","Topology":"拓扑","Topology file":"拓扑文件","Trace":"迹",
  "Transition Moments":"跃迁矩","Translation":"平移","Tree Sort":"树排序","Triplet States":"三重态",
  "Triplets":"三重态","Truncated Octahedron":"截断八面体","Tubes":"管","Two-Photon Absorption":"双光子吸收",
  "Two-electron properties":"双电子性质","Units":"单位","Unrestricted":"非限制","Update Interval":"更新间隔",
  "Use Canonical Steps":"使用正则步","Use Cartesians on Failure":"失败时使用笛卡尔坐标","Use DIIS":"使用 DIIS",
  "Use Dynamic Memory":"使用动态内存","Use Frozen Core":"使用冻结核","Use Gaussian-Blurred Charges":"使用高斯模糊电荷",
  "Use Integral Symmetry":"使用积分对称性","Use Lin K":"使用 Lin K","Use Point Group Symmetry":"使用点群对称性",
  "Use QChem/CHARMM Interface":"使用 QChem/CHARMM 接口","Use Reduced Active Space":"使用约化活性空间",
  "Use Smart Grid":"使用智能网格","Use Sperical Polar Grid":"使用球极网格","Use new EFP input format":"使用新 EFP 输入格式",
  "User-defined Topology":"用户自定义拓扑","Vibrational Frequencies":"振动频率","Vibronic Analysis":"电子振动分析",
  "Video Settings":"视频设置","Wall Time":"墙钟时间","Warn":"警告","Wavefunction Analysis":"波函数分析",
  "Web - Anonymous":"Web - 匿名","White":"白色","Width":"宽度","Wire Frame":"线框","Working Directory":"工作目录",
  "X Axis":"X 轴","X-Y Plane":"X-Y 平面","X-Z Plane":"X-Z 平面","Y Axis":"Y 轴","Y-Z Plane":"Y-Z 平面",
  "Z Axis":"Z 轴","ZPVE:":"ZPVE：","GDIIS Subspace":"GDIIS 子空间","Gaff":"Gaff","Gases":"气体",
  "Geminal(s):":"双生轨道：","Generate Checkpoint File":"生成检查点文件","Generated Input File:":"生成的输入文件：",
  "Ghemical":"Ghemical","Grid Transformation":"网格变换","Gromacs Control":"Gromacs 控制","Guess Mix":"猜测混合",
  "Help Browser":"帮助浏览器","Herzberg-Teller":"Herzberg-Teller","Hessian Update":"海森矩阵更新",
  "Hexagonal Prism":"六角棱柱","High":"高","Highlight":"高亮","Hirshfeld populations":"Hirshfeld 布居",
  "Host Address":"主机地址","IQmol Log Messages":"IQmol 日志消息","IQmol Preferences":"IQmol 首选项",
  "InChi":"InChI","Include Background":"包含背景","Include Orbital Relaxation":"包含轨道松弛",
  "Include complete residues":"包含完整残基","Increase Printout":"增加打印输出","Increase Speed (and memory)":"提高速度（及内存）",
  "Incremental DFT":"增量 DFT","Initial / (cm⁻¹)":"初始 /(cm⁻¹)","Initial Hessian":"初始海森矩阵",
  "Initial Velocities":"初始速度","Integrals Buffer":"积分缓冲","Intens. (km/mol)":"强度(km/mol)",
  "Interpolation Frames":"插值帧","Isotopic Analysis":"同位素分析","Isotopic Mass":"同位素质量",
  "Job Limit":"任务限制","Known Hosts":"已知主机","Large Molecule Methods":"大分子方法","Lebedev Grid":"Lebedev 网格",
  "Linear Dependence":"线性依赖","Logging Enabled":"已启用日志","Low":"低","Make Default":"设为默认",
  "Modes":"模式","Molecular Dynamics":"分子动力学","Mulliken Populations:":"Mulliken 布居：",
  "Multi-resolution XC":"多分辨率 XC","Multipole Derived Charges":"多极推导电荷","New Molecule From Selection":"从选区新建分子",
  "Nodes":"节点","Note: Some structures may not be built correctly.":"注意：某些结构可能无法正确构建。",
  "Notes:":"备注：","Open Server Configuration":"打开服务器配置","Open-shell Singlet ROSCF":"开壳单重态 ROSCF",
  "Opt Method":"优化方法","Orbital(s):":"轨道：","Out of plane":"面外","Outer Radius":"外半径",
  "Perform Link-Atom Projection":"执行连接原子投影","Perturbation Batch Size":"微扰批大小","Phosphorous (31P)":"磷(31P)",
  "Points":"点","Positions File":"位置文件","Post Hartree Fock":"后哈特里-福克","Preserve Aspect Ratio":"保持宽高比",
  "Pressure":"压力","Print Geometry at Each Step":"每步打印几何","Private Key":"私钥","Project Out Translational And Rotational Degrees Of Freedom":"投影掉平移与转动自由度",
  "Public Key":"公钥","Q-Cloud":"Q-Cloud","Q-Cloud Configuration":"Q-Cloud 配置","Query":"查询","Queue Info":"队列信息",
  "Radii":"半径","Radio button":"单选按钮","Raman":"拉曼","Raman Frequencies":"拉曼频率","Re-generate SCF Guess at Each Step":"每步重新生成 SCF 猜测",
  "Reaction Pathway":"反应路径","Read XYZ Input":"读取 XYZ 输入","Recompute Hessian":"重算海森矩阵",
  "Reconnect Servers":"重新连接服务器","Recording":"录制","Reduced Active Space":"约化活性空间",
  "Remove All Processes":"移除所有进程","Resource Limits":"资源限制","Restricted Open-Shell Kohn-Sham":"受限开壳 Kohn-Sham",
  "Rhombic Dodecahedron":"菱十二面体","Right":"右","Run gas phase":"运行气相","SSH Agent":"SSH 代理",
  "SSH File Locations":"SSH 文件位置","SSH Host Based":"SSH 基于主机","SSH Keyboard Interactive":"SSH 键盘交互",
  "SSH Prompt":"SSH 提示","SSH Public Key":"SSH 公钥","Sample":"样本","Save As Default":"设为默认",
  "Save File":"保存文件","Save G[Px] Data":"保存 G[Px] 数据","Save Input File":"保存输入文件","Save picture":"保存图片",
  "Scale Factor":"缩放因子","Scaling":"缩放","Scan":"扫描","Scratch":"临时目录","Search":"搜索",
  "Search for Seam Only":"仅搜索接缝","Second Basis":"第二基组","Second Order":"二阶","Second electronic state":"第二电子态",
  "Setup":"设置","Shell Pair Criterion:":"壳层对准则：","Shielding":"屏蔽","Shieldings":"屏蔽",
  "Show next conformer":"显示下一构象","Show previous conformer":"显示上一构象","Simplify Mesh":"简化网格",
  "Singles Guess Vectors":"单激发猜测向量","Singlets":"单重态","Skip CIS/RPA Calculation":"跳过 CIS/RPA 计算",
  "Smaller Hydrogen Atoms":"更小的氢原子","Smaller text":"缩小文字","Smoothness Precision:":"平滑精度：",
  "Solvate":"溶剂化","Solvent":"溶剂","Solvent Method":"溶剂方法","Solvent Model":"溶剂模型","Solvents":"溶剂",
  "Sort Criterion":"排序准则","Space Filling":"空间填充","Spin Flip":"自旋翻转","Spin box":"微调框",
  "Spin-Only Density":"仅自旋密度","Spin-Orbit Coupling":"自旋轨道耦合","Start and stop animation":"开始与停止动画",
  "State Mulliken Charges":"态 Mulliken 电荷","Static Memory":"静态内存","Stops":"停止","Strength":"强度",
  "String":"字符串","Surface Area:":"表面积：","Surface Crossing":"表面交叉","Swap Colors":"交换颜色",
  "Swap Orbitals":"交换轨道","Symmetry Decompositions:":"对称性分解：","Temperature":"温度","Textures":"纹理",
  "The directory %1 does not contain the Amber executable.":"目录 %1 不包含 Amber 可执行文件。",
  "The directory %1 does not exist.":"目录 %1 不存在。","Theory":"理论","Threads":"线程","Thresholds":"阈值",
  "Ticks":"刻度","Top":"顶部","Topology":"拓扑","Topology file":"拓扑文件","Trace":"迹",
  "Transition Moments":"跃迁矩","Translation":"平移","Tree Sort":"树排序","Triplet States":"三重态",
  "Triplets":"三重态","Truncated Octahedron":"截断八面体","Tubes":"管","Two-Photon Absorption":"双光子吸收",
  "Two-electron properties":"双电子性质","Units":"单位","Unrestricted":"非限制","Update Interval":"更新间隔",
  "Use Canonical Steps":"使用正则步","Use Cartesians on Failure":"失败时使用笛卡尔坐标","Use DIIS":"使用 DIIS",
  "Use Dynamic Memory":"使用动态内存","Use Frozen Core":"使用冻结核","Use Gaussian-Blurred Charges":"使用高斯模糊电荷",
  "Use Integral Symmetry":"使用积分对称性","Use Lin K":"使用 Lin K","Use Point Group Symmetry":"使用点群对称性",
  "Use QChem/CHARMM Interface":"使用 QChem/CHARMM 接口","Use Reduced Active Space":"使用约化活性空间",
  "Use Smart Grid":"使用智能网格","Use Sperical Polar Grid":"使用球极网格","User-defined Topology":"用户自定义拓扑",
  "Vibrational Frequencies":"振动频率","Vibronic Analysis":"电子振动分析","Video Settings":"视频设置",
  "Wall Time":"墙钟时间","Warn":"警告","Wavefunction Analysis":"波函数分析","Web - Anonymous":"Web - 匿名",
  "White":"白色","Width":"宽度","Wire Frame":"线框","Working Directory":"工作目录","X Axis":"X 轴",
  "Y Axis":"Y 轴","Z Axis":"Z 轴","ZPVE:":"ZPVE：","Andrew Gilbert":"Andrew Gilbert","FC + HT":"FC + HT",
  "Franck-Condon":"Franck-Condon","Energy (Low)":"能量(低)","Energy (eV)":"能量(eV)",
  "Freq. (cm⁻¹)":"频率(cm⁻¹)","Dipole:   ":"偶极矩：","Distance between atom 1 and 2: ":"原子 1 与 2 之间的距离：",
  "Electronic Transition":"电子跃迁","GDIIS Subspace":"GDIIS 子空间","Generate POV-Ray File":"生成 POV-Ray 文件",
}
PHRASE.update(EXTRA_PHRASE2)
WORD.update(EXTRA_WORD2)

def split_camel(s):
    return re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?![a-z])', s)

def is_excluded(s):
    st = s.strip()
    if st in ELEMENTS: return True
    if st in OBJS: return True
    if TECH_RE.match(st): return True
    if RES_RE.match(st): return True
    if VER_RE.match(st): return True
    if SYM_RE.match(st): return True
    if FORMULA_RE.match(st): return True
    if re.match(r'^[A-Z][a-z]?\d*([A-Z][a-z]?\d*)*$', st) and any(c.isdigit() for c in st):
        return True
    # Qt 样式表 (QSS) 字符串：非用户可见文本，保留原文
    if re.search(r'(QToolButton|QGraphicsView|QLinearGradient|QToolTip|QTextBrowser|QPushButton|'
                 r'QComboBox|QFrame|QWidget|QScrollBar|QMenu|QHeaderView|QSlider|QGroupBox|'
                 r'QTabWidget|QTableView|QTreeView)\s*[{:]', s):
        return True
    if re.search(r'(background\s*:|background-color|background-gradient|border-(width|color|style|radius)|'
                 r'min-width|max-width|min-height|max-height|padding\s*:|font-size\s*:|'
                 r'opacity\s*:|border\s*:\s*\d|margin\s*:|color\s*:\s*#)', s):
        return True
    # 单字符技术符号 / 希腊字母 / HTML 下标上标化学式 / 对象名 / 变量名
    if len(st) <= 1:
        return True
    if re.search(r'(<sub>|<sup>|&[a-zA-Z]+;|x10|e-|[\u0370-\u03FF])', s):
        return True
    if re.fullmatch(r'checkBox\d+', st):
        return True
    if st in ('versionString','Lable6','background: white'):
        return True
    return False

def is_upper_abbr(w):
    # 全大写缩写（≥2字母）保留英文，但 OK/NO 已译
    return w.isupper() and len(w) >= 2 and w not in ('OK','NO')

def translate_plain(s):
    """纯文本（无HTML）翻译，返回 (text, unfinished)"""
    st = s.strip()
    if st in KNOWN and KNOWN[st]: return KNOWN[st], False
    if st in PHRASE: return PHRASE[st], False
    for sig, tr in SIG_PHRASE:
        if sig in s:
            return tr, False
    if is_excluded(st): return s, False
    if st.lower() in WORD: return WORD[st.lower()], False
    # 同位素: Element (XXX)
    m = re.match(r'^([A-Z][a-z]?)\s*\((\d+[A-Za-z]?)\)$', st)
    if m and m.group(1) in ELEMENT_CN:
        return f"{ELEMENT_CN[m.group(1)]}({m.group(2)})", False
    # 组合合成
    parts = re.split(r'[\s/\(\)\[\]\{\}:,.\-]+', s)
    parts = [p for p in parts if p]
    out=[]; untrans=False
    for p in parts:
        if not p: continue
        if p.lower() in WORD:
            out.append(WORD[p.lower()]); continue
        subs = split_camel(p)
        if len(subs)==1 and is_upper_abbr(p):
            out.append(p); continue
        sub_tr=[]; ok=True
        for sub in subs:
            if sub.lower() in WORD: sub_tr.append(WORD[sub.lower()])
            elif is_upper_abbr(sub): sub_tr.append(sub)
            else: ok=False; sub_tr.append(sub)
        if ok: out.append(''.join(sub_tr))
        else: out.append(p); untrans=True
    text=''.join(out)
    if not text:
        return s, False   # 无法组合（纯数字/符号串），保留原文
    if untrans or re.search(r'[A-Za-z]{3,}', text):
        return None, True
    return text, False

def translate_html(s):
    """HTML 富文本：提取标签间可见文本翻译，保留标签与样式"""
    def repl(m):
        txt=m.group(1)
        if not txt.strip(): return txt
        tr, unf = translate_plain(txt)
        return tr if (tr and not unf) else txt
    return re.sub(r'(?<=>)([^<]+)(?=<)', repl, s)

def translate(s):
    # 收尾精确匹配（含尾随空格 / 特殊字符，避免组合逻辑遗漏）
    FINAL = {
        'MainWindow': '主窗口',
        'Dipole:   ': '偶极矩：',
        'Raman (\u212b4 amu\u207b\u00b9)': '拉曼(Å⁴·amu⁻¹)',
        'No breaky bonds': '无断裂键',
        'dipole': '偶极',
        'Distance between atom 1 and 2: ': '原子 1 与 2 之间的距离：',
        # 扩展任务新增（C++ 硬编码 tr 包裹）
        'Time (s)': '时间 (s)',
        'Raman (\u212b4/amu)': '拉曼 (Å⁴/amu)',
        'Frequency (cm\u207b\u00b9)': '频率 (cm⁻¹)',
        'Intensity (km/mol)': '强度 (km/mol)',
        'Indicies': '索引',
        'Resolution': '分辨率',
        'Function(s):': '函数:',
        'Invalid': '无效',
        'Ribbons': '飘带',
        'Logging disabled': '日志已禁用',
        'Download': '下载',
        'Job Info': '作业信息',
        'Add scan coordinated': '添加扫描约束',
        'Change atom type': '更改原子类型',
        'Change bond order': '更改键级',
    }
    if s in FINAL:
        return FINAL[s], False
    if '<html' in s or '<!DOCTYPE' in s:
        return translate_html(s), False
    return translate_plain(s)

# ---------- 处理 ts ----------
tree = ET.parse(TS)
root = tree.getroot()
root.set("language", "zh_CN")
stats={"known":0,"phrase":0,"word":0,"excluded":0,"html":0,"unfinished":0,"total":0}
for ctx in root.findall('context'):
    for m in ctx.findall('message'):
        s=m.find('source').text or ''
        tr_el=m.find('translation')
        t, unf = translate(s)
        stats["total"]+=1
        if unf or t is None:
            tr_el.clear(); tr_el.set('type','unfinished'); stats["unfinished"]+=1
        else:
            if s.strip() in KNOWN: stats["known"]+=1
            elif s.strip() in PHRASE: stats["phrase"]+=1
            elif ('<html' in s or '<!DOCTYPE' in s): stats["html"]+=1
            elif is_excluded(s.strip()): stats["excluded"]+=1
            else: stats["word"]+=1
            tr_el.clear(); tr_el.text=t
ET.register_namespace('', 'http://www.qt.io/2006/xml/ts')
tree.write(OUT, encoding='utf-8', xml_declaration=True)
print("统计:", stats)
