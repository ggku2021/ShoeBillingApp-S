import hashlib
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import datetime
import csv
import os
import random
import uuid

# 必须与主程序一致
SALT = "SHOE_BILLING_APP_SECRET_2026_V9"
HISTORY_FILE = "keygen_history.csv"

def save_history(machine_code, days, expire_str, key):
    """保存生成记录到CSV"""
    file_exists = os.path.exists(HISTORY_FILE)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(HISTORY_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["时间", "机器码", "有效期(天)", "到期日期", "激活码/序列号", "类型"])
            writer.writerow([timestamp, machine_code, days, expire_str, key, "绑定机器码" if machine_code != "BATCH" else "通用序列号"])
    except Exception as e:
        messagebox.showerror("错误", f"保存历史记录失败: {e}")

def show_history():
    """显示历史记录窗口"""
    hist_win = tk.Toplevel(root)
    hist_win.title("激活码生成历史")
    hist_win.geometry("900x400")
    
    # 表格
    cols = ("时间", "机器码", "有效期(天)", "到期日期", "激活码/序列号", "类型")
    tree = ttk.Treeview(hist_win, columns=cols, show='headings')
    
    for col in cols:
        tree.heading(col, text=col)
    
    tree.column("时间", width=140)
    tree.column("机器码", width=120)
    tree.column("有效期(天)", width=80)
    tree.column("到期日期", width=100)
    tree.column("激活码/序列号", width=250)
    tree.column("类型", width=80)
    
    tree.pack(fill="both", expand=True, padx=10, pady=10)
    
    # 滚动条
    scrollbar = ttk.Scrollbar(hist_win, orient="vertical", command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.place(relx=1, rely=0, relheight=1, anchor='ne')
    
    # 读取数据
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None) # 跳过表头
                for row in reader:
                    # 兼容旧格式（旧格式没有类型列）
                    if len(row) == 5:
                        row.append("绑定机器码")
                    tree.insert("", "0", values=row)
        except Exception as e:
            messagebox.showerror("错误", f"读取历史记录失败: {e}")
    else:
        lbl = tk.Label(hist_win, text="暂无历史记录", fg="gray")
        lbl.place(relx=0.5, rely=0.5, anchor="center")

def generate_key():
    """生成绑定机器的激活码"""
    machine_code = entry_code.get().strip()
    if not machine_code:
        messagebox.showwarning("提示", "请输入机器码")
        return
    
    try:
        days = int(entry_days.get().strip())
    except ValueError:
        messagebox.showwarning("提示", "有效期天数必须是整数")
        return

    # 计算过期日期
    expire_date = datetime.date.today() + datetime.timedelta(days=days)
    expire_str = expire_date.strftime("%Y%m%d")
        
    # 生成签名 (机器码 + 过期日期 + 盐)
    raw = machine_code + expire_str + SALT
    signature = hashlib.sha256(raw.encode()).hexdigest().upper()[:16]
    
    # 组合最终激活码
    key_raw = signature + expire_str
    key_formatted = f"{key_raw[:4]}-{key_raw[4:8]}-{key_raw[8:12]}-{key_raw[12:16]}-{key_raw[16:]}"
    
    entry_key.delete(0, tk.END)
    entry_key.insert(0, key_formatted)
    
    # 保存历史
    save_history(machine_code, days, expire_str, key_formatted)
    
    root.clipboard_clear()
    root.clipboard_append(key_formatted)
    lbl_status.config(text=f"激活码已生成！有效期至: {expire_str}", fg="green")

def generate_batch_sn():
    """批量生成通用序列号"""
    try:
        count = int(entry_batch_count.get().strip())
        days = int(entry_batch_days.get().strip())
    except ValueError:
        messagebox.showwarning("提示", "数量和天数必须为整数")
        return
        
    if count <= 0: return

    file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt"), ("CSV Files", "*.csv")])
    if not file_path: return
    
    generated_list = []
    
    for _ in range(count):
        # 序列号格式: SN + Days(Hex 4位) + Random(Hex 8位) + Signature(Hex 12位)
        # 1. 天数 hex
        days_hex = f"{days:04X}"
        
        # 2. 随机串
        rand_str = uuid.uuid4().hex[:8].upper()
        
        # 3. 签名: Hash(SN_PREFIX + DaysHex + Random + SALT)
        raw = "SN" + days_hex + rand_str + SALT
        sig = hashlib.sha256(raw.encode()).hexdigest().upper()[:12]
        
        sn = f"SN{days_hex}-{rand_str}-{sig}"
        generated_list.append(sn)
        
        # 保存历史 (批量生成时只记录一个特殊的机器码标记)
        save_history("BATCH", days, "激活时计算", sn)

    # 写入文件
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            for sn in generated_list:
                f.write(sn + "\n")
        messagebox.showinfo("成功", f"成功生成 {count} 个通用序列号！\n已保存至: {file_path}")
    except Exception as e:
        messagebox.showerror("错误", f"保存文件失败: {e}")

# --- UI 构建 ---
root = tk.Tk()
root.title("开单系统注册机 - 管理员专用 (多模式版)")
root.geometry("600x550")
root.configure(bg="#f0f2f5")

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=20, pady=20)

# Tab 1: 绑定机器码 (单机激活)
frame_single = tk.Frame(notebook, bg="white", padx=30, pady=30)
notebook.add(frame_single, text="单机绑定激活 (针对特定客户)")

tk.Label(frame_single, text="单机绑定模式", font=("微软雅黑", 16, "bold"), bg="white", fg="#333").pack(pady=(0, 20))
tk.Label(frame_single, text="输入客户机器码:", font=("微软雅黑", 12), bg="white").pack(anchor="w")
entry_code = tk.Entry(frame_single, font=("Consolas", 14), width=30, bd=2, relief="solid")
entry_code.pack(pady=(5, 10))

tk.Label(frame_single, text="有效期 (天):", font=("微软雅黑", 12), bg="white").pack(anchor="w")
entry_days = tk.Entry(frame_single, font=("Consolas", 14), width=30, bd=2, relief="solid")
entry_days.insert(0, "365")
entry_days.pack(pady=(5, 15))

tk.Button(frame_single, text="生成绑定激活码", command=generate_key, bg="#1976d2", fg="white", font=("微软雅黑", 12, "bold"), padx=20, pady=5, relief="flat").pack(pady=10)

tk.Label(frame_single, text="生成的激活码:", font=("微软雅黑", 12), bg="white").pack(anchor="w")
entry_key = tk.Entry(frame_single, font=("Consolas", 12), width=35, fg="#d32f2f", bd=2, relief="solid")
entry_key.pack(pady=(5, 15))

lbl_status = tk.Label(frame_single, text="", font=("微软雅黑", 10), bg="white")
lbl_status.pack(pady=5)

# Tab 2: 批量生成 (通用序列号)
frame_batch = tk.Frame(notebook, bg="white", padx=30, pady=30)
notebook.add(frame_batch, text="批量生成序列号 (用于自动发货)")

tk.Label(frame_batch, text="通用序列号模式", font=("微软雅黑", 16, "bold"), bg="white", fg="#333").pack(pady=(0, 10))
tk.Label(frame_batch, text="此模式生成的序列号不绑定特定机器，\n用户在软件中输入后自动绑定本机。", font=("微软雅黑", 10), bg="white", fg="#666").pack(pady=(0, 20))

tk.Label(frame_batch, text="生成数量 (个):", font=("微软雅黑", 12), bg="white").pack(anchor="w")
entry_batch_count = tk.Entry(frame_batch, font=("Consolas", 14), width=30, bd=2, relief="solid")
entry_batch_count.insert(0, "10")
entry_batch_count.pack(pady=(5, 10))

tk.Label(frame_batch, text="有效期 (天):", font=("微软雅黑", 12), bg="white").pack(anchor="w")
entry_batch_days = tk.Entry(frame_batch, font=("Consolas", 14), width=30, bd=2, relief="solid")
entry_batch_days.insert(0, "365")
entry_batch_days.pack(pady=(5, 15))

tk.Button(frame_batch, text="批量生成并导出...", command=generate_batch_sn, bg="#388e3c", fg="white", font=("微软雅黑", 12, "bold"), padx=20, pady=5, relief="flat").pack(pady=20)

# 底部按钮
btn_frame = tk.Frame(root, bg="#f0f2f5")
btn_frame.pack(fill="x", pady=10)
tk.Button(btn_frame, text="查看所有生成历史", command=show_history, bg="#607d8b", fg="white", font=("微软雅黑", 10), relief="flat", padx=15).pack()

root.mainloop()