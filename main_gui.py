import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import tkinter as tk
from gui.app import SecurityApp


def main():
    root = tk.Tk()
    SecurityApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
