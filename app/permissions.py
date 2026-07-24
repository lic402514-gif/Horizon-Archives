"""
RBAC permissions registry — all permission codes defined in the PRD.
Format: "resource.action"
"""

PERMISSIONS = {
    # ── Book ──
    "book.read":              "浏览图书",
    "book.create":            "新增图书",
    "book.update":            "编辑图书元数据",
    "book.delete":            "删除图书",
    "book.import":            "批量 JSON 导入",
    "book.export":            "CSV 导出",
    "book.batch_update":      "批量修改",
    "book.manage_metadata":   "管理元数据（标签/分类/作者/出版社）",
    "book.publish":           "发布站点",

    # ── File / OSS ──
    "oss.upload":             "上传文件（EPUB/PDF/Cover/OCR/附件）",
    "oss.delete":             "删除 OSS 文件",
    "oss.read":               "查看 OSS 使用情况",

    # ── User ──
    "user.read":              "查看用户",
    "user.create":            "创建账号",
    "user.update":            "编辑账号（昵称/邮箱）",
    "user.delete":            "删除账号",
    "user.disable":           "封禁/启用账号",
    "user.reset_password":    "重置密码",
    "user.assign_role":       "分配角色",

    # ── Role & Permission ──
    "role.read":              "查看角色",
    "role.create":            "创建角色",
    "role.update":            "编辑角色",
    "role.delete":            "删除角色",
    "permission.assign":      "分配权限",

    # ── Audit ──
    "audit.review":           "审核待发布资源",
    "audit.publish":          "发布审核通过资源",
    "audit.reject":           "驳回资源",
    "audit.history":          "查看审核历史",

    # ── System ──
    "system.config":          "修改系统配置",
    "system.log.read":        "查看操作日志",
    "system.stats":           "查看统计面板",
}

# ── Default role → permission mappings ──────────────────────────────────────
ROLE_PERMISSIONS = {
    "Super Admin": list(PERMISSIONS.keys()),  # all permissions

    "Library Admin": [
        "book.read", "book.create", "book.update", "book.delete",
        "book.import", "book.export", "book.batch_update",
        "book.manage_metadata", "book.publish",
        "oss.upload", "oss.delete", "oss.read",
        "system.stats",
    ],

    "Account Admin": [
        "user.read", "user.create", "user.update", "user.delete",
        "user.disable", "user.reset_password", "user.assign_role",
        "role.read",
    ],

    "Auditor": [
        "book.read",
        "audit.review", "audit.publish", "audit.reject", "audit.history",
    ],

    "Member": [
        "book.read",
    ],
}
