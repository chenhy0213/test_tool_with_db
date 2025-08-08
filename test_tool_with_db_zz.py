#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于PySide6的数据库查询工具
支持MySQL数据库连接和查询执行

功能说明：
1. 读取配置文件并动态生成查询界面
2. 支持MySQL数据库连接
3. 支持多种输入类型：文本、数字、日期、下拉选择
4. 提供查询结果展示区域
5. 支持配置文件的实时编辑和刷新
6. 完整的数据库连接异常处理
7. 支持{{字段名}}占位符替换
8. 支持搜索过滤执行项（新增功能）
9. 支持界面配置（新增功能）
"""

import sys
import json
import os
import re
from datetime import datetime, date
from typing import Dict, List, Any, Optional

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLineEdit, QTextEdit, 
                               QLabel, QGroupBox, QScrollArea, QDateEdit, 
                               QSpinBox, QDoubleSpinBox, QMessageBox, QComboBox,
                               QDialog, QDialogButtonBox, QPlainTextEdit, 
                               QTabWidget, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QSplitter, QCheckBox, QFormLayout,
                               QStackedWidget, QListWidget, QListWidgetItem,
                               QToolButton, QMenu, QInputDialog, QFileDialog)
from PySide6.QtCore import Qt, QDate, QTimer, QItemSelectionModel
from PySide6.QtGui import QFont, QAction, QIcon

# 数据库连接相关
try:
    import pymysql
    import pymysql.cursors
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    QMessageBox.warning(None, "警告", "未安装pymysql库，数据库功能将不可用\n请运行: pip install pymysql")


class SmartConfigDialog(QDialog):
    """界面配置管理对话框"""
    
    def __init__(self, config_path, parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self.config = None
        self.current_query_index = -1
        self.current_field_index = -1
        
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        """初始化对话框界面"""
        self.setWindowTitle("界面配置管理")
        self.setGeometry(100, 100, 1200, 800)
        
        layout = QVBoxLayout(self)
        
        # 创建主分割器
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：查询列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 查询列表工具栏
        query_toolbar = QHBoxLayout()
        
        add_query_btn = QPushButton("➕ 新增查询")
        add_query_btn.clicked.connect(self.add_new_query)
        
        remove_query_btn = QPushButton("➖ 删除查询")
        remove_query_btn.clicked.connect(self.remove_current_query)
        
        query_toolbar.addWidget(add_query_btn)
        query_toolbar.addWidget(remove_query_btn)
        query_toolbar.addStretch()
        
        left_layout.addLayout(query_toolbar)
        
        # 查询列表
        self.query_list = QListWidget()
        self.query_list.currentRowChanged.connect(self.on_query_selection_changed)
        left_layout.addWidget(self.query_list)
        
        # 右侧：配置编辑区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 创建标签页
        self.tab_widget = QTabWidget()

        # 查询配置页
        self.create_query_config_tab()

        # 字段配置页
        self.create_fields_tab()

        # 数据库配置页
        self.create_database_tab()
        
        right_layout.addWidget(self.tab_widget)
        
        # 按钮区域
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        
        # 修改按钮文本
        save_btn = button_box.button(QDialogButtonBox.Save)
        save_btn.setText("保存并关闭")
        
        cancel_btn = button_box.button(QDialogButtonBox.Cancel)
        cancel_btn.setText("取消")
        
        apply_btn = button_box.button(QDialogButtonBox.Apply)
        apply_btn.setText("应用")
        
        button_box.accepted.connect(self.save_and_close)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_changes)
        right_layout.addWidget(button_box)
        
        # 添加到分割器
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 3)
        
        layout.addWidget(main_splitter)
        
    def create_database_tab(self):
        """创建数据库配置标签页"""
        db_widget = QWidget()
        db_layout = QFormLayout(db_widget)
        
        # 数据库配置输入
        self.db_host = QLineEdit()
        self.db_port = QSpinBox()
        self.db_port.setRange(1, 65535)
        self.db_port.setValue(3306)
        
        self.db_username = QLineEdit()
        self.db_password = QLineEdit()
        self.db_password.setEchoMode(QLineEdit.Password)
        
        self.db_database = QLineEdit()
        
        db_layout.addRow("主机地址:", self.db_host)
        db_layout.addRow("端口:", self.db_port)
        db_layout.addRow("用户名:", self.db_username)
        db_layout.addRow("密码:", self.db_password)
        db_layout.addRow("数据库名:", self.db_database)
        
        self.tab_widget.addTab(db_widget, "🏠 数据库配置")
        
    def create_query_config_tab(self):
        """创建查询配置标签页"""
        query_widget = QWidget()
        query_layout = QVBoxLayout(query_widget)
        
        # 基本信息
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout(basic_group)
        
        self.query_name = QLineEdit()
        self.query_description = QTextEdit()
        self.query_description.setMaximumHeight(80)
        self.query_bubble_description = QTextEdit()
        self.query_bubble_description.setMaximumHeight(80)
        
        basic_layout.addRow("查询名称:", self.query_name)
        basic_layout.addRow("查询描述:", self.query_description)
        basic_layout.addRow("气泡描述:", self.query_bubble_description)
        
        # SQL配置
        sql_group = QGroupBox("SQL语句")
        sql_layout = QVBoxLayout(sql_group)
        
        sql_toolbar = QHBoxLayout()
        
        add_sql_btn = QPushButton("➕ 添加SQL")
        add_sql_btn.clicked.connect(self.add_sql_statement)
        
        clear_sql_btn = QPushButton("🗑️ 清空")
        clear_sql_btn.clicked.connect(self.clear_sql_statements)
        
        sql_toolbar.addWidget(add_sql_btn)
        sql_toolbar.addWidget(clear_sql_btn)
        sql_toolbar.addStretch()
        
        self.sql_text = QTextEdit()
        self.sql_text.setFont(QFont("Consolas", 11))
        self.sql_text.setPlaceholderText("输入SQL语句，多条语句用分号分隔，或使用占位符如 {{字段名}}")
        
        sql_layout.addLayout(sql_toolbar)
        sql_layout.addWidget(self.sql_text)
        
        query_layout.addWidget(basic_group)
        query_layout.addWidget(sql_group)
        
        self.tab_widget.addTab(query_widget, "🔍 查询配置")
        
    def create_fields_tab(self):
        """创建字段配置标签页"""
        fields_widget = QWidget()
        fields_layout = QVBoxLayout(fields_widget)
        
        # 字段工具栏
        fields_toolbar = QHBoxLayout()
        
        add_field_btn = QPushButton("➕ 新增字段")
        add_field_btn.clicked.connect(self.add_new_field)
        
        remove_field_btn = QPushButton("➖ 删除字段")
        remove_field_btn.clicked.connect(self.remove_current_field)
        
        move_up_btn = QPushButton("⬆️ 上移")
        move_up_btn.clicked.connect(self.move_field_up)
        
        move_down_btn = QPushButton("⬇️ 下移")
        move_down_btn.clicked.connect(self.move_field_down)
        
        fields_toolbar.addWidget(add_field_btn)
        fields_toolbar.addWidget(remove_field_btn)
        fields_toolbar.addWidget(move_up_btn)
        fields_toolbar.addWidget(move_down_btn)
        fields_toolbar.addStretch()
        
        # 字段表格
        self.fields_table = QTableWidget()
        self.fields_table.setColumnCount(4)
        self.fields_table.setHorizontalHeaderLabels(["字段标签", "类型", "占位符", "选项"])
        self.fields_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.fields_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.fields_table.itemChanged.connect(self.on_field_changed)
        
        fields_layout.addLayout(fields_toolbar)
        fields_layout.addWidget(self.fields_table)
        
        self.tab_widget.addTab(fields_widget, "📝 字段配置")
        
    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                
            self.refresh_query_list()
            self.load_database_config()
            
        except Exception as e:
            QMessageBox.warning(self, "警告", f"加载配置文件失败: {str(e)}")
            self.config = self.get_default_config()
            
    def get_default_config(self):
        """获取默认配置"""
        return {
            "database": {
                "host": "localhost",
                "port": 3306,
                "username": "root",
                "password": "",
                "database": "test_db"
            },
            "queries": []
        }
        
    def refresh_query_list(self):
        """刷新查询列表"""
        self.query_list.clear()
        
        if not self.config or 'queries' not in self.config:
            return
            
        for index, query in enumerate(self.config['queries']):
            name = query.get('name', f'查询 {index + 1}')
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, index)
            self.query_list.addItem(item)
            
    def load_database_config(self):
        """加载数据库配置"""
        if not self.config:
            return
            
        db_config = self.config.get('database', {})
        self.db_host.setText(db_config.get('host', 'localhost'))
        self.db_port.setValue(db_config.get('port', 3306))
        self.db_username.setText(db_config.get('username', 'root'))
        self.db_password.setText(db_config.get('password', ''))
        self.db_database.setText(db_config.get('database', ''))
        
    def on_query_selection_changed(self, current_row):
        """查询选择改变时的处理"""
        self.current_query_index = current_row
        
        if current_row >= 0 and self.config and 'queries' in self.config:
            query = self.config['queries'][current_row]
            self.load_query_config(query)
        else:
            self.clear_query_config()
            
    def load_query_config(self, query):
        """加载查询配置到界面"""
        self.query_name.setText(query.get('name', ''))
        self.query_description.setPlainText(query.get('description', ''))
        self.query_bubble_description.setPlainText(query.get('bubble_description', ''))
        
        # 加载SQL语句
        sql = query.get('sql', '')
        if isinstance(sql, list):
            sql_text = ';\n'.join(sql)
        else:
            sql_text = str(sql)
        self.sql_text.setPlainText(sql_text)
        
        # 加载字段配置
        self.load_fields_config(query.get('input_fields', []))
        
    def clear_query_config(self):
        """清空查询配置"""
        self.query_name.clear()
        self.query_description.clear()
        self.query_bubble_description.clear()
        self.sql_text.clear()
        self.fields_table.setRowCount(0)
        
    def load_fields_config(self, fields):
        """加载字段配置到表格"""
        self.fields_table.setRowCount(0)
        
        for field in fields:
            row = self.fields_table.rowCount()
            self.fields_table.insertRow(row)
            
            # 字段标签
            label_item = QTableWidgetItem(field.get('label', ''))
            self.fields_table.setItem(row, 0, label_item)
            
            # 字段类型
            type_item = QTableWidgetItem(field.get('type', 'text'))
            self.fields_table.setItem(row, 1, type_item)
            
            # 占位符
            placeholder_item = QTableWidgetItem(field.get('placeholder', ''))
            self.fields_table.setItem(row, 2, placeholder_item)
            
            # 选项（用于select类型）
            options = field.get('options', [])
            options_text = ','.join(options) if options else ''
            options_item = QTableWidgetItem(options_text)
            self.fields_table.setItem(row, 3, options_item)
            
    def add_new_query(self):
        """添加新查询"""
        if not self.config:
            return
            
        new_query = {
            "name": "新查询",
            "description": "新添加的查询",
            "bubble_description": "请编辑此查询的描述信息",
            "sql": "SELECT * FROM table_name WHERE field = {{字段名}}",
            "input_fields": []
        }
        
        if 'queries' not in self.config:
            self.config['queries'] = []
            
        self.config['queries'].append(new_query)
        self.refresh_query_list()
        
        # 选中新添加的查询
        new_index = len(self.config['queries']) - 1
        self.query_list.setCurrentRow(new_index)
        
    def remove_current_query(self):
        """删除当前查询"""
        if self.current_query_index >= 0 and self.config and 'queries' in self.config:
            reply = QMessageBox.question(self, "确认删除", 
                                       f"确定要删除查询 '{self.query_name.text()}' 吗？")
            if reply == QMessageBox.Yes:
                del self.config['queries'][self.current_query_index]
                self.refresh_query_list()
                self.clear_query_config()
                
    def add_new_field(self):
        """添加新字段"""
        if self.current_query_index < 0:
            QMessageBox.warning(self, "警告", "请先选择一个查询")
            return
            
        row = self.fields_table.rowCount()
        self.fields_table.insertRow(row)
        
        # 设置默认值
        self.fields_table.setItem(row, 0, QTableWidgetItem("新字段"))
        self.fields_table.setItem(row, 1, QTableWidgetItem("text"))
        self.fields_table.setItem(row, 2, QTableWidgetItem("请输入值"))
        self.fields_table.setItem(row, 3, QTableWidgetItem(""))
        
    def remove_current_field(self):
        """删除当前字段"""
        current_row = self.fields_table.currentRow()
        if current_row >= 0:
            self.fields_table.removeRow(current_row)
            
    def move_field_up(self):
        """上移字段"""
        current_row = self.fields_table.currentRow()
        if current_row > 0:
            self.swap_fields(current_row, current_row - 1)
            self.fields_table.setCurrentCell(current_row - 1, 0)
            
    def move_field_down(self):
        """下移字段"""
        current_row = self.fields_table.currentRow()
        if current_row < self.fields_table.rowCount() - 1:
            self.swap_fields(current_row, current_row + 1)
            self.fields_table.setCurrentCell(current_row + 1, 0)
            
    def swap_fields(self, row1, row2):
        """交换两行字段"""
        for col in range(self.fields_table.columnCount()):
            item1 = self.fields_table.takeItem(row1, col)
            item2 = self.fields_table.takeItem(row2, col)
            self.fields_table.setItem(row1, col, item2)
            self.fields_table.setItem(row2, col, item1)
            
    def on_field_changed(self, item):
        """字段改变时的处理"""
        # 可以在这里添加实时验证
        pass
        
    def add_sql_statement(self):
        """添加SQL语句"""
        current_sql = self.sql_text.toPlainText()
        if current_sql and not current_sql.endswith(';'):
            current_sql += ';\n'
        current_sql += "SELECT * FROM table_name WHERE {{字段名}} = '值'"
        self.sql_text.setPlainText(current_sql)
        
    def clear_sql_statements(self):
        """清空SQL语句"""
        self.sql_text.clear()
        
    def save_config(self):
        """保存配置到文件"""
        try:
            # 更新数据库配置
            if not self.config:
                self.config = self.get_default_config()
                
            self.config['database'] = {
                "host": self.db_host.text(),
                "port": self.db_port.value(),
                "username": self.db_username.text(),
                "password": self.db_password.text(),
                "database": self.db_database.text()
            }
            
            # 更新当前查询配置
            if self.current_query_index >= 0 and 'queries' in self.config:
                query = self.config['queries'][self.current_query_index]
                
                query['name'] = self.query_name.text()
                query['description'] = self.query_description.toPlainText()
                query['bubble_description'] = self.query_bubble_description.toPlainText()
                
                # # 处理SQL语句
                # sql_text = self.sql_text.toPlainText().strip()
                # if '\n' in sql_text or ';' in sql_text:
                #     # 多条SQL语句
                #     sql_statements = [stmt.strip() for stmt in sql_text.split(';') if stmt.strip()]
                #     query['sql'] = sql_statements
                # else:
                #     # 单条SQL语句
                #     query['sql'] = sql_text
                
                # 处理SQL语句 - 始终保存为字符串格式
                sql_text = self.sql_text.toPlainText().strip()
                query['sql'] = sql_text
                
                    
                # 处理字段配置
                fields = []
                for row in range(self.fields_table.rowCount()):
                    field = {
                        "label": self.fields_table.item(row, 0).text() if self.fields_table.item(row, 0) else "",
                        "type": self.fields_table.item(row, 1).text() if self.fields_table.item(row, 1) else "text",
                        "placeholder": self.fields_table.item(row, 2).text() if self.fields_table.item(row, 2) else ""
                    }
                    
                    # 处理选项
                    options_text = self.fields_table.item(row, 3).text() if self.fields_table.item(row, 3) else ""
                    if options_text:
                        field['options'] = [opt.strip() for opt in options_text.split(',') if opt.strip()]
                        
                    fields.append(field)
                    
                query['input_fields'] = fields
            
            # 保存到文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            
            # 添加：更新左侧列表显示
            if self.current_query_index >= 0 and self.current_query_index < self.query_list.count():
                current_item = self.query_list.item(self.current_query_index)
                if current_item:
                    current_item.setText(self.query_name.text())
                
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置文件失败: {str(e)}")
            return False
            
    def apply_changes(self):
        """应用更改但不关闭窗口"""
        if self.save_config():
            QMessageBox.information(self, "成功", "配置已保存！")
            
    def save_and_close(self):
        """保存并关闭窗口"""
        if self.save_config():
            self.accept()


class ConfigEditorDialog(QDialog):
    
    """配置文件编辑对话框（保留原有的文本编辑模式）"""
    
    def __init__(self, config_path, parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self.init_ui()
        self.load_config_content()
        
    def init_ui(self):
        """初始化对话框界面"""
        self.setWindowTitle("编辑配置文件")
        self.setGeometry(200, 200, 800, 600)
        
        layout = QVBoxLayout(self)
        
        # 添加说明标签
        info_label = QLabel("请编辑JSON配置文件，确保格式正确：")
        info_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # 创建文本编辑区域
        self.config_text = QPlainTextEdit()
        self.config_text.setFont(QFont("Consolas", 11))
        self.config_text.setStyleSheet("""
            QPlainTextEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.config_text)
        
        # 创建按钮区域
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.save_config)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def load_config_content(self):
        """加载配置文件内容到编辑区域"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.config_text.setPlainText(content)
        except Exception as e:
            QMessageBox.warning(self, "警告", f"无法加载配置文件: {str(e)}")
            self.config_text.setPlainText("")
            
    def save_config(self):
        """保存编辑后的配置"""
        try:
            # 验证JSON格式
            content = self.config_text.toPlainText()
            json.loads(content)  # 验证JSON格式
            
            # 保存到文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            QMessageBox.information(self, "成功", "配置文件已保存！")
            self.accept()
            
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "错误", f"JSON格式错误:\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败:\n{str(e)}")


class DatabaseConnection:
    """数据库连接管理类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
        
    def connect(self) -> bool:
        """建立数据库连接"""
        try:
            if not DB_AVAILABLE:
                raise ImportError("pymysql库未安装")
                
            db_config = self.config.get('database', {})
            self.connection = pymysql.connect(
                host=db_config.get('host', 'localhost'),
                port=db_config.get('port', 3306),
                user=db_config.get('username', 'root'),
                password=db_config.get('password', ''),
                database=db_config.get('database', 'test'),
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            return True
        except Exception as e:
            return False
            
    def execute_query(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行单条SQL查询并返回结果"""
        if not self.connection:
            raise ConnectionError("数据库未连接")
            
        try:
            with self.connection.cursor() as cursor:   
                # 开始事务
                self.connection.begin() 
                cursor.execute(sql)
                
                # 判断SQL类型
                sql_upper = sql.strip().upper()
                
                if sql_upper.startswith('SELECT'):
                    # SELECT查询返回结果集
                    results = cursor.fetchall()
                    return results if results else []
                elif sql_upper.startswith(('INSERT', 'UPDATE', 'DELETE')):
                    # 增删改操作 - 必须提交事务
                    self.connection.commit()
                    return [{"affected_rows": cursor.rowcount, "success": True}]
                else:
                    # 其他SQL语句 - 也需要提交事务
                    self.connection.commit()
                    return [{"affected_rows": cursor.rowcount, "success": True}]
        except Exception as e:
            # 发生错误时回滚
            if self.connection:
                self.connection.rollback()
            raise e

    def execute_multiple_queries(self, sql_statements: List[str], params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """执行多条SQL语句（事务处理）"""
        if not self.connection:
            raise ConnectionError("数据库未连接")
            
        results = []
        
        try:
            # 开始事务
            self.connection.begin()
            
            with self.connection.cursor() as cursor:
                for index, sql in enumerate(sql_statements):
                    if not sql.strip():  # 跳过空语句
                        continue
                        
                    # 替换占位符
                    processed_sql = sql
                    if params:
                        for key, value in params.items():
                            placeholder = f"{{{{{key}}}}}"
                            processed_sql = processed_sql.replace(placeholder, str(value))
                    
                    # 执行SQL
                    cursor.execute(processed_sql)
                    
                    # 判断SQL类型
                    sql_upper = processed_sql.strip().upper()
                    
                    if sql_upper.startswith('SELECT'):
                        # SELECT查询返回结果集
                        query_results = cursor.fetchall()
                        results.append({
                            "statement_index": index + 1,
                            "sql": processed_sql,
                            "type": "SELECT",
                            "results": query_results if query_results else [],
                            "row_count": len(query_results) if query_results else 0
                        })
                    else:
                        # 增删改操作
                        affected_rows = cursor.rowcount
                        results.append({
                            "statement_index": index + 1,
                            "sql": processed_sql,
                            "type": "MODIFY",
                            "affected_rows": affected_rows,
                            "success": True
                        })
                
                # 提交事务
                self.connection.commit()
                return results
                
        except Exception as e:
            # 回滚事务
            if self.connection:
                self.connection.rollback()
            raise e
            
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None


class DatabaseTool(QMainWindow):
    """数据库查询工具主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.config = None
        self.input_widgets = {}
        self.query_groups = []
        self.all_query_groups = []  # 存储所有查询组，用于搜索过滤
        self.db_connection = None
        self.search_timer = QTimer()  # 搜索延迟定时器
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        
        # 初始化界面
        self.init_ui()
        self.load_config()
        self.create_ui_from_config()
        self.create_menu_bar()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("数据库查询工具")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧：查询输入区域
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 添加搜索框
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 10)
        
        search_label = QLabel("🔍 搜索:")
        search_label.setStyleSheet("font-weight: bold;")
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索执行项（支持名称、描述模糊搜索）...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
        """)
        
        # 搜索统计标签
        self.search_stats_label = QLabel("")
        self.search_stats_label.setStyleSheet("color: #666; font-size: 12px; margin-left: 10px;")
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.search_stats_label)
        
        left_layout.addWidget(search_container)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumWidth(500)
        
        # 创建滚动内容区域
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        scroll_area.setWidget(self.scroll_content)
        
        left_layout.addWidget(QLabel("执行配置"))
        left_layout.addWidget(scroll_area)
        
        # 右侧：结果显示区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.result_text = QTextEdit()
        self.result_text.setFont(QFont("Consolas", 10))
        self.result_text.setMinimumWidth(600)
        self.result_text.setReadOnly(False)
        
        # 添加连接状态标签
        self.connection_status = QLabel("数据库状态: 未连接")
        self.connection_status.setStyleSheet("color: red; font-weight: bold;")
        
        # 添加连接按钮
        connect_btn = QPushButton("🔗 连接数据库")
        connect_btn.clicked.connect(self.connect_database)
        
        clear_btn = QPushButton("清除结果")
        clear_btn.clicked.connect(self.clear_results)
        
        right_layout.addWidget(QLabel("查询结果"))
        right_layout.addWidget(self.connection_status)
        right_layout.addWidget(self.result_text)
        right_layout.addWidget(connect_btn)
        right_layout.addWidget(clear_btn)
        
        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(right_widget, 1)
        
    def on_search_text_changed(self):
        """搜索文本改变时的处理"""
        # 使用定时器延迟搜索，避免频繁触发
        self.search_timer.stop()
        self.search_timer.start(300)  # 300ms延迟
        
    def perform_search(self):
        """执行搜索过滤"""
        search_text = self.search_input.text().strip().lower()
        
        if not search_text:
            # 如果搜索框为空，显示所有项
            self.show_all_groups()
            self.update_search_stats(len(self.all_query_groups), len(self.all_query_groups))
            return
        
        visible_count = 0
        total_count = len(self.all_query_groups)
        
        # 遍历所有查询组进行过滤
        for group_info in self.all_query_groups:
            group_box = group_info['group_box']
            query_config = group_info['query_config']
            
            # 检查是否匹配搜索条件
            is_match = self.is_query_match(query_config, search_text)
            
            # 显示或隐藏查询组
            group_box.setVisible(is_match)
            if is_match:
                visible_count += 1
        
        # 更新搜索统计
        self.update_search_stats(visible_count, total_count)
        
    def is_query_match(self, query_config: Dict[str, Any], search_text: str) -> bool:
        """检查查询配置是否匹配搜索条件"""
        # 搜索查询名称
        name = query_config.get('name', '').lower()
        if search_text in name:
            return True
        
        # 搜索查询描述
        description = query_config.get('description', '').lower()
        if search_text in description:
            return True
        
        # 搜索气泡描述
        bubble_description = query_config.get('bubble_description', '').lower()
        if search_text in bubble_description:
            return True
        
        # 搜索输入字段标签
        input_fields = query_config.get('input_fields', [])
        for field in input_fields:
            field_label = field.get('label', '').lower()
            if search_text in field_label:
                return True
        
        # 搜索SQL语句
        sql = query_config.get('sql', '')
        if isinstance(sql, str):
            if search_text in sql.lower():
                return True
        elif isinstance(sql, list):
            for sql_stmt in sql:
                if search_text in sql_stmt.lower():
                    return True
        
        return False
        
    def show_all_groups(self):
        """显示所有查询组"""
        for group_info in self.all_query_groups:
            group_info['group_box'].setVisible(True)
            
    def update_search_stats(self, visible_count: int, total_count: int):
        """更新搜索统计信息"""
        if visible_count == total_count:
            self.search_stats_label.setText(f"共 {total_count} 项")
        else:
            self.search_stats_label.setText(f"显示 {visible_count} / {total_count} 项")
            
        # 根据搜索结果设置不同颜色
        if visible_count == 0 and total_count > 0:
            self.search_stats_label.setStyleSheet("color: #d13438; font-size: 12px; margin-left: 10px;")
        elif visible_count < total_count:
            self.search_stats_label.setStyleSheet("color: #ff8c00; font-size: 12px; margin-left: 10px;")
        else:
            self.search_stats_label.setStyleSheet("color: #666; font-size: 12px; margin-left: 10px;")
        
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件(&F)')
        
        # 界面配置动作（新增）
        smart_config_action = QAction('界面配置', self)
        smart_config_action.setShortcut('Ctrl+Shift+C')
        smart_config_action.setStatusTip('使用可视化界面配置查询')
        smart_config_action.triggered.connect(self.open_smart_config)
        file_menu.addAction(smart_config_action)
        
        # 编辑配置动作（原有的文本编辑模式）
        edit_config_action = QAction('编辑配置', self)
        edit_config_action.setShortcut('Ctrl+E')
        edit_config_action.setStatusTip('编辑配置文件（文本模式）')
        edit_config_action.triggered.connect(self.edit_config)
        file_menu.addAction(edit_config_action)
        
        file_menu.addSeparator()
        
        # 连接数据库动作
        connect_action = QAction('连接数据库', self)
        connect_action.setShortcut('Ctrl+D')
        connect_action.setStatusTip('连接数据库')
        connect_action.triggered.connect(self.connect_database)
        file_menu.addAction(connect_action)
        
        # 刷新配置动作
        refresh_action = QAction('刷新配置', self)
        refresh_action.setShortcut('F5')
        refresh_action.setStatusTip('重新加载配置文件')
        refresh_action.triggered.connect(self.refresh_config)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        # 退出动作
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 查看菜单
        view_menu = menubar.addMenu('查看(&V)')
        
        # 清空搜索动作
        clear_search_action = QAction('清空搜索', self)
        clear_search_action.setShortcut('Ctrl+L')
        clear_search_action.setStatusTip('清空搜索框并显示所有项')
        clear_search_action.triggered.connect(self.clear_search)
        view_menu.addAction(clear_search_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助(&H)')
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def clear_search(self):
        """清空搜索框"""
        self.search_input.clear()
        self.show_all_groups()
        self.update_search_stats(len(self.all_query_groups), len(self.all_query_groups))
        
    def get_config_path(self):
        """获取配置文件路径（支持打包和开发环境）"""
        if getattr(sys, 'frozen', False):
            # 如果是打包后的exe
            application_path = os.path.dirname(sys.executable)
        else:
            # 如果是Python脚本
            application_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(application_path, 'config.json')
        
    def load_config(self):
        """加载配置文件"""
        config_path = self.get_config_path()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            self.append_result("✅ 配置文件加载成功")
            self.append_result(f"📁 配置文件路径: {config_path}")
            self.append_result(f"🔍 查询数量: {len(self.config.get('queries', []))}")
            
            # 显示数据库配置
            db_config = self.config.get('database', {})
            self.append_result(f"🗄️ 数据库配置: {db_config.get('host', 'localhost')}:{db_config.get('port', 3306)}")
            
            # 保存配置路径供后续使用
            self.config_path = config_path
            
        except FileNotFoundError:
            error_msg = f"配置文件不存在: {config_path}"
            QMessageBox.critical(self, "错误", error_msg)
            self.config = self.get_default_config()
            self.config_path = config_path
            self.append_result(f"⚠️ {error_msg}，使用默认配置")
        except json.JSONDecodeError as e:
            error_msg = f"配置文件格式错误: {e}"
            QMessageBox.critical(self, "错误", error_msg)
            self.config = self.get_default_config()
            self.config_path = config_path
            self.append_result(f"⚠️ {error_msg}，使用默认配置")
        except Exception as e:
            error_msg = f"加载配置文件失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            self.config = self.get_default_config()
            self.config_path = config_path
            self.append_result(f"⚠️ {error_msg}，使用默认配置")
            
    def get_default_config(self):
        """获取默认配置"""
        return {
            "database": {
                "host": "localhost",
                "port": 3306,
                "username": "root",
                "password": "password",
                "database": "test_db"
            },
            "queries": []
        }
        
    def connect_database(self):
        """连接数据库"""
        try:
            if not DB_AVAILABLE:
                QMessageBox.warning(self, "警告", "请先安装pymysql库：\npip install pymysql")
                return
                
            if self.db_connection:
                self.db_connection.close()
                
            self.db_connection = DatabaseConnection(self.config)
            
            if self.db_connection.connect():
                self.connection_status.setText("数据库状态: 已连接")
                self.connection_status.setStyleSheet("color: green; font-weight: bold;")
                self.append_result("✅ 数据库连接成功")
                QMessageBox.information(self, "成功", "数据库连接成功！")
            else:
                self.connection_status.setText("数据库状态: 连接失败")
                self.connection_status.setStyleSheet("color: red; font-weight: bold;")
                self.append_result("❌ 数据库连接失败")
                QMessageBox.critical(self, "连接失败", "无法连接到数据库，请检查配置")
                
        except Exception as e:
            error_msg = f"数据库连接错误: {str(e)}"
            self.connection_status.setText("数据库状态: 连接错误")
            self.connection_status.setStyleSheet("color: red; font-weight: bold;")
            self.append_result(f"❌ {error_msg}")
            QMessageBox.critical(self, "连接错误", error_msg)
            
    def create_ui_from_config(self):
        """根据配置文件创建UI界面"""
        if not self.config or 'queries' not in self.config:
            self.append_result("⚠️ 配置文件中未找到查询配置")
            return
            
        self.append_result("🔄 开始创建查询界面...")
        
        # 清空现有的查询组
        self.query_groups.clear()
        self.all_query_groups.clear()
        
        for index, query_config in enumerate(self.config['queries']):
            self.append_result(f"📋 创建查询 {index + 1}: {query_config.get('name', '未命名')}")
            self.create_query_group(query_config)
            
        self.scroll_layout.addStretch()
        self.append_result("✅ 查询界面创建完成")
        
        # 更新搜索统计
        self.update_search_stats(len(self.all_query_groups), len(self.all_query_groups))
        
    def create_query_group(self, query_config: Dict[str, Any]):
        """创建单个查询组"""
        # 创建分组框
        group_box = QGroupBox(query_config.get('name', '未命名查询'))
        group_layout = QVBoxLayout(group_box)
        
        # 添加查询描述
        if 'description' in query_config:
            desc_label = QLabel(query_config['description'])
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #666; font-size: 12px; margin-bottom: 5px;")
            group_layout.addWidget(desc_label)
        
        # 添加气泡描述（如果存在）
        if 'bubble_description' in query_config:
            group_box.setToolTip(query_config['bubble_description'])
            if 'description' in query_config:
                desc_label.setToolTip(query_config['bubble_description'])
        
        # 创建输入字段
        input_widgets = {}
        if 'input_fields' in query_config and query_config['input_fields']:
            for field_config in query_config['input_fields']:
                field_widget = self.create_input_field(field_config)
                if field_widget:
                    # 获取实际的输入控件（跳过容器）
                    actual_widget = field_widget.findChild(QLineEdit) or field_widget.findChild(QSpinBox) or \
                                   field_widget.findChild(QDoubleSpinBox) or field_widget.findChild(QDateEdit) or \
                                   field_widget.findChild(QComboBox)
                    if actual_widget:
                        input_widgets[field_config['label']] = actual_widget
                    else:
                        input_widgets[field_config['label']] = field_widget
                    group_layout.addWidget(field_widget)
        
        # 添加SQL预览
        sql_group = QWidget()
        sql_layout = QVBoxLayout(sql_group)
        sql_layout.setContentsMargins(0, 5, 0, 5)
        
        sql_label = QLabel("SQL语句:")
        sql_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        sql_layout.addWidget(sql_label)
        
        sql_preview = QTextEdit()
        sql_preview.setPlainText(query_config.get('sql', ''))
        sql_preview.setMaximumHeight(80)
        sql_preview.setReadOnly(True)
        sql_preview.setStyleSheet("""
            background-color: #f5f5f5;
            font-family: Consolas;
            font-size: 11px;
            border: 1px solid #ddd;
            border-radius: 3px;
        """)
        sql_layout.addWidget(sql_preview)
        group_layout.addWidget(sql_group)
        
        # 创建执行按钮
        execute_btn = QPushButton("🔍 执行查询")
        execute_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        execute_btn.clicked.connect(
            lambda: self.execute_query(query_config, input_widgets)
        )
        
        group_layout.addWidget(execute_btn)
        
        self.scroll_layout.addWidget(group_box)
        
        # 创建查询组信息
        group_info = {
            'group_box': group_box,
            'query_config': query_config,
            'input_widgets': input_widgets
        }
        
        self.query_groups.append(group_info)
        self.all_query_groups.append(group_info)
        
    def create_input_field(self, field_config: Dict[str, str]) -> QWidget:
        """创建单个输入字段"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 2, 0, 2)
        
        label = QLabel(field_config['label'] + ":")
        label.setMinimumWidth(80)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(label)
        
        input_type = field_config.get('type', 'text')
        
        if input_type == 'text':
            widget = QLineEdit()
            widget.setPlaceholderText(field_config.get('placeholder', ''))
            widget.setClearButtonEnabled(True)
            
        elif input_type == 'number':
            widget = QSpinBox()
            widget.setMaximum(999999)
            widget.setMinimum(-999999)
            widget.setButtonSymbols(QSpinBox.NoButtons)
            
        elif input_type == 'float':
            widget = QDoubleSpinBox()
            widget.setMaximum(999999.99)
            widget.setMinimum(-999999.99)
            widget.setDecimals(2)
            widget.setButtonSymbols(QDoubleSpinBox.NoButtons)
            
        elif input_type == 'date':
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDate(QDate.currentDate())
            widget.setDisplayFormat("yyyy-MM-dd")
            
        elif input_type == 'select':
            widget = QComboBox()
            if 'options' in field_config:
                widget.addItems(field_config['options'])
            else:
                widget.addItems(["选项1", "选项2", "选项3"])
                
        else:
            widget = QLineEdit()
            widget.setPlaceholderText(field_config.get('placeholder', ''))
        
        layout.addWidget(widget)
        return container
        
    def execute_query(self, query_config: Dict[str, Any], input_widgets: Dict[str, QWidget]):
        """执行查询（支持单条或多条SQL语句）"""
        try:
            if not self.db_connection:
                QMessageBox.warning(self, "警告", "请先连接数据库！")
                return
                
            if not self.db_connection.connection:
                QMessageBox.warning(self, "警告", "数据库连接已断开，请重新连接！")
                return
                
            # 收集输入参数
            values = {}
            
            # 按照input_fields的顺序收集参数
            if 'input_fields' in query_config:
                for field_config in query_config['input_fields']:
                    label = field_config['label']
                    if label in input_widgets:
                        widget = input_widgets[label]
                        
                        if isinstance(widget, QLineEdit):
                            value = widget.text().strip()
                            values[label] = value
                        elif isinstance(widget, QSpinBox):
                            value = widget.value()
                            values[label] = value
                        elif isinstance(widget, QDoubleSpinBox):
                            value = widget.value()
                            values[label] = value
                        elif isinstance(widget, QDateEdit):
                            value = widget.date().toString("yyyy-MM-dd")
                            values[label] = value
                        elif isinstance(widget, QComboBox):
                            value = widget.currentText()
                            values[label] = value

            # 获取SQL语句
            original_sql = query_config.get('sql', '')
            
            # 检测是否为多条SQL语句
            sql_statements = []
            if isinstance(original_sql, str):
                # 按分号分割SQL语句
                statements = [stmt.strip() for stmt in original_sql.split(';') if stmt.strip()]
                sql_statements = statements
            elif isinstance(original_sql, list):
                # 支持配置为SQL语句列表
                sql_statements = original_sql
            else:
                sql_statements = [str(original_sql)]

            # 替换所有{{字段名}}占位符
            processed_statements = []
            for sql in sql_statements:
                processed_sql = sql
                for label, value in values.items():
                    placeholder = f"{{{{{label}}}}}"
                    processed_sql = processed_sql.replace(placeholder, str(value))
                processed_statements.append(processed_sql)

            # 显示执行信息
            self.append_result("=" * 60)
            self.append_result(f"🔍 执行查询: {query_config.get('name', '未命名')}")
            self.append_result(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            if values:
                self.append_result("📊 输入参数:")
                self.append_result(json.dumps(values, ensure_ascii=False, indent=2, default=self.serialize_datetime))
            
            if len(processed_statements) > 1:
                self.append_result(f"📝 执行 {len(processed_statements)} 条SQL语句:")
                for i, sql in enumerate(processed_statements, 1):
                    self.append_result(f"  {i}. {sql}")
            else:
                self.append_result("📝 原始SQL:")
                self.append_result(original_sql)
                self.append_result("🔄 处理后SQL:")
                self.append_result(processed_statements[0])
            
            self.append_result("-" * 60)

            # 根据SQL语句数量选择执行方式
            if len(processed_statements) == 1:
                # 单条SQL执行
                results = self.db_connection.execute_query(processed_statements[0])
                
                # 显示结果
                if results:
                    self.append_result(f"📈 查询结果 ({len(results)} 条记录):")
                    self.append_result(json.dumps(results, ensure_ascii=False, indent=2, default=self.serialize_datetime))
                else:
                    self.append_result("📭 查询成功，但没有返回数据")
            else:
                # 多条SQL执行（事务处理）
                results = self.db_connection.execute_multiple_queries(processed_statements, values)
                
                # 显示结果
                total_statements = len(results)
                total_affected = 0
                total_selected = 0
                
                self.append_result(f"📊 执行完成 ({total_statements} 条语句):")
                
                for result in results:
                    stmt_num = result["statement_index"]
                    sql_type = result["type"]
                    
                    if sql_type == "SELECT":
                        row_count = result["row_count"]
                        total_selected += row_count
                        self.append_result(f"  语句 {stmt_num}: SELECT查询返回 {row_count} 条记录")
                        if result["results"]:
                            self.append_result(json.dumps(result["results"], ensure_ascii=False, indent=2, default=self.serialize_datetime))
                    else:
                        affected_rows = result["affected_rows"]
                        total_affected += affected_rows
                        self.append_result(f"  语句 {stmt_num}: 影响 {affected_rows} 行数据")
                
                self.append_result(f"📈 总计: 影响 {total_affected} 行, 查询 {total_selected} 条记录")
                
            self.append_result("✅ 查询执行完成")
            self.append_result("=" * 60)
            self.append_result("")
            
        except Exception as e:
            error_msg = f"❌ 查询执行失败: {str(e)}"
            self.append_result(error_msg)
            QMessageBox.critical(self, "执行错误", f"查询执行失败:\n{str(e)}")
            
    def serialize_datetime(self, obj):
        """序列化datetime对象为字符串"""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif hasattr(obj, '__float__'):  # 处理Decimal类型
            return float(obj)
        elif hasattr(obj, '__int__'):  # 处理其他数值类型
            return int(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
    def append_result(self, text: str):
        """添加结果到文本区域"""
        self.result_text.append(text)
        self.result_text.verticalScrollBar().setValue(
            self.result_text.verticalScrollBar().maximum()
        )
        
    def clear_results(self):
        """清除结果区域"""
        self.result_text.clear()
        self.append_result("🗑️ 结果已清除")
        
    def refresh_config(self):
        """重新加载配置文件"""
        self.append_result("🔄 开始刷新配置...")
        
        # 清除现有的查询组
        for group in self.all_query_groups:
            group['group_box'].deleteLater()
        self.query_groups.clear()
        self.all_query_groups.clear()
        
        # 清空搜索
        self.search_input.clear()
        
        self.load_config()
        self.create_ui_from_config()
        
        self.append_result("✅ 配置刷新完成")
        
    def open_smart_config(self):
        """打开界面配置界面"""
        config_path = self.get_config_path()
        
        try:
            dialog = SmartConfigDialog(config_path, self)
            if dialog.exec() == QDialog.Accepted:
                self.append_result("📝 配置文件已修改，正在重新加载...")
                self.refresh_config()
                self.append_result("✅ 配置已更新并重新加载")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开界面配置失败:\n{str(e)}")
        
    def edit_config(self):
        """编辑配置文件（原有的文本编辑模式）"""
        config_path = self.get_config_path()
        
        try:
            dialog = ConfigEditorDialog(config_path, self)
            if dialog.exec() == QDialog.Accepted:
                self.append_result("📝 配置文件已修改，正在重新加载...")
                self.refresh_config()
                self.append_result("✅ 配置已更新并重新加载")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑配置文件失败:\n{str(e)}")
        
    def show_about(self):
        """显示关于信息"""
        about_text = """
        <h3>数据库查询工具 v4.0</h3>
        <p><b>功能特点：</b></p>
        <ul>
            <li>基于配置文件动态生成查询界面</li>
            <li>支持MySQL数据库连接和查询执行</li>
            <li>支持多种输入类型（文本、数字、日期、下拉选择）</li>
            <li>支持{{字段名}}占位符替换</li>
            <li>支持单条或多条SQL语句执行</li>
            <li>支持事务处理（多条SQL在同一个事务中执行）</li>
            <li>支持SQL语句列表配置（JSON数组格式）</li>
            <li>实时配置更新（F5刷新）</li>
            <li>支持配置文件编辑（Ctrl+E）</li>
            <li>完整的数据库连接异常处理</li>
            <li>气泡描述提示功能</li>
            <li>🔍 搜索过滤功能</li>
            <li><b>🎯 界面配置（v4.0新增）</b></li>
        </ul>
        <p><b>界面配置功能：</b></p>
        <ul>
            <li>可视化编辑数据库配置</li>
            <li>图形化添加、编辑、删除查询</li>
            <li>拖拽式字段管理</li>
            <li>实时预览配置效果</li>
            <li>支持字段排序和批量操作</li>
            <li>快捷键：Ctrl+Shift+C 打开界面配置</li>
        </ul>
        <p><b>数据库支持：</b>MySQL (需要pymysql库)</p>
        <p><b>配置文件：</b>config.json（与程序同目录）</p>
        <p><b>技术支持：</b>PySide6 + pymysql</p>
        """
        QMessageBox.about(self, "关于数据库查询工具", about_text)
        
    def closeEvent(self, event):
        """关闭事件"""
        if self.db_connection:
            self.db_connection.close()
        event.accept()


def main():
    """主函数"""
    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        window = DatabaseTool()
        window.show()
        
        return app.exec()
        
    except Exception as e:
        print(f"程序启动失败: {e}")
        QMessageBox.critical(None, "启动错误", f"程序启动失败:\n{str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
