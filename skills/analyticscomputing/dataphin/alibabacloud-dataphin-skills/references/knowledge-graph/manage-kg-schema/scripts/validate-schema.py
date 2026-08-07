#!/usr/bin/env python3
"""
KG Schema YAML 预校验工具

在调用 ImportKgSchema API 之前，本地校验 YAML 格式合法性，减少 API 调用失败。
可独立使用，也可被 import-schema.py 作为模块调用。

用法:
  python3 validate-schema.py <yaml_file>            # 仅校验
  python3 validate-schema.py <yaml_file> --fix       # 自动修复常见问题后保存

校验规则:
  - 顶层结构: entityTypes / relationTypes 至少一个非空
  - 实体编码: 大写字母开头，仅含大写字母/小写字母/数字（**不含下划线**），2-64 字符
  - 关系编码: 大写字母开头，仅含大写字母/数字/下划线（**不含小写**），2-64 字符
  - 属性编码: 小写字母开头，仅含小写字母/数字/下划线，1-64 字符
  - dataType: 合法枚举值且全大写
  - 每实体至少一个 isPrimaryKey: true（useSysPk=false 时）
  - 每实体至少一个 isUsedShow: true
  - 关系引用实体的存在性
  - 编码/名称唯一性: 实体、关系各自空间内唯一，且编码与名称均跨类型（实体↔关系）唯一
  - 属性编码/名称在同一类型内唯一（实体与关系属性均校验）
"""

import sys
import re
import copy

try:
    import yaml
except ImportError:
    print("错误: 需要安装 PyYAML\n  pip3 install pyyaml")
    sys.exit(1)


# ── 合法值枚举 ──
VALID_DATA_TYPES = {
    'STRING', 'INTEGER', 'FLOAT', 'BOOLEAN', 'DATE',
    'TIMESTAMP', 'DECIMAL', 'BIGINTEGER', 'REGEXSTRING',
    'ENUM', 'DURATION', 'DATETIMERANGE', 'URL', 'EMAIL',
    'GEOPOINT', 'GEOPOLYGON', 'GEOLINESTRING', 'JSON',
    'BLOB', 'EMBEDDED', 'UNKNOWN', 'ARRAY', 'MAP', 'LIST',
}

VALID_CARDINAL_TYPES = {
    'MULTI_TO_MULTI', 'ONE_TO_MANY', 'ONE_TO_ONE',
    'MANY_TO_MANY', 'ONE_TO_MANY_REV',
}

# 实体编码: 大写字母开头，仅含大写/小写字母/数字（大驼峰，服务端不接受下划线）
ENTITY_CODE_RE = re.compile(r'^[A-Z][A-Za-z0-9]{1,63}$')
# 关系编码: 大写字母开头，仅含大写字母/数字/下划线（SCREAMING_SNAKE，不含小写）
RELATION_CODE_RE = re.compile(r'^[A-Z][A-Z0-9_]{1,63}$')
PROPERTY_CODE_RE = re.compile(r'^[a-z][a-z0-9_]{0,63}$')


class SchemaValidator:
    def __init__(self, data, filename='<stdin>'):
        self.data = data
        self.filename = filename
        self.errors = []
        self.warnings = []
        self.entity_codes = set()
        self.relation_codes = set()
        self.entity_names = set()
        self.relation_names = set()

    def error(self, path, msg):
        self.errors.append(f"  [{path}] {msg}")

    def warn(self, path, msg):
        self.warnings.append(f"  [{path}] {msg}")

    def validate(self):
        """执行全部校验"""
        self._check_top_level()
        self._check_entity_types()
        self._check_relation_types()
        self._check_code_uniqueness()
        return len(self.errors) == 0

    def _check_top_level(self):
        if not isinstance(self.data, dict):
            self.error("顶层", "YAML 必须是一个映射（dict）")
            return

        has_entities = bool(self.data.get('entityTypes'))
        has_relations = bool(self.data.get('relationTypes'))
        if not has_entities and not has_relations:
            self.error("顶层", "entityTypes 和 relationTypes 至少需要一个非空列表")

        if 'schemaVersion' in self.data:
            self.warn("顶层", "schemaVersion 字段在实际环境中可能不被识别，建议使用 name/workspaceId 格式")
        if 'workspaceCode' in self.data and 'workspaceId' not in self.data:
            self.warn("顶层", "workspaceCode 不被服务端识别，应使用 workspaceId")

    def _check_entity_types(self):
        entities = self.data.get('entityTypes', []) or []
        if not isinstance(entities, list):
            self.error("entityTypes", "必须是列表")
            return

        for i, et in enumerate(entities):
            prefix = f"entityTypes[{i}]"
            if not isinstance(et, dict):
                self.error(prefix, "必须是映射（dict）")
                continue

            # code
            code = et.get('code', '')
            if not code:
                self.error(prefix, "缺少必填字段 code")
            elif not ENTITY_CODE_RE.match(str(code)):
                self.error(f"{prefix}.code",
                           f"编码 '{code}' 格式不合法：须大写字母开头，仅含字母/数字（不含下划线），2-64字符")
            elif code in self.entity_codes:
                self.error(f"{prefix}.code", f"实体编码 '{code}' 在空间内重复")
            else:
                self.entity_codes.add(code)

            # name
            name = et.get('name', '')
            if not name:
                self.error(prefix, "缺少必填字段 name")
            elif len(str(name)) < 2 or len(str(name)) > 50:
                self.error(f"{prefix}.name", f"名称长度须在 2-50 字符之间，当前 {len(str(name))}")
            elif name in self.entity_names:
                self.error(f"{prefix}.name", f"实体名称 '{name}' 在空间内重复")
            else:
                self.entity_names.add(name)

            # useSysPk
            use_sys_pk = et.get('useSysPk', False)

            # properties
            props = et.get('properties', [])
            if not props:
                self.error(prefix, "properties 不能为空，至少包含一个属性")
                continue
            if not isinstance(props, list):
                self.error(f"{prefix}.properties", "必须是列表")
                continue

            has_pk, has_show = self._check_property_list(props, prefix, use_sys_pk)

            # 实体级校验
            if not use_sys_pk and not has_pk:
                self.error(prefix,
                           f"useSysPk=false 但无 isPrimaryKey: true 的属性 -> "
                           f"服务端会报「至少包含一个主键属性或者配置系统主键」")
            if not has_show:
                self.error(prefix,
                           f"无 isUsedShow: true 的属性 -> "
                           f"服务端会报「至少包含一个用于展示的属性」")

    def _check_property_list(self, props, prefix, use_sys_pk=False):
        """校验属性列表（实体与关系共用），返回 (has_pk, has_show)"""
        has_pk = False
        has_show = False
        prop_codes = set()
        prop_names = set()

        for j, prop in enumerate(props):
            pprefix = f"{prefix}.properties[{j}]"
            if not isinstance(prop, dict):
                self.error(pprefix, "必须是映射（dict）")
                continue

            # code
            pcode = prop.get('code', '')
            if not pcode:
                self.error(pprefix, "缺少必填字段 code")
            elif not PROPERTY_CODE_RE.match(str(pcode)):
                self.error(f"{pprefix}.code",
                           f"编码 '{pcode}' 格式不合法：须小写字母开头，仅含小写字母/数字/下划线，1-64字符")
            else:
                if pcode in prop_codes:
                    self.error(f"{pprefix}.code", f"属性编码 '{pcode}' 在同一类型内重复")
                prop_codes.add(pcode)

            # name
            pname = prop.get('name', '')
            if not pname:
                self.error(pprefix, "缺少必填字段 name")
            else:
                if pname in prop_names:
                    self.error(f"{pprefix}.name", f"属性名称 '{pname}' 在同一类型内重复")
                prop_names.add(pname)

            # dataType
            dt = prop.get('dataType', '')
            if not dt:
                self.error(pprefix, "缺少必填字段 dataType")
            elif str(dt).upper() not in VALID_DATA_TYPES:
                self.error(f"{pprefix}.dataType",
                           f"不支持的数据类型 '{dt}'，合法值: {', '.join(sorted(VALID_DATA_TYPES))}")
            elif str(dt) != str(dt).upper():
                self.warn(f"{pprefix}.dataType",
                          f"dataType '{dt}' 建议使用全大写 '{str(dt).upper()}'")

            # isPrimaryKey
            if prop.get('isPrimaryKey', False):
                if use_sys_pk:
                    self.warn(f"{pprefix}.isPrimaryKey",
                              f"useSysPk=true 时属性不应设置 isPrimaryKey: true")
                has_pk = True

            # isUsedShow
            if prop.get('isUsedShow', False):
                has_show = True

            # isRequired
            if 'isRequired' not in prop:
                self.warn(pprefix, "建议显式设置 isRequired (true/false)")

            # isIndexed
            if 'isIndexed' not in prop:
                self.warn(pprefix, "建议显式设置 isIndexed (true/false)")

            # defaultValue
            if 'defaultValue' not in prop:
                self.warn(pprefix, "建议设置 defaultValue（无默认值时传空字符串 ''）")

        return has_pk, has_show

    def _check_relation_types(self):
        relations = self.data.get('relationTypes', []) or []
        if not isinstance(relations, list):
            self.error("relationTypes", "必须是列表")
            return

        for i, rt in enumerate(relations):
            prefix = f"relationTypes[{i}]"
            if not isinstance(rt, dict):
                self.error(prefix, "必须是映射（dict）")
                continue

            # code
            code = rt.get('code', '')
            if not code:
                self.error(prefix, "缺少必填字段 code")
            elif not RELATION_CODE_RE.match(str(code)):
                self.error(f"{prefix}.code", f"编码 '{code}' 格式不合法：须大写字母开头，仅含大写字母/数字/下划线（不含小写），2-64字符")
            elif code in self.relation_codes:
                self.error(f"{prefix}.code", f"关系编码 '{code}' 在空间内重复")
            else:
                self.relation_codes.add(code)

            # name
            rname = rt.get('name', '')
            if not rname:
                self.error(prefix, "缺少必填字段 name")
            elif rname in self.relation_names:
                self.error(f"{prefix}.name", f"关系名称 '{rname}' 在空间内重复")
            else:
                self.relation_names.add(rname)

            # source/target
            src = rt.get('sourceEntityCode', '')
            tgt = rt.get('targetEntityCode', '')
            if not src:
                self.error(prefix, "缺少必填字段 sourceEntityCode")
            if not tgt:
                self.error(prefix, "缺少必填字段 targetEntityCode")

            # 检查引用的实体是否存在（仅在同一 YAML 内校验）
            all_entity_codes = self.entity_codes | {
                e.get('code') for e in (self.data.get('entityTypes') or []) if isinstance(e, dict)
            }
            if src and src not in all_entity_codes:
                self.warn(f"{prefix}.sourceEntityCode",
                          f"引用的实体类型 '{src}' 在当前 YAML 的 entityTypes 中未定义（可能在空间中已存在）")
            if tgt and tgt not in all_entity_codes:
                self.warn(f"{prefix}.targetEntityCode",
                          f"引用的实体类型 '{tgt}' 在当前 YAML 的 entityTypes 中未定义（可能在空间中已存在）")

            # cardinalType
            ct = rt.get('cardinalType', '')
            if ct and str(ct).upper() not in VALID_CARDINAL_TYPES:
                self.error(f"{prefix}.cardinalType",
                           f"不支持的基数类型 '{ct}'，合法值: {', '.join(sorted(VALID_CARDINAL_TYPES))}")

            # 关系属性（可选，结构与实体属性一致）
            rprops = rt.get('properties', [])
            if rprops:
                if not isinstance(rprops, list):
                    self.error(f"{prefix}.properties", "必须是列表")
                else:
                    self._check_property_list(rprops, prefix)

            # 常见错误字段
            if 'cardinality' in rt and 'cardinalType' not in rt:
                self.warn(prefix, "使用了 cardinality 字段，服务端实际使用 cardinalType "
                                  "(MULTI_TO_MULTI/ONE_TO_MANY/ONE_TO_ONE)")
            if 'directionality' in rt and 'hasDirection' not in rt:
                self.warn(prefix, "使用了 directionality 字段，服务端实际使用 hasDirection (true/false)")

    def _check_code_uniqueness(self):
        """实体/关系的编码与名称跨类型唯一性"""
        for code in (self.entity_codes & self.relation_codes):
            self.error("编码唯一性", f"编码 '{code}' 同时被实体类型和关系类型使用，须跨类型唯一")
        for name in (self.entity_names & self.relation_names):
            self.error("名称唯一性", f"名称 '{name}' 同时被实体类型和关系类型使用，须跨类型唯一")


def auto_fix(data):
    """自动修复常见问题"""
    data = copy.deepcopy(data)

    for et in (data.get('entityTypes') or []):
        if not isinstance(et, dict):
            continue
        for prop in (et.get('properties') or []):
            if not isinstance(prop, dict):
                continue
            # 修复 dataType 大小写
            dt = prop.get('dataType', '')
            if dt and dt != dt.upper():
                prop['dataType'] = dt.upper()
            # 补充缺失的 defaultValue
            if 'defaultValue' not in prop:
                prop['defaultValue'] = ''
            # 补充缺失的 boolean 字段
            for field in ('isPrimaryKey', 'isRequired', 'isIndexed', 'isUsedShow'):
                if field not in prop:
                    prop[field] = False

    # 修复 cardinality -> cardinalType
    for rt in (data.get('relationTypes') or []):
        if not isinstance(rt, dict):
            continue
        if 'cardinality' in rt and 'cardinalType' not in rt:
            mapping = {
                'ManyToMany': 'MULTI_TO_MULTI', 'N:M': 'MULTI_TO_MULTI',
                'OneToMany': 'ONE_TO_MANY', '1:N': 'ONE_TO_MANY',
                'OneToOne': 'ONE_TO_ONE', '1:1': 'ONE_TO_ONE',
            }
            rt['cardinalType'] = mapping.get(str(rt['cardinality']), rt['cardinality'])
        if 'directionality' in rt and 'hasDirection' not in rt:
            rt['hasDirection'] = rt['directionality'] != 'undirected'

    return data


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)

    filepath = sys.argv[1]
    do_fix = '--fix' in sys.argv

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"YAML 解析错误: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"文件不存在: {filepath}")
        sys.exit(1)

    if do_fix:
        data = auto_fix(data)
        fixed_path = filepath.rsplit('.', 1)[0] + '_fixed.yaml'
        with open(fixed_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"已修复并保存到: {fixed_path}")

    validator = SchemaValidator(data, filepath)
    ok = validator.validate()

    if validator.warnings:
        print(f"\n{'─' * 50}")
        print(f"{len(validator.warnings)} 个警告:")
        for w in validator.warnings:
            print(f"  {w}")

    if validator.errors:
        print(f"\n{'─' * 50}")
        print(f"{len(validator.errors)} 个错误:")
        for e in validator.errors:
            print(f"  {e}")
        print(f"\n校验失败！请修复上述错误后重试。")
        sys.exit(1)
    else:
        et_count = len(data.get('entityTypes') or [])
        rt_count = len(data.get('relationTypes') or [])
        print(f"\n{'─' * 50}")
        print(f"校验通过！{et_count} 个实体类型，{rt_count} 个关系类型")
        if validator.warnings:
            print(f"   （{len(validator.warnings)} 个警告，建议修复但不阻塞导入）")
        sys.exit(0)


if __name__ == '__main__':
    main()
