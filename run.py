from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QPlainTextEdit, QLineEdit,
    QHBoxLayout, QLabel, QGroupBox, QGraphicsDropShadowEffect, QMessageBox
)
from PyQt5.QtCore import QFileSystemWatcher, QTimer, QUrl
from PyQt5.QtGui import QDesktopServices, QColor
import os
from dotenv import load_dotenv
import subprocess
import sys
from src.utils.logger import logger


class ControlUI(QWidget):
    def __init__(self):
        super().__init__()
        
        # 初始化环境变量监控
        self.env_watcher = QFileSystemWatcher(['.env'])
        self.env_watcher.fileChanged.connect(self.reload_env)
        
        # 清空日志文件
        if not os.path.exists('logs'):
            os.makedirs('logs')
        with open('logs/app.log', 'w') as f:
            f.truncate(0)
            
        logger.info("初始化控制界面")
        
        # 初始化环境变量
        self.api_key = ''
        
        # 初始化UI
        self.init_ui()
        
        # 加载环境变量
        self.reload_env()
        
        # 初始化进程
        self.process = None
        
        # 初始化日志监控
        self.log_watcher = QFileSystemWatcher(['logs/app.log'])
        self.log_watcher.fileChanged.connect(self.update_log_view)
        
        # 记录日志文件读取位置
        self._log_file_pos = 0
        
        # 初始化定时器
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.update_log_view)
        self.log_timer.start(500)  # 每500ms更新一次
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle('BOZOYAN 语音控制面板 V2.3.0')
        self.setGeometry(300, 300, 1200, 800)
        
        # 设置窗口样式
        # 设置窗口阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(5)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f2f5;
                font-family: 'Segoe UI', sans-serif;
                font-size: 20px;
            }
            QGroupBox {
                background-color: white;
                border-radius: 8px;
                padding: 15px;
                margin-top: 20px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
            }
            QPushButton {
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                background-color: #2196F3;
                color: white;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
            }
            QPushButton:disabled {
                background-color: #90CAF9;
                opacity: 0.7;
            }
            QPlainTextEdit {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 12px;
                font-family: 'Consolas', monospace;
                font-size: 16px;
            }
            QLabel {
                color: #666;
                font-weight: 500;
            }
        """)
        
        # 创建布局
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 创建API Key分组框
        self.api_key_group = QGroupBox("API Key 设置")
        self.api_key_group.setVisible(False)  # 默认隐藏
        self.api_key_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #ddd;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
                color: #666;
            }
        """)
        api_key_layout = QVBoxLayout()
        
        # 创建API Key输入框
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("请输入SILICONFLOW API Key")
        self.api_key_input.setText(self.api_key)
        self.api_key_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                color: black;
                padding: 10px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
        """)
        api_key_layout.addWidget(self.api_key_input)

        # 创建获取Key的链接和保存按钮
        key_link_layout = QHBoxLayout()
        key_link_layout.setSpacing(10)
        get_key_label = QLabel("获取key")
        get_key_label.setFixedWidth(80)
        key_link_layout.addWidget(get_key_label)
        self.key_link_btn = QPushButton("https://cloud.siliconflow.cn/account/ak")
        self.key_link_btn.setStyleSheet("""
            QPushButton {
                color: #2196F3;
                text-decoration: none;
                background: transparent;
                border: none;
                padding: 0;
                text-align: left;
            }
            QPushButton:hover {
                color: #1976D2;
                text-decoration: underline;
            }
        """)
        self.key_link_btn.setFlat(True)
        self.key_link_btn.clicked.connect(self.open_key_url)
        key_link_layout.addWidget(self.key_link_btn)
        
        # 添加保存按钮到最右边
        self.save_btn = QPushButton('保存设置')
        self.save_btn.setFixedWidth(60)  # 缩小按钮宽度
        self.save_btn.setFixedHeight(24)  # 设置固定高度
        self.save_btn.clicked.connect(self.save_settings)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                padding: 2px;
                font-size: 11px;
                margin-left: 10px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        key_link_layout.addWidget(self.save_btn)
        api_key_layout.addLayout(key_link_layout)
        self.api_key_group.setLayout(api_key_layout)
        layout.addWidget(self.api_key_group)

        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 创建设置按钮
        self.settings_btn = QPushButton('设置')
        self.settings_btn.clicked.connect(self.toggle_settings)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        button_layout.addWidget(self.settings_btn)
        
        # 创建启动按钮
        self.start_btn = QPushButton('启动')
        self.start_btn.clicked.connect(self.start_main)
        button_layout.addWidget(self.start_btn)
        
        # 创建关闭按钮
        self.stop_btn = QPushButton('关闭')
        self.stop_btn.clicked.connect(self.stop_main)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
        """)
        button_layout.addWidget(self.stop_btn)
        
        layout.addLayout(button_layout)
        
        # 创建字幕窗口控制布局
        subtitle_control_layout = QHBoxLayout()
        
        # 创建字幕窗口按钮
        self.subtitle_btn = QPushButton('字幕窗口')
        self.subtitle_btn.clicked.connect(self.toggle_subtitle_window)
        self.subtitle_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        subtitle_control_layout.addWidget(self.subtitle_btn)
        
        # 创建字体大小调节按钮
        self.font_size_increase_btn = QPushButton('字体+')
        self.font_size_increase_btn.clicked.connect(lambda: self.adjust_subtitle_font_size(1.2))
        self.font_size_increase_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        subtitle_control_layout.addWidget(self.font_size_increase_btn)
        
        self.font_size_decrease_btn = QPushButton('字体-')
        self.font_size_decrease_btn.clicked.connect(lambda: self.adjust_subtitle_font_size(0.8))
        self.font_size_decrease_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        subtitle_control_layout.addWidget(self.font_size_decrease_btn)
        
        layout.addLayout(subtitle_control_layout)
        
        # 创建日志显示区域
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("""
            QPlainTextEdit {
                background-color: #2d2d2d;
                color: #f5f5f5;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 10px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                transition: all 0.2s ease;
            }
            QPlainTextEdit:hover {
                border-color: #666;
            }
            QScrollBar:vertical {
                background: #444;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #666;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                background: none;
            }
        """)
        layout.addWidget(self.log_view)
        
        self.setLayout(layout)
        
        # 字幕窗口实例
        self.subtitle_window = None
    
    def get_api_key(self):
        """获取当前输入的API Key"""
        return self.api_key_input.text().strip()

    def check_env_file(self):
        """检查.env文件是否存在"""
        if not os.path.exists('.env'):
            self.log_view.setPlainText("警告：未找到.env文件")
            return False
        return True

    def reload_env(self):
        """重新加载.env文件"""
        load_dotenv(override=True)
        self.api_key = os.getenv('SILICONFLOW_API_KEY', '')
        # 更新UI中的API Key显示
        self.api_key_input.setText(self.api_key)

    def open_key_url(self):
        """打开获取API Key的URL"""
        url = QUrl("https://cloud.siliconflow.cn/account/ak")
        QDesktopServices.openUrl(url)

    def toggle_settings(self):
        """切换API Key设置区域的显示/隐藏"""
        self.api_key_group.setVisible(not self.api_key_group.isVisible())
        if self.api_key_group.isVisible():
            self.settings_btn.setText('隐藏设置')
        else:
            self.settings_btn.setText('设置')
    def save_settings(self):
        """保存设置到.env文件"""
        api_key = self.get_api_key()
        if not api_key:
            self.log_view.setPlainText("API Key不能为空")
            return
            
        try:
            # 读取现有.env内容
            env_lines = []
            if os.path.exists('.env'):
                with open('.env', 'r') as f:
                    env_lines = f.readlines()
            
            # 更新或添加SILICONFLOW_API_KEY
            found = False
            with open('.env', 'w') as f:
                for line in env_lines:
                    if line.startswith('SILICONFLOW_API_KEY='):
                        f.write(f'SILICONFLOW_API_KEY={api_key}\n')
                        found = True
                    else:
                        f.write(line)
                if not found:
                    f.write(f'\nSILICONFLOW_API_KEY={api_key}\n')
                    
            self.log_view.setPlainText("API Key设置保存成功")
            self.reload_env()  # 重新加载环境变量
        except Exception as e:
            self.log_view.setPlainText(f"保存失败：{str(e)}")

    def start_main(self):
        """启动main.py"""
        if not self.check_env_file():
            return
            
        if not self.get_api_key():
            self.log_view.setPlainText("请先输入SILICONFLOW API Key")
            return
            
        # 检查依赖
        if not self.check_dependencies():
            return
            
        if self.process is None:
            logger.info("启动主程序")
            self.process = subprocess.Popen(["python", "main.py"])
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            
            # 初始化日志显示
            self.update_log_view()
    
    def stop_main(self):
        """停止main.py"""
        if self.process is not None:
            logger.info("停止主程序")
            self.process.terminate()
            self.process = None
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
    
    def check_dependencies(self):
        """检查依赖是否安装"""
        try:
            import pynput
            import openai
            import sounddevice
            return True
        except ImportError as e:
            self.log_view.setPlainText(f"缺少依赖库: {str(e)}\n请运行以下命令安装依赖:\n\npip install -r requirements.txt")
            return False
    
    def update_log_view(self):
        """实时更新日志显示"""
        try:
            with open('logs/app.log', 'r') as f:
                # 跳转到上次读取位置
                f.seek(self._log_file_pos)
                
                # 读取新增内容
                new_content = f.read()
                
                # 更新文件位置
                self._log_file_pos = f.tell()
                
                # 如果文件被清空或轮转，重置位置
                if self._log_file_pos > os.path.getsize('logs/app.log'):
                    self._log_file_pos = 0
                    new_content = f.read()
                
                # 追加新内容到日志视图
                if new_content:
                    self.log_view.appendPlainText(new_content)
                    self.log_view.verticalScrollBar().setValue(
                        self.log_view.verticalScrollBar().maximum()
                    )
        except FileNotFoundError:
            self.log_view.setPlainText('日志文件不存在')
    
    def toggle_subtitle_window(self):
        """切换字幕窗口显示/隐藏"""
        try:
            from src.ui.subtitle import SubtitleWindow
            from PyQt5.QtWidgets import QApplication
            
            # 检查是否已有QApplication实例
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            
            if self.subtitle_window is None:
                # 创建新的字幕窗口实例
                self.subtitle_window = SubtitleWindow()
                self.subtitle_window.show()
                self.subtitle_btn.setText('隐藏字幕')
                
                # 连接窗口的隐藏按钮信号
                self.subtitle_window.hide_btn.clicked.connect(self.on_subtitle_window_hide)
            else:
                if self.subtitle_window.isVisible():
                    # 隐藏窗口
                    self.subtitle_window.hide()
                    self.subtitle_btn.setText('字幕窗口')
                else:
                    # 显示窗口并确保它置顶
                    self.subtitle_window.show()
                    self.subtitle_window.raise_()
                    self.subtitle_window.activateWindow()
                    self.subtitle_btn.setText('隐藏字幕')
        except Exception as e:
            self.log_view.appendPlainText(f"字幕窗口错误: {str(e)}")
    
    def on_subtitle_window_hide(self):
        """字幕窗口隐藏时的回调函数"""
        self.subtitle_btn.setText('字幕窗口')
        
    def adjust_subtitle_font_size(self, scale_factor):
        """调整字幕窗口的字体大小
        
        Args:
            scale_factor: 字体大小缩放因子，大于1表示增大，小于1表示减小
        """
        if self.subtitle_window and self.subtitle_window.isVisible():
            # 获取当前字体大小
            current_style = self.subtitle_window.text_edit.styleSheet()
            import re
            font_size_match = re.search(r'font-size:\s*(\d+)px', current_style)
            
            if font_size_match:
                current_size = int(font_size_match.group(1))
                new_size = max(12, min(120, int(current_size * scale_factor)))  # 限制字体大小范围
                
                # 更新字体大小
                new_style = re.sub(
                    r'font-size:\s*\d+px', 
                    f'font-size: {new_size}px', 
                    current_style
                )
                self.subtitle_window.text_edit.setStyleSheet(new_style)
                self.log_view.appendPlainText(f"字幕字体大小已调整为 {new_size}px")
        else:
            self.log_view.appendPlainText("请先打开字幕窗口")

if __name__ == "__main__":
    app = QApplication([])
    window = ControlUI()
    window.show()
    app.exec_()
