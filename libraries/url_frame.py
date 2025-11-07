from tkinter import ttk

class URLFrame():
    def __init__(self, label: str, variable, parent):
        self.label = label
        self.variable = variable
        self.parent = parent
        self.set_up_tab()
    
    def set_up_tab(self):
        self.config_frame = ttk.Frame(self.parent)

        self.url_lbl = ttk.Label(self.config_frame, text=self.label)
        self.url_lbl.pack(side='left', padx=5, pady=5)

        self.url = ttk.Entry(self.config_frame, textvariable=self.variable)
        self.url.pack(side='left', fill='x', padx=(0,5), expand=True)

        self.config_frame.pack(anchor='nw', fill='x', expand=True)
