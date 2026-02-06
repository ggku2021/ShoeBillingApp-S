import tkinter as tk
from tkinter import messagebox, ttk, filedialog, simpledialog
import os, datetime, webbrowser, base64, json, sys, csv, shutil, hashlib, uuid, ctypes, subprocess
from io import BytesIO
from PIL import Image, ImageTk, ImageGrab

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FILES = {
    "product": os.path.join(BASE_DIR, "products.json"),
    "history": os.path.join(BASE_DIR, "billing_history.json"),
    "quote": os.path.join(BASE_DIR, "quote_history.json"),
    "inventory": os.path.join(BASE_DIR, "inventory_history.json"),
    "password": os.path.join(BASE_DIR, "password.hash")
}

SHARE_CONFIG_PATH = os.path.join(BASE_DIR, "share_config.json")
BACKUP_CONFIG_PATH = os.path.join(BASE_DIR, "backup_config.json")
ICON_PATH = os.path.join(BASE_DIR, "app.ico")

class ShoeBillingApp:
    def __init__(self, root):
        self.root = root
        try:
            if os.path.exists(ICON_PATH):
                self.root.iconbitmap(ICON_PATH)
        except Exception:
            pass
        self.root.title("鞋类产品报价开单系统 V1.1.1正式版")
        self.root.geometry("1550x950")
        
        # --- 打印语言设置 ---
        self.print_lang_var = tk.StringVar(value="en") # 销售单默认英文
        self.quote_print_lang_var = tk.StringVar(value="en") # 报价单默认英文
        
        self.TRANS = {
            "zh": {
                "title_quotation": "报价单",
                "title_invoice": "销售发货单",
                "client": "客户",
                "ref": "报价单号",
                "date": "日期",
                "sender": "发货人",
                "phone": "电话",
                "address": "地址",
                "mark": "唛头",
                "receiver": "收货人",
                "photo": "图片",
                "no": "货号",
                "size": "码段",
                "color": "颜色",
                "moq": "起订量(箱)",
                "pcs_ctn": "每箱(双)",
                "ctns": "箱数",
                "pcs": "每箱(双)",
                "qty": "总数(双)",
                "price": "单价",
                "amount": "金额",
                "total": "总计",
                "subtotal": "小计",
                "freight": "运费",
                "deposit": "定金",
                "paid": "已付",
                "balance": "余额",
                "print_quotation": "打印报价单",
                "print_invoice": "打印发货单",
                "valid_note": "* 报价单有效期30天。<br>* 本公司保留所有权利。",
                "note": "备注",
                "invoice_no": "单号"
            },
            "en": {
                "title_quotation": "QUOTATION",
                "title_invoice": "SALES INVOICE",
                "client": "Client",
                "ref": "Ref",
                "date": "Date",
                "sender": "Sender",
                "phone": "Phone",
                "address": "Address",
                "mark": "Mark",
                "receiver": "RECEIVER",
                "photo": "Photo",
                "no": "No.",
                "size": "Size",
                "color": "Color",
                "moq": "MOQ(Ctns)",
                "pcs_ctn": "Pcs/Ctn",
                "ctns": "Ctns",
                "pcs": "Pcs",
                "qty": "Qty",
                "price": "Price",
                "amount": "Amount",
                "total": "Total",
                "subtotal": "Subtotal",
                "freight": "Freight",
                "deposit": "Deposit",
                "paid": "Paid",
                "balance": "BALANCE",
                "print_quotation": "PRINT",
                "print_invoice": "PRINT",
                "valid_note": "* Quotation valid for 30 days.<br>* All rights reserved by the company.",
                "note": "Note",
                "invoice_no": "No."
            }
        }
        
        # --- 授权验证 ---
        self.SALT = "SHOE_BILLING_APP_SECRET_2026_V9"
        self.LICENSE_FILE = os.path.join(BASE_DIR, "license.json")
        self.license_info = {} # 存储授权信息
        
        valid, msg = self.check_license()
        if not valid:
            self.show_activation_ui(msg)
            return
        
        # 显示授权状态
        self.root.title(f"鞋类产品报价开单系统 V1.1正式版 - [已授权] 到期时间: {self.license_info.get('expire_date', '未知')} ({self.license_info.get('days_left', 0)}天剩余)")
        # ----------------

        # 检查是否需要设置初始密码或登录
        if not os.path.exists(FILES["password"]):
            self.show_initial_password_ui()
        else:
            self.show_login_ui()
    
    # --- 授权验证功能 ---
    def get_machine_code(self):
        """获取机器唯一特征码"""
        try:
            # 组合 MAC 地址和系统信息作为指纹
            node = uuid.getnode()
            system_info = f"{node}-{sys.platform}"
            return hashlib.md5(system_info.encode()).hexdigest().upper()[:12]
        except:
            return "UNKNOWN-DEVICE"

    def verify_key_content(self, key_str):
        """验证激活码内容，返回 (是否有效, 数据, 密钥类型)"""
        # 密钥类型: 'MACHINE' (本机绑定) 或 'UNIVERSAL' (通用序列号)
        # 数据: 对于 MACHINE 是过期日期字符串(YYYYMMDD); 对于 UNIVERSAL 是有效天数(int)
        
        clean_key = key_str.replace("-", "").strip()
        
        # 1. 尝试验证通用序列号 (Universal SN)
        # 格式: SN + Days(4) + Rand(8) + Sig(12) = 26 chars
        if clean_key.startswith("SN") and len(clean_key) == 26:
            days_hex = clean_key[2:6]
            rand_str = clean_key[6:14]
            signature = clean_key[14:]
            
            raw = "SN" + days_hex + rand_str + self.SALT
            expected_sig = hashlib.sha256(raw.encode()).hexdigest().upper()[:12]
            
            if signature == expected_sig:
                try:
                    days = int(days_hex, 16)
                    return True, days, 'UNIVERSAL'
                except:
                    pass

        # 2. 验证本机激活码 (Machine Bound)
        # 格式: Sig(16) + Date(8) = 24 chars
        if len(clean_key) == 24:
            signature = clean_key[:16]
            expire_str = clean_key[16:]
            
            machine_code = self.get_machine_code()
            raw = machine_code + expire_str + self.SALT
            expected_sig = hashlib.sha256(raw.encode()).hexdigest().upper()[:16]
            
            if signature == expected_sig:
                return True, expire_str, 'MACHINE'
                
        return False, None, None

    def check_time_tampering(self):
        """检查系统时间是否被回调 (反时间回溯)"""
        ts_file = os.path.join(BASE_DIR, "sys_config.bin")
        current_ts = datetime.datetime.now().timestamp()
        
        try:
            if os.path.exists(ts_file):
                with open(ts_file, "r") as f:
                    content = f.read().strip()
                    # 简单解密 (Base64)
                    try:
                        last_ts_str = base64.b64decode(content.encode()).decode()
                        last_ts = float(last_ts_str)
                        
                        # 允许 1 小时的误差，防止时区调整等误判
                        if current_ts < last_ts - 3600:
                            return True, f"检测到系统时间异常回退！\n当前: {datetime.datetime.fromtimestamp(current_ts)}\n记录: {datetime.datetime.fromtimestamp(last_ts)}"
                    except:
                        pass # 文件损坏或格式不对，重置
                        
            # 更新最新时间
            with open(ts_file, "w") as f:
                new_content = base64.b64encode(str(current_ts).encode()).decode()
                f.write(new_content)
                
            return False, ""
            
        except Exception as e:
            # 如果读写文件出错，暂时放行，以免影响正常使用
            return False, ""

    def check_license(self):
        """检查授权文件是否有效
        返回: (isValid, message)
        """
        # 0. 先检查时间篡改
        is_tampered, tamper_msg = self.check_time_tampering()
        if is_tampered:
            return False, tamper_msg

        if not os.path.exists(self.LICENSE_FILE):
            return False, "软件未激活"
            
        try:
            with open(self.LICENSE_FILE, 'r') as f:
                data = json.load(f)
                
            key = data.get('key', '')
            activated_at = data.get('activated_at', '未知')
            
            is_valid, key_data, key_type = self.verify_key_content(key)
            
            if not is_valid:
                return False, "授权文件损坏或机器码不匹配"
            
            if key_type == 'UNIVERSAL':
                return False, "检测到通用序列号，请在软件界面重新激活以绑定本机"
                
            # 此时 key_type == 'MACHINE'，key_data 是过期日期字符串
            expire_str = key_data
                
            # 检查日期
            expire_date = datetime.datetime.strptime(expire_str, "%Y%m%d").date()
            today = datetime.date.today()
            
            if today > expire_date:
                return False, f"授权已过期 (过期日: {expire_str})"
            
            days_left = (expire_date - today).days
            
            self.license_info = {
                "key": key,
                "expire_date": expire_str,
                "activated_at": activated_at,
                "days_left": days_left
            }
            
            return True, "OK"
            
        except Exception as e:
            return False, f"授权验证错误: {str(e)}"
            
    def show_activation_ui(self, message=""):
        """显示激活界面"""
        self.act_frame = tk.Frame(self.root, bg="#f0f2f5")
        self.act_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        card = tk.Frame(self.act_frame, bg="white", padx=50, pady=50, relief="raised", bd=1)
        card.place(relx=0.5, rely=0.5, anchor="center")
        
        tk.Label(card, text="系统激活", font=("微软雅黑", 24, "bold"), bg="white", fg="#333").pack(pady=(0, 10))
        if message:
            tk.Label(card, text=message, font=("微软雅黑", 12, "bold"), bg="white", fg="#d32f2f").pack(pady=(0, 10))
        tk.Label(card, text="本软件为付费软件，请激活后使用", font=("微软雅黑", 12), bg="white", fg="#666").pack(pady=(0, 20))
        
        mc = self.get_machine_code()
        
        # 机器码区域
        mc_frame = tk.Frame(card, bg="#f8f9fa", pady=10, padx=10, bd=1, relief="solid")
        mc_frame.pack(fill="x", pady=(0, 15))
        tk.Label(mc_frame, text="您的机器码：", font=("微软雅黑", 10), bg="#f8f9fa", fg="#666").pack(anchor="w")
        tk.Label(mc_frame, text=mc, font=("Consolas", 16, "bold"), bg="#f8f9fa", fg="#1976d2").pack(pady=5)
        
        def copy_mc():
            self.root.clipboard_clear()
            self.root.clipboard_append(mc)
            messagebox.showinfo("提示", "机器码已复制，请发送给管理员获取激活码！")
            
        tk.Button(card, text="复制机器码", command=copy_mc, bg="#e0e0e0", relief="flat", font=("微软雅黑", 10)).pack(pady=(0, 25))
        
        tk.Label(card, text="输入激活码 / 序列号：", font=("微软雅黑", 12, "bold"), bg="white", anchor="w").pack(fill="x")
        self.key_entry = tk.Entry(card, font=("Consolas", 14), width=35, bd=2, relief="solid", justify="center")
        self.key_entry.pack(pady=(5, 25), ipady=5)
        
        btn = tk.Button(card, text="立即激活", command=self.do_activate, font=("微软雅黑", 12, "bold"), bg="#1976d2", fg="white", relief="flat", padx=40, pady=10, cursor="hand2")
        btn.pack()
        
        tk.Label(card, text="联系方式: 微信：124714825", font=("微软雅黑", 10), bg="white", fg="#999").pack(pady=(20, 0))

    def do_activate(self):
        user_key = self.key_entry.get().strip()
        if not user_key:
            messagebox.showwarning("提示", "请输入激活码")
            return
            
        is_valid, key_data, key_type = self.verify_key_content(user_key)
        
        if is_valid:
            final_key = ""
            expire_str_display = ""
            
            if key_type == 'UNIVERSAL':
                # 通用序列号，转换为本机绑定码
                days = key_data
                expire_date = datetime.date.today() + datetime.timedelta(days=days)
                expire_str = expire_date.strftime("%Y%m%d")
                
                # 生成本机特征码签名
                mc = self.get_machine_code()
                raw = mc + expire_str + self.SALT
                sig = hashlib.sha256(raw.encode()).hexdigest().upper()[:16]
                
                final_key = sig + expire_str
                expire_str_display = expire_str
                
                messagebox.showinfo("提示", f"通用序列号验证成功！\n有效期 {days} 天\n已自动转换为本机绑定激活码。")
                
            else:
                # 本机绑定码
                expire_str = key_data
                expire_str_display = expire_str
                
                expire_date = datetime.datetime.strptime(expire_str, "%Y%m%d").date()
                if datetime.date.today() > expire_date:
                    messagebox.showerror("激活失败", f"该激活码已于 {expire_str} 过期！")
                    return
                
                final_key = user_key

            try:
                data = {
                    "key": final_key,
                    "activated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                with open(self.LICENSE_FILE, 'w') as f:
                    json.dump(data, f)
                messagebox.showinfo("成功", f"激活成功！\n有效期至: {expire_str_display}\n请重新启动软件以生效。")
                self.root.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"无法写入授权文件: {e}")
        else:
            messagebox.showerror("激活失败", "激活码无效，请检查输入是否正确。\n如果是本机激活码，请确保机器码匹配。")
    
    def load_main_application(self):
        """加载主应用程序(登录成功后调用)"""
        self.products = self.load_json(FILES["product"])
        for p in self.products:
            if '_checked' not in p: p['_checked'] = False
            if 'tag' not in p: p['tag'] = ""
            if 'cost_price' not in p: p['cost_price'] = 0
            if 'stock' not in p: p['stock'] = 0  # Initialize stock
            if '_id' not in p: p['_id'] = str(uuid.uuid4())

            
        self.history = self.load_json(FILES["history"])
        self.quote_history = self.load_json(FILES["quote"])
        self.inventory_history = self.load_json(FILES["inventory"])  # Load inventory history
        self.cart_items = []
        self.current_img_data = None 
        self.curr_bill_img = None     
        self.browser_idx = 0
        self.current_filter_tag = "全部"
        self.current_edit_bill_id = None
        self.side_vars = {}
        self.current_page = 1
        self.items_per_page = 5
        self._product_canvas_inited = False
        self.share_dir = None
        self.share_base_url = None
        self.load_share_config()
        self.gdrive_backup_dir = None
        self.load_backup_config()

        self.setup_ui()
        self.refresh_product_list()
        self.refresh_history_list()
        self.refresh_quote_history_list()
        if self.products: self.update_browser()

    def load_json(self, f):
        if os.path.exists(f):
            try:
                with open(f, "r", encoding="utf-8") as file: return json.load(file)
            except: return []
        return []

    def save_json(self, f, d):
        save_data = []
        for item in d:
            temp = item.copy()
            if '_checked' in temp: del temp['_checked']
            save_data.append(temp)
        with open(f, "w", encoding="utf-8") as file: json.dump(save_data, file, ensure_ascii=False, indent=2)
    
    # --- 密码管理功能 ---
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def show_login_ui(self):
        """在主窗口显示登录界面"""
        # 读取密码哈希
        with open(FILES["password"], "r", encoding="utf-8") as f:
            self.stored_hash = f.read().strip()
        
        # 创建登录框架
        self.login_frame = tk.Frame(self.root, bg="#f0f2f5")
        self.login_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # 创建居中容器
        center_frame = tk.Frame(self.login_frame, bg="white", relief="raised", bd=2, width=430, height=430)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")
        center_frame.pack_propagate(False)
        
        # 标题
        tk.Label(center_frame, text="鞋类产品报价开单系统", font=("微软雅黑", 21, "bold"), bg="white", fg="#1a1a1a").pack(pady=(30, 6))
        tk.Label(center_frame, text="V1.1 正式版", font=("微软雅黑", 12, "bold"), bg="white", fg="#1677ff").pack(pady=(0, 24))
        
        # 分隔线
        tk.Frame(center_frame, height=2, bg="#1677ff").pack(fill="x", padx=36, pady=(0, 24))
        
        # 密码输入区域
        input_frame = tk.Frame(center_frame, bg="white")
        input_frame.pack(pady=6, padx=48)
        
        tk.Label(input_frame, text="请输入系统密码", font=("微软雅黑", 13, "bold"), bg="white", fg="#1f1f1f").pack(pady=(0, 12))
        self.pwd_entry = tk.Entry(input_frame, show="●", width=30, font=("微软雅黑", 12), relief="solid", bd=1,
                                  highlightthickness=1, highlightbackground="#d9d9d9", highlightcolor="#1677ff")
        self.pwd_entry.pack(pady=6, ipady=6)
        self.pwd_entry.focus()
        
        # 按钮
        tk.Button(center_frame, text="登 录 Login", command=self.verify_login, bg="#1677ff", fg="white",
                 width=28, height=2, font=("微软雅黑", 12, "bold"), relief="flat", cursor="hand2",
                 activebackground="#0958d9").pack(pady=(26, 28), padx=48)
        
        # 绑定回车键
        self.pwd_entry.bind("<Return>", lambda e: self.verify_login())
    
    def verify_login(self):
        """验证登录密码"""
        input_hash = self.hash_password(self.pwd_entry.get())
        if input_hash == self.stored_hash:
            # 密码正确，销毁登录界面并加载主应用
            self.login_frame.destroy()
            self.load_main_application()
        else:
            messagebox.showerror("错误", "密码错误！")
            self.pwd_entry.delete(0, tk.END)
            self.pwd_entry.focus()
    
    def show_initial_password_ui(self):
        """在主窗口显示初始密码设置界面"""
        # 创建设置密码框架
        self.login_frame = tk.Frame(self.root, bg="#f0f2f5")
        self.login_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # 创建居中容器
        center_frame = tk.Frame(self.login_frame, bg="white", relief="raised", bd=2, width=430, height=510)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")
        center_frame.pack_propagate(False)
        
        # 标题
        tk.Label(center_frame, text="鞋类产品报价开单系统", font=("微软雅黑", 21, "bold"), bg="white", fg="#1a1a1a").pack(pady=(26, 6))
        tk.Label(center_frame, text="V1.1 正式版", font=("微软雅黑", 12, "bold"), bg="white", fg="#1677ff").pack(pady=(0, 10))
        tk.Label(center_frame, text="首次运行，请设置系统密码", font=("微软雅黑", 12, "bold"), bg="white", fg="#1677ff").pack(pady=(0, 24))
        
        # 分隔线
        tk.Frame(center_frame, height=2, bg="#1677ff").pack(fill="x", padx=36, pady=(0, 24))
        
        # 密码输入区域
        input_frame = tk.Frame(center_frame, bg="white")
        input_frame.pack(pady=6, padx=48)
        
        tk.Label(input_frame, text="设置新密码", font=("微软雅黑", 13, "bold"), bg="white", fg="#1f1f1f").pack(pady=(0, 10))
        self.pwd_entry1 = tk.Entry(input_frame, show="●", width=30, font=("微软雅黑", 12), relief="solid", bd=1,
                                  highlightthickness=1, highlightbackground="#d9d9d9", highlightcolor="#1677ff")
        self.pwd_entry1.pack(pady=(0, 12), ipady=6)
        
        tk.Label(input_frame, text="确认新密码", font=("微软雅黑", 13, "bold"), bg="white", fg="#1f1f1f").pack(pady=(10, 10))
        self.pwd_entry2 = tk.Entry(input_frame, show="●", width=30, font=("微软雅黑", 12), relief="solid", bd=1,
                                  highlightthickness=1, highlightbackground="#d9d9d9", highlightcolor="#1677ff")
        self.pwd_entry2.pack(pady=(0, 12), ipady=6)
        
        self.pwd_entry1.focus()
        
        # 按钮
        tk.Button(center_frame, text="保存密码并登录", command=self.save_initial_password, bg="#1677ff", fg="white",
                 width=28, height=2, font=("微软雅黑", 12, "bold"), relief="flat", cursor="hand2",
                 activebackground="#0958d9").pack(pady=(26, 28), padx=48)
        
        # 绑定回车键
        self.pwd_entry2.bind("<Return>", lambda e: self.save_initial_password())
    
    def save_initial_password(self):
        """保存初始密码"""
        pwd1 = self.pwd_entry1.get()
        pwd2 = self.pwd_entry2.get()
        if not pwd1:
            messagebox.showwarning("提示", "密码不能为空！")
            return
        if pwd1 != pwd2:
            messagebox.showerror("错误", "两次输入的密码不一致！")
            self.pwd_entry1.delete(0, tk.END)
            self.pwd_entry2.delete(0, tk.END)
            self.pwd_entry1.focus()
            return
        with open(FILES["password"], "w", encoding="utf-8") as f:
            f.write(self.hash_password(pwd1))
        messagebox.showinfo("成功", "密码设置成功！")
        # 销毁设置密码界面并加载主应用
        self.login_frame.destroy()
        self.load_main_application()
    
    def change_password(self):
        # 验证旧密码
        with open(FILES["password"], "r", encoding="utf-8") as f:
            stored_hash = f.read().strip()
        
        pwd_win = tk.Toplevel(self.root)
        pwd_win.title("修改密码")
        pwd_win.geometry("400x250")
        pwd_win.grab_set()
        pwd_win.resizable(False, False)
        
        pwd_win.update_idletasks()
        x = (pwd_win.winfo_screenwidth() // 2) - (pwd_win.winfo_width() // 2)
        y = (pwd_win.winfo_screenheight() // 2) - (pwd_win.winfo_height() // 2)
        pwd_win.geometry(f"+{x}+{y}")
        
        tk.Label(pwd_win, text="修改系统密码", font=("Arial", 10, "bold")).pack(pady=10)
        tk.Label(pwd_win, text="旧密码:", font=("Arial", 9)).pack(anchor="w", padx=30)
        old_pwd = tk.Entry(pwd_win, show="*", width=30, font=("Arial", 10))
        old_pwd.pack(pady=5)
        tk.Label(pwd_win, text="新密码:", font=("Arial", 9)).pack(anchor="w", padx=30)
        new_pwd1 = tk.Entry(pwd_win, show="*", width=30, font=("Arial", 10))
        new_pwd1.pack(pady=5)
        tk.Label(pwd_win, text="确认新密码:", font=("Arial", 9)).pack(anchor="w", padx=30)
        new_pwd2 = tk.Entry(pwd_win, show="*", width=30, font=("Arial", 10))
        new_pwd2.pack(pady=5)
        old_pwd.focus()
        
        def save_new_pwd():
            if self.hash_password(old_pwd.get()) != stored_hash:
                messagebox.showerror("错误", "旧密码错误！")
                old_pwd.delete(0, tk.END)
                old_pwd.focus()
                return
            pwd1 = new_pwd1.get()
            pwd2 = new_pwd2.get()
            if not pwd1:
                messagebox.showwarning("提示", "新密码不能为空！")
                return
            if pwd1 != pwd2:
                messagebox.showerror("错误", "两次输入的新密码不一致！")
                new_pwd1.delete(0, tk.END)
                new_pwd2.delete(0, tk.END)
                new_pwd1.focus()
                return
            with open(FILES["password"], "w", encoding="utf-8") as f:
                f.write(self.hash_password(pwd1))
            messagebox.showinfo("成功", "密码修改成功！")
            pwd_win.destroy()
        
        new_pwd2.bind("<Return>", lambda e: save_new_pwd())
        tk.Button(pwd_win, text="确定", command=save_new_pwd, bg="#4caf50", fg="white", width=10, font=("Arial", 9, "bold")).pack(pady=10)
    
    # --- 商品导入导出功能 ---
    def export_products(self):
        if not self.products:
            messagebox.showinfo("提示", "没有商品可导出！")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")], title="导出商品")
        if path:
            try:
                with open(path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(f, fieldnames=["no", "tag", "color", "size", "price", "cost_price", "pcs", "moq_ctns", "img"])
                    writer.writeheader()
                    for p in self.products:
                        writer.writerow({
                            "no": p.get("no", ""),
                            "tag": p.get("tag", ""),
                            "color": p.get("color", ""),
                            "size": p.get("size", ""),
                            "price": p.get("price", ""),
                            "cost_price": p.get("cost_price", ""),
                            "pcs": p.get("pcs", ""),
                            "moq_ctns": p.get("moq_ctns", ""),
                            "img": p.get("img", "")
                        })
                messagebox.showinfo("成功", f"商品已导出到：\n{path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败：{str(e)}")
    
    def import_products(self):
        path = filedialog.askopenfilename(filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")], title="导入商品")
        if path:
            try:
                imported = []
                with open(path, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # 允许重复货号，直接添加
                        self.products.append({
                            "no": row.get("no", ""),
                            "tag": row.get("tag", ""),
                            "color": row.get("color", ""),
                            "size": row.get("size", ""),
                            "price": float(row.get("price", 0) or 0),
                            "cost_price": float(row.get("cost_price", 0) or 0),
                            "pcs": int(row.get("pcs", 0) or 0),
                            "moq_ctns": int(row.get("moq_ctns", 0) or 0),
                            "img": row.get("img", ""),
                            "_checked": False,
                            "_id": str(uuid.uuid4())
                        })
                        imported.append(row.get("no"))
                self.save_json(FILES["product"], self.products)
                self.refresh_product_list()
                messagebox.showinfo("成功", f"成功导入 {len(imported)} 个商品！")
            except Exception as e:
                messagebox.showerror("错误", f"导入失败：{str(e)}")
    
    def backup_data(self):
        win = tk.Toplevel(self.root)
        win.title("选择备份内容")
        win.resizable(False, False)
        win.minsize(320, 260)
        win.grab_set()
        win.transient(self.root)

        win.update_idletasks()
        x = (win.winfo_screenwidth() // 2) - (win.winfo_width() // 2)
        y = (win.winfo_screenheight() // 2) - (win.winfo_height() // 2)
        win.geometry(f"+{x}+{y}")

        title = tk.Label(win, text="请选择需要备份的数据", font=self.fonts['subtitle'])
        title.pack(pady=(16, 8))

        all_var = tk.BooleanVar(value=True)
        prod_var = tk.BooleanVar(value=True)
        quote_var = tk.BooleanVar(value=True)
        history_var = tk.BooleanVar(value=True)

        def on_all_toggle():
            v = all_var.get()
            prod_var.set(v)
            quote_var.set(v)
            history_var.set(v)

        def refresh_all_var(*args):
            if prod_var.get() and quote_var.get() and history_var.get():
                all_var.set(True)
            else:
                all_var.set(False)

        prod_var.trace_add("write", lambda *a: refresh_all_var())
        quote_var.trace_add("write", lambda *a: refresh_all_var())
        history_var.trace_add("write", lambda *a: refresh_all_var())

        body = tk.Frame(win)
        body.pack(pady=4)

        tk.Checkbutton(body, text="全部", variable=all_var, command=on_all_toggle, font=self.fonts['body']).pack(anchor="w", padx=24, pady=2)
        tk.Checkbutton(body, text="商品数据", variable=prod_var, font=self.fonts['body']).pack(anchor="w", padx=40, pady=2)
        tk.Checkbutton(body, text="报价记录", variable=quote_var, font=self.fonts['body']).pack(anchor="w", padx=40, pady=2)
        tk.Checkbutton(body, text="销售记录", variable=history_var, font=self.fonts['body']).pack(anchor="w", padx=40, pady=2)

        hint = tk.Label(win, text="提示：勾选的项目将备份到同一个文件夹。", font=self.fonts['small'], fg="#666")
        hint.pack(pady=(4, 0))

        btn_row = tk.Frame(win)
        btn_row.pack(pady=12)

        def on_ok():
            selected_keys = []
            label_map = {"product": "商品数据", "quote": "报价记录", "history": "销售记录"}
            if prod_var.get():
                selected_keys.append("product")
            if quote_var.get():
                selected_keys.append("quote")
            if history_var.get():
                selected_keys.append("history")
            if not selected_keys:
                messagebox.showwarning("提示", "请至少选择一项需要备份的数据。")
                return
            win.destroy()
            folder = filedialog.askdirectory(title="选择备份保存位置")
            if not folder:
                return
            try:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                if len(selected_keys) == 3:
                    type_tag = "all"
                else:
                    code_map = {"product": "prod", "quote": "quote", "history": "history"}
                    type_tag = "_".join(code_map[k] for k in selected_keys)
                backup_folder = os.path.join(folder, f"backup_{timestamp}_{type_tag}")
                os.makedirs(backup_folder, exist_ok=True)
                for name, file_path in FILES.items():
                    if name == "password":
                        continue
                    if name not in selected_keys:
                        continue
                    if os.path.exists(file_path):
                        shutil.copy2(file_path, os.path.join(backup_folder, os.path.basename(file_path)))
                labels = [label_map[k] for k in selected_keys]
                messagebox.showinfo("成功", f"数据备份完成！\n备份位置：{backup_folder}\n备份内容：{', '.join(labels)}")
            except Exception as e:
                messagebox.showerror("错误", f"备份失败：{str(e)}")

        def on_cancel():
            win.destroy()

        tk.Button(btn_row, text="取消", command=on_cancel, bg="#d9d9d9", fg="#1f1f1f",
                  font=self.fonts['button'], relief="flat", cursor="hand2",
                  padx=16, pady=6, activebackground="#bfbfbf").pack(side="right", padx=6)
        tk.Button(btn_row, text="开始备份", command=on_ok, bg="#3498db", fg="white",
                  font=self.fonts['button'], relief="flat", cursor="hand2",
                  padx=16, pady=6, activebackground="#2980b9").pack(side="right", padx=6)
    
    def restore_data(self):
        if not messagebox.askyesno("确认", "恢复数据将覆盖当前选中的数据，是否继续？"):
            return
        folder = filedialog.askdirectory(title="选择备份文件夹")
        if not folder:
            return
        available = {}
        for name, file_path in FILES.items():
            if name == "password":
                continue
            backup_file = os.path.join(folder, os.path.basename(file_path))
            if os.path.exists(backup_file):
                available[name] = backup_file
        label_map = {"product": "商品数据", "quote": "报价记录", "history": "销售记录"}
        if not available:
            messagebox.showwarning("提示", "选定文件夹中未找到可用的备份文件。")
            return
        win = tk.Toplevel(self.root)
        win.title("选择恢复内容")
        win.resizable(False, False)
        win.minsize(320, 260)
        win.grab_set()
        win.transient(self.root)

        win.update_idletasks()
        x = (win.winfo_screenwidth() // 2) - (win.winfo_width() // 2)
        y = (win.winfo_screenheight() // 2) - (win.winfo_height() // 2)
        win.geometry(f"+{x}+{y}")

        tk.Label(win, text="请选择需要恢复的数据", font=self.fonts['subtitle']).pack(pady=(12, 4))

    def backup_to_gdrive(self):
        folder = getattr(self, "gdrive_backup_dir", None)
        if not folder or not os.path.isdir(folder):
            folder = filedialog.askdirectory(title="选择 Google Drive 备份文件夹")
            if not folder:
                return
            self.save_backup_config(folder)
        try:
            selected_keys = ["product", "quote", "history"]
            label_map = {"product": "商品数据", "quote": "报价记录", "history": "销售记录"}
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_folder = os.path.join(folder, f"backup_{timestamp}_all")
            os.makedirs(backup_folder, exist_ok=True)
            for name, file_path in FILES.items():
                if name == "password":
                    continue
                if name not in selected_keys:
                    continue
                if os.path.exists(file_path):
                    shutil.copy2(file_path, os.path.join(backup_folder, os.path.basename(file_path)))
            labels = [label_map[k] for k in selected_keys]
            messagebox.showinfo("成功", f"已备份到 Google Drive 文件夹：\n{backup_folder}\n备份内容：{', '.join(labels)}")
        except Exception as e:
            messagebox.showerror("错误", f"备份失败：{str(e)}")

        mode_frame = tk.Frame(win)
        mode_frame.pack(pady=(0, 4))
        mode_var = tk.StringVar(value="overwrite")
        tk.Radiobutton(mode_frame, text="完全覆盖", variable=mode_var, value="overwrite",
                       font=self.fonts['body']).pack(side="left", padx=6)
        tk.Radiobutton(mode_frame, text="追加合并", variable=mode_var, value="append",
                       font=self.fonts['body']).pack(side="left", padx=6)

        all_var = tk.BooleanVar(value=True)
        prod_var = tk.BooleanVar(value="product" in available)
        quote_var = tk.BooleanVar(value="quote" in available)
        history_var = tk.BooleanVar(value="history" in available)

        def refresh_children():
            v = all_var.get()
            if "product" in available:
                prod_var.set(v)
            if "quote" in available:
                quote_var.set(v)
            if "history" in available:
                history_var.set(v)

        def refresh_all(*args):
            values = []
            for key, var in [("product", prod_var), ("quote", quote_var), ("history", history_var)]:
                if key in available:
                    values.append(var.get())
            if values and all(values):
                all_var.set(True)
            else:
                all_var.set(False)

        prod_var.trace_add("write", lambda *a: refresh_all())
        quote_var.trace_add("write", lambda *a: refresh_all())
        history_var.trace_add("write", lambda *a: refresh_all())

        body = tk.Frame(win)
        body.pack(pady=4)

        tk.Checkbutton(body, text="全部", variable=all_var, command=refresh_children, font=self.fonts['body']).pack(anchor="w", padx=24, pady=2)
        tk.Checkbutton(body, text="商品数据", variable=prod_var, state="normal" if "product" in available else "disabled", font=self.fonts['body']).pack(anchor="w", padx=40, pady=2)
        tk.Checkbutton(body, text="报价记录", variable=quote_var, state="normal" if "quote" in available else "disabled", font=self.fonts['body']).pack(anchor="w", padx=40, pady=2)
        tk.Checkbutton(body, text="销售记录", variable=history_var, state="normal" if "history" in available else "disabled", font=self.fonts['body']).pack(anchor="w", padx=40, pady=2)

        tk.Label(win, text="提示：仅会恢复当前文件夹中存在的备份文件。", font=self.fonts['small'], fg="#666").pack(pady=(4, 0))

        btn_row = tk.Frame(win)
        btn_row.pack(pady=12)

        def on_ok():
            selected = []
            if prod_var.get() and "product" in available:
                selected.append("product")
            if quote_var.get() and "quote" in available:
                selected.append("quote")
            if history_var.get() and "history" in available:
                selected.append("history")
            if not selected:
                messagebox.showwarning("提示", "请至少选择一项需要恢复的数据。")
                return
            try:
                mode = mode_var.get()
                details = []
                for name in selected:
                    backup_file = available.get(name)
                    if not backup_file:
                        continue
                    try:
                        with open(backup_file, "r", encoding="utf-8") as f:
                            backup_data = json.load(f)
                    except Exception:
                        backup_data = []
                    if not isinstance(backup_data, list):
                        backup_data = []
                    count_backup = len(backup_data)
                    file_path = FILES[name]
                    if mode == "overwrite":
                        if os.path.exists(file_path):
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    current_data = json.load(f)
                                if not isinstance(current_data, list):
                                    current_data = []
                            except Exception:
                                current_data = []
                        else:
                            current_data = []
                        shutil.copy2(backup_file, file_path)
                        details.append(f"{label_map.get(name, name)}：覆盖 {len(current_data)} 条，写入 {count_backup} 条")
                    else:
                        if os.path.exists(file_path):
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    current_data = json.load(f)
                                if not isinstance(current_data, list):
                                    current_data = []
                            except Exception:
                                current_data = []
                        else:
                            current_data = []
                        existing = set()
                        # 商品数据允许货号重复，这里用内部 _id 作为去重键；
                        # 如果老备份没有 _id，则退回到 (no+size+color) 组合键。
                        if name == "product":
                            for it in current_data:
                                kid = it.get("_id")
                                if not kid:
                                    kid = f"{it.get('no','')}|{it.get('size','')}|{it.get('color','')}"
                                kid = str(kid)
                                if kid:
                                    existing.add(kid)
                            appended = 0
                            for it in backup_data:
                                kid = it.get("_id")
                                if not kid:
                                    kid = f"{it.get('no','')}|{it.get('size','')}|{it.get('color','')}"
                                kid = str(kid)
                                if kid and kid in existing:
                                    continue
                                current_data.append(it)
                                if kid:
                                    existing.add(kid)
                                appended += 1
                        else:
                            for it in current_data:
                                k = str(it.get("id", ""))
                                if k:
                                    existing.add(k)
                            appended = 0
                            for it in backup_data:
                                k = str(it.get("id", ""))
                                if k and k in existing:
                                    continue
                                current_data.append(it)
                                if k:
                                    existing.add(k)
                                appended += 1
                        merged = current_data
                        try:
                            with open(file_path, "w", encoding="utf-8") as f:
                                json.dump(merged, f, ensure_ascii=False, indent=2)
                        except Exception:
                            shutil.copy2(backup_file, file_path)
                            merged = backup_data
                            appended = count_backup
                        details.append(f"{label_map.get(name, name)}：去重追加 {appended} 条，合计 {len(merged)} 条")
                if details:
                    win.destroy()
                    messagebox.showinfo("成功", "数据恢复完成！\n" + "\n".join(details) + "\n请重启程序以加载恢复的数据。")
                    self.root.quit()
                else:
                    messagebox.showwarning("提示", "未找到可恢复的数据。")
            except Exception as e:
                messagebox.showerror("错误", f"恢复失败：{str(e)}")

        def on_cancel():
            win.destroy()

        tk.Button(btn_row, text="取消", command=on_cancel, bg="#d9d9d9", fg="#1f1f1f",
                  font=self.fonts['button'], relief="flat", cursor="hand2",
                  padx=16, pady=6, activebackground="#bfbfbf").pack(side="right", padx=6)
        tk.Button(btn_row, text="开始恢复", command=on_ok, bg="#e67e22", fg="white",
                  font=self.fonts['button'], relief="flat", cursor="hand2",
                  padx=16, pady=6, activebackground="#d35400").pack(side="right", padx=6)

    def load_share_config(self):
        self.share_dir = None
        self.share_base_url = None
        self.share_auto_push = False
        self.share_git_remote = "origin"
        self.share_git_branch = "main"
        self.share_file_map = {}
        if os.path.exists(SHARE_CONFIG_PATH):
            try:
                with open(SHARE_CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.share_dir = cfg.get("dir") or None
                self.share_base_url = cfg.get("base_url") or None
                self.share_auto_push = bool(cfg.get("auto_push", False))
                self.share_git_remote = cfg.get("git_remote") or "origin"
                self.share_git_branch = cfg.get("git_branch") or "main"
                m = cfg.get("file_map")
                if isinstance(m, dict):
                    self.share_file_map = m
                else:
                    self.share_file_map = {}
            except Exception:
                self.share_dir = None
                self.share_base_url = None
                self.share_auto_push = False
                self.share_git_remote = "origin"
                self.share_git_branch = "main"
                self.share_file_map = {}

    def load_backup_config(self):
        self.gdrive_backup_dir = None
        if os.path.exists(BACKUP_CONFIG_PATH):
            try:
                with open(BACKUP_CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.gdrive_backup_dir = cfg.get("gdrive_dir") or None
            except Exception:
                self.gdrive_backup_dir = None

    def save_backup_config(self, dir_path):
        try:
            cfg = {"gdrive_dir": dir_path or ""}
            with open(BACKUP_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            return
        self.gdrive_backup_dir = dir_path or None

    def save_share_config(self, dir_path, base_url, auto_push, git_remote, git_branch):
        try:
            cfg = {}
            if os.path.exists(SHARE_CONFIG_PATH):
                try:
                    with open(SHARE_CONFIG_PATH, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                except Exception:
                    cfg = {}
            cfg["dir"] = dir_path or ""
            cfg["base_url"] = base_url or ""
            cfg["auto_push"] = bool(auto_push)
            cfg["git_remote"] = git_remote or "origin"
            cfg["git_branch"] = git_branch or "main"
            file_map = getattr(self, "share_file_map", None)
            if isinstance(file_map, dict):
                cfg["file_map"] = file_map
            with open(SHARE_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            return
        self.share_dir = dir_path or None
        self.share_base_url = base_url or None
        self.share_auto_push = bool(auto_push)
        self.share_git_remote = git_remote or "origin"
        self.share_git_branch = git_branch or "main"

    def get_share_remote_name(self, fname):
        file_map = getattr(self, "share_file_map", None)
        if not isinstance(file_map, dict):
            file_map = {}
        remote = file_map.get(fname)
        if not remote:
            ext = os.path.splitext(fname)[1]
            remote = uuid.uuid4().hex + ext
            file_map[fname] = remote
            self.share_file_map = file_map
            try:
                self.save_share_config(
                    getattr(self, "share_dir", None),
                    getattr(self, "share_base_url", None),
                    getattr(self, "share_auto_push", False),
                    getattr(self, "share_git_remote", "origin"),
                    getattr(self, "share_git_branch", "main"),
                )
            except Exception:
                pass
        return remote

    def sync_share_file(self, local_path, fname, silent=False):
        dir_path = getattr(self, "share_dir", None)
        if not dir_path:
            return
        try:
            os.makedirs(dir_path, exist_ok=True)
            remote_name = fname
            try:
                remote_name = self.get_share_remote_name(fname)
            except Exception:
                remote_name = fname
            target_path = os.path.join(dir_path, remote_name)
            shutil.copy2(local_path, target_path)
            base_url = getattr(self, "share_base_url", None)
            if base_url:
                url = base_url.rstrip("/") + "/" + remote_name
                if not silent:
                    try:
                        self.root.clipboard_clear()
                        self.root.clipboard_append(url)
                    except Exception:
                        pass
                    try:
                        messagebox.showinfo("分享链接", "已同步到分享目录，并复制链接到剪贴板：\n" + url)
                    except Exception:
                        pass
            if getattr(self, "share_auto_push", False):
                self.git_auto_push(remote_name)
        except Exception:
            pass

    def write_and_open(self, html, fname):
        f_path = os.path.join(BASE_DIR, fname)
        with open(f_path, "w", encoding="utf-8") as f:
            f.write(html)
        webbrowser.open('file://' + os.path.realpath(f_path))

    def process_image(self, image, target, size=(320, 240)):
        if not image: return None
        img_original = image.convert("RGB")
        img = img_original.copy()
        img.thumbnail(size, Image.Resampling.LANCZOS)
        new_img = Image.new("RGB", size, (245, 245, 245)) 
        x = (size[0] - img.size[0]) // 2
        y = (size[1] - img.size[1]) // 2
        new_img.paste(img, (x, y))
        tk_img = ImageTk.PhotoImage(new_img)
        target.config(image=tk_img, text="")
        target.image = tk_img
        buf = BytesIO()
        img_original.save(buf, format="JPEG", quality=95)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def open_share_settings(self):
        win = tk.Toplevel(self.root)
        win.title("GitHub Pages 分享设置")
        win.geometry("700x360")
        win.minsize(700, 320)
        win.resizable(True, True)
        win.grab_set()
        win.configure(bg="#f5f5f5")

        frame = tk.Frame(win, bg="#f5f5f5")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        row1 = tk.Frame(frame, bg="#f5f5f5")
        row1.pack(fill="x", pady=8)
        tk.Label(row1, text="本地分享目录（GitHub Pages 仓库路径）:", bg="#f5f5f5",
                 fg="#1f1f1f", font=self.fonts['body']).pack(side="left")
        dir_frame = tk.Frame(row1, bg="#f5f5f5")
        dir_frame.pack(fill="x", expand=True, side="left", padx=(10, 0))
        dir_var = tk.StringVar(value=self.share_dir or "")
        ent_dir = tk.Entry(dir_frame, textvariable=dir_var, font=self.fonts['body'])
        ent_dir.pack(side="left", fill="x", expand=True)
        def choose_dir():
            p = filedialog.askdirectory(title="选择 GitHub Pages 本地目录")
            if p:
                dir_var.set(p)
        tk.Button(dir_frame, text="浏览", command=choose_dir, bg="#d9d9d9", fg="#1f1f1f",
                 font=self.fonts['small'], relief="flat", cursor="hand2",
                 padx=10, pady=4, activebackground="#bfbfbf").pack(side="left", padx=(8, 0))

        row2 = tk.Frame(frame, bg="#f5f5f5")
        row2.pack(fill="x", pady=8)
        tk.Label(row2, text="在线基础 URL（例如：https://用户名.github.io/仓库 或 https://你的域名）:", bg="#f5f5f5",
                 fg="#1f1f1f", font=self.fonts['body']).pack(side="left")
        url_var = tk.StringVar(value=self.share_base_url or "")
        ent_url = tk.Entry(row2, textvariable=url_var, font=self.fonts['body'])
        ent_url.pack(side="left", fill="x", expand=True, padx=(10, 0))

        row3 = tk.Frame(frame, bg="#f5f5f5")
        row3.pack(fill="x", pady=8)
        auto_push_var = tk.BooleanVar(value=getattr(self, "share_auto_push", False))
        tk.Checkbutton(row3, text="自动执行 git add/commit/push 推送到远程仓库",
                       variable=auto_push_var, bg="#f5f5f5",
                       font=self.fonts['small'], anchor="w").pack(anchor="w")

        row4 = tk.Frame(frame, bg="#f5f5f5")
        row4.pack(fill="x", pady=4)
        tk.Label(row4, text="远程名称:", bg="#f5f5f5",
                 fg="#666666", font=self.fonts['small']).pack(side="left")
        remote_var = tk.StringVar(value=getattr(self, "share_git_remote", "origin"))
        tk.Entry(row4, textvariable=remote_var, width=10,
                 font=self.fonts['small']).pack(side="left", padx=(4, 12))
        tk.Label(row4, text="分支名称:", bg="#f5f5f5",
                 fg="#666666", font=self.fonts['small']).pack(side="left")
        branch_var = tk.StringVar(value=getattr(self, "share_git_branch", "main"))
        tk.Entry(row4, textvariable=branch_var, width=10,
                 font=self.fonts['small']).pack(side="left", padx=(4, 0))

        hint_row = tk.Frame(frame, bg="#f5f5f5")
        hint_row.pack(fill="x", pady=4)
        tk.Label(hint_row, text="生成的报价单和销售单 HTML 会复制到该目录，",
                 bg="#f5f5f5", fg="#666666",
                 font=self.fonts['small']).pack(anchor="w")
        tk.Label(hint_row, text="并使用基础 URL + 文件名 组成可分享链接。",
                 bg="#f5f5f5", fg="#666666",
                 font=self.fonts['small']).pack(anchor="w")

        btn_row = tk.Frame(frame, bg="#f5f5f5")
        btn_row.pack(fill="x", pady=10)
        def on_save():
            d = dir_var.get().strip()
            u = url_var.get().strip()
            self.save_share_config(d, u, auto_push_var.get(),
                                   remote_var.get().strip(), branch_var.get().strip())
            win.destroy()
            messagebox.showinfo("保存成功", "GitHub Pages 分享设置已保存。")
        tk.Button(btn_row, text="取消", command=win.destroy, bg="#d9d9d9", fg="#1f1f1f",
                 font=self.fonts['button'], relief="flat", cursor="hand2",
                 padx=16, pady=6, activebackground="#bfbfbf").pack(side="right", padx=6)
        tk.Button(btn_row, text="保存设置", command=on_save, bg="#3498db", fg="white",
                 font=self.fonts['button'], relief="flat", cursor="hand2",
                 padx=16, pady=6, activebackground="#2980b9").pack(side="right", padx=6)

    def git_auto_push(self, fname):
        dir_path = getattr(self, "share_dir", None)
        if not dir_path:
            return
        remote = getattr(self, "share_git_remote", "origin") or "origin"
        branch = getattr(self, "share_git_branch", "main") or "main"
        try:
            subprocess.run(["git", "add", fname], cwd=dir_path,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            msg = f"Update {fname}"
            subprocess.run(["git", "commit", "-m", msg], cwd=dir_path,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            r = subprocess.run(["git", "push", remote, branch], cwd=dir_path,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if r.returncode != 0:
                try:
                    messagebox.showwarning("Git 推送失败",
                                           "已生成分享文件，但 git push 失败，请手动检查仓库：\n" +
                                           r.stderr[:200])
                except Exception:
                    pass
        except Exception:
            try:
                messagebox.showwarning("Git 推送异常",
                                       "已生成分享文件，但执行 git 命令时出现异常，请手动推送。")
            except Exception:
                pass

    def get_clipboard_image(self):
        try:
            data = ImageGrab.grabclipboard()
            if isinstance(data, Image.Image):
                return data
            if isinstance(data, list) and data:
                first = data[0]
                if isinstance(first, str) and os.path.exists(first):
                    try:
                        return Image.open(first)
                    except Exception:
                        return None
            return None
        except Exception:
            return None

    # --- 报价单生成 (V18.0 完全复刻参考图) ---
    def gen_quotation_html(self, d):
        lang = self.quote_print_lang_var.get()
        t = self.TRANS.get(lang, self.TRANS['en'])

        rows = ""
        for i, it in enumerate(d['items']):
            moq_ctns = int(it.get('moq_ctns', 0) or 0)
            pcs_per_ctn = int(it.get('pcs', 0) or 0)
            total_qty = moq_ctns * pcs_per_ctn
            
            rows += f"""
            <tr style="text-align:center; height:100px;">
                <td style="border:1px solid #ddd; padding:8px;">
                    <img src="data:image/jpeg;base64,{it['img'] or ''}" style="height:90px; max-width:120px; object-fit:contain;">
                </td>
                <td style="border:1px solid #ddd; padding:8px;">{it['no']}</td>
                <td style="border:1px solid #ddd; padding:10px; font-size:14px; white-space:nowrap;">{it['size']}</td>
                <td style="border:1px solid #ddd; padding:8px;">{it['color']}</td>
                <td style="border:1px solid #ddd; padding:8px;">{moq_ctns}</td>
                <td style="border:1px solid #ddd; padding:8px;">{pcs_per_ctn}</td>
                <td style="border:1px solid #ddd; padding:8px; font-weight:bold; color:#d32f2f;">{total_qty}</td>
                <td style="border:1px solid #ddd; padding:8px; font-weight:bold;">¥{it['price']:.2f}</td>
            </tr>"""

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; padding: 40px; color: #333; }}
                .header-table {{ width: 100%; margin-bottom: 20px; border:none; }}
                .title {{ font-size: 36px; font-weight: bold; text-align: center; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 2px; }}
                .line {{ border-bottom: 3px solid #000; margin-bottom: 20px; }}
                .meta-info {{ font-size: 16px; margin-bottom: 10px; line-height: 1.6; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }}
                th {{ background: #333; color: #fff; padding: 15px 5px; text-transform: uppercase; border: 1px solid #333; }}
                .footer-note {{ margin-top: 30px; font-size: 13px; color: #666; font-style: italic; }}
                /* 打印页码设置 */
                body {{ counter-reset: page; }}
                .page-numbering {{
                    display: none;
                    position: fixed;
                    bottom: 10px;
                    right: 20px;
                    font-size: 12px;
                    color: #666;
                }}
                @media print {{ 
                    .no-print {{ display: none; }} 
                    .page-numbering {{ 
                        display: block; 
                        counter-increment: page; 
                    }}
                    .page-numbering::after {{
                        content: "第 " counter(page) " 页 / Page " counter(page);
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="title">{t['title_quotation']}</div>
            <div class="line"></div>
            
            <table class="header-table">
                <tr>
                    <td class="meta-info" style="width: 60%; vertical-align: top;">
                        <div style="margin-bottom: 5px;"><span style="display:inline-block; width:110px; white-space:nowrap;"><b>{t['client']}:</b></span> {d.get('client', '-')}</div>
                        <div style="margin-bottom: 5px;"><span style="display:inline-block; width:110px; white-space:nowrap;"><b>{t['ref']}:</b></span> {d['id']}</div>
                    </td>
                    <td class="meta-info" style="width: 40%; vertical-align: top; text-align: right;">
                        <div style="margin-bottom: 5px;"><span style="display:inline-block; width:100px; text-align:left; white-space:nowrap;"><b>{t['date']}:</b></span> {d['date']}</div>
                    </td>
                </tr>
            </table>

            <table>
                <thead>
                    <tr>
                        <th width="140">{t['photo']}</th>
                        <th width="100">{t['no']}</th>
                        <th width="120">{t['size']}</th>
                        <th width="100">{t['color']}</th>
                        <th width="90">{t['moq']}</th>
                        <th width="80">{t['pcs_ctn']}</th>
                        <th width="100">{t['qty']}</th>
                        <th width="110">{t['price']}</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>

            <div class="footer-note">
                {t['valid_note']}
            </div>

            <div class="page-numbering"></div>

            <button class="no-print" onclick="window.print()" style="position:fixed; bottom:30px; right:30px; padding:15px 40px; background:#333; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold; box-shadow: 0 4px 10px rgba(0,0,0,0.2);">{t['print_quotation']}</button>
        </body>
        </html>"""
        self.write_and_open(html, f"Quote_{d['id']}.html")

    # --- 报价单生成（大图模式 - 网格布局） ---
    def gen_quotation_html_large_image(self, d, cols=3):
        """生成大图模式的报价单，网格布局，列数可变"""
        lang = self.quote_print_lang_var.get()
        t = self.TRANS.get(lang, self.TRANS['en'])
        
        # 计算每行cols个商品
        items = d['items']
        grid_items = ""
        
        # 精确计算宽度: calc((100% - (cols - 1) * gap) / cols)
        gap = 20
        gap_total = (cols - 1) * gap
        width_style = f"calc((100% - {gap_total}px) / {cols})"
        
        for i in range(0, len(items), cols):
            row_items = items[i:i+cols]
            grid_items += f'<div style="display: flex; justify-content: flex-start; margin-bottom: 30px; page-break-inside: avoid; gap: {gap}px;">'
            
            for it in row_items:
                moq_ctns = int(it.get('moq_ctns', 0) or 0)
                pcs_per_ctn = int(it.get('pcs', 0) or 0)
                total_qty = moq_ctns * pcs_per_ctn
                packing = f"{pcs_per_ctn} PCS/CTN"
                moq_text = f"{moq_ctns} CTNS ({total_qty} PAIRS)" if moq_ctns > 0 and pcs_per_ctn > 0 else "--"
                
                grid_items += f"""
                <div style="flex: 0 0 {width_style}; min-width: 0; text-align: center; border: 1px solid #e0e0e0; padding: 20px; background: #fff; border-radius: 4px;">
                    <div style="margin-bottom: 15px; width: 100%; aspect-ratio: 1 / 1; display: flex; align-items: center; justify-content: center; background: #f9f9f9; border-radius: 4px; overflow: hidden;">
                        <img src="data:image/jpeg;base64,{it.get('img', '')}" 
                             style="width: 100%; height: 100%; object-fit: contain;">
                    </div>
                    <div style="font-size: 13px; font-weight: bold; margin-bottom: 8px; color: #333; text-align: left; padding-left: 5px;">
                        {t['no']}: {it.get('no', '--')}
                    </div>
                    <div style="font-size: 12px; margin-bottom: 5px; color: #666; text-align: left; padding-left: 5px;">
                        {t['color']}: {it.get('color', '--')}
                    </div>
                    <div style="font-size: 12px; margin-bottom: 5px; color: #666; text-align: left; padding-left: 5px;">
                        {t['size']}: {it.get('size', '--')}
                    </div>
                    <div style="font-size: 14px; font-weight: bold; margin-top: 10px; margin-bottom: 8px; color: #d32f2f; text-align: left; padding-left: 5px;">
                        {t['price']}: ¥{float(it.get('price', 0)):.2f}
                    </div>
                    <div style="font-size: 12px; margin-top: 8px; margin-bottom: 4px; color: #555; text-align: left; padding-left: 5px; border-top: 1px solid #eee; padding-top: 8px;">
                        Packing: {packing}
                    </div>
                    <div style="font-size: 12px; margin-bottom: 4px; color: #555; text-align: left; padding-left: 5px;">
                        {t['moq'].split('(')[0]}: {moq_text}
                    </div>
                </div>"""
            
            # 如果最后一行不足 cols 个，补齐空白 div 以保持左对齐布局（虽然 flex justify-content: flex-start 已经处理了，但为了严谨）
            # 其实 flex-start 足够了，不需要补齐
            
            grid_items += '</div>'
        
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                * {{ box-sizing: border-box; }}
                body {{ 
                    font-family: 'Segoe UI', Arial, 'Microsoft YaHei', sans-serif; 
                    padding: 40px 60px; 
                    color: #333; 
                    background: #f5f5f5;
                }}
                .quotation-container {{
                    background: white;
                    padding: 40px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    width: 100%;
                    max-width: 100%;
                }}
                .title {{
                    font-size: 42px;
                    font-weight: bold;
                    text-align: center;
                    margin-bottom: 30px;
                    text-transform: uppercase;
                    letter-spacing: 3px;
                    color: #1a1a1a;
                }}
                .header-info {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 30px;
                    padding-bottom: 15px;
                    border-bottom: 2px solid #333;
                }}
                .header-left, .header-right {{
                    font-size: 14px;
                    line-height: 1.8;
                }}
                .header-left div, .header-right div {{
                    margin-bottom: 5px;
                }}
                .header-label {{
                    font-weight: bold;
                    color: #555;
                }}
                .product-grid {{
                    margin: 30px 0;
                    width: 100%;
                }}
                .footer-info {{
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    font-size: 14px;
                    line-height: 2;
                }}
                .footer-info div {{
                    margin-bottom: 5px;
                }}
                .disclaimer {{
                    margin-top: 30px;
                    font-size: 12px;
                    color: #666;
                    font-style: italic;
                    line-height: 1.6;
                }}
                @media print {{
                    .no-print {{ display: none; }}
                    body {{ 
                        padding: 0;
                        margin: 0;
                        background: white;
                        width: 100%;
                    }}
                    .quotation-container {{
                        box-shadow: none;
                        padding: 0;
                        margin: 0;
                        width: 100%;
                    }}
                    @page {{
                        margin: 1cm;
                        size: auto;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="quotation-container">
                <div class="title">{t['title_quotation']}</div>
                
                <div class="header-info">
                    <div class="header-left">
                        <div><span class="header-label">{t['client']}:</span> {d.get('client', '-')}</div>
                        <div><span class="header-label">{t['ref']}:</span> {d['id']}</div>
                    </div>
                    <div class="header-right">
                        <div><span class="header-label">{t['date']}:</span> {d['date']}</div>
                    </div>
                </div>
                
                <div class="product-grid">
                    {grid_items}
                </div>
                
                <div class="disclaimer">
                    {t['valid_note']}
                </div>
            </div>
            
            <button class="no-print" onclick="window.print()" 
                    style="position:fixed; bottom:30px; right:30px; padding:15px 40px; background:#333; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold; box-shadow: 0 4px 10px rgba(0,0,0,0.2);">
                {t['print_quotation']}
            </button>
        </body>
        </html>"""
        self.write_and_open(html, f"Quote_{d['id']}_Large.html")

    # --- 现代化后台管理系统 UI（优化字体和可读性） ---
    def setup_ui(self):
        # 定义字体配置（更大更清晰）
        self.fonts = {
            'title': ('微软雅黑', 20, 'bold'),
            'subtitle': ('微软雅黑', 14, 'bold'),
            'body': ('微软雅黑', 12),
            'body_bold': ('微软雅黑', 12, 'bold'),
            'small': ('微软雅黑', 11),
            'label': ('微软雅黑', 12),
            'button': ('微软雅黑', 12, 'bold'),
            'table_header': ('微软雅黑', 13, 'bold'),
            'table_cell': ('微软雅黑', 12)
        }
        
        # 顶部工具栏（更大更清晰）
        toolbar = tk.Frame(self.root, bg="#2c3e50", pady=8, height=56)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)
        
        # 左侧：数据管理（更大字体和间距）
        data_frame = tk.Frame(toolbar, bg="#2c3e50")
        data_frame.pack(side="left", padx=16)
        tk.Label(data_frame, text="数据管理:", bg="#2c3e50", fg="white", font=self.fonts['body_bold']).pack(side="left", padx=(0, 8))
        tk.Button(data_frame, text="📥 备份数据", command=self.backup_data, bg="#3498db", fg="white", 
                 font=self.fonts['body'], relief="flat", cursor="hand2", padx=14, pady=6,
                 activebackground="#2980b9").pack(side="left", padx=4)
        tk.Button(data_frame, text="📤 恢复数据", command=self.restore_data, bg="#e67e22", fg="white", 
                 font=self.fonts['body'], relief="flat", cursor="hand2", padx=14, pady=6,
                 activebackground="#d35400").pack(side="left", padx=4)
        # Removed Google Drive Button
        
        # 右侧：系统设置（更大字体和间距）
        sys_frame = tk.Frame(toolbar, bg="#2c3e50")
        sys_frame.pack(side="right", padx=16)
        # Removed Share Settings Button
        tk.Button(sys_frame, text="🔒 修改密码", command=self.change_password, bg="#9b59b6", fg="white", 
                 font=self.fonts['body'], relief="flat", cursor="hand2", padx=14, pady=6,
                 activebackground="#8e44ad").pack(side="left", padx=4)
        
        # 配置Notebook样式（更大标签）
        style = ttk.Style()
        style.configure("TNotebook.Tab", font=self.fonts['body'], padding=[20, 12])
        style.configure("TNotebook", padding=[0, 0])
        
        self.notebook = ttk.Notebook(self.root, style="TNotebook")
        self.notebook.pack(pady=8, expand=True, fill="both", padx=8)
        self.tab_products = tk.Frame(self.notebook, bg="#f5f5f5")
        self.tab_billing = tk.Frame(self.notebook, bg="#f5f5f5")
        self.tab_inventory = tk.Frame(self.notebook, bg="#f5f5f5")
        self.tab_history = tk.Frame(self.notebook, bg="#f5f5f5") 
        self.tab_quote_hist = tk.Frame(self.notebook, bg="#f5f5f5")
        self.notebook.add(self.tab_products, text="📦 商品库管理")
        self.notebook.add(self.tab_inventory, text="📊 库存管理")
        self.notebook.add(self.tab_billing, text="📝 销售开单")
        self.notebook.add(self.tab_history, text="📋 开单记录") 
        self.notebook.add(self.tab_quote_hist, text="💼 报价记录")
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.setup_product_lib_ui()
        self.setup_inventory_ui()
        self.setup_billing_ui()
        self.setup_history_ui()
        self.setup_quote_history_ui()

    def on_tab_changed(self, event):
        try:
            tab = event.widget.select()
            text = event.widget.tab(tab, "text")
            if text == "📊 库存管理":
                self.refresh_inventory_list()
        except:
            pass

    def setup_product_lib_ui(self):
        f_con = tk.Frame(self.tab_products, bg="#f5f5f5")
        f_con.pack(fill="both", expand=True, padx=16, pady=16)
        f_l = tk.Frame(f_con, bg="#ffffff", relief="flat", bd=0); 
        # 商品列表全屏：列表区域占满整个页面（右侧编辑面板改为弹窗编辑）
        f_l.pack(side="left", fill="both", expand=True)

        # 1. Top Filter Bar（更大间距和字体）
        f_top = tk.Frame(f_l, bg="#ffffff", pady=16, padx=16)
        f_top.pack(fill="x")
        
        # Search area（更大字体）
        f_search_area = tk.Frame(f_top, bg="#ffffff")
        f_search_area.pack(side="left", padx=(0, 24))
        tk.Label(f_search_area, text="🔍 搜索货号:", font=self.fonts['body_bold'], 
                bg="#ffffff", fg="#1f1f1f").pack(side="left", padx=(0, 10))
        self.ent_lib_search = tk.Entry(f_search_area, width=28, font=self.fonts['body'],
                                       relief="solid", bd=1, highlightthickness=2,
                                       highlightbackground="#e0e0e0", highlightcolor="#1677ff")
        self.ent_lib_search.pack(side="left", padx=6, ipady=5)
        self.ent_lib_search.bind("<KeyRelease>", lambda e: [setattr(self, 'current_page', 1), self.refresh_product_list()])

        # Tag area（更大字体）
        self.f_tag_filter = tk.Frame(f_top, bg="#ffffff")
        self.f_tag_filter.pack(side="left", fill="x", expand=True)

        # 2. Action Bar（更大按钮和字体）
        f_actions = tk.Frame(f_l, bg="#ffffff", pady=12, padx=16)
        f_actions.pack(fill="x")
        
        btn_style = {"font": self.fonts['button'], "relief": "flat", "cursor": "hand2", 
                    "padx": 16, "pady": 8, "bd": 0}
        
        tk.Button(f_actions, text="➕ 新增商品", command=self.open_new_product_dialog, bg="#52c41a", fg="white", 
                 activebackground="#389e0d", **btn_style).pack(side="left", padx=4)
        tk.Button(f_actions, text="✏️ 编辑商品", command=self.open_edit_product_dialog, bg="#1677ff", fg="white", 
                 activebackground="#0958d9", **btn_style).pack(side="left", padx=4)
        tk.Button(f_actions, text="📤 导出商品", command=self.export_products, bg="#1677ff", fg="white", 
                 activebackground="#0958d9", **btn_style).pack(side="left", padx=4)
        tk.Button(f_actions, text="📥 导入商品", command=self.import_products, bg="#52c41a", fg="white", 
                 activebackground="#389e0d", **btn_style).pack(side="left", padx=4)
        tk.Button(f_actions, text="🖼 导出商品原图", command=self.export_product_images, bg="#13c2c2", fg="white", 
                 activebackground="#08979c", **btn_style).pack(side="left", padx=4)
        tk.Button(f_actions, text="🏷️ 批量标签", command=self.manage_tags_dialog, bg="#722ed1", fg="white", 
                 activebackground="#531dab", **btn_style).pack(side="left", padx=4)
        tk.Button(f_actions, text="📄 生成报价表", command=self.open_quotation_editor, bg="#fa8c16", fg="white", 
                 activebackground="#d46b08", **btn_style).pack(side="left", padx=4)
        tk.Button(f_actions, text="⚡ 快速开单", command=self.quick_billing, bg="#faad14", fg="white", 
                 activebackground="#d48806", **btn_style).pack(side="left", padx=4)
        tk.Button(f_actions, text="🗑️ 删除选中", command=self.delete_product, bg="#ff4d4f", fg="white", 
                 activebackground="#cf1322", **btn_style).pack(side="right", padx=4)

        # 3. Product List Header（更大更清晰）
        header_f = tk.Frame(f_l, bg="#fafafa", pady=12, relief="flat", bd=0)
        header_f.pack(fill="x", pady=(0, 0))
        
        self.select_page_var = tk.BooleanVar(value=False)
        self.select_all_var = tk.BooleanVar(value=False)
        # 列配置：第三个数值作为“基础宽度”，用于按比例自适应拉伸
        self.cols_cfg = [
            ("chk", "select_all", 50), 
            ("img", "图片 Image", 120), 
            ("no", "货号 No", 130), 
            ("tag", "标签 Tag", 110), 
            ("color", "颜色 Color", 90), 
            ("size", "码段 Size", 90), 
            ("cost", "成本价 Cost", 100), 
            ("price", "单价 Price", 100), 
            ("pcs", "每箱 Pcs", 70),
            ("moq", "最小起订量 (箱)", 110)
        ]
        # 表头每一列的 Frame 引用，方便后面动态调整宽度
        self.header_col_frames = []
        
        for k, name, base_w in self.cols_cfg:
             f_h = tk.Frame(header_f, width=base_w, height=44, bg="#fafafa")
             f_h.pack(side="left", padx=1)
             f_h.pack_propagate(False)
             self.header_col_frames.append(f_h)
             if k == "chk":
                 inner = tk.Frame(f_h, bg="#fafafa")
                 inner.place(relx=0.5, rely=0.5, anchor="center")
                 cb_page = tk.Checkbutton(
                     inner,
                     text="本页",
                     variable=self.select_page_var,
                     command=self.toggle_select_page,
                     bg="#fafafa",
                     activebackground="#fafafa",
                     selectcolor="#fafafa",
                     font=self.fonts['small']
                 )
                 cb_page.pack(anchor="w")
                 cb_all = tk.Checkbutton(
                     inner,
                     text="全部",
                     variable=self.select_all_var,
                     command=self.toggle_select_all,
                     bg="#fafafa",
                     activebackground="#fafafa",
                     selectcolor="#fafafa",
                     font=self.fonts['small']
                 )
                 cb_all.pack(anchor="w")
             else:
                 tk.Label(f_h, text=name, font=self.fonts['table_header'], 
                         fg="#1f1f1f", bg="#fafafa").place(relx=0.5, rely=0.5, anchor="center")

        # 4. Scrollable Content（白色背景）- 创建一个容器来包含列表和滚动条
        f_list_container = tk.Frame(f_l, bg="#ffffff")
        f_list_container.pack(fill="both", expand=True)
        
        self.canvas_p = tk.Canvas(f_list_container, bg="#ffffff", highlightthickness=0)
        self.scr_p = ttk.Scrollbar(f_list_container, command=self.canvas_p.yview)
        self.frm_p_list = tk.Frame(self.canvas_p, bg="#ffffff")
        self.win_p_list = self.canvas_p.create_window((0,0), window=self.frm_p_list, anchor="nw")
        
        # 绑定尺寸变化：同步内部宽度，并按比例重新计算每列宽度
        self.canvas_p.bind('<Configure>', self._on_product_canvas_configure)
        self.canvas_p.configure(yscrollcommand=self.scr_p.set)
        
        self.canvas_p.pack(side="left", fill="both", expand=True)
        self.scr_p.pack(side="right", fill="y")
        
        # 翻页控件 - 放在列表容器下方
        f_pagination = tk.Frame(f_l, bg="#ffffff", pady=10)
        f_pagination.pack(fill="x", padx=16)
        
        # 翻页按钮和页码显示
        self.btn_prev = tk.Button(f_pagination, text="◀ 上一页", command=self.prev_page,
                                  bg="#f0f0f0", fg="#1f1f1f", font=self.fonts['body'],
                                  relief="flat", cursor="hand2", padx=12, pady=6,
                                  activebackground="#e0e0e0", state="disabled")
        self.btn_prev.pack(side="left", padx=5)
        
        self.lbl_page_info = tk.Label(f_pagination, text="第 1 页 / 共 1 页 (共 0 条)",
                                      font=self.fonts['body'], bg="#ffffff", fg="#1f1f1f")
        self.lbl_page_info.pack(side="left", padx=15)
        
        self.btn_next = tk.Button(f_pagination, text="下一页 ▶", command=self.next_page,
                                  bg="#f0f0f0", fg="#1f1f1f", font=self.fonts['body'],
                                  relief="flat", cursor="hand2", padx=12, pady=6,
                                  activebackground="#e0e0e0", state="disabled")
        self.btn_next.pack(side="left", padx=5)
        
        def on_mw(e):
            """鼠标滚轮滚动商品列表（针对触控板/不同设备做步长自适应）。"""
            delta = e.delta
            # Windows 上通常是 ±120 的倍数，这里做一个通用处理，保证至少移动 1 个单位
            step = int(-delta / 120) if delta not in (0, None) else 0
            if step == 0:
                step = -1 if delta < 0 else 1
            self.canvas_p.yview_scroll(step, "units")
        # 仅在商品列表区域内滚动，更自然
        self.canvas_p.bind("<MouseWheel>", on_mw)
        self.frm_p_list.bind("<MouseWheel>", on_mw)

        self.selected_prod_id = None
        self.prod_row_widgets = {}  # id -> list of widgets
        self.prod_check_vars = {}   # id -> BooleanVar（勾选状态）
        self.prod_context_menu = tk.Menu(self.root, tearoff=0)
        self.prod_context_menu.add_command(label="✏️ 编辑商品", command=self.open_edit_product_dialog)
        self.prod_context_menu.add_command(label="🗑️ 删除商品", command=self.delete_product)
        self.prod_context_menu.add_command(label="🖼 导出商品原图", command=self.export_product_images)

        # Right Panel: Edit Details（更大更清晰）
        f_e = tk.LabelFrame(f_con, text=" 商品资料编辑 ", padx=18, pady=16, width=420,
                           font=self.fonts['subtitle'], fg="#1f1f1f", bg="#ffffff")
        # 右侧编辑栏隐藏（改为弹窗编辑/新增），保留构建以兼容旧逻辑但不显示
        self.f_product_editor = f_e
        f_e.pack_propagate(False)
        img_f = tk.Frame(f_e, width=360, height=260, bg="#f5f5f5", relief="solid", bd=1); 
        img_f.pack(pady=(0, 12)); img_f.pack_propagate(False)
        self.lbl_prod_img = tk.Label(img_f, bg="#f5f5f5", text="暂无图片", font=self.fonts['small'], fg="#8c8c8c"); 
        self.lbl_prod_img.pack(fill="both", expand=True)
        btn_img_frame = tk.Frame(f_e, bg="#ffffff"); btn_img_frame.pack(fill="x", pady=(0, 12))
        tk.Button(btn_img_frame, text="🖼️ 选择图片", command=self.select_img_for_lib, 
                 bg="#f0f0f0", fg="#1f1f1f", font=self.fonts['body'], relief="flat", cursor="hand2",
                 activebackground="#e0e0e0").pack(fill="x", pady=3, ipady=6)
        tk.Button(btn_img_frame, text="📋 粘贴图片", command=self.paste_img_for_lib, 
                 bg="#f0f0f0", fg="#1f1f1f", font=self.fonts['body'], relief="flat", cursor="hand2",
                 activebackground="#e0e0e0").pack(fill="x", pady=3, ipady=6)
        self.prod_ents = {}
        for l, k in [("货号 No:", "no"), ("单价 Price:", "price"), ("最小起订量 (箱):", "moq_ctns"), ("成本价 Cost:", "cost_price"), 
                    ("码段 Size:", "size"), ("颜色 Color:", "color"), ("每箱 Pcs:", "pcs")]:
            r = tk.Frame(f_e, bg="#ffffff"); r.pack(fill="x", pady=8)
            tk.Label(r, text=l, width=14, anchor="w", font=self.fonts['label'], 
                    bg="#ffffff", fg="#1f1f1f").pack(side="left", padx=(0, 10))
            e = tk.Entry(r, font=self.fonts['body'], relief="solid", bd=1,
                        highlightthickness=2, highlightbackground="#e0e0e0", highlightcolor="#1677ff"); 
            e.pack(side="left", fill="x", expand=True, ipady=5); self.prod_ents[k] = e
        
        # Action Buttons in Panel（更大更清晰）
        btn_style = {"relief": "flat", "cursor": "hand2", "bd": 0, "font": self.fonts['button'], "padx": 12, "pady": 8}
        tk.Button(f_e, text="➕ 新增为新商品", bg="#52c41a", fg="white", height=2, 
                 command=self.add_as_new_product, activebackground="#389e0d", **btn_style).pack(fill="x", pady=(12, 8))
        tk.Button(f_e, text="📝 更新选中商品", bg="#1677ff", fg="white", height=2, 
                 command=self.update_selected_product, activebackground="#0958d9", **btn_style).pack(fill="x", pady=(0, 8))
        tk.Button(f_e, text="🧹 清空输入区域", bg="#d9d9d9", fg="#1f1f1f", height=1, 
                 command=self.reset_edit_panel, activebackground="#bfbfbf", **btn_style).pack(fill="x")

    # --- 库存管理模块 ---
    def setup_inventory_ui(self):
        f_con = tk.Frame(self.tab_inventory, bg="#f5f5f5")
        f_con.pack(fill="both", expand=True, padx=16, pady=16)
        f_l = tk.Frame(f_con, bg="#ffffff", relief="flat", bd=0)
        f_l.pack(side="left", fill="both", expand=True)

        # 1. Top Filter Bar
        f_top = tk.Frame(f_l, bg="#ffffff", pady=16, padx=16)
        f_top.pack(fill="x")
        
        # Search area
        f_search_area = tk.Frame(f_top, bg="#ffffff")
        f_search_area.pack(side="left", padx=(0, 24))
        tk.Label(f_search_area, text="🔍 搜索货号:", font=self.fonts['body_bold'], 
                bg="#ffffff", fg="#1f1f1f").pack(side="left", padx=(0, 10))
        self.ent_inv_search = tk.Entry(f_search_area, width=28, font=self.fonts['body'],
                                       relief="solid", bd=1, highlightthickness=2,
                                       highlightbackground="#e0e0e0", highlightcolor="#1677ff")
        self.ent_inv_search.pack(side="left", padx=6, ipady=5)
        self.ent_inv_search.bind("<KeyRelease>", lambda e: self.refresh_inventory_list())

        # 2. Action Bar
        f_actions = tk.Frame(f_l, bg="#ffffff", pady=12, padx=16)
        f_actions.pack(fill="x")
        
        btn_style = {"font": self.fonts['button'], "relief": "flat", "cursor": "hand2", 
                    "padx": 16, "pady": 8, "bd": 0}
        
        tk.Button(f_actions, text="📥 入库 (进货/退货/盘点)", command=self.open_inbound_dialog, bg="#52c41a", fg="white", 
                 activebackground="#389e0d", **btn_style).pack(side="left", padx=4)
        tk.Button(f_actions, text="📤 出库 (销售/盘点)", command=self.open_outbound_dialog, bg="#fa8c16", fg="white", 
                 activebackground="#d46b08", **btn_style).pack(side="left", padx=4)
        tk.Button(f_actions, text="📋 出入库记录", command=self.open_inventory_history_dialog, bg="#1677ff", fg="white", 
                 activebackground="#0958d9", **btn_style).pack(side="left", padx=4)

        # 3. Inventory List Header
        header_f = tk.Frame(f_l, bg="#fafafa", pady=12, relief="flat", bd=0)
        header_f.pack(fill="x", pady=(0, 0))
        
        # Inventory Columns
        self.inv_cols_cfg = [
            ("img", "图片", 100), 
            ("no", "货号", 140), 
            ("color", "颜色", 100), 
            ("size", "码段", 100), 
            ("stock", "当前库存(双)", 140),
            ("moq", "装箱数(双/箱)", 120)
        ]
        self.inv_header_col_frames = []
        
        for k, name, base_w in self.inv_cols_cfg:
             f_h = tk.Frame(header_f, width=base_w, height=44, bg="#fafafa")
             f_h.pack(side="left", padx=1)
             f_h.pack_propagate(False)
             self.inv_header_col_frames.append(f_h)
             tk.Label(f_h, text=name, font=self.fonts['table_header'], 
                     fg="#1f1f1f", bg="#fafafa").place(relx=0.5, rely=0.5, anchor="center")

        # 4. Scrollable Content
        f_list_container = tk.Frame(f_l, bg="#ffffff")
        f_list_container.pack(fill="both", expand=True)
        
        self.canvas_inv = tk.Canvas(f_list_container, bg="#ffffff", highlightthickness=0)
        self.scr_inv = ttk.Scrollbar(f_list_container, command=self.canvas_inv.yview)
        self.frm_inv_list = tk.Frame(self.canvas_inv, bg="#ffffff")
        self.win_inv_list = self.canvas_inv.create_window((0,0), window=self.frm_inv_list, anchor="nw")
        
        self.canvas_inv.bind('<Configure>', self._on_inventory_canvas_configure)
        self.canvas_inv.configure(yscrollcommand=self.scr_inv.set)
        
        self.canvas_inv.pack(side="left", fill="both", expand=True)
        self.scr_inv.pack(side="right", fill="y")

        def on_mw(e):
            delta = e.delta
            if e.num == 5: delta = -120
            elif e.num == 4: delta = 120
            step = int(-1 * (delta / 120))
            if step == 0: step = -1 if delta < 0 else 1
            self.canvas_inv.yview_scroll(step, "units")
            
        self.canvas_inv.bind("<MouseWheel>", on_mw)
        self.frm_inv_list.bind("<MouseWheel>", on_mw)
        
        self.selected_inv_id = None
        self.inv_row_widgets = {}

    def _on_inventory_canvas_configure(self, event):
        width = event.width
        self.canvas_inv.itemconfig(self.win_inv_list, width=width)
        
        total_base = sum(c[2] for c in self.inv_cols_cfg)
        factor = width / total_base if total_base > 0 else 1
        
        for i, (k, name, base_w) in enumerate(self.inv_cols_cfg):
            new_w = int(base_w * factor)
            self.inv_header_col_frames[i].config(width=new_w)
            for pid, widgets in self.inv_row_widgets.items():
                if i < len(widgets):
                    widgets[i].config(width=new_w)

    def refresh_inventory_list(self):
        for w in self.frm_inv_list.winfo_children(): w.destroy()
        self.inv_row_widgets = {}
        
        keyword = self.ent_inv_search.get().strip().lower()
        
        filtered = []
        for p in self.products:
            if keyword and keyword not in str(p.get('no', '')).lower():
                continue
            filtered.append(p)
            
        total_base = sum(c[2] for c in self.inv_cols_cfg)
        canvas_width = self.canvas_inv.winfo_width()
        if canvas_width <= 1: canvas_width = 1200 
        factor = canvas_width / total_base if total_base > 0 else 1

        for i, p in enumerate(filtered):
            bg_color = "#f9f9f9" if i % 2 == 0 else "#ffffff"
            row = tk.Frame(self.frm_inv_list, bg=bg_color, pady=4)
            row.pack(fill="x")
            
            widgets = []
            pid = p.get('_id')
            
            for k, name, base_w in self.inv_cols_cfg:
                w = int(base_w * factor)
                cell = tk.Frame(row, width=w, bg=bg_color, height=60)
                cell.pack(side="left", padx=1)
                cell.pack_propagate(False)
                widgets.append(cell)
                
                if k == "img":
                    if p.get("img"):
                        try:
                            img = Image.open(BytesIO(base64.b64decode(p["img"])))
                            img.thumbnail((50, 50))
                            ph = ImageTk.PhotoImage(img)
                            lbl = tk.Label(cell, image=ph, bg=bg_color)
                            lbl.image = ph
                            lbl.place(relx=0.5, rely=0.5, anchor="center")
                        except:
                            tk.Label(cell, text="无图", bg=bg_color).place(relx=0.5, rely=0.5, anchor="center")
                    else:
                        tk.Label(cell, text="无图", bg=bg_color).place(relx=0.5, rely=0.5, anchor="center")
                elif k == "stock":
                    stk = p.get('stock', 0)
                    fg = "#52c41a" if stk > 0 else "#f5222d"
                    tk.Label(cell, text=str(stk), font=("Arial", 12, "bold"), fg=fg, bg=bg_color).place(relx=0.5, rely=0.5, anchor="center")
                elif k == "moq": 
                    # Display pcs per carton (pairs/ctn)
                    tk.Label(cell, text=str(p.get('pcs', 0)), font=self.fonts['body'], bg=bg_color).place(relx=0.5, rely=0.5, anchor="center")
                else:
                    tk.Label(cell, text=str(p.get(k, "")), font=self.fonts['body'], bg=bg_color).place(relx=0.5, rely=0.5, anchor="center")
            
            self.inv_row_widgets[pid] = widgets

        self.canvas_inv.update_idletasks()
        self.canvas_inv.configure(scrollregion=self.canvas_inv.bbox("all"))

    def open_inbound_dialog(self):
        self.open_stock_dialog("in")

    def open_outbound_dialog(self):
        self.open_stock_dialog("out")

    def open_stock_dialog(self, direction):
        title = "商品入库" if direction == "in" else "商品出库"
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("500x650")
        win.configure(bg="white")
        win.grab_set()
        
        win.update_idletasks()
        x = (win.winfo_screenwidth() // 2) - (win.winfo_width() // 2)
        y = (win.winfo_screenheight() // 2) - (win.winfo_height() // 2)
        win.geometry(f"+{x}+{y}")
        
        tk.Label(win, text=title, font=self.fonts['subtitle'], bg="white").pack(pady=10)
        
        tk.Label(win, text="选择商品 (搜索货号):", font=self.fonts['body'], bg="white").pack(anchor="w", padx=20)
        search_var = tk.StringVar()
        entry_search = tk.Entry(win, textvariable=search_var, font=self.fonts['body'], bd=1, relief="solid")
        entry_search.pack(fill="x", padx=20, pady=5)
        
        lb_frame = tk.Frame(win, bd=1, relief="solid")
        lb_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        lb_prods = tk.Listbox(lb_frame, font=self.fonts['small'], height=6)
        scroll = tk.Scrollbar(lb_frame, command=lb_prods.yview)
        lb_prods.configure(yscrollcommand=scroll.set)
        lb_prods.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        
        filtered_prods = []
        
        def refresh_list(*args):
            nonlocal filtered_prods
            key = search_var.get().lower()
            lb_prods.delete(0, tk.END)
            filtered_prods = []
            for p in self.products:
                display = f"{p.get('no')} - {p.get('color')} - {p.get('size')} (库存: {p.get('stock', 0)})"
                if key in display.lower():
                    lb_prods.insert(tk.END, display)
                    filtered_prods.append(p)
                    
        search_var.trace("w", refresh_list)
        refresh_list()
        
        op_frame = tk.Frame(win, bg="white", pady=10)
        op_frame.pack(fill="x", padx=20)
        
        tk.Label(op_frame, text="操作类型:", font=self.fonts['body'], bg="white").grid(row=0, column=0, sticky="w")
        type_var = tk.StringVar(value="进货" if direction == "in" else "销售")
        
        if direction == "in":
            tk.Radiobutton(op_frame, text="进货", variable=type_var, value="进货", bg="white").grid(row=0, column=1)
            tk.Radiobutton(op_frame, text="退货", variable=type_var, value="退货", bg="white").grid(row=0, column=2)
            tk.Radiobutton(op_frame, text="盘点入库", variable=type_var, value="盘点", bg="white").grid(row=0, column=3)
        else:
            tk.Radiobutton(op_frame, text="销售", variable=type_var, value="销售", bg="white").grid(row=0, column=1)
            tk.Radiobutton(op_frame, text="盘点出库", variable=type_var, value="盘点", bg="white").grid(row=0, column=2)
            
        tk.Label(op_frame, text="数量模式:", font=self.fonts['body'], bg="white").grid(row=1, column=0, sticky="w", pady=10)
        mode_var = tk.StringVar(value="ctn")
        tk.Radiobutton(op_frame, text="整箱入库" if direction == "in" else "整箱出库", variable=mode_var, value="ctn", bg="white").grid(row=1, column=1)
        tk.Radiobutton(op_frame, text="散数(双/个)", variable=mode_var, value="pcs", bg="white").grid(row=1, column=2)
        
        tk.Label(op_frame, text="数量:", font=self.fonts['body'], bg="white").grid(row=2, column=0, sticky="w")
        qty_entry = tk.Entry(op_frame, font=self.fonts['body'], width=10, bd=1, relief="solid")
        qty_entry.grid(row=2, column=1, sticky="w")
        
        tk.Label(op_frame, text="备注:", font=self.fonts['body'], bg="white").grid(row=3, column=0, sticky="w", pady=10)
        note_entry = tk.Entry(op_frame, font=self.fonts['body'], width=20, bd=1, relief="solid")
        note_entry.grid(row=3, column=1, columnspan=3, sticky="we")
        
        def on_confirm():
            idx = lb_prods.curselection()
            if not idx:
                messagebox.showwarning("提示", "请先选择一个商品！")
                return
            
            p = filtered_prods[idx[0]]
            try:
                q = int(qty_entry.get())
                if q <= 0: raise ValueError
            except:
                messagebox.showwarning("提示", "请输入有效的正整数数量！")
                return
                
            mode = mode_var.get()
            change_qty = 0
            
            if mode == "ctn":
                pcs_per_ctn = int(p.get("pcs", 0) or 0)
                if pcs_per_ctn <= 0:
                     messagebox.showwarning("提示", "该商品未设置每箱双数(Pcs/Ctn)，无法使用整箱模式！")
                     return
                change_qty = q * pcs_per_ctn
                mode_str = f"整箱 ({q}箱 x {pcs_per_ctn}双)"
            else:
                change_qty = q
                mode_str = f"散数 ({q}双)"
                
            self.update_stock(p, change_qty, type_var.get(), direction, mode_str, note_entry.get())
            win.destroy()
            self.refresh_inventory_list()
            messagebox.showinfo("成功", "库存更新成功！")
            
        tk.Button(win, text="确认提交", command=on_confirm, bg="#1976d2", fg="white", font=self.fonts['button'], padx=20).pack(pady=20)

    def update_stock(self, product, qty, type_str, direction, mode_str, note):
        # Update Stock
        current_stock = int(product.get("stock", 0))
        if direction == "in":
            new_stock = current_stock + qty
        else:
            new_stock = current_stock - qty
            
        product["stock"] = new_stock
        
        # Save Product Data
        self.save_json(FILES["product"], self.products)
        
        # Record History
        record = {
            "id": str(uuid.uuid4()),
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": type_str, # 进货/销售/盘点
            "direction": "入库" if direction == "in" else "出库",
            "mode": mode_str,
            "change_qty": qty,
            "stock_after": new_stock,
            "product_no": product.get("no"),
            "product_color": product.get("color"),
            "product_size": product.get("size"),
            "note": note
        }
        
        if not hasattr(self, "inventory_history"):
            self.inventory_history = []
        self.inventory_history.insert(0, record)
        self.save_json(FILES["inventory"], self.inventory_history)

    def open_inventory_history_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("出入库记录")
        win.geometry("900x600")
        
        # Table
        cols = ("time", "type", "direction", "no", "color", "size", "change", "stock", "mode", "note")
        headers = ("时间", "类型", "方向", "货号", "颜色", "码段", "数量变动", "结余库存", "模式", "备注")
        
        tree = ttk.Treeview(win, columns=cols, show="headings", height=20)
        for c, h in zip(cols, headers):
            tree.heading(c, text=h)
            tree.column(c, width=80 if c != "time" else 140, anchor="center")
            
        scroll = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        
        # Load Data
        if hasattr(self, "inventory_history"):
            for r in self.inventory_history:
                tree.insert("", "end", values=(
                    r.get("time"),
                    r.get("type"),
                    r.get("direction"),
                    r.get("product_no"),
                    r.get("product_color"),
                    r.get("product_size"),
                    r.get("change_qty"),
                    r.get("stock_after"),
                    r.get("mode"),
                    r.get("note")
                ))


    def quick_billing(self):
        checked_prods = [p for p in self.products if p.get('_checked')]
        if not checked_prods:
            messagebox.showwarning("提示", "请先在商品列表中通过勾选（复选框）选择商品！")
            return
            
        added_count = 0
        for p in checked_prods:
            pcs = int(p.get('pcs', 0) or 0)
            prc = float(p.get('price', 0) or 0)
            # 默认添加1箱
            self.cart_items.append({
                "no": p['no'], 
                "size": p.get('size', ''), 
                "color": p.get('color', ''), 
                "ctns": 1, 
                "pcs": pcs, 
                "total": pcs, 
                "price": prc, 
                "amount": pcs * prc, 
                "img": p.get('img')
            })
            added_count += 1
            
        self.refresh_cart()
        self.notebook.select(self.tab_billing)
        messagebox.showinfo("成功", f"已成功将 {added_count} 个商品添加到开单购物车！")

    def _on_product_canvas_configure(self, event):
        try:
            self.canvas_p.itemconfig(self.win_p_list, width=event.width)
        except Exception:
            pass
        try:
            if not getattr(self, "_product_canvas_inited", False):
                self._product_canvas_inited = True
                self.refresh_product_list()
        except Exception:
            pass

    def open_quotation_editor(self):
        items = [p for p in self.products if p.get('_checked')]
        if not items: return
        q_win = tk.Toplevel(self.root); q_win.title("报价单编辑器"); q_win.geometry("1000x800"); q_win.grab_set()
        
        # 1. 顶部客户信息
        top_f = tk.Frame(q_win, bg="#f0f0f0", pady=10); top_f.pack(fill="x")
        tk.Label(top_f, text="客户名称 Client:", font=("Arial", 11, "bold"), bg="#f0f0f0").pack(side="left", padx=(20, 10))
        ent_c = tk.Entry(top_f, width=50, font=("Arial", 11)); ent_c.pack(side="left", padx=10)

        # 2. 列表表头
        head_f = tk.Frame(q_win, bg="#333", pady=5); head_f.pack(fill="x")
        cols = [("图片 Image", 12), ("货号 Article No", 20), ("MOQ (箱)", 15), ("单价 Price (¥)", 15), ("每箱 Pcs/Ctn", 15)]
        for txt, w in cols:
            tk.Label(head_f, text=txt, font=("Arial", 10, "bold"), fg="white", bg="#333", width=w).pack(side="left", padx=5)

        # 3. 滚动列表区域
        list_f = tk.Frame(q_win); list_f.pack(fill="both", expand=True)
        can = tk.Canvas(list_f, bg="white"); scr = ttk.Scrollbar(list_f, command=can.yview)
        frm = tk.Frame(can, bg="white"); 
        can_win = can.create_window((0,0), window=frm, anchor="nw")
        
        def on_canvas_configure(e): can.itemconfig(can_win, width=e.width)
        can.bind('<Configure>', on_canvas_configure)
        can.configure(yscrollcommand=scr.set)
        
        can.pack(side="left", fill="both", expand=True); scr.pack(side="right", fill="y")
        
        def on_mousewheel(event):
            try: can.yview_scroll(int(-1*(event.delta/120)), "units")
            except: pass
        can.bind_all("<MouseWheel>", on_mousewheel)

        rows = []
        q_win.imgs = [] 
        
        for i, p in enumerate(items):
            color = "#f9f9f9" if i % 2 == 0 else "white"
            r = tk.Frame(frm, pady=5, bg=color, bd=1, relief="solid"); r.pack(fill="x", padx=10, pady=2)
            
            # 这里的宽度和顺序必须与表头 strictly 对应
            # 1. 图片 (width ~10-12 char equivalent roughly 80-100px)
            img_container = tk.Frame(r, width=100, height=80, bg=color); img_container.pack(side="left", padx=5); img_container.pack_propagate(False)
            if p.get('img'):
                try:
                    img_data = base64.b64decode(p['img'])
                    pil_img = Image.open(BytesIO(img_data))
                    pil_img.thumbnail((75, 75))
                    tk_img = ImageTk.PhotoImage(pil_img)
                    q_win.imgs.append(tk_img)
                    tk.Label(img_container, image=tk_img, bg=color).place(relx=0.5, rely=0.5, anchor="center")
                except:
                    tk.Label(img_container, text="[无图]", bg=color).place(relx=0.5, rely=0.5, anchor="center")
            else:
                tk.Label(img_container, text="[无图]", bg=color).place(relx=0.5, rely=0.5, anchor="center")

            # 2. 货号
            tk.Label(r, text=p['no'], width=20, font=("Arial", 10, "bold"), bg=color).pack(side="left", padx=5)
            
            # 3. MOQ
            em = tk.Entry(r, width=15, font=("Arial", 10), justify="center"); em.insert(0, str(p.get('moq_ctns', 100))); em.pack(side="left", padx=5)
            
            # 4. 单价
            ep = tk.Entry(r, width=15, font=("Arial", 10), justify="center"); ep.insert(0, str(p.get('price', 0))); ep.pack(side="left", padx=5)
            
            # 5. 每箱
            tk.Label(r, text=f"{p.get('pcs',0)} 双/箱", width=15, bg=color).pack(side="left", padx=5)

            rows.append({"p": p, "em": em, "ep": ep})

        frm.update_idletasks()
        can.config(scrollregion=can.bbox("all"))

        # 4. 底部功能区
        bot_f = tk.Frame(q_win, bg="#e0e0e0", pady=15); bot_f.pack(fill="x")
        
        # 报价单模式选择
        mode_frame = tk.Frame(bot_f, bg="#e0e0e0"); mode_frame.pack(pady=(0, 10))
        tk.Label(mode_frame, text="报价单模板:", font=("Arial", 10, "bold"), bg="#e0e0e0").pack(side="left", padx=5)
        quote_mode = tk.StringVar(value="table")
        
        # 定义状态更新函数
        def update_sp_state(*args):
            if quote_mode.get() == "large_image":
                sp_cols.config(state="normal")
            else:
                sp_cols.config(state="disabled")
        quote_mode.trace("w", update_sp_state)

        tk.Radiobutton(mode_frame, text="列表模板", variable=quote_mode, value="table", 
                      bg="#e0e0e0", font=("Arial", 10)).pack(side="left", padx=10)
        tk.Radiobutton(mode_frame, text="网格模板", variable=quote_mode, value="large_image", 
                      bg="#e0e0e0", font=("Arial", 10)).pack(side="left", padx=10)
        
        # 大图模式列数设置
        tk.Label(mode_frame, text="列数:", font=("Arial", 10), bg="#e0e0e0").pack(side="left", padx=(5, 0))
        sp_cols = tk.Spinbox(mode_frame, from_=1, to=6, width=3, font=("Arial", 10))
        sp_cols.delete(0, "end")
        sp_cols.insert(0, "4")
        sp_cols.pack(side="left", padx=2)
        update_sp_state()
        
        # 打印语言选择
        tk.Label(mode_frame, text="|  打印语言:", font=("Arial", 10, "bold"), bg="#e0e0e0").pack(side="left", padx=(20, 5))
        tk.Radiobutton(mode_frame, text="English", variable=self.quote_print_lang_var, value="en", 
                      bg="#e0e0e0", font=("Arial", 10)).pack(side="left", padx=5)
        tk.Radiobutton(mode_frame, text="中文", variable=self.quote_print_lang_var, value="zh", 
                      bg="#e0e0e0", font=("Arial", 10)).pack(side="left", padx=5)
        
        def gen():
            res = [{"no": r['p']['no'], "price": float(r['ep'].get() or 0), "moq_ctns": r['em'].get(), "pcs": r['p'].get('pcs', 0), "img": r['p'].get('img',''), "size": r['p'].get('size','--'), "color": r['p'].get('color','--')} for r in rows]
            data = {"id": "Q"+datetime.datetime.now().strftime("%y%m%d%H%M"), "date": datetime.datetime.now().strftime("%Y-%m-%d"), "client": ent_c.get(), "items": res}
            self.quote_history.append(data); self.save_json(FILES["quote"], self.quote_history)
            
            # 根据选择的模式生成不同的报价单
            if quote_mode.get() == "large_image":
                try:
                    c = int(sp_cols.get())
                except:
                    c = 3
                self.gen_quotation_html_large_image(data, cols=c)
            else:
                self.gen_quotation_html(data)
            
            q_win.destroy(); self.refresh_quote_history_list()
        
        tk.Button(bot_f, text="🚀 生成专业报价单 (生成 HTML 并打印)", command=gen, bg="#333", fg="white", height=2, font=("微软雅黑", 12, "bold"), width=40).pack()

    # --- 以下为系统原有支撑逻辑 ---
    def setup_billing_ui(self):
        # 主容器：顶部（区域1+区域2）和底部（区域3）
        main_wrapper = tk.Frame(self.tab_billing, bg="#f5f5f5")
        main_wrapper.pack(fill="both", expand=True, padx=16, pady=8)
        
        # 顶部容器：区域1和区域2（宽度比2:3）
        top_container = tk.Frame(main_wrapper, bg="#f5f5f5")
        # 让顶部容器可在垂直方向扩展，这样左侧可以放“商品搜索列表”来填满与右侧清单对齐后的空白
        top_container.pack(fill="both", expand=True, pady=(0, 8))
        # 左侧比右侧稍大（3:2），给搜索列表更多水平空间
        top_container.columnconfigure(0, weight=3)
        top_container.columnconfigure(1, weight=2)
        
        # 区域1容器（宽度比例2）
        left_top_container = tk.Frame(top_container, bg="#f5f5f5")
        left_top_container.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        
        # 1. Header Information Section - 三行布局（缩窄，高度减少50%）
        f_header_con = tk.Frame(left_top_container, bg="#ffffff", pady=6)
        # Header 只占内容高度，避免把“财务结算”下面撑出大空白
        f_header_con.pack(fill="x")
        
        self.head_ents = {}
        
        # 第一行：收货信息（所有字段一行显示，高度减少50%）
        f_receiver_row = tk.LabelFrame(f_header_con, text=" 📦 收货信息 ", 
                                      font=self.fonts['body_bold'], padx=10, pady=6, 
                                      bg="#ffffff", fg="#1677ff", relief="flat", bd=1,
                                      highlightthickness=1, highlightbackground="#e0e0e0")
        f_receiver_row.pack(fill="x", pady=(0, 4))
        
        f_receiver = tk.Frame(f_receiver_row, bg="#ffffff")
        f_receiver.pack(fill="x", padx=6, pady=4)
        
        # 收货信息字段：客户、唛头、业务电话、收货地址、备注 - 一行显示（去掉英文）
        r_fields = [("客户:", "client", 12), ("唛头:", "mark", 12), 
                   ("业务电话:", "phone", 14), ("收货地址:", "address", 18),
                   ("备注:", "note", 15)]
        
        col = 0
        for l, k, w in r_fields:
            # 标签（更紧凑）
            tk.Label(f_receiver, text=l, font=self.fonts['label'], bg="#ffffff", 
                    fg="#1f1f1f", anchor="w").grid(row=0, column=col*2, sticky="w", padx=(0, 4))
            
            if k == "note":
                # 备注使用Entry控件（单行显示）
                e = tk.Entry(f_receiver, width=w, font=self.fonts['body'], bd=1, relief="solid",
                            highlightthickness=2, highlightbackground="#e0e0e0", highlightcolor="#1677ff")
                e.grid(row=0, column=col*2+1, sticky="ew", padx=(0, 8), ipady=3)
                self.head_ents[k] = e
                # 创建兼容层：txt_note指向Entry，但提供Text接口
                class NoteWrapper:
                    def __init__(self, entry):
                        self.entry = entry
                    def get(self, start="1.0", end=tk.END):
                        # 返回Entry的内容，模拟Text的get方法
                        content = self.entry.get()
                        return content + "\n" if content else "\n"
                    def delete(self, start="1.0", end=tk.END):
                        # 清空Entry内容
                        self.entry.delete(0, tk.END)
                    def insert(self, index, text):
                        # 插入内容到Entry（去除换行符）
                        if text:
                            clean_text = text.replace("\n", " ").strip()
                            self.entry.delete(0, tk.END)
                            self.entry.insert(0, clean_text)
                self.txt_note = NoteWrapper(e)
            else:
                # 其他字段使用Entry（更紧凑）
                e = tk.Entry(f_receiver, width=w, font=self.fonts['body'], bd=1, relief="solid",
                            highlightthickness=2, highlightbackground="#e0e0e0", highlightcolor="#1677ff")
                e.grid(row=0, column=col*2+1, sticky="ew", padx=(0, 8), ipady=3)
                self.head_ents[k] = e
            
            col += 1
        
        # 配置列权重，让输入框可以拉伸
        for i in range(len(r_fields) * 2):
            f_receiver.columnconfigure(i, weight=1 if i % 2 == 1 else 0)
        
        # 第二行：发货信息（所有字段一行显示，高度减少50%）
        f_sender_row = tk.LabelFrame(f_header_con, text=" 🚚 发货信息 ", 
                                     font=self.fonts['body_bold'], padx=10, pady=6, 
                                     bg="#ffffff", fg="#52c41a", relief="flat", bd=1,
                                     highlightthickness=1, highlightbackground="#e0e0e0")
        f_sender_row.pack(fill="x", pady=(0, 4))
        
        f_sender = tk.Frame(f_sender_row, bg="#ffffff")
        f_sender.pack(fill="x", padx=6, pady=4)
        
        # 发货信息字段：发货人、联系电话、发货地址 - 一行显示（去掉英文）
        s_fields = [("发货人:", "sender", 12), ("联系电话:", "sender_phone", 14), 
                   ("发货地址:", "sender_address", 18)]
        
        col = 0
        for l, k, w in s_fields:
            # 标签（居中对齐）
            tk.Label(f_sender, text=l, font=self.fonts['label'], bg="#ffffff", 
                    fg="#1f1f1f", anchor="center").grid(row=0, column=col*2, sticky="ew", padx=(0, 6))
            
            # 输入框（更紧凑，居中对齐）
            e = tk.Entry(f_sender, width=w, font=self.fonts['body'], bd=1, relief="solid",
                        highlightthickness=2, highlightbackground="#e0e0e0", highlightcolor="#1677ff",
                        justify="center")
            e.grid(row=0, column=col*2+1, sticky="ew", padx=(0, 8), ipady=3)
            self.head_ents[k] = e
            
            col += 1
        
        # 配置列权重
        for i in range(len(s_fields) * 2):
            f_sender.columnconfigure(i, weight=1 if i % 2 == 1 else 0)
        
        # 第三行：财务结算（所有字段一行显示，高度减少50%）
        f_settle_row = tk.LabelFrame(f_header_con, text=" 💰 财务结算 ", 
                                     font=self.fonts['body_bold'], padx=10, pady=6, 
                                     bg="#fff7e6", fg="#fa8c16", relief="flat", bd=1,
                                     highlightthickness=1, highlightbackground="#ffd591")
        f_settle_row.pack(fill="x")
        
        f_settle = tk.Frame(f_settle_row, bg="#fff7e6")
        f_settle.pack(fill="x", padx=6, pady=4)
        
        self.fin_ents = {}
        fin_fields = [("运费:", "shipping", 10), ("定金:", "deposit", 10), 
                     ("已收:", "paid", 10)]
        
        col = 0
        for l, k, w in fin_fields:
            # 标签（居中对齐）
            tk.Label(f_settle, text=l, font=self.fonts['label'], bg="#fff7e6", 
                    fg="#1f1f1f", anchor="center").grid(row=0, column=col*2, sticky="ew", padx=(0, 6))
            
            # 输入框（更紧凑，居中对齐）
            e = tk.Entry(f_settle, width=w, justify="center", font=self.fonts['body'], bd=1, relief="solid",
                        highlightthickness=2, highlightbackground="#e0e0e0", highlightcolor="#1677ff")
            e.insert(0, "0")
            e.grid(row=0, column=col*2+1, sticky="ew", padx=(0, 8), ipady=3)
            self.fin_ents[k] = e
            
            col += 1
        
        # 重置按钮（更紧凑）
        tk.Button(f_settle, text="🔄 重置单据", bg="#ff4d4f", fg="white", command=self.reset_billing, 
                 font=self.fonts['button'], padx=12, pady=6, relief="flat", cursor="hand2",
                 activebackground="#cf1322").grid(row=0, column=col*2, padx=(8, 0), sticky="e")
        
        # 配置列权重
        for i in range(len(fin_fields) * 2):
            f_settle.columnconfigure(i, weight=1 if i % 2 == 1 else 0)
        
        # 区域2容器（宽度比例3，与区域1宽度比2:3）
        right_top_container = tk.Frame(top_container, bg="#f5f5f5")
        right_top_container.grid(row=0, column=1, sticky="nsew")
        
        # 区域2：待发货清单（在右侧顶部）
        cart_card = tk.Frame(right_top_container, bg="#ffffff", relief="flat", bd=0)
        cart_card.pack(fill="both", expand=True)
        
        # 标题
        ch_f = tk.Frame(cart_card, bg="#fafafa", pady=12)
        ch_f.pack(fill="x", padx=8, pady=(0, 8))
        tk.Label(ch_f, text="📦 待发货清单", bg="#fafafa", fg="#1f1f1f", 
                font=self.fonts['subtitle']).pack(side="left", padx=10)
        
        f_cart_con = tk.Frame(cart_card, bg="#ffffff")
        f_cart_con.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        # 配置Treeview样式（更大字体）
        style = ttk.Style()
        style.configure("Treeview", font=self.fonts['table_cell'], rowheight=36)
        style.configure("Treeview.Heading", font=self.fonts['table_header'])

        self.tree_cart = ttk.Treeview(f_cart_con, columns=("idx", "no", "size", "color", "ctns", "pcs", "qty", "prc", "amt"), 
                                     show="headings", style="Treeview")
        heads = ["#", "货号", "码段", "颜色", "箱数", "每箱", "总数", "单价", "金额"]
        for cid, head in zip(self.tree_cart["columns"], heads):
            self.tree_cart.heading(cid, text=head); self.tree_cart.column(cid, width=75, anchor="center")
        self.tree_cart.pack(fill="both", expand=True)
        self.tree_cart.bind("<Delete>", lambda e: self.delete_cart_item())
        self.tree_cart.bind("<Button-3>", self.show_cart_context_menu)
        self.tree_cart.bind("<Double-1>", self.on_cart_item_edit)
        
        self.cart_context_menu = tk.Menu(self.root, tearoff=0, font=self.fonts['body'])
        self.cart_context_menu.add_command(label="🗑️ 从当前清单删除", command=self.delete_cart_item)

        self.invoice_img_mode = tk.StringVar(value="small")
        self.invoice_img_h = tk.StringVar(value="150")
        self.invoice_img_w = tk.StringVar(value="150")

        img_size_frame = tk.Frame(cart_card, bg="#ffffff")
        img_size_frame.pack(fill="x", padx=8, pady=(0, 4))
        tk.Label(img_size_frame, text="主图大小：", bg="#ffffff", fg="#1f1f1f",
                 font=self.fonts['body']).pack(side="left")
        tk.Radiobutton(
            img_size_frame,
            text="默认小图模式",
            variable=self.invoice_img_mode,
            value="small",
            bg="#ffffff",
            font=self.fonts['small']
        ).pack(side="left", padx=(4, 8))
        custom_frame = tk.Frame(img_size_frame, bg="#ffffff")
        custom_frame.pack(side="left")
        tk.Radiobutton(
            custom_frame,
            text="自定义",
            variable=self.invoice_img_mode,
            value="custom",
            bg="#ffffff",
            font=self.fonts['small'],
            command=lambda: self.update_invoice_img_hint()
        ).pack(side="left")
        tk.Label(custom_frame, text="高", bg="#ffffff", fg="#1f1f1f",
                 font=self.fonts['small']).pack(side="left", padx=(6, 2))
        tk.Entry(custom_frame, width=4, textvariable=self.invoice_img_h,
                 font=self.fonts['small']).pack(side="left")
        tk.Label(custom_frame, text="宽", bg="#ffffff", fg="#1f1f1f",
                 font=self.fonts['small']).pack(side="left", padx=(6, 2))
        tk.Entry(custom_frame, width=4, textvariable=self.invoice_img_w,
                 font=self.fonts['small']).pack(side="left")
        tk.Label(custom_frame, text="(建议 150)", bg="#ffffff", fg="#999999",
                 font=self.fonts['small']).pack(side="left", padx=(6, 0))
        self.invoice_img_hint = tk.Label(custom_frame, text="", bg="#ffffff", fg="#999999",
                                         font=self.fonts['small'])
        self.invoice_img_hint.pack(side="left", padx=(6, 0))

        self.invoice_img_h.trace_add("write", lambda *a: self.update_invoice_img_hint())
        self.invoice_img_w.trace_add("write", lambda *a: self.update_invoice_img_hint())
        self.update_invoice_img_hint()

        btn_save = tk.Frame(cart_card, bg="#ffffff")
        btn_save.pack(fill="x", padx=8, pady=(0, 8))
        
        self.show_price_var = tk.BooleanVar(value=True)
        tk.Checkbutton(btn_save, text="显示价格金额", variable=self.show_price_var,
                      bg="#ffffff", font=self.fonts['body']).pack(side="left", padx=(0, 10))

        # 打印语言选择
        tk.Label(btn_save, text="|  打印语言:", bg="#ffffff", fg="#999", font=self.fonts['body']).pack(side="left", padx=(5, 5))
        tk.Radiobutton(btn_save, text="English", variable=self.print_lang_var, value="en", bg="#ffffff", font=self.fonts['body']).pack(side="left")
        tk.Radiobutton(btn_save, text="中文", variable=self.print_lang_var, value="zh", bg="#ffffff", font=self.fonts['body']).pack(side="left", padx=(0, 10))

        tk.Button(btn_save, text="💾 保存并打印", bg="#1677ff", fg="white", 
                 font=self.fonts['button'], height=1, command=self.save_print, relief="flat", cursor="hand2",
                 activebackground="#0958d9", padx=20, pady=8).pack(side="left", fill="x", expand=True)

        # 3. 左侧下方：区域3（商品搜索列表）放到左侧区域1下面，紧贴“财务结算”
        # 这样右侧待发货清单变高时，左侧不会留下大空白，而是由商品列表填充
        f_pick_con = tk.Frame(left_top_container, bg="#f5f5f5")
        f_pick_con.pack(fill="both", expand=True, pady=(8, 0))
        
        # Search Entry for Picking（更大字体）
        f_pick_search = tk.Frame(f_pick_con, bg="#ffffff", pady=14, padx=14); 
        f_pick_search.pack(fill="x", pady=(0, 8))
        tk.Label(f_pick_search, text="货号搜索:", font=self.fonts['body_bold'], 
                bg="#ffffff", fg="#1f1f1f").pack(side="left", padx=(0, 10))
        self.ent_bill_pick_search = tk.Entry(f_pick_search, width=28, font=self.fonts['body'],
                                            relief="solid", bd=1, highlightthickness=2,
                                            highlightbackground="#e0e0e0", highlightcolor="#1677ff"); 
        self.ent_bill_pick_search.pack(side="left", padx=8, ipady=5)
        self.ent_bill_pick_search.bind("<Return>", lambda e: self.on_bill_pick_search())
        tk.Button(f_pick_search, text="🔍 搜索", command=self.on_bill_pick_search, bg="#1677ff", fg="white", 
                 font=self.fonts['button'], relief="flat", cursor="hand2", padx=14, pady=6,
                 activebackground="#0958d9").pack(side="left", padx=6)
        
        # Batch Add Button
        tk.Button(f_pick_search, text="➕ 批量加入清单", command=self.add_picking_to_cart, bg="#52c41a", fg="white", 
                 font=self.fonts['button'], padx=14, pady=6, relief="flat", cursor="hand2",
                 activebackground="#389e0d").pack(side="right")

        # Picking List Header（更大更清晰）
        ph_f = tk.Frame(f_pick_con, bg="#fafafa", pady=12)
        ph_f.pack(fill="x")
        # 重要：表头不能用 Label(width=字符数)，否则和下面每行用 Frame(width=像素) 会对不齐
        # 这里表头也改成按像素宽度的列容器，确保字段名与内容严格对齐
        # 同时适当加宽列，保证视觉协调、输入框不被挤压
        for t, w in [("选择", 60), ("图片", 130), ("货号 No.", 150), ("颜色/码段", 200), ("单价 Price", 130), ("箱数 Ctns", 130)]:
            col_f = tk.Frame(ph_f, width=w, height=36, bg="#fafafa")
            col_f.pack(side="left", padx=1)
            col_f.pack_propagate(False)
            tk.Label(col_f, text=t, bg="#fafafa", fg="#1f1f1f",
                     font=self.fonts['table_header']).place(relx=0.5, rely=0.5, anchor="center")

        # Picking List Canvas
        self.canvas_bp = tk.Canvas(f_pick_con, bg="white", highlightthickness=0)
        self.canvas_bp.pack(side="left", fill="both", expand=True)
        self.scbar_bp = ttk.Scrollbar(f_pick_con, command=self.canvas_bp.yview)
        self.scbar_bp.pack(side="right", fill="y")
        self.canvas_bp.config(yscrollcommand=self.scbar_bp.set)
        
        self.frm_bill_pick = tk.Frame(self.canvas_bp, bg="white")
        self.canvas_bp.create_window((0,0), window=self.frm_bill_pick, anchor="nw", tags="frame")
        self.frm_bill_pick.bind("<Configure>", lambda e: self.canvas_bp.config(scrollregion=self.canvas_bp.bbox("all")))
        self.canvas_bp.bind('<Configure>', lambda e: self.canvas_bp.itemconfig("frame", width=e.width))
        self.canvas_bp.bind_all("<MouseWheel>", lambda e: self.on_mousewheel_bp(e))


    def on_mousewheel_bp(self, event):
        try: self.canvas_bp.yview_scroll(int(-1*(event.delta/120)), "units")
        except: pass

    def on_bill_pick_search(self):
        for w in self.frm_bill_pick.winfo_children(): w.destroy()
        self.bill_pick_rows = []
        self.bill_pick_imgs = [] # Refs
        q = self.ent_bill_pick_search.get().lower().strip()
        if not q: return
        
        filtered = [p for p in self.products if q in str(p.get('no', '')).lower()]

        for i, p in enumerate(filtered):
            bg = "#fafafa" if i%2==0 else "#ffffff"
            row = tk.Frame(self.frm_bill_pick, bg=bg, height=120, bd=0)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)
            
            # Checkbox
            var = tk.BooleanVar(value=True)
            chk_f = tk.Frame(row, width=50, height=120, bg=bg); chk_f.pack(side="left"); chk_f.pack_propagate(False)
            cb = tk.Checkbutton(chk_f, variable=var, bg=bg); cb.place(relx=0.5, rely=0.5, anchor="center")
            
            # Image
            img_f = tk.Frame(row, width=120, height=120, bg=bg); img_f.pack(side="left"); img_f.pack_propagate(False)
            img_lbl = tk.Label(img_f, text="无图", bg="#f5f5f5", fg="#8c8c8c", font=self.fonts['small'])
            if p.get('img'):
                try:
                    p_img = Image.open(BytesIO(base64.b64decode(p['img'])))
                    p_img.thumbnail((100, 100))
                    tk_img = ImageTk.PhotoImage(p_img)
                    self.bill_pick_imgs.append(tk_img)
                    img_lbl.config(image=tk_img, text="")
                except: pass
            img_lbl.place(relx=0.5, rely=0.5, anchor="center", width=100, height=100)
            
            # Data Labels - NO（更大字体）
            nf = tk.Frame(row, width=150, height=120, bg=bg); nf.pack(side="left", padx=1); nf.pack_propagate(False)
            tk.Label(nf, text=p['no'], bg=bg, font=self.fonts['body_bold'], fg="#1f1f1f").place(relx=0.5, rely=0.5, anchor="center")
            
            # Data Labels - Color/Size（更大字体）
            cs_f = tk.Frame(row, width=200, height=120, bg=bg); cs_f.pack(side="left", padx=1); cs_f.pack_propagate(False)
            tk.Label(cs_f, text=f"{p.get('color','')} / {p.get('size','')}", bg=bg, 
                    font=self.fonts['body'], fg="#1f1f1f", wraplength=150).place(relx=0.5, rely=0.5, anchor="center")
            
            # Editable Price（更大字体）
            pf = tk.Frame(row, width=130, height=120, bg=bg); pf.pack(side="left", padx=1); pf.pack_propagate(False)
            ep = tk.Entry(pf, width=12, font=self.fonts['body'], justify="center",
                         relief="solid", bd=1, highlightthickness=2,
                         highlightbackground="#e0e0e0", highlightcolor="#1677ff"); 
            ep.insert(0, str(p.get('price', 0))); ep.place(relx=0.5, rely=0.5, anchor="center")
            
            # Editable Ctns（更大字体）
            cf = tk.Frame(row, width=130, height=120, bg=bg); cf.pack(side="left", padx=1); cf.pack_propagate(False)
            ec = tk.Entry(cf, width=12, font=self.fonts['body_bold'], bg="#fff7e6", justify="center",
                         relief="solid", bd=1, highlightthickness=2,
                         highlightbackground="#ffd591", highlightcolor="#fa8c16"); 
            ec.place(relx=0.5, rely=0.5, anchor="center")
            
            self.bill_pick_rows.append({"p": p, "var": var, "ep": ep, "ec": ec})

        self.canvas_bp.update_idletasks()
        self.canvas_bp.config(scrollregion=self.canvas_bp.bbox("all"))

    def add_picking_to_cart(self):
        added = 0
        for r in self.bill_pick_rows:
            if r['var'].get():
                try:
                    ctns_str = r['ec'].get().strip()
                    if not ctns_str: continue # 允许箱数为空则跳过
                    ctns = int(ctns_str)
                    if ctns <= 0: continue
                    
                    prc = float(r['ep'].get() or 0)
                    p = r['p']
                    pcs = int(p.get('pcs', 0) or 0)
                    
                    self.cart_items.append({
                        "no": p['no'], 
                        "size": p.get('size', ''), 
                        "color": p.get('color', ''), 
                        "ctns": ctns, 
                        "pcs": pcs, 
                        "total": ctns*pcs, 
                        "price": prc, 
                        "amount": ctns*pcs*prc, 
                        "img": p.get('img')
                    })
                    added += 1
                except: continue
        
        if added > 0:
            self.refresh_cart()
            for w in self.frm_bill_pick.winfo_children(): w.destroy()
            self.bill_pick_rows = []
            messagebox.showinfo("成功", f"已成功将 {added} 款商品加入发货清单！")
        else:
            messagebox.showwarning("提示", "未检测到已填写箱数的已选商品。")

    def update_invoice_img_hint(self):
        try:
            mode = self.invoice_img_mode.get()
        except Exception:
            return
        try:
            if mode != "custom":
                if hasattr(self, "invoice_img_hint"):
                    self.invoice_img_hint.config(text="")
                return
            h = int(self.invoice_img_h.get() or 0)
            w = int(self.invoice_img_w.get() or 0)
        except Exception:
            if hasattr(self, "invoice_img_hint"):
                self.invoice_img_hint.config(text="")
            return
        if h <= 0 or w <= 0:
            if hasattr(self, "invoice_img_hint"):
                self.invoice_img_hint.config(text="请输入大于 0 的高宽值，例如 150")
            return
        row_h = h + 10
        approx_rows = max(1, 800 // row_h)
        if hasattr(self, "invoice_img_hint"):
            self.invoice_img_hint.config(text=f"预计每页约 {approx_rows} 个商品")

    def gen_invoice_html(self, d):
        lang = self.print_lang_var.get()
        t = self.TRANS.get(lang, self.TRANS['en'])

        subtotal = sum(it['amount'] for it in d['items'])
        shipping = float(d.get('shipping', 0) or 0)
        deposit = float(d.get('deposit', 0) or 0)
        paid = float(d.get('paid', 0) or 0)
        total_all = subtotal + shipping
        balance = total_all - deposit - paid
        total_ctns = sum(it['ctns'] for it in d['items'])
        total_qty = sum(it['total'] for it in d['items'])

        # 获取显示价格选项
        show_price = True
        if hasattr(self, 'show_price_var'):
            show_price = self.show_price_var.get()

        img_mode = getattr(self, "invoice_img_mode", None)
        img_h = 70
        img_w = 100
        if img_mode is not None and self.invoice_img_mode.get() == "custom":
            try:
                h = int(self.invoice_img_h.get() or 0)
                w = int(self.invoice_img_w.get() or 0)
                if h > 0 and w > 0:
                    img_h = h
                    img_w = w
            except Exception:
                pass
        row_h = img_h + 10
        photo_col_w = img_w + 20

        try:
            approx_rows = max(1, 800 // row_h)
            if hasattr(self, "invoice_img_hint"):
                self.invoice_img_hint.config(text=f"预计每页约 {approx_rows} 个商品")
        except Exception:
            pass

        rows = ""
        for it in d['items']:
            price_td = f'<td style="border:1px solid #ddd; padding:8px;">¥{it["price"]:.2f}</td>' if show_price else ''
            amount_td = f'<td style="border:1px solid #ddd; padding:8px; font-weight:bold; color:#d32f2f;">¥{it["amount"]:.2f}</td>' if show_price else ''
            
            rows += f"""
            <tr style="text-align:center; height:{row_h}px;">
                <td style="border:1px solid #ddd; padding:8px;">
                    <img src="data:image/jpeg;base64,{it.get('img', '')}" style="height:{img_h}px; max-width:{img_w}px; object-fit:contain;">
                </td>
                <td style="border:1px solid #ddd; padding:8px; font-weight:bold;">{it['no']}</td>
                <td style="border:1px solid #ddd; padding:8px;">{it.get('size', '--')}</td>
                <td style="border:1px solid #ddd; padding:8px;">{it.get('color', '--')}</td>
                <td style="border:1px solid #ddd; padding:8px;">{it['ctns']}</td>
                <td style="border:1px solid #ddd; padding:8px;">{it['pcs']}</td>
                <td style="border:1px solid #ddd; padding:8px; font-weight:bold;">{it['total']}</td>
                {price_td}
                {amount_td}
            </tr>"""

        # 表头处理
        price_th = f'<th width="100">{t["price"]}</th>' if show_price else ''
        amount_th = f'<th width="120">{t["amount"]}</th>' if show_price else ''

        # 底部统计处理
        summary_html = f"""
                <div class="summary-item"><b>{t['ctns']}:</b> <span style="color:#1976d2; font-weight:bold;">{total_ctns}</span></div>
                <div class="summary-item"><b>{t['qty']}:</b> <span style="color:#1976d2; font-weight:bold;">{total_qty}</span></div>
        """
        if show_price:
            summary_html += f"""
                <div class="summary-item"><b>{t['subtotal']}:</b> ¥{subtotal:.2f}</div>
                <div class="summary-item"><b>{t['freight']}:</b> ¥{shipping:.2f}</div>
                <div class="summary-item"><b>{t['total']}:</b> <span style="font-weight:bold; color:#f57c00; font-size:1.1em;">¥{total_all:.2f}</span></div>
                <div class="summary-item"><b>{t['deposit']}:</b> ¥{deposit:.2f}</div>
                <div class="summary-item"><b>{t['paid']}:</b> ¥{paid:.2f}</div>
                <div class="summary-item" style="border-left: 2px solid #f57c00; padding-left:15px; margin-left:10px;">
                    <b style="color:#d32f2f; border:none; padding:0;">{t['balance']}:</b> <span class="summary-highlight">¥{balance:.2f}</span>
                </div>
            """

        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; padding: 40px; color: #333; }}
                .header-table {{ width: 100%; margin-bottom: 20px; border:none; }}
                .title {{ font-size: 38px; font-weight: bold; text-align: center; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 2px; }}
                .title-sender {{ text-align: center; font-size: 9px; color: #666; margin-bottom: 8px; white-space: nowrap; line-height: 1.2; }}
                .line {{ border-bottom: 3px solid #000; margin-bottom: 12px; }}
                .meta-row {{ display: flex; flex-wrap: nowrap; align-items: center; justify-content: flex-start; margin-bottom: 4px; padding: 5px 10px; border: 1px solid #eee; background: #fafafa; border-radius: 4px; overflow: hidden; }}
                .meta-label {{ font-weight: bold; color: #1976d2; margin-right: 12px; border-right: 2px solid #1976d2; padding-right: 10px; flex-shrink: 0; font-size: 15px; min-width: 110px; }}
                .meta-container {{ display: flex; flex-wrap: nowrap; flex-grow: 1; align-items: center; overflow: hidden; font-size: clamp(10px, 1.35vw, 16px); }}
                .meta-item {{ margin-right: 15px; white-space: nowrap; flex-shrink: 0; }}
                .meta-item b {{ color: #777; font-size: 0.9em; margin-right: 4px; border-left: 1px solid #ddd; padding-left: 8px; }}
                .meta-item:first-child b {{ border-left: none; padding-left: 0; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 5px; font-size: 18px; }}
                th {{ background: #333; color: #fff; padding: 6px 5px; text-transform: uppercase; border: 1px solid #333; font-size: 18px; }}
                td {{ border: 1px solid #ddd; padding: 10px 8px; }}
                .summary-row {{ display: flex; flex-wrap: nowrap; align-items: center; justify-content: space-between; margin-top: 15px; padding: 10px 15px; border: 2px solid #f57c00; background: #fff8e1; border-radius: 4px; overflow: hidden; font-size: clamp(9px, 1.2vw, 17px); }}
                .summary-item {{ white-space: nowrap; flex-shrink: 1; margin: 0 5px; }}
                .summary-item b {{ color: #666; font-size: 0.85em; margin-right: 4px; border-left: 1px solid #ffcc80; padding-left: 8px; text-transform: uppercase; }}
                .summary-item:first-child b {{ border-left: none; padding-left: 0; }}
                .summary-highlight {{ font-weight: bold; font-size: 1.2em; color: #d32f2f; }}
                .note-box {{ margin-top: 20px; padding: 15px; border: 1px solid #ddd; background: #f9f9f9; font-size: 13px; }}
                /* 打印页码设置 */
                body {{ counter-reset: page; }}
                .page-numbering {{
                    display: none;
                    position: fixed;
                    bottom: 10px;
                    right: 20px;
                    font-size: 12px;
                    color: #666;
                }}
                @media print {{
                    .no-print {{ display: none; }}
                    body {{ padding: 20px; }}
                    @page {{ margin: 1cm; }}
                    .page-numbering {{ 
                        display: block; 
                        counter-increment: page; 
                    }}
                    .page-numbering::after {{
                        content: "第 " counter(page) " 页 / Page " counter(page);
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="title">{t['title_invoice']}</div>
            <div class="title-sender">
                {t['invoice_no']}: {d['id']} | {t['date']}: {d['date']} | {t['sender']}: {d.get('sender', '-')} | {t['phone']}: {d.get('sender_phone', '-')} | {t['address']}: {d.get('sender_address', '-')}
            </div>
            <div class="line"></div>
            
            <div class="meta-row" style="border-left: 5px solid #1976d2;">
                <div class="meta-label">{t['receiver']}</div>
                <div class="meta-container">
                    <div class="meta-item"><b>{t['client']}:</b> {d.get('client', '-')}</div>
                    <div class="meta-item"><b>{t['mark']}:</b> {d.get('mark', '-')}</div>
                    <div class="meta-item"><b>{t['phone']}:</b> {d.get('phone', '-')}</div>
                    <div class="meta-item"><b>{t['address']}:</b> {d.get('address', '-')}</div>
                </div>
            </div>

            <table>
                <thead>
                    <tr>
                        <th width="{photo_col_w}">{t['photo']}</th>
                        <th width="100">{t['no']}</th>
                        <th width="80">{t['size']}</th>
                        <th width="100">{t['color']}</th>
                        <th width="80">{t['ctns']}</th>
                        <th width="80">{t['pcs_ctn']}</th>
                        <th width="100">{t['qty']}</th>
                        {price_th}
                        {amount_th}
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>

            <div class="summary-row" style="{f'justify-content: flex-end;' if not show_price else ''}">
                {summary_html}
            </div>

            {f'<div class="note-box"><b>{t["note"]}:</b> {d.get("note", "")}</div>' if d.get("note") else ''}

            <div class="page-numbering"></div>

            <button class="no-print" onclick="window.print()" style="position:fixed; bottom:30px; right:30px; padding:15px 40px; background:#333; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold; box-shadow: 0 4px 10px rgba(0,0,0,0.2);">{t['print_invoice']}</button>
        </body>
        </html>"""
        self.write_and_open(html, f"Inv_{d['id']}.html")

    def delete_product(self):
        # 如果有选中的选中项（复选框），则批量删除；否则删除当前选中的高亮项
        checked_ids = [p.get('_id') for p in self.products if p.get('_checked')]
        if checked_ids:
            if messagebox.askyesno("确认删除", f"确定要删除选中的 {len(checked_ids)} 个商品吗？"):
                self.products = [p for p in self.products if p.get('_id') not in checked_ids]
                self.save_json(FILES["product"], self.products)
                self.refresh_product_list()
                if self.products: self.update_browser()
        elif self.selected_prod_id:
            if messagebox.askyesno("确认删除", "确定要删除当前选中的商品吗？"):
                self.products = [p for p in self.products if p.get('_id') != self.selected_prod_id]
                self.selected_prod_id = None
                self.save_json(FILES["product"], self.products)
                self.refresh_product_list()
                if self.products: self.update_browser()
        else:
            messagebox.showinfo("提示", "请先选择要删除的商品！")

    def show_product_context_menu(self, e, pid=None):
        # 右键时同步选中行，便于“编辑/删除”作用于当前行
        if pid is not None:
            self.selected_prod_id = str(pid)
            self.refresh_product_list()
        self.prod_context_menu.post(e.x_root, e.y_root)
    
    def delete_cart_item(self):
        sel = self.tree_cart.selection()
        if sel:
            idx = int(self.tree_cart.item(sel[0], "values")[0]) - 1
            if 0 <= idx < len(self.cart_items):
                del self.cart_items[idx]
                self.refresh_cart()
    
    def show_cart_context_menu(self, e):
        item = self.tree_cart.identify_row(e.y)
        if item:
            self.tree_cart.selection_set(item)
            self.cart_context_menu.post(e.x_root, e.y_root)
    
    def delete_history_item(self):
        sel = self.tree_hist.selection()
        if sel:
            bid = self.tree_hist.item(sel[0], "values")[1]
            if messagebox.askyesno("确认删除", f"确定要删除销售单 {bid} 吗？"):
                self.history = [h for h in self.history if h['id'] != bid]
                self.save_json(FILES["history"], self.history)
                self.refresh_history_list()
    
    def show_history_context_menu(self, e):
        item = self.tree_hist.identify_row(e.y)
        if item:
            self.tree_hist.selection_set(item)
            self.history_context_menu.post(e.x_root, e.y_root)

    def refresh_history_list(self):
        self.tree_hist.delete(*self.tree_hist.get_children())
        for d in reversed(self.history): self.tree_hist.insert("", "end", values=(d['date'], d['id'], d.get('client',''), f"¥{sum(i['amount'] for i in d['items']):.2f}"))

    def refresh_quote_history_list(self):
        self.tree_q_hist.delete(*self.tree_q_hist.get_children())
        for d in reversed(self.quote_history): self.tree_q_hist.insert("", "end", values=(d['date'], d['id'], d.get('client','')))

    def refresh_product_list(self):
        for w in self.frm_p_list.winfo_children(): w.destroy()
        # 每次刷新前清空映射，避免残留旧引用
        self.prod_row_widgets = {}
        self.prod_check_vars = {}
        
        # 当前列表区域总宽度，用于计算各列按“基础宽度”比例放大
        try:
            total_width = max(self.canvas_p.winfo_width(), 600)
        except Exception:
            total_width = 1200
        base_total = sum(w for _, _, w in self.cols_cfg)
        scale = total_width / base_total if base_total > 0 else 1
        # 计算实际像素宽度，并同步更新表头列宽
        self.current_col_widths = [int(base_w * scale) for _, _, base_w in self.cols_cfg]
        if getattr(self, "header_col_frames", None):
            for f, w in zip(self.header_col_frames, self.current_col_widths):
                try:
                    f.config(width=w)
                except Exception:
                    pass
        search_q = self.ent_lib_search.get().lower()
        
        # Refresh filters
        for w in self.f_tag_filter.winfo_children(): w.destroy()
        all_tags = ["全部"] + sorted(list(set(t.strip() for p in self.products for t in (p.get('tag') or '').split(',') if t.strip())))
        for t in all_tags:
            is_active = (t == self.current_filter_tag)
            btn_bg = "#1677ff" if is_active else "#f0f0f0"
            btn_fg = "white" if is_active else "#1f1f1f"
            tk.Button(self.f_tag_filter, text=t, bg=btn_bg, fg=btn_fg, 
                     font=self.fonts['body'], relief="flat", cursor="hand2",
                     activebackground="#1677ff" if not is_active else "#0958d9",
                     activeforeground="white",
                     command=lambda x=t: [setattr(self, 'current_filter_tag', x), setattr(self, 'current_page', 1), self.refresh_product_list()],
                     padx=12, pady=5).pack(side="left", padx=4, pady=2)
        
        self.prod_list_imgs = [] # Keep refs
        self.prod_row_widgets = {}

        filtered = []
        for p in self.products:
            if '_id' not in p: p['_id'] = str(uuid.uuid4())
            if search_q and search_q not in p['no'].lower(): continue
            tag_str = p.get('tag') or ''
            if self.current_filter_tag != "全部" and self.current_filter_tag not in [x.strip() for x in tag_str.split(',')]: continue
            filtered.append(p)

        # 分页逻辑
        total_items = len(filtered)
        total_pages = max(1, (total_items + self.items_per_page - 1) // self.items_per_page)  # 向上取整
        
        # 确保当前页码在有效范围内
        if self.current_page > total_pages:
            self.current_page = max(1, total_pages)
        if self.current_page < 1:
            self.current_page = 1
        
        # 计算当前页的数据范围
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        current_page_items = filtered[start_idx:end_idx]
        
        # 更新翻页按钮状态
        if hasattr(self, 'btn_prev') and hasattr(self, 'btn_next'):
            self.btn_prev.config(state="normal" if self.current_page > 1 else "disabled")
            self.btn_next.config(state="normal" if self.current_page < total_pages else "disabled")
        
        # 更新页码信息显示
        if hasattr(self, 'lbl_page_info'):
            self.lbl_page_info.config(text=f"第 {self.current_page} 页 / 共 {total_pages} 页 (共 {total_items} 条)")
        
        # Render Rows（只渲染当前页的数据）
        for i, p in enumerate(current_page_items):
            p_id = str(p.get('_id', ''))
            is_selected = (self.selected_prod_id and str(self.selected_prod_id) == p_id)
            base_bg = "#fafafa" if i % 2 == 0 else "#ffffff"
            bg_color = "#e6f7ff" if is_selected else base_bg
            row = tk.Frame(self.frm_p_list, bg=bg_color, height=120, bd=0)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)
            
            # 1. 选中状态 Checkbox
            var = tk.BooleanVar(value=p.get('_checked', False))
            def on_chk_click(v=var, prod=p): prod['_checked'] = v.get()
            # 记录勾选变量，方便“全选/取消全选”时直接更新 UI，而不用重建整列表
            self.prod_check_vars[p_id] = var
            
            chk_w, img_w = self.current_col_widths[0], self.current_col_widths[1]
            chk_f = tk.Frame(row, width=chk_w, height=120, bg=bg_color); chk_f.pack(side="left"); chk_f.pack_propagate(False)
            cb = tk.Checkbutton(chk_f, variable=var, command=on_chk_click, bg=bg_color)
            cb.place(relx=0.5, rely=0.5, anchor="center")
            
            img_f = tk.Frame(row, width=img_w, height=120, bg=bg_color); img_f.pack(side="left"); img_f.pack_propagate(False)
            row.chk_var = var # Keep BooleanVar alive
            img_lbl = tk.Label(img_f, text="无图", bg="#f5f5f5", fg="#8c8c8c", font=self.fonts['small'])
            if p.get('img'):
                try:
                    p_img = Image.open(BytesIO(base64.b64decode(p['img'])))
                    p_img.thumbnail((100, 100))
                    tk_img = ImageTk.PhotoImage(p_img)
                    self.prod_list_imgs.append(tk_img)
                    img_lbl.config(image=tk_img, text="")
                except: pass
            img_lbl.place(relx=0.5, rely=0.5, anchor="center", width=100, height=100)
            
            # 保存商品引用到控件，用于事件处理
            img_lbl._product_data = p
            img_f._product_data = p
            
            # 图片单独绑定双击事件：查看原图（使用命名函数避免闭包问题）
            def on_img_double_click(event):
                widget = event.widget
                if hasattr(widget, '_product_data'):
                    self.view_original_image(widget._product_data)
            
            img_lbl.bind("<Double-1>", on_img_double_click)
            img_f.bind("<Double-1>", on_img_double_click)
            
            # 图片控件也绑定单击事件，用于选中行
            img_lbl.bind("<Button-1>", lambda e, pid=p_id: self.on_list_row_click(e, pid))
            img_f.bind("<Button-1>", lambda e, pid=p_id: self.on_list_row_click(e, pid))
            
            # Cols Data（更大字体）
            # 后面 7 列根据当前宽度比例进行拉伸
            data_widths = self.current_col_widths[2:]
            cols_data = [
                (p['no'],                data_widths[0]),
                (p.get('tag', ''),       data_widths[1]),
                (p.get('color', ''),     data_widths[2]),
                (p.get('size', ''),      data_widths[3]),
                (f"{p.get('cost_price', 0)}", data_widths[4]),
                (f"{p.get('price', 0)}",      data_widths[5]),
                (f"{p.get('pcs', 0)}",        data_widths[6]),
                (f"{p.get('moq_ctns', 0)}",   data_widths[7]),
            ]
            
            # row_widgets：用于后续高亮/恢复背景色（包括图片控件，但图片有单独的双击查看原图事件）
            row_widgets = [row, img_f, img_lbl, chk_f]
            
            # 数据行：所有列都按比例拉伸，不只是最后一列
            for txt, w in cols_data:
                cf = tk.Frame(row, width=w, height=120, bg=bg_color)
                cf.pack(side="left", padx=1)
                cf.pack_propagate(False)
                text_color = "#1677ff" if is_selected and txt == p['no'] else "#1f1f1f"
                l = tk.Label(cf, text=txt, bg=bg_color, font=self.fonts['table_cell'], fg=text_color)
                l.place(relx=0.5, rely=0.5, anchor="center")
                # 记录默认背景色，方便后续仅更新选中行而不重绘整个列表
                cf._default_bg = base_bg
                l._default_bg = base_bg
                row_widgets.append(cf)
                row_widgets.append(l)

            # 将行内所有控件的默认背景记录下来（未选中时恢复用）
            for w in row_widgets:
                try:
                    w._default_bg = base_bg
                except Exception:
                    pass

            # 仅在行主体和数据列上绑定选中事件（复选框只负责勾选，不触发行重绘）
            # 图片控件不在这里绑定双击编辑事件，因为它有单独的双击查看原图事件
            for w in row_widgets:
                # 跳过图片控件，它们已经有单独的事件绑定
                if w == img_f or w == img_lbl:
                    continue
                w.bind("<Button-1>", lambda e, pid=p_id: self.on_list_row_click(e, pid))
                w.bind("<Double-1>", lambda e, pid=p_id: [self.on_list_row_click(e, pid), self.open_edit_product_dialog()])
                w.bind("<Button-3>", lambda e, pid=p_id: self.show_product_context_menu(e, pid))
            
            # 确保图片控件的双击事件在最后绑定，优先级最高
            def on_img_double_click_final(event):
                widget = event.widget
                if hasattr(widget, '_product_data'):
                    self.view_original_image(widget._product_data)
            
            img_lbl.bind("<Double-1>", on_img_double_click_final)
            img_f.bind("<Double-1>", on_img_double_click_final)
            
            self.prod_row_widgets[p_id] = row_widgets

        self.canvas_p.update_idletasks()
        self.canvas_p.config(scrollregion=self.canvas_p.bbox("all"))

    def view_original_image(self, product):
        """查看商品原图"""
        if not product.get('img'):
            messagebox.showinfo("提示", "该商品没有图片")
            return

        try:
            # 解码图片数据
            img_data = base64.b64decode(product['img'])
            img = Image.open(BytesIO(img_data))

            # 创建查看原图窗口
            img_win = tk.Toplevel(self.root)
            img_win.title(f"查看原图 - {product.get('no', '商品')}")
            img_win.geometry("800x600")
            img_win.grab_set()
            
            # 居中显示
            img_win.update_idletasks()
            x = (img_win.winfo_screenwidth() // 2) - (img_win.winfo_width() // 2)
            y = (img_win.winfo_screenheight() // 2) - (img_win.winfo_height() // 2)
            img_win.geometry(f"+{x}+{y}")
            
            # 获取图片原始尺寸
            orig_width, orig_height = img.size
            
            # 计算显示尺寸（保持宽高比，最大不超过窗口大小）
            max_width = 750
            max_height = 550
            
            if orig_width > max_width or orig_height > max_height:
                ratio = min(max_width / orig_width, max_height / orig_height)
                display_width = int(orig_width * ratio)
                display_height = int(orig_height * ratio)
            else:
                display_width = orig_width
                display_height = orig_height

            # 调整图片大小用于显示
            display_img = img.copy()
            display_img.thumbnail((display_width, display_height), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(display_img)

            # 创建Canvas用于显示图片（支持滚动）
            canvas_frame = tk.Frame(img_win, bg="#f5f5f5")
            canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            canvas = tk.Canvas(canvas_frame, bg="#ffffff", highlightthickness=1, highlightbackground="#d9d9d9")
            scrollbar_v = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
            scrollbar_h = ttk.Scrollbar(canvas_frame, orient="horizontal", command=canvas.xview)
            
            canvas.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)

            # 显示图片
            canvas.create_image(0, 0, anchor="nw", image=tk_img)
            canvas.config(scrollregion=canvas.bbox("all"))

            # 布局滚动条和画布
            canvas.grid(row=0, column=0, sticky="nsew")
            scrollbar_v.grid(row=0, column=1, sticky="ns")
            scrollbar_h.grid(row=1, column=0, sticky="ew")
            canvas_frame.grid_rowconfigure(0, weight=1)
            canvas_frame.grid_columnconfigure(0, weight=1)

            # 保存图片引用，防止被垃圾回收
            canvas.image = tk_img

            # 底部信息栏
            info_frame = tk.Frame(img_win, bg="#f5f5f5", pady=5)
            info_frame.pack(fill="x", padx=10, pady=(0, 10))

            info_text = f"货号: {product.get('no', '')} | 原始尺寸: {orig_width} × {orig_height} 像素"
            tk.Label(info_frame, text=info_text, font=self.fonts['body'], bg="#f5f5f5", fg="#666").pack(side="left", padx=10)

            def copy_image_to_clipboard():
                try:
                    kernel32 = ctypes.windll.kernel32
                    user32 = ctypes.windll.user32

                    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
                    kernel32.GlobalAlloc.restype = ctypes.c_void_p
                    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
                    kernel32.GlobalLock.restype = ctypes.c_void_p
                    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
                    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]

                    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
                    user32.OpenClipboard.restype = ctypes.c_int
                    user32.EmptyClipboard.argtypes = []
                    user32.EmptyClipboard.restype = ctypes.c_int
                    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
                    user32.SetClipboardData.restype = ctypes.c_void_p
                    user32.CloseClipboard.argtypes = []
                    user32.CloseClipboard.restype = ctypes.c_int

                    output = BytesIO()
                    img.convert("RGB").save(output, "BMP")
                    data = output.getvalue()[14:]
                    output.close()

                    CF_DIB = 8
                    GMEM_MOVEABLE = 0x0002
                    GMEM_DDESHARE = 0x2000
                    flags = GMEM_MOVEABLE | GMEM_DDESHARE

                    if not user32.OpenClipboard(None):
                        raise RuntimeError("OpenClipboard 失败")
                    user32.EmptyClipboard()

                    h_global = kernel32.GlobalAlloc(flags, len(data))
                    if not h_global:
                        raise RuntimeError("GlobalAlloc 失败")

                    p_data = kernel32.GlobalLock(h_global)
                    if not p_data:
                        kernel32.GlobalFree(h_global)
                        raise RuntimeError("GlobalLock 失败")

                    ctypes.memmove(ctypes.c_void_p(p_data), data, len(data))
                    kernel32.GlobalUnlock(h_global)
                    user32.SetClipboardData(CF_DIB, h_global)
                    user32.CloseClipboard()

                    messagebox.showinfo("成功", "图片已复制到剪贴板，可在微信、Word 等处粘贴。")
                except Exception as e:
                    try:
                        ctypes.windll.user32.CloseClipboard()
                    except Exception:
                        pass
                    messagebox.showerror("错误", f"复制图片失败：{str(e)}")

            def save_image_as():
                try:
                    default_name = f"{product.get('no', '商品')}.jpg"
                    path = filedialog.asksaveasfilename(
                        title="图片另存为",
                        defaultextension=".jpg",
                        initialfile=default_name,
                        filetypes=[
                            ("JPEG 图片", "*.jpg;*.jpeg"),
                            ("PNG 图片", "*.png"),
                            ("所有文件", "*.*")
                        ]
                    )
                    if not path:
                        return
                    ext = os.path.splitext(path)[1].lower()
                    fmt = "JPEG" if ext != ".png" else "PNG"
                    img.save(path, fmt)
                    messagebox.showinfo("成功", "图片已保存。")
                except Exception as e:
                    messagebox.showerror("错误", f"保存图片失败：{str(e)}")

            tk.Button(info_frame, text="复制图片", command=copy_image_to_clipboard,
                     bg="#52c41a", fg="white", font=self.fonts['button'],
                     relief="flat", cursor="hand2", padx=14, pady=5,
                     activebackground="#389e0d").pack(side="right", padx=(0, 8))

            tk.Button(info_frame, text="图片另存为", command=save_image_as,
                     bg="#1677ff", fg="white", font=self.fonts['button'],
                     relief="flat", cursor="hand2", padx=14, pady=5,
                     activebackground="#0958d9").pack(side="right", padx=8)

            tk.Button(info_frame, text="关闭", command=img_win.destroy,
                     bg="#d9d9d9", fg="#1f1f1f", font=self.fonts['button'],
                     relief="flat", cursor="hand2", padx=14, pady=5,
                     activebackground="#bfbfbf").pack(side="right", padx=8)

            # 鼠标滚轮缩放（可选功能）
            def on_mousewheel(event):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            
            canvas.bind("<MouseWheel>", on_mousewheel)
            
        except Exception as e:
            messagebox.showerror("错误", f"无法显示图片：{str(e)}")

    def export_product_images(self):
        targets = [p for p in self.products if p.get('_checked')]
        if not targets and self.selected_prod_id:
            p = next((x for x in self.products if str(x.get('_id', '')) == str(self.selected_prod_id)), None)
            if p:
                targets = [p]
        if not targets:
            messagebox.showinfo("提示", "请先勾选商品，或在列表中点击选中一个商品，再导出原图。")
            return
        targets = [p for p in targets if p.get('img')]
        if not targets:
            messagebox.showinfo("提示", "选中的商品都没有图片，无法导出原图。")
            return

        folder = filedialog.askdirectory(title="选择原图导出文件夹")
        if not folder:
            return

        def sanitize(text):
            if text is None:
                text = ""
            s = str(text).strip()
            if not s:
                s = "未命名"
            bad = '<>:"/\\|?*'
            for ch in bad:
                s = s.replace(ch, "_")
            s = s.replace("\n", "_").replace("\r", "_")
            return s

        ok = 0
        for p in targets:
            try:
                img_b64 = p.get('img')
                if not img_b64:
                    continue
                img_data = base64.b64decode(img_b64)
                img = Image.open(BytesIO(img_data))
                no = sanitize(p.get('no', ''))
                color = sanitize(p.get('color', ''))
                size = sanitize(p.get('size', ''))
                price_val = p.get('price', 0)
                try:
                    price = float(price_val or 0)
                except Exception:
                    try:
                        price = float(str(price_val).replace("¥", "").strip() or 0)
                    except Exception:
                        price = 0.0
                price_str = f"{price:.2f}"
                name_core = f"{no}+{color}+{size}+{price_str}"
                filename = sanitize(name_core) + ".jpg"
                path = os.path.join(folder, filename)
                img.convert("RGB").save(path, "JPEG", quality=95)
                ok += 1
            except Exception:
                continue

        if ok > 0:
            messagebox.showinfo("成功", f"已导出 {ok} 张商品原图到：\n{folder}")
        else:
            messagebox.showwarning("提示", "未能成功导出任何图片。")

    def prev_page(self):
        """上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_product_list()
            # 滚动到顶部
            self.canvas_p.yview_moveto(0)
    
    def next_page(self):
        """下一页"""
        # 计算总页数
        search_q = self.ent_lib_search.get().lower()
        filtered = []
        for p in self.products:
            if '_id' not in p: p['_id'] = str(uuid.uuid4())
            if search_q and search_q not in p['no'].lower(): continue
            tag_str = p.get('tag') or ''
            if self.current_filter_tag != "全部" and self.current_filter_tag not in [x.strip() for x in tag_str.split(',')]: continue
            filtered.append(p)
        total_pages = max(1, (len(filtered) + self.items_per_page - 1) // self.items_per_page)
        
        if self.current_page < total_pages:
            self.current_page += 1
            self.refresh_product_list()
            # 滚动到顶部
            self.canvas_p.yview_moveto(0)
    
    def get_filtered_products(self):
        search_q = self.ent_lib_search.get().lower()
        filtered = []
        for p in self.products:
            if '_id' not in p:
                p['_id'] = str(uuid.uuid4())
            if search_q and search_q not in p['no'].lower():
                continue
            tag_str = p.get('tag') or ''
            if self.current_filter_tag != "全部" and self.current_filter_tag not in [x.strip() for x in tag_str.split(',')]:
                continue
            filtered.append(p)
        return filtered

    def toggle_select_page(self):
        val = self.select_page_var.get()
        filtered = self.get_filtered_products()
        start = (self.current_page - 1) * self.items_per_page
        end = start + self.items_per_page
        page_items = filtered[start:end]

        for p in page_items:
            p['_checked'] = val
            pid = str(p.get('_id', ''))
            var = self.prod_check_vars.get(pid)
            if var is not None:
                try:
                    var.set(val)
                except Exception:
                    pass

        if not val:
            try:
                self.select_all_var.set(False)
            except Exception:
                pass

    def toggle_select_all(self):
        """全选/取消全选：可以选择作用于当前页或所有筛选结果。这里是“全部筛选结果”复选框。"""
        val = self.select_all_var.get()
        filtered = self.get_filtered_products()

        for p in filtered:
            p['_checked'] = val
            pid = str(p.get('_id', ''))
            var = self.prod_check_vars.get(pid)
            if var is not None:
                try:
                    var.set(val)
                except Exception:
                    pass

        try:
            self.select_page_var.set(val)
        except Exception:
            pass

    def reset_edit_panel(self):
        self.selected_prod_id = None
        for w in self.prod_ents.values(): w.delete(0, tk.END)
        self.lbl_prod_img.config(image="", text="无图")
        self.lbl_prod_img.image = None
        self.current_img_data = None
        self.refresh_product_list()

    def open_new_product_panel(self):
        """显式打开新增商品模块：清空右侧表单并聚焦货号"""
        self.reset_edit_panel()
        # 聚焦到货号输入框，提升“新增”流程可见性
        if self.prod_ents.get('no'):
            self.prod_ents['no'].focus_set()
        # 切到商品库标签，确保用户能看到新增区域
        try:
            self.notebook.select(self.tab_products)
        except: 
            pass

    def open_multi_spec_image_dialog(self, products_to_add, parent_win):
        """
        打开多规格图片设置窗口
        products_to_add: 待保存的商品字典列表
        parent_win: 新增商品的主窗口 (用于保存成功后关闭)
        """
        win = tk.Toplevel(self.root)
        win.title("设置多规格图片")
        win.geometry("600x600")
        win.configure(bg="#f0f2f5")
        win.grab_set()
        
        # 居中
        win.update_idletasks()
        w = 600
        h = 600
        x = (win.winfo_screenwidth() // 2) - (w // 2)
        y = (win.winfo_screenheight() // 2) - (h // 2)
        win.geometry(f"+{x}+{y}")

        tk.Label(win, text="请为不同颜色的商品设置图片", font=("微软雅黑", 14, "bold"), bg="#f0f2f5").pack(pady=10)
        
        # Scrollable Frame
        canvas = tk.Canvas(win, bg="#f0f2f5", highlightthickness=0)
        scrollbar = tk.Scrollbar(win, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f0f2f5")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10)
        scrollbar.pack(side="right", fill="y")
        
        # Store image labels/data references to update UI
        img_refs = []

        def update_row_img(idx, b64_data):
            products_to_add[idx]["img"] = b64_data
            # Update thumbnail
            try:
                if b64_data:
                    img = Image.open(BytesIO(base64.b64decode(b64_data)))
                    # Resize for thumbnail
                    img.thumbnail((80, 80))
                    photo = ImageTk.PhotoImage(img)
                    img_refs[idx]['lbl'].config(image=photo, text="")
                    img_refs[idx]['lbl'].image = photo # keep reference
                else:
                    img_refs[idx]['lbl'].config(image="", text="无图片")
            except Exception as e:
                print(e)

        def choose_img_for(idx):
            p = filedialog.askopenfilename(title="选择图片", filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.webp")])
            if p:
                try:
                    with open(p, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                    update_row_img(idx, b64)
                except Exception as e:
                    messagebox.showerror("错误", str(e))

        def paste_img_for(idx):
            try:
                img = self.get_clipboard_image()
                if img:
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    b64 = base64.b64encode(buf.getvalue()).decode()
                    update_row_img(idx, b64)
                else:
                    messagebox.showinfo("提示", "剪贴板无图片")
            except Exception as e:
                messagebox.showerror("错误", str(e))

        for i, p in enumerate(products_to_add):
            row = tk.Frame(scrollable_frame, bg="white", pady=10, padx=10, relief="groove", bd=1)
            row.pack(fill="x", pady=5, padx=5)
            
            # Color Label
            tk.Label(row, text=f"颜色: {p.get('color')}", font=("微软雅黑", 12, "bold"), width=15, anchor="w", bg="white").pack(side="left")
            
            # Image Thumbnail
            img_frame = tk.Frame(row, width=80, height=80, bg="#eee")
            img_frame.pack(side="left", padx=10)
            img_frame.pack_propagate(False)
            
            lbl = tk.Label(img_frame, text="无图片", bg="#eee")
            lbl.pack(fill="both", expand=True)
            
            img_refs.append({'lbl': lbl})
            
            # Init with existing image if any
            if p.get("img"):
                update_row_img(i, p["img"])

            # Buttons
            btn_frame = tk.Frame(row, bg="white")
            btn_frame.pack(side="left", padx=10)
            
            tk.Button(btn_frame, text="选择图片", command=lambda idx=i: choose_img_for(idx)).pack(fill="x", pady=2)
            tk.Button(btn_frame, text="粘贴图片", command=lambda idx=i: paste_img_for(idx)).pack(fill="x", pady=2)

        # Bottom Action Bar
        action_bar = tk.Frame(win, bg="#f0f2f5", pady=10)
        action_bar.pack(side="bottom", fill="x")
        
        def confirm_save():
            # Save all
            for p in products_to_add:
                self.products.append(p)
            
            self.save_json(FILES["product"], self.products)
            self.refresh_product_list()
            if self.products:
                try:
                    self.update_browser()
                except: pass
            
            win.destroy()
            parent_win.destroy()
            messagebox.showinfo("成功", f"批量新增 {len(products_to_add)} 个商品成功！")

        tk.Button(action_bar, text="确认保存全部", command=confirm_save, bg="#1976d2", fg="white", font=("微软雅黑", 12), padx=20).pack()

    def open_new_product_dialog(self):
        """弹出新增商品窗口（独立弹窗）"""
        win = tk.Toplevel(self.root)
        win.title("新增商品")
        win.geometry("760x580")
        win.configure(bg="#f0f2f5")
        win.grab_set()

        # 居中
        win.update_idletasks()
        w = win.winfo_width()
        h = win.winfo_height()
        x = (win.winfo_screenwidth() // 2) - (w // 2)
        y = (win.winfo_screenheight() // 2) - (h // 2)
        win.geometry(f"+{x}+{y}")

        card = tk.Frame(win, bg="#ffffff", bd=2, relief="groove")
        card.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(card, text="新增商品", font=self.fonts['subtitle'], bg="#ffffff", fg="#1f1f1f").pack(anchor="w", padx=16, pady=(14, 8))
        tk.Frame(card, height=2, bg="#1976d2").pack(fill="x", padx=16, pady=(0, 12))

        # 底部按钮栏：必须固定在底部，否则会被上方 body 的 expand 吃掉空间导致“没有确认按钮”
        btn_row = tk.Frame(card, bg="#ffffff")
        btn_row.pack(side="bottom", fill="x", padx=16, pady=(0, 14))

        tk.Button(btn_row, text="取消", command=win.destroy, bg="#d9d9d9", fg="#1f1f1f",
                  font=self.fonts['button'], relief="flat", cursor="hand2",
                  activebackground="#bfbfbf", padx=16, pady=8).pack(side="right", padx=6)

        # 先定义保存逻辑（下方会赋值到按钮）
        def do_save():
            raw_data = {k: w.get().strip() for k, w in ents.items()}
            if not raw_data.get("no"):
                messagebox.showwarning("提示", "请输入货号！")
                ents["no"].focus_set()
                return

            # 解析颜色（支持用 / 分隔多个颜色）
            color_input = raw_data.get("color", "")
            # 如果包含 / 则分割，否则就是单个颜色
            if "/" in color_input:
                colors = [c.strip() for c in color_input.split("/") if c.strip()]
            else:
                colors = [color_input]
            
            if not colors:
                colors = [""] # 即使为空也创建一个

            products_to_add = []
            
            for c in colors:
                d = raw_data.copy()
                d["color"] = c
                
                # 数值字段转换（允许为空）
                try:
                    d["price"] = float(d.get("price") or 0)
                except:
                    d["price"] = 0
                try:
                    d["cost_price"] = float(d.get("cost_price") or 0)
                except:
                    d["cost_price"] = 0
                try:
                    d["pcs"] = int(d.get("pcs") or 0)
                except:
                    d["pcs"] = 0
                try:
                    d["moq_ctns"] = int(d.get("moq_ctns") or 0)
                except:
                    d["moq_ctns"] = 0

                d["img"] = new_img_data["b64"]
                d["_checked"] = False
                d["_id"] = str(uuid.uuid4())

                if d.get("tag") is None:
                    d["tag"] = ""

                products_to_add.append(d)

            if len(products_to_add) > 1:
                self.open_multi_spec_image_dialog(products_to_add, win)
                return

            # Single product save
            for d in products_to_add:
                self.products.append(d)
                saved_count += 1

            self.save_json(FILES["product"], self.products)
            self.refresh_product_list()
            if self.products:
                try:
                    self.update_browser()
                except:
                    pass
            win.destroy()
            
            messagebox.showinfo("成功", f"商品 {raw_data['no']} 已新增成功！")

        tk.Button(btn_row, text="保存新增", command=do_save, bg="#1976d2", fg="white",
                  font=self.fonts['button'], relief="flat", cursor="hand2",
                  activebackground="#1253a4", padx=16, pady=8).pack(side="right", padx=6)

        # 表单主体区域
        body = tk.Frame(card, bg="#ffffff")
        body.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        left = tk.Frame(body, bg="#ffffff")
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))

        right = tk.Frame(body, bg="#ffffff", width=260)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        # 图片预览
        img_box = tk.Frame(right, width=240, height=180, bg="#f5f5f5", bd=1, relief="solid")
        img_box.pack(pady=(6, 10))
        img_box.pack_propagate(False)
        img_lbl = tk.Label(img_box, bg="#f5f5f5", text="暂无图片", font=self.fonts['small'], fg="#8c8c8c")
        img_lbl.pack(fill="both", expand=True)

        new_img_data = {"b64": None}  # 用 dict 包装以便闭包内可写

        def choose_img():
            p = filedialog.askopenfilename(
                title="选择商品图片",
                filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.webp"), ("All files", "*.*")]
            )
            if not p:
                return
            try:
                b64 = self.process_image(Image.open(p), img_lbl, size=(240, 180))
                new_img_data["b64"] = b64
            except Exception as e:
                messagebox.showerror("错误", f"读取图片失败：{str(e)}")

        def paste_img():
            try:
                img = self.get_clipboard_image()
                if img:
                    b64 = self.process_image(img, img_lbl, size=(240, 180))
                    new_img_data["b64"] = b64
                else:
                    messagebox.showinfo("提示", "剪贴板没有可识别的图片。可以从微信/浏览器复制后再试。")
            except Exception as e:
                messagebox.showerror("错误", f"粘贴图片失败：{str(e)}")

        tk.Button(right, text="🖼️ 选择图片", command=choose_img, bg="#f0f0f0", fg="#1f1f1f",
                  font=self.fonts['body'], relief="flat", cursor="hand2",
                  activebackground="#e0e0e0").pack(fill="x", pady=4, ipady=6)
        tk.Button(right, text="📋 粘贴图片", command=paste_img, bg="#f0f0f0", fg="#1f1f1f",
                  font=self.fonts['body'], relief="flat", cursor="hand2",
                  activebackground="#e0e0e0").pack(fill="x", pady=4, ipady=6)

        # 左侧表单
        form = tk.Frame(left, bg="#ffffff")
        form.pack(fill="both", expand=True)

        fields = [
            ("货号 No", "no"),
            ("标签 Tag", "tag"),
            ("单价 Price", "price"),
            ("最小起订量 (箱)", "moq_ctns"),
            ("成本价 Cost", "cost_price"),
            ("码段 Size", "size"),
            ("颜色 Color (多色用/分隔)", "color"),
            ("每箱 Pcs", "pcs"),
        ]

        ents = {}
        for i, (label, key) in enumerate(fields):
            r = tk.Frame(form, bg="#ffffff")
            r.pack(fill="x", pady=6)
            # Increase width to 28 to fit long labels like "颜色 Color (多色用/分隔)"
            tk.Label(r, text=label + ":", width=28, anchor="w", bg="#ffffff", fg="#1f1f1f", font=self.fonts['label']).pack(side="left")
            e = tk.Entry(r, font=self.fonts['body'], relief="solid", bd=1,
                         highlightthickness=1, highlightbackground="#d9d9d9", highlightcolor="#1976d2")
            e.pack(side="left", fill="x", expand=True, ipady=5)
            ents[key] = e

        ents["no"].focus_set()

        # 保存逻辑已在底部按钮栏定义（保证按钮可见）

    def open_edit_product_dialog(self):
        """弹出编辑商品窗口（独立弹窗）"""
        if not self.selected_prod_id:
            messagebox.showinfo("提示", "请先在商品列表中点击选中一个商品，再进行编辑。")
            return
        p = next((x for x in self.products if str(x.get('_id', '')) == str(self.selected_prod_id)), None)
        if not p:
            messagebox.showerror("错误", "找不到选中的商品数据。")
            return

        win = tk.Toplevel(self.root)
        win.title(f"编辑商品 - {p.get('no','')}")
        win.geometry("760x580")
        win.configure(bg="#f0f2f5")
        win.grab_set()

        # 居中
        win.update_idletasks()
        w = win.winfo_width()
        h = win.winfo_height()
        x = (win.winfo_screenwidth() // 2) - (w // 2)
        y = (win.winfo_screenheight() // 2) - (h // 2)
        win.geometry(f"+{x}+{y}")

        card = tk.Frame(win, bg="#ffffff", bd=2, relief="groove")
        card.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(card, text="编辑商品", font=self.fonts['subtitle'], bg="#ffffff", fg="#1f1f1f").pack(anchor="w", padx=16, pady=(14, 8))
        tk.Frame(card, height=2, bg="#1976d2").pack(fill="x", padx=16, pady=(0, 12))

        # 底部按钮栏（固定）
        btn_row = tk.Frame(card, bg="#ffffff")
        btn_row.pack(side="bottom", fill="x", padx=16, pady=(0, 14))

        tk.Button(btn_row, text="取消", command=win.destroy, bg="#d9d9d9", fg="#1f1f1f",
                  font=self.fonts['button'], relief="flat", cursor="hand2",
                  activebackground="#bfbfbf", padx=16, pady=8).pack(side="right", padx=6)

        body = tk.Frame(card, bg="#ffffff")
        body.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        left = tk.Frame(body, bg="#ffffff")
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))

        right = tk.Frame(body, bg="#ffffff", width=260)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        # 图片预览
        img_box = tk.Frame(right, width=240, height=180, bg="#f5f5f5", bd=1, relief="solid")
        img_box.pack(pady=(6, 10))
        img_box.pack_propagate(False)
        img_lbl = tk.Label(img_box, bg="#f5f5f5", text="暂无图片", font=self.fonts['small'], fg="#8c8c8c")
        img_lbl.pack(fill="both", expand=True)

        edit_img_data = {"b64": p.get("img")}
        if p.get("img"):
            try:
                self.process_image(Image.open(BytesIO(base64.b64decode(p["img"]))), img_lbl, size=(240, 180))
            except:
                img_lbl.config(text="图片损坏", image="")

        def choose_img():
            path = filedialog.askopenfilename(
                title="选择商品图片",
                filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.webp"), ("All files", "*.*")]
            )
            if not path:
                return
            try:
                b64 = self.process_image(Image.open(path), img_lbl, size=(240, 180))
                edit_img_data["b64"] = b64
            except Exception as e:
                messagebox.showerror("错误", f"读取图片失败：{str(e)}")

        def paste_img():
            try:
                img = self.get_clipboard_image()
                if img:
                    b64 = self.process_image(img, img_lbl, size=(240, 180))
                    edit_img_data["b64"] = b64
                else:
                    messagebox.showinfo("提示", "剪贴板没有可识别的图片。可以从微信/浏览器复制后再试。")
            except Exception as e:
                messagebox.showerror("错误", f"粘贴图片失败：{str(e)}")

        tk.Button(right, text="🖼️ 选择图片", command=choose_img, bg="#f0f0f0", fg="#1f1f1f",
                  font=self.fonts['body'], relief="flat", cursor="hand2",
                  activebackground="#e0e0e0").pack(fill="x", pady=4, ipady=6)
        tk.Button(right, text="📋 粘贴图片", command=paste_img, bg="#f0f0f0", fg="#1f1f1f",
                  font=self.fonts['body'], relief="flat", cursor="hand2",
                  activebackground="#e0e0e0").pack(fill="x", pady=4, ipady=6)

        # 左侧表单
        form = tk.Frame(left, bg="#ffffff")
        form.pack(fill="both", expand=True)

        fields = [
            ("货号 No", "no"),
            ("标签 Tag", "tag"),
            ("单价 Price", "price"),
            ("最小起订量 (箱)", "moq_ctns"),
            ("成本价 Cost", "cost_price"),
            ("码段 Size", "size"),
            ("颜色 Color", "color"),
            ("每箱 Pcs", "pcs"),
        ]

        ents = {}
        for (label, key) in fields:
            r = tk.Frame(form, bg="#ffffff")
            r.pack(fill="x", pady=6)
            tk.Label(r, text=label + ":", width=16, anchor="w", bg="#ffffff", fg="#1f1f1f", font=self.fonts['label']).pack(side="left")
            e = tk.Entry(r, font=self.fonts['body'], relief="solid", bd=1,
                         highlightthickness=1, highlightbackground="#d9d9d9", highlightcolor="#1976d2")
            e.pack(side="left", fill="x", expand=True, ipady=5)
            e.insert(0, str(p.get(key, "")))
            ents[key] = e

        ents["no"].focus_set()

        def do_save():
            d = {k: w.get().strip() for k, w in ents.items()}
            if not d.get("no"):
                messagebox.showwarning("提示", "请输入货号！")
                ents["no"].focus_set()
                return

            try:
                d["price"] = float(d.get("price") or 0)
            except:
                d["price"] = 0
            try:
                d["cost_price"] = float(d.get("cost_price") or 0)
            except:
                d["cost_price"] = 0
            try:
                d["pcs"] = int(d.get("pcs") or 0)
            except:
                d["pcs"] = 0
            try:
                d["moq_ctns"] = int(d.get("moq_ctns") or 0)
            except:
                d["moq_ctns"] = 0

            d["img"] = edit_img_data["b64"]

            idx = next((i for i, x in enumerate(self.products) if str(x.get('_id', '')) == str(self.selected_prod_id)), -1)
            if idx < 0:
                messagebox.showerror("错误", "找不到对应商品，保存失败。")
                return

            # 保留内部字段
            keep_checked = self.products[idx].get("_checked", False)
            keep_id = self.products[idx].get("_id")
            self.products[idx].update(d)
            self.products[idx]["_checked"] = keep_checked
            self.products[idx]["_id"] = keep_id

            self.save_json(FILES["product"], self.products)
            self.refresh_product_list()
            if self.products:
                try:
                    self.update_browser()
                except:
                    pass
            win.destroy()
            messagebox.showinfo("成功", f"商品 {d['no']} 已更新成功！")

        tk.Button(btn_row, text="保存修改", command=do_save, bg="#1976d2", fg="white",
                  font=self.fonts['button'], relief="flat", cursor="hand2",
                  activebackground="#1253a4", padx=16, pady=8).pack(side="right", padx=6)

    def on_list_row_click(self, event, pid):
        """商品行点击：只更新高亮和右侧编辑区，不整页重绘，提高流畅度。"""
        # 如果是点击复选框本身，则不改变“当前选中行”，只处理勾选逻辑
        if isinstance(event.widget, tk.Checkbutton):
            return

        new_id = str(pid)
        old_id = getattr(self, "selected_prod_id", None)
        if new_id == old_id:
            # 已经是当前选中行，只需要确保右侧数据已经是最新即可
            self._load_product_to_editor(new_id)
            return

        self.selected_prod_id = new_id

        # 1）恢复旧行背景
        if old_id and old_id in self.prod_row_widgets:
            for w in self.prod_row_widgets[old_id]:
                bg = getattr(w, "_default_bg", "#ffffff")
                try:
                    w.config(bg=bg)
                except Exception:
                    pass

        # 2）高亮新行
        if new_id in self.prod_row_widgets:
            for w in self.prod_row_widgets[new_id]:
                try:
                    w.config(bg="#e6f7ff")
                except Exception:
                    pass

        # 3）把数据加载到右侧编辑区域
        self._load_product_to_editor(new_id)

    def _load_product_to_editor(self, pid_str):
        """根据商品 _id 把数据加载到右侧编辑面板。"""
        p = next((x for x in self.products if str(x.get('_id', '')) == pid_str), None)
        if not p:
            return
        for k, w in self.prod_ents.items():
            w.delete(0, tk.END)
            w.insert(0, str(p.get(k, "")))
        self.current_img_data = p.get('img')  # 同步图片数据，防止更新时丢失
        if p.get('img'):
            try:
                self.process_image(Image.open(BytesIO(base64.b64decode(p['img']))), self.lbl_prod_img)
            except Exception:
                self.lbl_prod_img.config(image="", text="图片损坏")
        else:
            self.lbl_prod_img.config(image="", text="无图")
            self.lbl_prod_img.image = None

    def setup_history_ui(self):
        # 配置Treeview样式（更大字体）
        style = ttk.Style()
        style.configure("Treeview", font=self.fonts['table_cell'], rowheight=36)
        style.configure("Treeview.Heading", font=self.fonts['table_header'])
        
        f = tk.Frame(self.tab_history, bg="#f5f5f5"); 
        f.pack(fill="both", expand=True, padx=16, pady=16)
        self.tree_hist = ttk.Treeview(f, columns=("date", "id", "client", "amt"), 
                                     show="headings", style="Treeview")
        for c, h in zip(self.tree_hist["columns"], ["日期 Date", "单号 No", "客户 Client", "金额 Amount"]): 
            self.tree_hist.heading(c, text=h); self.tree_hist.column(c, anchor="center", width=200)
        self.tree_hist.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree_hist.bind("<Double-1>", lambda e: self.reprint_bill())
        self.tree_hist.bind("<Delete>", lambda e: self.delete_history_item())
        self.tree_hist.bind("<Button-3>", self.show_history_context_menu)
        self.history_context_menu = tk.Menu(self.root, tearoff=0, font=self.fonts['body'])
        self.history_context_menu.add_command(label="🗑️ 删除销售单", command=self.delete_history_item)
        self.history_context_menu.add_command(label="🖨️ 原单据重新打印", command=self.reprint_bill)
        self.history_context_menu.add_command(label="✏️ 编辑后打印", command=self.edit_and_print_bill)
        # self.history_context_menu.add_command(label="🔗 分享链接", command=self.share_history_bill)

    def setup_quote_history_ui(self):
        # 配置Treeview样式（更大字体）
        style = ttk.Style()
        style.configure("Treeview", font=self.fonts['table_cell'], rowheight=36)
        style.configure("Treeview.Heading", font=self.fonts['table_header'])
        
        f = tk.Frame(self.tab_quote_hist, bg="#f5f5f5"); 
        f.pack(fill="both", expand=True, padx=16, pady=16)
        self.tree_q_hist = ttk.Treeview(f, columns=("date", "id", "client"), 
                                       show="headings", style="Treeview")
        for c, h in zip(self.tree_q_hist["columns"], ["日期 Date", "单号 No", "客户 Client"]): 
            self.tree_q_hist.heading(c, text=h); self.tree_q_hist.column(c, anchor="center", width=250)
        self.tree_q_hist.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree_q_hist.bind("<Double-1>", lambda e: self.reprint_quote())
        self.tree_q_hist.bind("<Delete>", lambda e: self.delete_quote_item())
        self.tree_q_hist.bind("<Button-3>", self.show_quote_context_menu)
        self.quote_context_menu = tk.Menu(self.root, tearoff=0, font=self.fonts['body'])
        self.quote_context_menu.add_command(label="🗑️ 删除报价单", command=self.delete_quote_item)
        self.quote_context_menu.add_command(label="🖨️ 原单据重新打印", command=self.reprint_quote)
        self.quote_context_menu.add_command(label="✏️ 编辑后打印", command=self.edit_and_print_quote)
        # Removed Share Link

    def share_history_bill(self):
        sel = self.tree_hist.selection()
        if not sel:
            return
        messagebox.showinfo("提示", "当前版本已暂时关闭同步到 GitHub 的分享功能。")

    def share_quote_link(self):
        sel = self.tree_q_hist.selection()
        if not sel:
            return
        messagebox.showinfo("提示", "当前版本已暂时关闭同步到 GitHub 的分享功能。")

    def reprint_bill(self):
        sel = self.tree_hist.selection()
        if sel:
            bid = self.tree_hist.item(sel[0], "values")[1]; b = next((x for x in self.history if x['id'] == bid), None)
            if b: self.gen_invoice_html(b)

    def reprint_quote(self):
        sel = self.tree_q_hist.selection()
        if sel:
            qid = self.tree_q_hist.item(sel[0], "values")[1]; q = next((x for x in self.quote_history if x['id'] == qid), None)
            if q: self.gen_quotation_html(q)
    
    def show_quote_context_menu(self, e):
        item = self.tree_q_hist.identify_row(e.y)
        if item:
            self.tree_q_hist.selection_set(item)
            self.quote_context_menu.post(e.x_root, e.y_root)
    
    def delete_quote_item(self):
        sel = self.tree_q_hist.selection()
        if sel:
            qid = self.tree_q_hist.item(sel[0], "values")[1]
            if messagebox.askyesno("确认删除", f"确定要删除报价单 {qid} 吗？"):
                self.quote_history = [q for q in self.quote_history if q['id'] != qid]
                self.save_json(FILES["quote"], self.quote_history)
                self.refresh_quote_history_list()
    
    def edit_and_print_bill(self):
        sel = self.tree_hist.selection()
        if sel:
            bid = self.tree_hist.item(sel[0], "values")[1]
            b = next((x for x in self.history if x['id'] == bid), None)
            if b:
                # 设置编辑模式
                self.current_edit_bill_id = bid
                # 切换到开单页面
                self.notebook.select(self.tab_billing)
                # 加载数据到表单
                for k, e in self.head_ents.items():
                    e.delete(0, tk.END)
                    e.insert(0, b.get(k, ''))
                for k, e in self.fin_ents.items():
                    e.delete(0, tk.END)
                    e.insert(0, str(b.get(k, '0')))
                self.txt_note.delete("1.0", tk.END)
                self.txt_note.insert("1.0", b.get('note', ''))
                # 加载商品到购物车
                self.cart_items = b['items'].copy()
                self.refresh_cart()
                messagebox.showinfo("编辑模式", "销售单数据已加载到开单页面，修改后点击'保存并打印销售发货单'即可。")
    
    def edit_and_print_quote(self):
        sel = self.tree_q_hist.selection()
        if sel:
            qid = self.tree_q_hist.item(sel[0], "values")[1]
            q = next((x for x in self.quote_history if x['id'] == qid), None)
            if q:
                # 打开编辑窗口
                q_win = tk.Toplevel(self.root)
                q_win.title("编辑报价单")
                q_win.geometry("950x800")
                q_win.grab_set()
                
                # 1. 顶部客户信息
                top_f = tk.Frame(q_win, bg="#f0f0f0", pady=10); top_f.pack(fill="x")
                tk.Label(top_f, text="客户名称 Client:", font=("Arial", 11, "bold"), bg="#f0f0f0").pack(side="left", padx=(20, 10))
                ent_c = tk.Entry(top_f, width=50, font=("Arial", 11)); ent_c.pack(side="left", padx=10)
                ent_c.insert(0, q.get('client', ''))
                
                # 2. 列表表头
                head_f = tk.Frame(q_win, bg="#333", pady=5); head_f.pack(fill="x")
                cols = [("图片 Image", 12), ("货号 Article No", 20), ("MOQ (箱)", 15), ("单价 Price (¥)", 15), ("每箱 Pcs/Ctn", 15)]
                for txt, w in cols:
                    tk.Label(head_f, text=txt, font=("Arial", 10, "bold"), fg="white", bg="#333", width=w).pack(side="left", padx=5)

                # 3. 列表区域
                list_f = tk.Frame(q_win); list_f.pack(fill="both", expand=True)
                can = tk.Canvas(list_f, bg="white"); scr = ttk.Scrollbar(list_f, command=can.yview)
                frm = tk.Frame(can, bg="white")
                can_win = can.create_window((0,0), window=frm, anchor="nw")
                
                def on_canvas_configure(e): can.itemconfig(can_win, width=e.width)
                can.bind('<Configure>', on_canvas_configure)
                can.configure(yscrollcommand=scr.set)
                
                can.pack(side="left", fill="both", expand=True); scr.pack(side="right", fill="y")
                
                def on_mousewheel(event):
                    try: can.yview_scroll(int(-1*(event.delta/120)), "units")
                    except: pass
                can.bind_all("<MouseWheel>", on_mousewheel)
                
                rows = []
                q_win.imgs = []
                for i, it in enumerate(q['items']):
                    color = "#f9f9f9" if i % 2 == 0 else "white"
                    r = tk.Frame(frm, pady=5, bg=color, bd=1, relief="solid"); r.pack(fill="x", padx=10, pady=2)
                    
                    # 1. 图片
                    img_container = tk.Frame(r, width=100, height=80, bg=color); img_container.pack(side="left", padx=5); img_container.pack_propagate(False)
                    if it.get('img'):
                        try:
                            img_data = base64.b64decode(it['img'])
                            pil_img = Image.open(BytesIO(img_data))
                            pil_img.thumbnail((75, 75))
                            tk_img = ImageTk.PhotoImage(pil_img)
                            q_win.imgs.append(tk_img)
                            tk.Label(img_container, image=tk_img, bg=color).place(relx=0.5, rely=0.5, anchor="center")
                        except:
                            tk.Label(img_container, text="[无图]", bg=color).place(relx=0.5, rely=0.5, anchor="center")
                    else:
                        tk.Label(img_container, text="[无图]", bg=color).place(relx=0.5, rely=0.5, anchor="center")

                    # 2. 货号
                    tk.Label(r, text=f"{it['no']}", width=20, font=("Arial", 10, "bold"), bg=color).pack(side="left", padx=5)
                    
                    # 3. MOQ
                    em = tk.Entry(r, width=15, font=("Arial", 10), justify="center"); em.insert(0, str(it.get('moq_ctns', 100))); em.pack(side="left", padx=5)
                    
                    # 4. 单价
                    ep = tk.Entry(r, width=15, font=("Arial", 10), justify="center"); ep.insert(0, str(it.get('price', 0))); ep.pack(side="left", padx=5)
                    
                    # 5. 每箱
                    tk.Label(r, text=f"{it.get('pcs',0)} 双/箱", width=15, bg=color).pack(side="left", padx=5)
                    
                    rows.append({"it": it, "em": em, "ep": ep})
                
                frm.update_idletasks()
                can.config(scrollregion=can.bbox("all"))

                def gen():
                    res = [{"no": r['it']['no'], "price": float(r['ep'].get() or 0), "moq_ctns": r['em'].get(), "pcs": r['it'].get('pcs', 0), "img": r['it'].get('img',''), "size": r['it'].get('size','--'), "color": r['it'].get('color','--')} for r in rows]
                    data = {"id": q['id'], "date": q['date'], "client": ent_c.get(), "items": res}
                    # 更新报价历史
                    idx = next((i for i, x in enumerate(self.quote_history) if x['id'] == qid), -1)
                    if idx >= 0:
                        self.quote_history[idx] = data
                    self.save_json(FILES["quote"], self.quote_history)
                    
                    # 根据选择的模式生成不同的报价单
                    if quote_mode.get() == "large_image":
                        try:
                            c = int(sp_cols.get())
                        except:
                            c = 3
                        self.gen_quotation_html_large_image(data, cols=c)
                    else:
                        self.gen_quotation_html(data)
                    
                    q_win.destroy()
                    self.refresh_quote_history_list()
                
                # 4. 底部功能区
                bot_f = tk.Frame(q_win, bg="#e0e0e0", pady=15); bot_f.pack(fill="x")
                
                # 报价单模式选择
                mode_frame = tk.Frame(bot_f, bg="#e0e0e0"); mode_frame.pack(pady=(0, 10))
                tk.Label(mode_frame, text="报价单模板:", font=("Arial", 10, "bold"), bg="#e0e0e0").pack(side="left", padx=5)
                quote_mode = tk.StringVar(value="table")
                
                # 定义状态更新函数
                def update_sp_state(*args):
                    if quote_mode.get() == "large_image":
                        sp_cols.config(state="normal")
                    else:
                        sp_cols.config(state="disabled")
                quote_mode.trace("w", update_sp_state)

                tk.Radiobutton(mode_frame, text="列表模板", variable=quote_mode, value="table", 
                              bg="#e0e0e0", font=("Arial", 10)).pack(side="left", padx=10)
                tk.Radiobutton(mode_frame, text="网格模板", variable=quote_mode, value="large_image", 
                              bg="#e0e0e0", font=("Arial", 10)).pack(side="left", padx=10)
                
                # 大图模式列数设置
                tk.Label(mode_frame, text="列数:", font=("Arial", 10), bg="#e0e0e0").pack(side="left", padx=(5, 0))
                sp_cols = tk.Spinbox(mode_frame, from_=1, to=6, width=3, font=("Arial", 10))
                sp_cols.delete(0, "end")
                sp_cols.insert(0, "4")
                sp_cols.pack(side="left", padx=2)
                update_sp_state()
                
                tk.Button(bot_f, text="🚀 保存并打印报价单", command=gen, bg="#333", fg="white", height=2, font=("微软雅黑", 12, "bold"), width=30).pack()

    def refresh_cart(self):
        self.tree_cart.delete(*self.tree_cart.get_children())
        for i, it in enumerate(self.cart_items): self.tree_cart.insert("", "end", values=(i+1, it['no'], it['size'], it['color'], it['ctns'], it['pcs'], it['total'], f"{it['price']:.2f}", f"{it['amount']:.2f}"))

    def select_img_for_lib(self):
        p = filedialog.askopenfilename()
        if p: self.current_img_data = self.process_image(Image.open(p), self.lbl_prod_img)

    def paste_img_for_lib(self):
        img = self.get_clipboard_image()
        if img:
            self.current_img_data = self.process_image(img, self.lbl_prod_img)
        else:
            messagebox.showinfo("提示", "剪贴板没有可识别的图片。可以从微信/浏览器复制后再试。")

    def get_prod_data_from_panel(self):
        d = {k: e.get().strip() for k, e in self.prod_ents.items()}
        try:
            d['price'] = float(d.get('price', 0) or 0)
            d['cost_price'] = float(d.get('cost_price', 0) or 0)
            d['pcs'] = int(d.get('pcs', 0) or 0)
            d['moq_ctns'] = int(d.get('moq_ctns', 0) or 0)
        except: pass
        d['img'] = self.current_img_data
        return d

    def add_as_new_product(self):
        d = self.get_prod_data_from_panel()
        if not d['no']:
            messagebox.showwarning("提示", "请输入货号！")
            return
        
        # 追加添加新产品（不再判断是否重复）
        d['_checked'] = False
        d['tag'] = ""
        d['_id'] = str(uuid.uuid4())
        self.products.append(d)
        
        self.save_json(FILES["product"], self.products)
        self.refresh_product_list()
        messagebox.showinfo("成功", f"商品 {d['no']} 已新增成功！")

    def update_selected_product(self):
        if not self.selected_prod_id:
            messagebox.showwarning("提示", "请在左侧列表中点击确认选中某个商品后再进行更新！")
            return
            
        d = self.get_prod_data_from_panel()
        idx = next((i for i, x in enumerate(self.products) if x.get('_id') == self.selected_prod_id), -1)
        if idx >= 0:
            self.products[idx].update(d)
            self.save_json(FILES["product"], self.products)
            self.refresh_product_list()
            messagebox.showinfo("成功", f"商品 {d['no']} 资料已成功更新！")
        else:
            messagebox.showerror("错误", "找不到对应商品的原始数据，更新失败。")

    def on_bill_search(self, e):
        # 此方法已废弃，由 on_bill_pick_search 替代
        pass

    def add_item(self):
        # 此方法现由 add_picking_to_cart 替代，或保留作为辅助
        pass

    def on_cart_item_edit(self, event):
        """双击编辑待发货清单中的商品信息，可修改码段和每箱数量"""
        item_id = self.tree_cart.selection()
        if not item_id: return
        
        idx_str = self.tree_cart.item(item_id, "values")[0]
        try:
            idx = int(idx_str) - 1
            it = self.cart_items[idx]
        except (ValueError, IndexError):
            return
        
        edit_win = tk.Toplevel(self.root)
        edit_win.title(f"修改商品 - {it['no']}")
        edit_win.geometry("400x420")
        edit_win.grab_set()
        
        # 居中显示
        edit_win.update_idletasks()
        w = edit_win.winfo_width()
        h = edit_win.winfo_height()
        x = (edit_win.winfo_screenwidth() // 2) - (w // 2)
        y = (edit_win.winfo_screenheight() // 2) - (h // 2)
        edit_win.geometry(f"+{x}+{y}")
        
        tk.Label(edit_win, text=f"正在修改货号: {it['no']}", font=self.fonts['subtitle'], 
                fg="#1677ff").pack(pady=20)
        
        f_in = tk.Frame(edit_win, bg="#ffffff")
        f_in.pack(pady=16)
        
        # 码段 (Size)
        tk.Label(f_in, text="码段 (Size):", font=self.fonts['label'], bg="#ffffff", 
                fg="#1f1f1f").grid(row=0, column=0, padx=12, pady=10, sticky="e")
        e_size = tk.Entry(f_in, font=self.fonts['body'], width=18, relief="solid", bd=1,
                         highlightthickness=2, highlightbackground="#e0e0e0", highlightcolor="#1677ff")
        e_size.insert(0, str(it.get('size', '')))
        e_size.grid(row=0, column=1, padx=12, pady=10, ipady=5)
        
        # 每箱数量 (Pcs)
        tk.Label(f_in, text="每箱数量 (Pcs):", font=self.fonts['label'], bg="#ffffff", 
                fg="#1f1f1f").grid(row=1, column=0, padx=12, pady=10, sticky="e")
        e_pcs = tk.Entry(f_in, font=self.fonts['body'], width=18, relief="solid", bd=1,
                         highlightthickness=2, highlightbackground="#e0e0e0", highlightcolor="#1677ff")
        e_pcs.insert(0, str(it.get('pcs', '')))
        e_pcs.grid(row=1, column=1, padx=12, pady=10, ipady=5)
        
        # 箱数 (Ctns)
        tk.Label(f_in, text="箱数 (Ctns):", font=self.fonts['label'], bg="#ffffff", 
                fg="#1f1f1f").grid(row=2, column=0, padx=12, pady=10, sticky="e")
        e_ctns = tk.Entry(f_in, font=self.fonts['body'], width=18, relief="solid", bd=1,
                         highlightthickness=2, highlightbackground="#e0e0e0", highlightcolor="#1677ff")
        e_ctns.insert(0, str(it['ctns']))
        e_ctns.grid(row=2, column=1, padx=12, pady=10, ipady=5)
        
        # 单价 (Price)
        tk.Label(f_in, text="单价 (Price):", font=self.fonts['label'], bg="#ffffff", 
                fg="#1f1f1f").grid(row=3, column=0, padx=12, pady=10, sticky="e")
        e_price = tk.Entry(f_in, font=self.fonts['body'], width=18, relief="solid", bd=1,
                          highlightthickness=2, highlightbackground="#e0e0e0", highlightcolor="#1677ff")
        e_price.insert(0, str(it['price']))
        e_price.grid(row=3, column=1, padx=12, pady=10, ipady=5)
        
        def do_save():
            try:
                # 获取码段（可以为空）
                new_size = e_size.get().strip()
                
                # 验证每箱数量
                new_pcs = int(e_pcs.get().strip())
                if new_pcs <= 0:
                    messagebox.showwarning("提示", "每箱数量必须大于 0！")
                    return
                
                # 验证箱数
                new_ctns = int(e_ctns.get().strip())
                if new_ctns <= 0:
                    messagebox.showwarning("提示", "箱数必须大于 0！")
                    return
                
                # 验证单价
                new_price = float(e_price.get().strip())
                
                # 更新商品信息
                it['size'] = new_size
                it['pcs'] = new_pcs
                it['ctns'] = new_ctns
                it['price'] = new_price
                it['total'] = new_ctns * new_pcs
                it['amount'] = it['total'] * new_price
                
                self.refresh_cart()
                edit_win.destroy()
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字！")
        
        btn_f = tk.Frame(edit_win, bg="#ffffff")
        btn_f.pack(pady=20)
        tk.Button(btn_f, text="取消", command=edit_win.destroy, width=12, 
                 font=self.fonts['body'], relief="flat", cursor="hand2",
                 bg="#d9d9d9", fg="#1f1f1f", activebackground="#bfbfbf").pack(side="left", padx=12)
        tk.Button(btn_f, text="确定保存", command=do_save, bg="#52c41a", fg="white", width=14, 
                 font=self.fonts['button'], relief="flat", cursor="hand2",
                 activebackground="#389e0d", padx=14, pady=6).pack(side="left", padx=12)
        
        e_size.focus()
        edit_win.bind("<Return>", lambda e: do_save())
        edit_win.bind("<Escape>", lambda e: edit_win.destroy())

    def save_print(self):
        if not self.cart_items: return
        
        # 提取字段数据
        info = {k: e.get().strip() for k, e in self.head_ents.items()}
        fin = {k: e.get().strip() for k, e in self.fin_ents.items()}
        
        if self.current_edit_bill_id:
            # 编辑模式：更新现有订单
            order = {
                "id": self.current_edit_bill_id, 
                "date": datetime.datetime.now().strftime("%Y-%m-%d"), 
                **info, **fin,
                "note": self.txt_note.get("1.0", tk.END).strip(), 
                "items": self.cart_items
            }
            idx = next((i for i, x in enumerate(self.history) if x['id'] == self.current_edit_bill_id), -1)
            if idx >= 0: self.history[idx] = order
            self.current_edit_bill_id = None
        else:
            # 新建模式
            order = {
                "id": "INV" + datetime.datetime.now().strftime("%y%m%d%H%M%S"), 
                "date": datetime.datetime.now().strftime("%Y-%m-%d"), 
                **info, **fin,
                "note": self.txt_note.get("1.0", tk.END).strip(), 
                "items": self.cart_items
            }
            self.history.append(order)
            
        self.save_json(FILES["history"], self.history)
        self.refresh_history_list()
        self.gen_invoice_html(order)
        self.reset_billing()
        messagebox.showinfo("成功", "单据已保存并生成发货单。")

    def reset_billing(self):
        self.current_edit_bill_id = None
        self.cart_items = []; self.refresh_cart()
        for e in list(self.head_ents.values()) + list(self.fin_ents.values()): 
            e.delete(0, tk.END)
        self.ent_bill_pick_search.delete(0, tk.END)
        for w in self.frm_bill_pick.winfo_children(): w.destroy()
        for k, e in self.fin_ents.items(): e.insert(0, "0")
        self.txt_note.delete("1.0", tk.END)

    def manage_tags_dialog(self):
        checked = [p for p in self.products if p.get('_checked')]
        if not checked:
            messagebox.showinfo("提示", "请先选择要管理的商品！")
            return
        
        # 创建标签管理窗口
        tag_win = tk.Toplevel(self.root)
        tag_win.title("标签管理")
        tag_win.geometry("500x400")
        tag_win.grab_set()
        
        # 获取所有选中商品的标签（去重）
        all_tags = set()
        for p in checked:
            tag_str = p.get('tag') or ''
            tags = [tag.strip() for tag in tag_str.split(',') if tag.strip()]
            all_tags.update(tags)
        all_tags = sorted(list(all_tags))
        
        # 显示当前标签
        tk.Label(tag_win, text=f"已选择 {len(checked)} 个商品", font=("Arial", 10, "bold")).pack(pady=10)
        
        # 当前标签列表
        if all_tags:
            tk.Label(tag_win, text="当前标签列表:", font=("Arial", 9, "bold")).pack(anchor="w", padx=20, pady=(10, 5))
            tag_list_frame = tk.Frame(tag_win)
            tag_list_frame.pack(fill="both", expand=True, padx=20, pady=5)
            
            # 标签显示区域（带滚动条）
            tag_canvas = tk.Canvas(tag_list_frame, height=150, bg="#f5f5f5")
            tag_scroll = ttk.Scrollbar(tag_list_frame, orient="vertical", command=tag_canvas.yview)
            tag_scrollable_frame = tk.Frame(tag_canvas)
            
            tag_scrollable_frame.bind(
                "<Configure>",
                lambda e: tag_canvas.configure(scrollregion=tag_canvas.bbox("all"))
            )
            
            tag_canvas.create_window((0, 0), window=tag_scrollable_frame, anchor="nw")
            tag_canvas.configure(yscrollcommand=tag_scroll.set)
            
            # 显示每个标签
            for tag in all_tags:
                tag_frame = tk.Frame(tag_scrollable_frame, bg="#fff", relief="groove", bd=1)
                tag_frame.pack(fill="x", pady=2, padx=5)
                tk.Label(tag_frame, text=tag, bg="#fff", font=("Arial", 9), padx=10, pady=5).pack(side="left", fill="x", expand=True)
                tk.Button(tag_frame, text="删除", bg="#ffebee", fg="#c62828", command=lambda t=tag: self.remove_tag_from_checked(tag_win, t), font=("Arial", 8)).pack(side="right", padx=5)
            
            tag_canvas.pack(side="left", fill="both", expand=True)
            tag_scroll.pack(side="right", fill="y")
        else:
            tk.Label(tag_win, text="当前没有标签", fg="#999", font=("Arial", 9)).pack(pady=20)
        
        # 分隔线
        tk.Frame(tag_win, height=1, bg="#ddd").pack(fill="x", padx=20, pady=10)
        
        # 添加标签区域
        add_frame = tk.Frame(tag_win)
        add_frame.pack(fill="x", padx=20, pady=10)
        tk.Label(add_frame, text="添加新标签:", font=("Arial", 9, "bold")).pack(anchor="w")
        add_entry_frame = tk.Frame(add_frame)
        add_entry_frame.pack(fill="x", pady=5)
        add_entry = tk.Entry(add_entry_frame, font=("Arial", 9))
        add_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        def add_tag():
            new_tag = add_entry.get().strip()
            if new_tag:
                for p in checked:
                    current_tag_str = p.get('tag') or ''
                    existing_tags = [tag.strip() for tag in current_tag_str.split(',') if tag.strip()]
                    if new_tag not in existing_tags:
                        existing_tags.append(new_tag)
                        p['tag'] = ','.join(existing_tags)
                self.save_json(FILES["product"], self.products)
                self.refresh_product_list()
                tag_win.destroy()
                self.manage_tags_dialog()  # 重新打开对话框以刷新显示
            else:
                messagebox.showwarning("提示", "请输入标签名称！")
        
        tk.Button(add_entry_frame, text="添加", bg="#4caf50", fg="white", command=add_tag, font=("Arial", 9, "bold")).pack(side="right")
        
        # 关闭按钮
        tk.Button(tag_win, text="关闭", command=tag_win.destroy, bg="#e0e0e0", font=("Arial", 9)).pack(pady=10)
    
    def remove_tag_from_checked(self, parent_win, tag_to_remove):
        checked = [p for p in self.products if p.get('_checked')]
        if messagebox.askyesno("确认删除", f"确定要从所有选中商品中删除标签 '{tag_to_remove}' 吗？"):
            for p in checked:
                current_tag_str = p.get('tag') or ''
                existing_tags = [tag.strip() for tag in current_tag_str.split(',') if tag.strip()]
                if tag_to_remove in existing_tags:
                    existing_tags.remove(tag_to_remove)
                    p['tag'] = ','.join(existing_tags) if existing_tags else ''
            self.save_json(FILES["product"], self.products)
            self.refresh_product_list()
            parent_win.destroy()
            self.manage_tags_dialog()  # 重新打开对话框以刷新显示

    def update_browser(self):
        p = self.products[self.browser_idx]
        for k, lbl in self.side_vars.items(): lbl.config(text=str(p.get(k, '--')))
        if p.get('img') and hasattr(self, "lbl_side_img"):
            self.process_image(Image.open(BytesIO(base64.b64decode(p['img']))), self.lbl_side_img)

    def prev_prod(self): self.browser_idx = (self.browser_idx-1)%len(self.products); self.update_browser()
    def next_prod(self): self.browser_idx = (self.browser_idx+1)%len(self.products); self.update_browser()
    def select_browse_prod(self):
        p = self.products[self.browser_idx]
        for k in ["no", "size", "color", "pcs", "price"]: self.bill_ents[k].delete(0, tk.END); self.bill_ents[k].insert(0, str(p.get(k, "")))
        self.curr_bill_img = p.get('img')

if __name__ == "__main__":
    root = tk.Tk(); app = ShoeBillingApp(root); root.mainloop()
