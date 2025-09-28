#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片转PDF工具
支持拖拽图片文件或选择文件夹批量转换
可设置每页PDF包含的图片数量
作者：小庄-Python办公
邮箱：ikun2788@outlook.com
"""

import sys
import os
import glob
from pathlib import Path
from typing import List, Optional
import traceback

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QWidget, QPushButton, QLabel, QListWidget, QSpinBox,
    QGroupBox, QProgressBar, QTextEdit, QFileDialog,
    QMessageBox, QGridLayout, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMimeData
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPalette

from PIL import Image
import img2pdf


class ImageToPDFConverter(QThread):
    """图片转PDF转换线程"""
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    conversion_finished = pyqtSignal(bool, str)
    
    def __init__(self, image_files: List[str], output_path: str, images_per_page: int = 1):
        super().__init__()
        self.image_files = image_files
        self.output_path = output_path
        self.images_per_page = images_per_page
        
    def run(self):
        try:
            self.status_updated.emit("开始转换图片...")
            
            # 支持的图片格式
            supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif'}
            
            # 过滤有效的图片文件
            valid_images = []
            for img_file in self.image_files:
                if Path(img_file).suffix.lower() in supported_formats:
                    valid_images.append(img_file)
                    
            if not valid_images:
                self.conversion_finished.emit(False, "没有找到有效的图片文件")
                return
                
            total_images = len(valid_images)
            self.status_updated.emit(f"找到 {total_images} 个有效图片文件")
            
            # 按照设置的每页图片数量分组
            if self.images_per_page == 1:
                # 每个图片生成一个PDF
                for i, img_file in enumerate(valid_images):
                    try:
                        # 转换单个图片
                        img_name = Path(img_file).stem
                        output_file = os.path.join(self.output_path, f"{img_name}.pdf")
                        
                        # 使用img2pdf转换
                        with open(output_file, "wb") as f:
                            f.write(img2pdf.convert(img_file))
                            
                        progress = int((i + 1) / total_images * 100)
                        self.progress_updated.emit(progress)
                        self.status_updated.emit(f"已转换: {img_name}.pdf")
                        
                    except Exception as e:
                        self.status_updated.emit(f"转换失败 {img_file}: {str(e)}")
                        continue
            else:
                # 多个图片合并为一个PDF
                output_file = os.path.join(self.output_path, "merged_images.pdf")
                
                # 按组处理图片
                groups = [valid_images[i:i + self.images_per_page] 
                         for i in range(0, len(valid_images), self.images_per_page)]
                
                if len(groups) == 1:
                    # 所有图片合并为一个PDF
                    try:
                        with open(output_file, "wb") as f:
                            f.write(img2pdf.convert(valid_images))
                        self.progress_updated.emit(100)
                        self.status_updated.emit(f"已生成合并PDF: merged_images.pdf")
                    except Exception as e:
                        self.conversion_finished.emit(False, f"合并PDF失败: {str(e)}")
                        return
                else:
                    # 生成多个PDF文件
                    for group_idx, group in enumerate(groups):
                        try:
                            group_output = os.path.join(self.output_path, f"images_group_{group_idx + 1}.pdf")
                            with open(group_output, "wb") as f:
                                f.write(img2pdf.convert(group))
                                
                            progress = int((group_idx + 1) / len(groups) * 100)
                            self.progress_updated.emit(progress)
                            self.status_updated.emit(f"已生成: images_group_{group_idx + 1}.pdf")
                            
                        except Exception as e:
                            self.status_updated.emit(f"转换组 {group_idx + 1} 失败: {str(e)}")
                            continue
            
            self.conversion_finished.emit(True, "转换完成！")
            
        except Exception as e:
            error_msg = f"转换过程中发生错误: {str(e)}\n{traceback.format_exc()}"
            self.conversion_finished.emit(False, error_msg)


class DropArea(QListWidget):
    """支持拖拽的文件列表区域"""
    files_dropped = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #aaa;
                border-radius: 10px;
                background-color: #f9f9f9;
                font-size: 14px;
                padding: 20px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #ddd;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)
        
        # 添加提示文本
        self.addItem("📁 拖拽图片文件或文件夹到这里")
        self.addItem("🖱️ 或点击下方按钮选择文件/文件夹")
        self.addItem("📄 支持格式: JPG, PNG, BMP, TIFF, GIF")
        self.addItem("✨ 支持单个文件或批量处理")
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.setStyleSheet("""
                QListWidget {
                    border: 2px dashed #4CAF50;
                    border-radius: 10px;
                    background-color: #e8f5e8;
                    font-size: 14px;
                    padding: 20px;
                }
            """)
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """拖拽移动事件 - 必须实现以支持拖拽"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
            
    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #aaa;
                border-radius: 10px;
                background-color: #f9f9f9;
                font-size: 14px;
                padding: 20px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #ddd;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)
        
    def dropEvent(self, event):
        files = []
        dropped_items = []
        # 支持的图片格式
        supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif'}
        
        # 收集所有拖拽的项目
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            dropped_items.append(file_path)
            
            if os.path.isfile(file_path):
                # 检查文件扩展名是否为支持的图片格式
                file_ext = Path(file_path).suffix.lower()
                if file_ext in supported_formats:
                    files.append(file_path)
            elif os.path.isdir(file_path):
                # 如果是文件夹，获取其中的图片文件
                image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.tif', '*.gif']
                for ext in image_extensions:
                    files.extend(glob.glob(os.path.join(file_path, ext)))
                    files.extend(glob.glob(os.path.join(file_path, ext.upper())))
                    
        if files:
            self.files_dropped.emit(files)
        else:
            # 如果没有有效的图片文件，显示提示
            from PyQt5.QtWidgets import QMessageBox
            if dropped_items:
                QMessageBox.information(None, "提示", 
                    f"拖拽的文件中没有找到支持的图片格式\n"
                    f"拖拽的项目: {len(dropped_items)} 个\n"
                    f"支持格式: JPG, PNG, BMP, TIFF, GIF")
            else:
                QMessageBox.information(None, "提示", "请拖拽有效的图片文件或包含图片的文件夹\n支持格式: JPG, PNG, BMP, TIFF, GIF")
            
        # 恢复样式
        self.dragLeaveEvent(event)
        event.accept()


class ImageToPDFApp(QMainWindow):
    """主应用程序窗口"""
    
    def __init__(self):
        super().__init__()
        self.image_files = []
        self.converter_thread = None
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("图片转PDF工具 v1.0")
        self.setGeometry(100, 100, 800, 900)
        self.setMinimumSize(600, 500)
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("图片转PDF工具")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setStyleSheet("color: #2196F3; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # 文件拖拽区域
        file_group = QGroupBox("文件选择")
        file_group.setFont(QFont("Arial", 12))
        file_layout = QVBoxLayout(file_group)
        
        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self.add_files)
        file_layout.addWidget(self.drop_area)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.select_files_btn = QPushButton("选择图片文件/文件夹")
        self.select_files_btn.clicked.connect(self.select_files)
        self.select_files_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        

        
        self.clear_btn = QPushButton("清空列表")
        self.clear_btn.clicked.connect(self.clear_files)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        
        button_layout.addWidget(self.select_files_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        
        file_layout.addLayout(button_layout)
        main_layout.addWidget(file_group)
        
        # 设置区域
        settings_group = QGroupBox("转换设置")
        settings_group.setFont(QFont("Arial", 12))
        settings_layout = QGridLayout(settings_group)
        
        settings_layout.addWidget(QLabel("每页PDF包含图片数量:"), 0, 0)
        self.images_per_page_spin = QSpinBox()
        self.images_per_page_spin.setMinimum(1)
        self.images_per_page_spin.setMaximum(50)
        self.images_per_page_spin.setValue(1)
        self.images_per_page_spin.setToolTip("设置为1表示每个图片生成一个PDF文件")
        settings_layout.addWidget(self.images_per_page_spin, 0, 1)
        
        settings_layout.addWidget(QLabel("输出文件夹:"), 1, 0)
        self.output_path_label = QLabel("未选择")
        self.output_path_label.setStyleSheet("border: 1px solid #ddd; padding: 5px; background-color: #f9f9f9;")
        settings_layout.addWidget(self.output_path_label, 1, 1)
        
        self.select_output_btn = QPushButton("选择输出文件夹")
        self.select_output_btn.clicked.connect(self.select_output_folder)
        self.select_output_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        settings_layout.addWidget(self.select_output_btn, 1, 2)
        
        main_layout.addWidget(settings_group)
        
        # 转换按钮
        self.convert_btn = QPushButton("开始转换")
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        main_layout.addWidget(self.convert_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 状态显示
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(150)
        self.status_text.setReadOnly(True)
        self.status_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: #f9f9f9;
                font-family: Consolas, monospace;
                font-size: 12px;
            }
        """)
        main_layout.addWidget(self.status_text)
        
        # 初始化输出路径为当前目录
        self.output_path = os.getcwd()
        self.output_path_label.setText(self.output_path)
        
    def add_files(self, files):
        """添加文件到列表"""
        # 清空拖拽区域并添加文件
        self.drop_area.clear()
        self.image_files = files
        
        if files:
            # 添加文件到列表
            for file_path in files:
                file_name = os.path.basename(file_path)
                self.drop_area.addItem(f"📄 {file_name}")
                
            self.status_text.append(f"✅ 已添加 {len(files)} 个文件")
            
            # 强制刷新界面
            self.drop_area.repaint()
            self.status_text.repaint()
        else:
            # 如果没有文件，恢复提示文本
            self.drop_area.addItem("📁 拖拽图片文件或文件夹到这里")
            self.drop_area.addItem("🖱️ 或点击下方按钮选择文件/文件夹")
            self.drop_area.addItem("📄 支持格式: JPG, PNG, BMP, TIFF, GIF")
            self.drop_area.addItem("✨ 支持单个文件或批量处理")
            
        # 确保界面更新
        self.drop_area.update()
        
    def select_files(self):
        """选择图片文件或文件夹"""
        # 创建选择对话框，让用户选择是选择文件还是文件夹
        from PyQt5.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self, "选择类型", 
            "请选择要添加的内容类型：\n\n点击 'Yes' 选择图片文件\n点击 'No' 选择文件夹",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            # 选择图片文件
            files, _ = QFileDialog.getOpenFileNames(
                self, "选择图片文件", "",
                "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.gif);;所有文件 (*)"
            )
            if files:
                self.add_files(files)
                
        elif reply == QMessageBox.No:
            # 选择文件夹
            folder = QFileDialog.getExistingDirectory(self, "选择包含图片的文件夹")
            if folder:
                # 获取文件夹中的所有图片文件
                image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.tif', '*.gif']
                files = []
                for ext in image_extensions:
                    files.extend(glob.glob(os.path.join(folder, ext)))
                    files.extend(glob.glob(os.path.join(folder, ext.upper())))
                
                if files:
                    self.add_files(files)
                else:
                    QMessageBox.information(self, "提示", "所选文件夹中没有找到图片文件")
            

    def clear_files(self):
        """清空文件列表"""
        self.image_files = []
        self.drop_area.clear()
        self.drop_area.addItem("📁 拖拽图片文件或文件夹到这里")
        self.drop_area.addItem("🖱️ 或点击下方按钮选择文件/文件夹")
        self.drop_area.addItem("📄 支持格式: JPG, PNG, BMP, TIFF, GIF")
        self.drop_area.addItem("✨ 支持单个文件或批量处理")
        self.status_text.append("已清空文件列表")
        
    def select_output_folder(self):
        """选择输出文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择输出文件夹", self.output_path)
        if folder:
            self.output_path = folder
            self.output_path_label.setText(folder)
            
    def start_conversion(self):
        """开始转换"""
        if not self.image_files:
            QMessageBox.warning(self, "警告", "请先选择要转换的图片文件")
            return
            
        if not os.path.exists(self.output_path):
            QMessageBox.warning(self, "警告", "输出文件夹不存在")
            return
            
        # 禁用转换按钮
        self.convert_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 清空状态文本
        self.status_text.clear()
        
        # 创建转换线程
        images_per_page = self.images_per_page_spin.value()
        self.converter_thread = ImageToPDFConverter(
            self.image_files, self.output_path, images_per_page
        )
        
        # 连接信号
        self.converter_thread.progress_updated.connect(self.progress_bar.setValue)
        self.converter_thread.status_updated.connect(self.status_text.append)
        self.converter_thread.conversion_finished.connect(self.conversion_finished)
        
        # 启动线程
        self.converter_thread.start()
        
    def conversion_finished(self, success, message):
        """转换完成"""
        self.convert_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            self.status_text.append(f"\n✅ {message}")
            QMessageBox.information(self, "成功", message)
        else:
            self.status_text.append(f"\n❌ {message}")
            QMessageBox.critical(self, "错误", message)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("图片转PDF工具")
    app.setApplicationVersion("1.0")
    
    # 设置应用程序图标（如果有的话）
    # app.setWindowIcon(QIcon("icon.png"))
    
    window = ImageToPDFApp()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()