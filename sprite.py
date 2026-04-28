import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
from PIL import Image, ImageTk

class SpriteExtractorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("スプライト番号抽出・管理ツール v3")
        self.geometry("1000x650")

        # 内部データ
        self.sprite_image = None
        self.tk_image = None
        self.grid_size = 16
        self.cols = 16
        self.selected_snum = 0
        self.current_w = 16
        self.current_h = 16
        self.registered_sprites = {} # {snum: {"name": "キャラ名", "state": "状態", "size": "16x16"}}

        self.create_widgets()

    def create_widgets(self):
        # --- メニューバー (インポート/エクスポート用) ---
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="データをエクスポート (JSON)", command=self.export_data)
        filemenu.add_command(label="データをインポート (JSON)", command=self.import_data)
        menubar.add_cascade(label="ファイル", menu=filemenu)
        self.config(menu=menubar)

        # --- 左側：スプライトシート表示 ---
        left_frame = tk.Frame(self)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        btn_load = tk.Button(left_frame, text="画像(PNG)を読み込む", command=self.load_image)
        btn_load.pack(pady=5)

        self.canvas = tk.Canvas(left_frame, bg="gray")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        # --- 右側：操作パネル ---
        right_frame = tk.Frame(self, width=350)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        # プレビュー
        tk.Label(right_frame, text="プレビュー").pack(pady=(0, 5))
        self.preview_canvas = tk.Canvas(right_frame, width=128, height=128, bg="black")
        self.preview_canvas.pack()

        self.lbl_snum = tk.Label(right_frame, text="スプライト番号: -", font=("Arial", 12, "bold"))
        self.lbl_snum.pack(pady=10)

        # サイズ設定 (手入力 + プリセット)
        size_frame = tk.LabelFrame(right_frame, text="サイズ設定 (幅x高さ)")
        size_frame.pack(fill=tk.X, pady=5)
        
        self.size_var = tk.StringVar(value="16x16")
        self.size_combo = ttk.Combobox(size_frame, textvariable=self.size_var, values=["16x16", "16x32", "32x32", "32x16", "64x64"], width=15)
        self.size_combo.pack(side=tk.LEFT, padx=5, pady=5)
        self.size_combo.bind("<<ComboboxSelected>>", lambda e: self.update_preview())
        self.size_combo.bind("<Return>", lambda e: self.update_preview()) # Enterキーでも適用
        
        btn_apply_size = tk.Button(size_frame, text="適用", command=self.update_preview)
        btn_apply_size.pack(side=tk.LEFT, padx=5, pady=5)

        # カテゴリ登録 (キャラ名 + 状態)
        cat_frame = tk.LabelFrame(right_frame, text="データ登録")
        cat_frame.pack(fill=tk.X, pady=10)

        # キャラ名 (自由入力 or 選択)
        tk.Label(cat_frame, text="キャラ名:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        self.entry_name = ttk.Combobox(cat_frame, values=["マリオ(チビ)", "マリオ(デカ)", "マリオ(ファイア)", "クリボー", "ノコノコ", "アイテム"])
        self.entry_name.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)

        # 状態 (自由入力 or 選択)
        tk.Label(cat_frame, text="状態:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
        self.state_combo = ttk.Combobox(cat_frame, values=["右", "左", "正面", "ジャンプ", "待機", "歩き1", "歩き2"])
        self.state_combo.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        self.state_combo.set("右")
        
        btn_register = tk.Button(cat_frame, text="リストに登録/更新", command=self.register_sprite)
        btn_register.grid(row=2, column=0, columnspan=3, pady=10)

        # 登録済みリスト
        tk.Label(right_frame, text="登録済みリスト (キャラ名順でソート)").pack(anchor=tk.W, pady=(10, 0))
        columns = ("snum", "name", "state", "size")
        self.tree = ttk.Treeview(right_frame, columns=columns, show="headings", height=10)
        self.tree.heading("snum", text="番号")
        self.tree.heading("name", text="キャラ名")
        self.tree.heading("state", text="状態")
        self.tree.heading("size", text="サイズ")
        self.tree.column("snum", width=40)
        self.tree.column("name", width=120)
        self.tree.column("state", width=60)
        self.tree.column("size", width=60)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # 削除ボタンエリア
        btn_action_frame = tk.Frame(right_frame)
        btn_action_frame.pack(fill=tk.X, pady=5)
        
        btn_delete = tk.Button(btn_action_frame, text="選択した項目を削除", command=self.delete_sprite)
        btn_delete.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        
        btn_clear = tk.Button(btn_action_frame, text="全件クリア", command=self.clear_sprites, fg="red")
        btn_clear.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(2, 0))

    def load_image(self):
        filepath = filedialog.askopenfilename(filetypes=[("PNG files", "*.png")])
        if not filepath: return

        self.sprite_image = Image.open(filepath).convert("RGBA")
        self.tk_image = ImageTk.PhotoImage(self.sprite_image)
        self.canvas.config(scrollregion=(0, 0, self.sprite_image.width, self.sprite_image.height))
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        
        self.draw_grid()
        self.auto_detect_sprites()

    def draw_grid(self):
        self.canvas.delete("grid")
        w, h = self.sprite_image.width, self.sprite_image.height
        for x in range(0, w, self.grid_size):
            self.canvas.create_line(x, 0, x, h, fill="#555555", tags="grid")
        for y in range(0, h, self.grid_size):
            self.canvas.create_line(0, y, w, y, fill="#555555", tags="grid")

    def auto_detect_sprites(self):
        w, h = self.sprite_image.width, self.sprite_image.height
        rows = h // self.grid_size
        self.canvas.delete("highlight_valid")
        for r in range(rows):
            for c in range(self.cols):
                box = (c * self.grid_size, r * self.grid_size, (c + 1) * self.grid_size, (r + 1) * self.grid_size)
                region = self.sprite_image.crop(box)
                alpha = region.split()[-1]
                if alpha.getextrema()[1] > 0:
                    x1, y1 = box[0], box[1]
                    self.canvas.create_rectangle(x1, y1, x1+16, y1+16, outline="green", tags="highlight_valid")

    def on_canvas_click(self, event):
        if not self.sprite_image: return
        col = int(self.canvas.canvasx(event.x)) // self.grid_size
        row = int(self.canvas.canvasy(event.y)) // self.grid_size
        if col >= self.cols: return
        self.selected_snum = row * self.cols + col
        self.lbl_snum.config(text=f"スプライト番号: {self.selected_snum}")
        self.update_preview()

    def update_preview(self):
        if not self.sprite_image: return
        
        size_str = self.size_var.get().lower().replace(' ', '')
        try:
            self.current_w, self.current_h = map(int, size_str.split('x'))
        except ValueError:
            messagebox.showwarning("サイズエラー", "サイズは「幅x高さ」の形式で入力してください。(例: 16x16)")
            return

        sx = (self.selected_snum & 15) << 4
        sy = (self.selected_snum >> 4) << 4
        box = (sx, sy, sx + self.current_w, sy + self.current_h)
        
        if box[2] > self.sprite_image.width or box[3] > self.sprite_image.height: return
        region = self.sprite_image.crop(box)
        
        # プレビュー表示用にスケーリング (最大128pxに収める)
        max_dim = max(self.current_w, self.current_h)
        scale = max(1, 128 // max_dim)
        preview_img = region.resize((self.current_w * scale, self.current_h * scale), Image.NEAREST)
        self.preview_tk = ImageTk.PhotoImage(preview_img)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(64, 64, anchor=tk.CENTER, image=self.preview_tk)

        self.canvas.delete("select_box")
        self.canvas.create_rectangle(sx, sy, sx + self.current_w, sy + self.current_h, outline="red", width=2, tags="select_box")

    def register_sprite(self):
        if not self.sprite_image: return
        name = self.entry_name.get()
        if not name:
            messagebox.showwarning("警告", "キャラ名を入力してください。")
            return

        state = self.state_combo.get()
        size_str = self.size_var.get().lower().replace(' ', '')
        
        self.registered_sprites[str(self.selected_snum)] = {
            "name": name,
            "state": state,
            "size": size_str
        }
        self.update_tree()

    def update_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # キャラ名でソートし、同じキャラ名ならスプライト番号順にする
        sorted_items = sorted(
            self.registered_sprites.items(), 
            key=lambda x: (x[1]["name"], int(x[0]))
        )
        
        for snum_str, data in sorted_items:
            self.tree.insert("", tk.END, iid=snum_str, values=(snum_str, data["name"], data["state"], data["size"]))

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected: return
        
        snum_str = selected[0]
        data = self.registered_sprites[snum_str]
        
        self.selected_snum = int(snum_str)
        self.lbl_snum.config(text=f"スプライト番号: {self.selected_snum}")
        self.size_var.set(data["size"])
        self.entry_name.set(data["name"])
        self.state_combo.set(data["state"])
        
        self.update_preview()

    def delete_sprite(self):
        selected = self.tree.selection()
        if not selected: return
        snum_str = selected[0]
        del self.registered_sprites[snum_str]
        self.update_tree()

    def clear_sprites(self):
        if not self.registered_sprites: return
        if messagebox.askyesno("確認", "登録済みリストをすべて削除しますか？"):
            self.registered_sprites.clear()
            self.update_tree()

    def export_data(self):
        if not self.registered_sprites:
            messagebox.showinfo("情報", "エクスポートするデータがありません。")
            return
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.registered_sprites, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("完了", "データを保存しました。")

    def import_data(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    
                    # 古いバージョン(dir)のJSONフォーマットを新しいバージョン(state)に自動変換
                    for key, val in loaded_data.items():
                        if "dir" in val:
                            val["state"] = val.pop("dir")
                            
                    self.registered_sprites = loaded_data
                    
                self.update_tree()
                messagebox.showinfo("完了", "データを読み込みました。")
            except Exception as e:
                messagebox.showerror("エラー", f"ファイルの読み込みに失敗しました:\n{e}")

if __name__ == "__main__":
    app = SpriteExtractorApp()
    app.mainloop()