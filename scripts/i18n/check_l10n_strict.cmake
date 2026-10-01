# check_l10n_strict.cmake
# 用法（由 CMakeLists 在 lrelease POST_BUILD 阶段调用）:
#   cmake -DTS_FILE=<path/to/zh_CN.ts> -DIQMOL_STRICT_L10N=ON|OFF
#        -P scripts/i18n/check_l10n_strict.cmake
#
# 行为:
#   - 统计 .ts 中未完成的翻译 (<translation type="unfinished">) 与空翻译 (<translation></translation>)。
#   - 当 IQMOL_STRICT_L10N=ON 且存在未完成/空翻译时，构建失败（禁止带未译发布）。
#   - 当 IQMOL_STRICT_L10N=OFF 时仅打印统计，不中断。

if(NOT DEFINED TS_FILE OR NOT EXISTS "${TS_FILE}")
  message(STATUS "[IQmol] l10n 严格检查: 未指定或找不到 TS 文件 ${TS_FILE}，跳过")
  return()
endif()

file(READ "${TS_FILE}" _ts_content)

# 未完成翻译
string(REGEX MATCHALL "<translation type=\"unfinished\"" _unfinished "${_ts_content}")
list(LENGTH _unfinished _n_unfinished)

# 空翻译（vanished / 机械缺失）
string(REGEX MATCHALL "<translation></translation>" _empty "${_ts_content}")
list(LENGTH _empty _n_empty)

# 复数形式 (numerus) 的未完成翻译也会被上面的 unfinished 模式命中（type 属性一致），无需额外处理。

message(STATUS "[IQmol] l10n 检查: ts=${TS_FILE} unfinished=${_n_unfinished} empty=${_n_empty}")

if(IQMOL_STRICT_L10N AND (_n_unfinished GREATER 0 OR _n_empty GREATER 0))
  message(FATAL_ERROR
    "[IQmol] 严格本地化模式(IQMOL_STRICT_L10N=ON): 发现 ${_n_unfinished} 条未完成 + ${_n_empty} 条空翻译，禁止带未译发布。\n"
    "请先补全 zh_CN.ts 中的翻译，或将 IQMOL_STRICT_L10N 设为 OFF 仅作警告。")
elseif(IQMOL_STRICT_L10N)
  message(STATUS "[IQmol] 严格本地化模式: 无未译条目 ✅")
endif()
