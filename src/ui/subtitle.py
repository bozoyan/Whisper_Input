import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QApplication, QMenu, 
                            QPushButton, QHBoxLayout, QSlider, QLabel, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QFont, QContextMenuEvent
import os
import pyperclip
import datetime


class SubtitleWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_file_watcher()
        
    def init_ui(self):
        """初始化字幕窗口UI"""
        # 设置窗口属性 - 使用更强的置顶标志组合
        self.setWindowFlags(
            Qt.FramelessWindowHint |  # 无边框
            Qt.WindowStaysOnTopHint |  # 置顶
            Qt.Tool |  # 避免在任务栏显示
            Qt.WindowDoesNotAcceptFocus |  # 不获取焦点
            Qt.X11BypassWindowManagerHint  # 绕过窗口管理器，确保始终在最上层
        )
        
        # 设置透明背景和其他窗口属性
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)  # 显示但不激活
        self.setAttribute(Qt.WA_AlwaysStackOnTop, True)  # 确保窗口始终在最上层
        
        # 设置窗口位置和大小为800x300，并允许调整大小
        self.setGeometry(100, 100, 1000, 300)
        self.setMinimumSize(1000, 300)  # 设置最小尺寸，防止窗口过小
        self.setMouseTracking(True)  # 启用鼠标跟踪以支持调整大小
        
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建控制按钮布局
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(10, 5, 10, 0)
        
        # 创建置顶按钮
        self.always_on_top_btn = QPushButton("置顶")
        self.always_on_top_btn.setFixedSize(60, 25)
        self.always_on_top_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 120, 215, 180);
                color: white;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(0, 120, 215, 220);
            }
            QPushButton:pressed {
                background-color: rgba(0, 120, 215, 250);
            }
        """)
        self.always_on_top_btn.clicked.connect(self.toggle_always_on_top)
        self.is_always_on_top = True  # 默认置顶
        control_layout.addWidget(self.always_on_top_btn)
        
        # 创建清除按钮
        self.clear_btn = QPushButton("清除")
        self.clear_btn.setFixedSize(60, 25)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 152, 0, 180);
                color: white;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 152, 0, 220);
            }
            QPushButton:pressed {
                background-color: rgba(255, 152, 0, 250);
            }
        """)
        self.clear_btn.clicked.connect(self.clear_history)
        control_layout.addWidget(self.clear_btn)
        
        # 创建保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.setFixedSize(60, 25)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(76, 175, 80, 180);
                color: white;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(76, 175, 80, 220);
            }
            QPushButton:pressed {
                background-color: rgba(76, 175, 80, 250);
            }
        """)
        self.save_btn.clicked.connect(self.save_to_file)
        control_layout.addWidget(self.save_btn)
        
        # 创建透明度控制
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel("透明度:")
        opacity_label.setStyleSheet("color: white; font-size: 12px;")
        opacity_layout.addWidget(opacity_label)
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(10, 100)  # 10%-100%的透明度范围
        self.opacity_slider.setValue(80)  # 默认80%不透明度
        self.opacity_slider.setFixedWidth(80)
        self.opacity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #555;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: white;
                border: 1px solid #777;
                width: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }
        """)
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        opacity_layout.addWidget(self.opacity_slider)
        
        control_layout.addLayout(opacity_layout)
        
        # 创建历史行数控制
        history_layout = QHBoxLayout()
        history_label = QLabel("历史行数:")
        history_label.setStyleSheet("color: white; font-size: 12px;")
        history_layout.addWidget(history_label)
        
        self.history_slider = QSlider(Qt.Horizontal)
        self.history_slider.setRange(1, 10)  # 1-10行历史记录
        self.history_slider.setValue(5)  # 默认5行
        self.history_slider.setFixedWidth(80)
        self.history_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #555;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: white;
                border: 1px solid #777;
                width: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }
        """)
        self.history_slider.valueChanged.connect(self.change_history_lines)
        history_layout.addWidget(self.history_slider)
        
        control_layout.addLayout(history_layout)
        
        # 添加弹性空间
        control_layout.addStretch()
        
        # 创建隐藏按钮
        self.hide_btn = QPushButton("X")
        self.hide_btn.setFixedSize(60, 25)
        self.hide_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(220, 0, 0, 180);
                color: white;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(220, 0, 0, 220);
            }
            QPushButton:pressed {
                background-color: rgba(220, 0, 0, 250);
            }
        """)
        self.hide_btn.clicked.connect(self.hide)
        control_layout.addWidget(self.hide_btn)
        
        main_layout.addLayout(control_layout)
        
        # 创建文本布局
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(20, 10, 20, 20)
        
        # 创建文本显示区域
        self.text_edit = QTextEdit()
        self.text_edit.setAlignment(Qt.AlignCenter)
        self.background_opacity = 180  # 默认背景透明度
        self.update_text_edit_style()
        # 修复：使用正确的 WordWrap 模式
        from PyQt5.QtGui import QTextOption
        self.text_edit.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        
        text_layout.addWidget(self.text_edit)
        main_layout.addLayout(text_layout)
        self.setLayout(main_layout)
        
        # 文本历史记录
        self.text_history = []
        self.max_history = 5  # 默认最多显示5行历史
        
        # 用于窗口调整大小的变量
        self.resizing = False
        self.resize_direction = None
        self.margin = 10  # 边缘检测范围
        
        # 创建定时器，用于确保窗口始终在最前面
        self.top_most_timer = QTimer(self)
        self.top_most_timer.timeout.connect(self.ensure_top_most)
        self.top_most_timer.start(300)  # 每300毫秒检查一次

    def setup_file_watcher(self):
        """设置文件监视器以监听字幕更新"""
        subtitle_file = os.path.join("logs", "subtitle.txt")
        if not os.path.exists("logs"):
            os.makedirs("logs")
        
        # 创建空的字幕文件（如果不存在）
        if not os.path.exists(subtitle_file):
            with open(subtitle_file, "w", encoding="utf-8") as f:
                pass
        
        # 使用定时器定期检查文件更新
        self.last_position = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_subtitle_file)
        self.timer.start(500)  # 每500ms检查一次
        
    def check_subtitle_file(self):
        """检查字幕文件更新"""
        try:
            subtitle_file = os.path.join("logs", "subtitle.txt")
            if not os.path.exists(subtitle_file):
                return
                
            current_size = os.path.getsize(subtitle_file)
            if current_size < self.last_position:
                # 文件被清空或轮转
                self.last_position = 0
                
            if current_size > self.last_position:
                with open(subtitle_file, "r", encoding="utf-8") as f:
                    f.seek(self.last_position)
                    new_content = f.read()
                    self.last_position = f.tell()
                    
                if new_content:
                    lines = new_content.strip().split('\n')
                    for line in lines:
                        if line.strip():
                            self.add_text(line)
        except Exception as e:
            pass  # 静默处理文件读取错误
    
    def add_text(self, text):
        """添加新文本到显示"""
        if text:
            # 避免添加重复的文本
            if not self.text_history or self.text_history[-1] != text:
                self.text_history.append(text)
                # 限制历史记录数量
                if len(self.text_history) > self.max_history:
                    self.text_history.pop(0)
            else:
                # 如果是重复文本，不进行任何操作
                return
            
            # 更新显示文本
            display_text = '\n'.join(self.text_history)
            self.text_edit.setPlainText(display_text)
            
            # 调整字体大小以适应窗口
            self.adjust_font_size()
            
            # 调整窗口大小以适应文本
            self.adjustSize()
            self.show()  # 确保窗口显示
            
            # 确保窗口始终保持在最前面
            self.ensure_top_most()
    
    def update_text_edit_style(self):
        """更新文本编辑区域的样式"""
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                color: white;
                background-color: rgba(0, 0, 0, {self.background_opacity});
                border-radius: 10px;
                padding: 15px;
                font-size: 60px;
                font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
                border: none;
            }}
        """)
    
    def change_opacity(self, value):
        """改变窗口透明度"""
        self.background_opacity = int(value * 2.55)  # 将百分比转换为0-255的值
        self.update_text_edit_style()
        
    def change_history_lines(self, value):
        """改变历史记录行数"""
        old_max = self.max_history
        self.max_history = value
        
        # 如果减少了历史行数，需要裁剪历史记录
        if self.max_history < old_max and len(self.text_history) > self.max_history:
            self.text_history = self.text_history[-self.max_history:]
            # 更新显示
            display_text = '\n'.join(self.text_history)
            self.text_edit.setPlainText(display_text)
    
    def ensure_top_most(self):
        """确保窗口始终在最前面"""
        if self.is_always_on_top and self.isVisible():
            self.raise_()
            self.activateWindow()
    
    def adjust_font_size(self):
        """根据窗口大小调整字体大小"""
        # 获取窗口尺寸
        window_width = self.width()
        window_height = self.height()
        
        # 根据窗口宽度计算字体大小（可以根据需要调整系数）
        font_size = max(12, min(window_width // 20, window_height // 10))
        
        # 应用字体大小
        current_style = self.text_edit.styleSheet()
        # 移除旧的font-size样式
        import re
        current_style = re.sub(r'font-size:\s*\d+px;', '', current_style)
        # 添加新的font-size样式
        new_style = current_style.replace(
            '}', 
            f'font-size: {font_size}px; }}'
        )
        self.text_edit.setStyleSheet(new_style)
    
    def mousePressEvent(self, event):
        """鼠标按下事件，用于移动窗口"""
        if event.button() == Qt.LeftButton:
            # 检查是否在边缘区域（用于调整大小）
            pos = event.pos()
            width, height = self.width(), self.height()
            
            # 检查是否在边缘
            if pos.x() < self.margin:
                self.resize_direction = "left"
            elif pos.x() > width - self.margin:
                self.resize_direction = "right"
            elif pos.y() < self.margin:
                self.resize_direction = "top"
            elif pos.y() > height - self.margin:
                self.resize_direction = "bottom"
            else:
                # 不在边缘，准备移动窗口
                self.resize_direction = None
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件，用于移动或调整窗口大小"""
        if event.buttons() == Qt.LeftButton:
            if self.resize_direction:
                # 调整窗口大小
                self.resize_window(event.globalPos())
            elif hasattr(self, 'drag_position'):
                # 移动窗口
                self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def resize_window(self, global_pos):
        """根据鼠标位置调整窗口大小"""
        if not self.resize_direction:
            return
            
        rect = self.geometry()
        x, y, width, height = rect.x(), rect.y(), rect.width(), rect.height()
        
        # 根据不同的调整方向更新窗口几何形状
        if self.resize_direction == "right":
            new_width = max(self.minimumWidth(), global_pos.x() - x)
            self.setGeometry(x, y, new_width, height)
        elif self.resize_direction == "left":
            new_width = max(self.minimumWidth(), x + width - global_pos.x())
            if new_width >= self.minimumWidth():
                self.setGeometry(global_pos.x(), y, new_width, height)
        elif self.resize_direction == "bottom":
            new_height = max(self.minimumHeight(), global_pos.y() - y)
            self.setGeometry(x, y, width, new_height)
        elif self.resize_direction == "top":
            new_height = max(self.minimumHeight(), y + height - global_pos.y())
            if new_height >= self.minimumHeight():
                self.setGeometry(x, global_pos.y(), width, new_height)
    
    def resizeEvent(self, event):
        """窗口大小调整事件"""
        super().resizeEvent(event)
        # 调整字体大小以适应新窗口尺寸
        self.adjust_font_size()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        super().mouseReleaseEvent(event)
        
    def toggle_always_on_top(self):
        """切换窗口置顶状态"""
        self.is_always_on_top = not self.is_always_on_top
        
        # 保存当前窗口位置和大小
        current_geometry = self.geometry()
        
        if self.is_always_on_top:
            # 设置为置顶
            self.setWindowFlags(
                Qt.FramelessWindowHint |
                Qt.WindowStaysOnTopHint |
                Qt.Tool |
                Qt.WindowDoesNotAcceptFocus |
                Qt.X11BypassWindowManagerHint  # 绕过窗口管理器，确保始终在最上层
            )
            self.setAttribute(Qt.WA_AlwaysStackOnTop, True)  # 确保窗口始终在最上层
            self.always_on_top_btn.setText("置顶")
            self.always_on_top_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 120, 215, 180);
                    color: white;
                    border-radius: 4px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 120, 215, 220);
                }
            """)
            # 启动定时器确保置顶
            if not self.top_most_timer.isActive():
                self.top_most_timer.start(300)
        else:
            # 取消置顶
            self.setWindowFlags(
                Qt.FramelessWindowHint |
                Qt.Tool |
                Qt.WindowDoesNotAcceptFocus
            )
            self.setAttribute(Qt.WA_AlwaysStackOnTop, False)  # 取消始终在最上层
            self.always_on_top_btn.setText("不置顶")
            self.always_on_top_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(128, 128, 128, 180);
                    color: white;
                    border-radius: 4px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: rgba(128, 128, 128, 220);
                }
            """)
            # 停止定时器
            self.top_most_timer.stop()
        
        # 恢复窗口位置和大小
        self.setGeometry(current_geometry)
        self.show()  # 重新显示窗口以应用新的窗口标志
    
    def clear_history(self):
        """清除字幕历史记录"""
        self.text_history = []
        self.text_edit.clear()
    
    def save_to_file(self):
        """保存字幕内容到文件"""
        if not self.text_history:
            QMessageBox.information(self, "提示", "当前没有字幕内容可保存")
            return
            
        # 生成默认文件名（当前日期时间）
        default_filename = f"字幕记录_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # 打开文件保存对话框
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存字幕内容", default_filename, 
            "文本文件 (*.txt);;所有文件 (*)", options=options
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(self.text_history))
                QMessageBox.information(self, "成功", f"字幕内容已保存到:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def contextMenuEvent(self, event: QContextMenuEvent):
        """右键菜单事件，用于复制文本和清除历史"""
        context_menu = QMenu(self)
        copy_action = context_menu.addAction("复制")
        clear_action = context_menu.addAction("清除历史")
        save_action = context_menu.addAction("保存到文件")
        action = context_menu.exec_(self.mapToGlobal(event.pos()))
        
        if action == copy_action:
            text = self.text_edit.toPlainText()
            if text:
                try:
                    pyperclip.copy(text)
                except Exception as e:
                    pass  # 静默处理复制错误
        elif action == clear_action:
            self.clear_history()
        elif action == save_action:
            self.save_to_file()

    def showEvent(self, event):
        """窗口显示事件"""
        super().showEvent(event)
        # 确保窗口在显示时置顶
        if self.is_always_on_top:
            QTimer.singleShot(100, self.ensure_top_most)

# 测试代码
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SubtitleWindow()
    window.show()
    sys.exit(app.exec_())