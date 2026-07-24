"""
Seed data script — populates the database with sample CLC categories,
a few authors, publishers, and books for development and testing.

Usage:  python seed_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, init_db
from app.models import Category, Author, Publisher, Tag, Book, User
from app.auth import hash_password


def seed():
    init_db()
    db = SessionLocal()

    try:
        # ── CLC Categories (中图法简表 — top 2 levels) ─────────────────────
        categories = [
            # Parent categories
            ("A", "马克思主义、列宁主义、毛泽东思想、邓小平理论", None),
            ("B", "哲学、宗教", None),
            ("C", "社会科学总论", None),
            ("D", "政治、法律", None),
            ("E", "军事", None),
            ("F", "经济", None),
            ("G", "文化、科学、教育、体育", None),
            ("H", "语言、文字", None),
            ("I", "文学", None),
            ("J", "艺术", None),
            ("K", "历史、地理", None),
            ("N", "自然科学总论", None),
            ("O", "数理科学和化学", None),
            ("P", "天文学、地球科学", None),
            ("Q", "生物科学", None),
            ("R", "医药、卫生", None),
            ("S", "农业科学", None),
            ("T", "工业技术", None),
            ("U", "交通运输", None),
            ("V", "航空、航天", None),
            ("X", "环境科学、安全科学", None),
            ("Z", "综合性图书", None),
            # A sub-categories
            ("A1", "马克思、恩格斯著作", "A"),
            ("A2", "列宁著作", "A"),
            ("A3", "斯大林著作", "A"),
            ("A4", "毛泽东著作", "A"),
            ("A5", "邓小平著作", "A"),
            ("A7", "江泽民著作", "A"),
            ("A8", "马克思主义、列宁主义、毛泽东思想、邓小平理论的学习和研究", "A"),
            ("A81", "马克思主义的学习和研究", "A8"),
            ("A82", "列宁主义的学习和研究", "A8"),
            ("A84", "毛泽东思想的学习和研究", "A8"),
            # B sub-categories
            ("B0", "哲学理论", "B"),
            ("B1", "世界哲学", "B"),
            ("B2", "中国哲学", "B"),
            ("B5", "欧洲哲学", "B"),
            ("B9", "宗教", "B"),
            # I sub-categories
            ("I0", "文学理论", "I"),
            ("I1", "世界文学", "I"),
            ("I2", "中国文学", "I"),
            ("I24", "小说", "I2"),
            ("I25", "报告文学", "I2"),
            ("I26", "散文", "I2"),
            ("I27", "民间文学", "I2"),
            # K sub-categories
            ("K0", "史学理论", "K"),
            ("K1", "世界史", "K"),
            ("K2", "中国史", "K"),
            ("K3", "亚洲史", "K"),
            ("K5", "欧洲史", "K"),
            # T sub-categories
            ("TP", "自动化技术、计算机技术", "T"),
            ("TP3", "计算技术、计算机技术", "TP"),
            ("TP31", "计算机软件", "TP3"),
        ]

        for code, name, parent in categories:
            existing = db.query(Category).filter(Category.code == code).first()
            if not existing:
                db.add(Category(code=code, name=name, parent_code=parent))

        # ── Authors ─────────────────────────────────────────────────────────
        authors_data = [
            ("马克思 (Karl Marx)", "德国哲学家、经济学家，马克思主义创始人"),
            ("恩格斯 (Friedrich Engels)", "德国哲学家，马克思主义创始人之一"),
            ("毛泽东", "中国伟大的无产阶级革命家、战略家和理论家"),
            ("鲁迅", "中国现代文学的奠基人"),
            ("钱钟书", "中国现代作家、文学研究家"),
            ("费孝通", "中国社会学家、人类学家"),
        ]
        author_map = {}
        for name, bio in authors_data:
            existing = db.query(Author).filter(Author.name == name).first()
            if not existing:
                author = Author(name=name, bio=bio)
                db.add(author)
                db.flush()
                author_map[name] = author
            else:
                author_map[name] = existing

        # ── Publishers ──────────────────────────────────────────────────────
        publishers_data = [
            ("人民出版社", "北京"),
            ("商务印书馆", "北京"),
            ("中华书局", "北京"),
            ("三联书店", "北京"),
            ("人民文学出版社", "北京"),
        ]
        pub_map = {}
        for name, addr in publishers_data:
            existing = db.query(Publisher).filter(Publisher.name == name).first()
            if not existing:
                pub = Publisher(name=name, address=addr)
                db.add(pub)
                db.flush()
                pub_map[name] = pub
            else:
                pub_map[name] = existing

        # ── Tags ────────────────────────────────────────────────────────────
        tag_names = ["马克思主义", "历史唯物主义", "哲学", "经济学", "社会学", "中国文学", "经典"]
        tag_map = {}
        for tname in tag_names:
            existing = db.query(Tag).filter(Tag.name == tname).first()
            if not existing:
                tag = Tag(name=tname)
                db.add(tag)
                db.flush()
                tag_map[tname] = tag
            else:
                tag_map[tname] = existing

        # ── Books ───────────────────────────────────────────────────────────
        books_data = [
            {
                "title": "德意志意识形态",
                "author": "马克思 (Karl Marx)",
                "publisher": "人民出版社",
                "isbn": "9787010000001",
                "pub_year": 1960,
                "category_code": "A81",
                "summary": "《德意志意识形态》是马克思和恩格斯于1845-1846年合著的哲学著作，系统阐述了历史唯物主义的基本原理。",
                "tags": ["马克思主义", "历史唯物主义", "哲学"],
            },
            {
                "title": "资本论（第一卷）",
                "author": "马克思 (Karl Marx)",
                "publisher": "人民出版社",
                "isbn": "9787010000002",
                "pub_year": 2004,
                "category_code": "A81",
                "summary": "《资本论》是马克思毕生研究政治经济学的伟大成果，揭示了资本主义生产方式的运动规律。",
                "tags": ["马克思主义", "经济学"],
            },
            {
                "title": "自然辩证法",
                "author": "恩格斯 (Friedrich Engels)",
                "publisher": "人民出版社",
                "isbn": "9787010000003",
                "pub_year": 1971,
                "category_code": "A81",
                "summary": "恩格斯晚年未完成的重要著作，系统阐述了辩证唯物主义自然观。",
                "tags": ["马克思主义", "哲学"],
            },
            {
                "title": "毛泽东选集（第一卷）",
                "author": "毛泽东",
                "publisher": "人民出版社",
                "isbn": "9787010000004",
                "pub_year": 1991,
                "category_code": "A4",
                "summary": "收录了毛泽东同志在中国革命各个时期的重要著作。",
                "tags": ["马克思主义", "经典"],
            },
            {
                "title": "呐喊",
                "author": "鲁迅",
                "publisher": "人民文学出版社",
                "isbn": "9787020000005",
                "pub_year": 2006,
                "category_code": "I24",
                "summary": "鲁迅的第一部短篇小说集，收录《狂人日记》《阿Q正传》等经典作品。",
                "tags": ["中国文学", "经典"],
            },
            {
                "title": "围城",
                "author": "钱钟书",
                "publisher": "人民文学出版社",
                "isbn": "9787020000006",
                "pub_year": 1991,
                "category_code": "I24",
                "summary": "钱钟书唯一一部长篇小说，被誉为'新儒林外史'，是中国现代文学经典。",
                "tags": ["中国文学", "经典"],
            },
            {
                "title": "乡土中国",
                "author": "费孝通",
                "publisher": "三联书店",
                "isbn": "9787108000007",
                "pub_year": 2013,
                "category_code": "C",
                "summary": "费孝通的社会学经典之作，深入分析了中国乡土社会的结构与文化特征。",
                "tags": ["社会学"],
            },
        ]

        for bd in books_data:
            existing = db.query(Book).filter(Book.title == bd["title"]).first()
            if not existing:
                book = Book(
                    title=bd["title"],
                    author_id=author_map[bd["author"]].id,
                    publisher_id=pub_map[bd["publisher"]].id,
                    isbn=bd["isbn"],
                    pub_year=bd["pub_year"],
                    category_code=bd["category_code"],
                    summary=bd["summary"],
                    status="published",
                )
                book.tags = [tag_map[t] for t in bd["tags"]]
                db.add(book)

        # ── Admin user (must exist before RBAC role assignment) ────────────
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                password_hash=hash_password("admin123"),
                email="admin@library.local",
                role="admin",
                status="ACTIVE",
            )
            db.add(admin_user)
            db.flush()

        # ── Test users ──────────────────────────────────────────────────────
        test_users = [
            ("alice", "alice123", "alice@example.com", "user", "ACTIVE"),
            ("bob", "bob123", "bob@example.com", "user", "ACTIVE"),
            ("charlie", "charlie123", "charlie@example.com", "user", "BANNED"),
        ]
        for uname, pwd, email, role, status in test_users:
            existing = db.query(User).filter(User.username == uname).first()
            if not existing:
                user = User(
                    username=uname,
                    password_hash=hash_password(pwd),
                    email=email,
                    role=role,
                    status=status,
                )
                db.add(user)

        # ── RBAC: Default Roles & Permissions ────────────────────────────
        from app.models import Role, Permission, user_roles, role_permissions

        # Define all permissions
        perm_defs = [
            ("book.read", "浏览图书"),
            ("book.create", "新增/编辑图书"),
            ("book.delete", "删除图书"),
            ("book.import", "批量导入图书"),
            ("book.export", "导出图书"),
            ("book.batch_update", "批量修改图书"),
            ("book.publish", "发布/下架图书"),
            ("book.dedup", "图书去重"),
            ("user.read", "查看用户"),
            ("user.create", "创建/编辑用户"),
            ("user.delete", "删除用户"),
            ("user.disable", "封禁/启封用户"),
            ("user.reset_password", "重置密码"),
            ("user.assign_role", "分配角色"),
            ("oss.upload", "上传文件到OSS"),
            ("oss.delete", "删除OSS文件"),
            ("oss.read", "查看OSS使用情况"),
            ("system.config", "系统配置"),
            ("system.log.read", "查看操作日志"),
            ("role.read", "查看角色权限"),
            ("role.create", "创建/编辑角色"),
            ("role.delete", "删除角色"),
            ("permission.assign", "分配权限"),
            ("article.create", "创建/编辑文章"),
            ("article.publish", "发布文章"),
            ("asset.create", "创建资源"),
            ("asset.delete", "删除资源"),
            ("election.create", "创建/管理选举"),
            ("election.vote", "参与选举投票"),
            ("issue.create", "创建/管理议题"),
            ("issue.read", "查看议题"),
            ("issue.vote", "参与议题投票"),
            ("issue.comment", "评论议题"),
            ("notification.write", "发送通知"),
        ]
        perm_map = {}
        for code, desc in perm_defs:
            existing = db.query(Permission).filter(Permission.code == code).first()
            if not existing:
                p = Permission(code=code, description=desc)
                db.add(p); db.flush()
                perm_map[code] = p
            else:
                perm_map[code] = existing

        # Define roles and their permissions
        role_defs = [
            ("Super Admin", "超级管理员", list(perm_map.keys())),
            ("Library Admin", "图书管理员", [
                "book.read","book.create","book.delete","book.import","book.export",
                "book.batch_update","oss.upload","oss.delete","oss.read",
            ]),
            ("Account Admin", "账号管理员", [
                "user.read","user.create","user.delete","user.disable",
                "user.reset_password","user.assign_role","role.read",
            ]),
            ("Member", "普通会员", []),
        ]
        for name, desc, perm_codes in role_defs:
            existing = db.query(Role).filter(Role.name == name).first()
            if not existing:
                role = Role(name=name, display_name=desc)
                db.add(role); db.flush()
                for code in perm_codes:
                    if code in perm_map:
                        db.execute(role_permissions.insert().values(role_id=role.id, permission_id=perm_map[code].id))
                # Assign Super Admin role to admin user
                if name == "Super Admin":
                    admin_user = db.query(User).filter(User.username == "admin").first()
                    if admin_user:
                        db.execute(user_roles.insert().values(user_id=admin_user.id, role_id=role.id))
                # Assign Member role to test users
                if name == "Member":
                    for uname in ["alice", "bob"]:
                        u = db.query(User).filter(User.username == uname).first()
                        if u:
                                db.execute(user_roles.insert().values(user_id=u.id, role_id=role.id))

        db.commit()

        print(f"  Roles: {db.query(Role).count()}")
        print(f"  Permissions: {db.query(Permission).count()}")
        print("✓ Seed data inserted successfully!")
        print(f"  Categories: {db.query(Category).count()}")
        print(f"  Authors: {db.query(Author).count()}")
        print(f"  Publishers: {db.query(Publisher).count()}")
        print(f"  Tags: {db.query(Tag).count()}")
        print(f"  Books: {db.query(Book).count()}")
        print(f"  Users: {db.query(User).count()}")
        print(f"\n  Admin: admin / admin123")
        print(f"  Test users: alice/alice123, bob/bob123, charlie/charlie123 (banned)")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
